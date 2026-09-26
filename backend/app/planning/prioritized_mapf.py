"""Prioritized multi-agent planning (initial planning only, never used for ordinary repair).

Robots are planned one at a time in descending ``planning_priority``.  After a robot is planned
its complete path is reserved before the next robot is planned.  If some robot cannot be planned,
a limited number of deterministic priority-order retries is attempted (failed robot is bumped to
the front, then seeded shuffles).
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from ..domain.grid import Grid, ObstacleMap, TimedPosition
from ..domain.robot import Robot, make_plan
from .reservation_table import ReservationTable
from .space_time_astar import PlanningContext, space_time_astar


@dataclass
class InitialPlanResult:
    success: bool
    plans: dict[str, list[TimedPosition]] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    retries: int = 0
    failed_robot: Optional[str] = None
    failure_reason: Optional[str] = None
    runtime_ms: float = 0.0
    expansions: int = 0
    phase: str = "INITIAL_PLANNING"  # distinguishes this from disruption repair


def default_order(robots: Sequence[Robot]) -> list[str]:
    return [r.robot_id for r in sorted(robots, key=lambda r: (-r.planning_priority, r.robot_id))]


def _attempt(grid: Grid, obstacles: ObstacleMap, robots: Mapping[str, Robot], order: Sequence[str]):
    table = ReservationTable()
    ctx = PlanningContext(grid, obstacles, table)
    plans: dict[str, list[TimedPosition]] = {}
    expansions = 0
    for rid in order:
        r = robots[rid]
        wps = [w.position for w in r.remaining_waypoints()]
        res = space_time_astar(ctx, rid, r.current_position, 0, wps)
        expansions += res.expansions
        if not res.found:
            return None, rid, res.failure, expansions
        plan = make_plan(res.path, 0)
        table.reserve_path(rid, plan)
        plans[rid] = plan
    return plans, None, None, expansions


def plan_all(
    grid: Grid,
    robots: Sequence[Robot],
    obstacles: Optional[ObstacleMap] = None,
    max_retries: int = 5,
    seed: int = 0,
    order: Optional[Sequence[str]] = None,
) -> InitialPlanResult:
    t0 = time.perf_counter()
    obstacles = obstacles or ObstacleMap()
    by_id = {r.robot_id: r for r in robots}
    cur_order = list(order) if order else default_order(robots)
    rng = random.Random(seed)
    total_exp = 0
    last_fail: Optional[str] = None
    last_reason: Optional[str] = None
    for attempt in range(max_retries + 1):
        plans, failed, reason, exp = _attempt(grid, obstacles, by_id, cur_order)
        total_exp += exp
        if plans is not None:
            return InitialPlanResult(True, plans, cur_order, attempt, None, None,
                                     (time.perf_counter() - t0) * 1000, total_exp)
        last_fail, last_reason = failed, reason
        if reason == "unreachable":
            break  # a static/permanent obstacle makes a task impossible: reordering cannot help
        if attempt == 0 or rng.random() < 0.5:
            cur_order = [failed] + [r for r in cur_order if r != failed]  # bump the failed robot
        else:
            cur_order = list(cur_order)
            rng.shuffle(cur_order)
    return InitialPlanResult(False, {}, cur_order, min(attempt + 1, max_retries), last_fail, last_reason,
                             (time.perf_counter() - t0) * 1000, total_exp)


def apply_initial_plans(robots: Sequence[Robot], result: InitialPlanResult) -> None:
    """Install computed plans on robots (original plan is frozen for later comparison)."""
    for r in robots:
        plan = result.plans[r.robot_id]
        r.original_plan = list(plan)
        r.active_plan = list(plan)
        r.executed_prefix = [plan[0]]
        r.current_position = plan[0].position
