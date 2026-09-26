"""Turns a disruption into a repair problem and runs the selected strategy.

Strategies
    "local"         proposed incremental negotiated repair (Baseline B, the normal mechanism)
    "single_agent"  Baseline A: only directly affected robots replan; a conflict with an unchanged plan is a failure
    "global"        Baseline C (experimental only): every remaining path is recomputed
"""
from __future__ import annotations

from dataclasses import replace
from typing import Optional

from ..domain.disruption import Disruption, DisruptionType
from ..domain.grid import DynamicObstacle
from ..domain.robot import RobotStatus
from .affected_set import find_directly_invalidated
from .local_repair import RepairSession, global_replan
from .models import RepairContext, RepairResult
from .task_reassignment import NoCapableRobot, insert_emergency, reassign_unfinished

STRATEGIES = ("local", "single_agent", "global")


def _make_session(ctx: RepairContext, strategy: str, reason: str) -> RepairSession:
    if strategy == "single_agent":
        cfg = replace(ctx.config, allow_negotiation=False, allow_expansion=False)
        ctx = RepairContext(ctx.grid, ctx.robots, ctx.obstacles, ctx.table, ctx.time, cfg, ctx.emit)
    return RepairSession(ctx, strategy, reason)


def _fail(ctx: RepairContext, strategy: str, reason: str, direct: Optional[dict[str, str]] = None) -> RepairResult:
    return RepairResult(False, strategy, reason, direct=sorted(direct or {}))


def apply_disruption(ctx: RepairContext, d: Disruption, strategy: str = "local") -> RepairResult:
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}")
    t = ctx.time
    forced: dict = {}
    base_wps: dict = {}
    full: set = set()
    deps: list = []
    reassignments: list = []
    direct: dict[str, str] = {}
    priority_updates: list[tuple[str, int]] = []

    if d.type == DisruptionType.CELL_BLOCKAGE:
        pos = d.affected_position
        if pos is None or not ctx.grid.is_traversable(pos):
            raise ValueError("cell blockage needs a traversable cell")
        end = None if d.duration is None else t + d.duration
        ctx.obstacles.add(DynamicObstacle(f"OBS-{d.disruption_id}", pos, t, end))
        direct = find_directly_invalidated(ctx.robots, ctx.obstacles, t)
        reason = "DYNAMIC_CELL_BLOCKAGE"

    elif d.type == DisruptionType.ROBOT_BREAKDOWN:
        robot = ctx.robots.get(d.affected_robot_id or "")
        if robot is None:
            raise ValueError(f"unknown robot {d.affected_robot_id}")
        if not robot.on_grid or robot.status in (RobotStatus.BROKEN, RobotStatus.DONE):
            raise ValueError(f"robot {robot.robot_id} is not running")
        before = {rid: [w.position for w in r.remaining_waypoints()] for rid, r in ctx.robots.items()}
        robot.status = RobotStatus.BROKEN
        robot.broken_at = t
        ctx.obstacles.add(DynamicObstacle(f"BRK-{robot.robot_id}", robot.current_position, t, None,
                                          owner_robot_id=robot.robot_id))
        forced[robot.robot_id] = list(robot.active_plan[: t + 1])   # executed prefix preserved, future dropped
        try:
            reassignments = reassign_unfinished(ctx, robot)
        except NoCapableRobot as exc:
            return _fail(ctx, strategy, str(exc))
        for rec in reassignments:
            rid = rec["to"]
            base_wps.setdefault(rid, before[rid])
            direct[rid] = f"received reassigned task {rec['task_id']} from {robot.robot_id}"
            deps.append((robot.robot_id, rid, f"task {rec['task_id']} reassigned"))
        for rid, why in find_directly_invalidated(ctx.robots, ctx.obstacles, t).items():
            direct.setdefault(rid, why)
        reason = "ROBOT_BREAKDOWN"

    elif d.type == DisruptionType.EMERGENCY_TASK:
        if d.emergency_task is None:
            raise ValueError("emergency disruption needs a task")
        try:
            robot, rec = insert_emergency(ctx, d.emergency_task, d.affected_robot_id)
        except NoCapableRobot as exc:
            return _fail(ctx, strategy, str(exc))
        reassignments = [rec]
        full.add(robot.robot_id)
        direct[robot.robot_id] = f"assigned emergency task {d.emergency_task.task_id}"
        priority_updates.append((robot.robot_id, robot.planning_priority))
        reason = "EMERGENCY_TASK"
    else:  # pragma: no cover
        raise ValueError(f"unsupported disruption {d.type}")

    if strategy == "global":
        res = global_replan(ctx, direct, forced, reassignments, reason)
        for rid, prio in priority_updates:
            pass
        return res
    session = _make_session(ctx, strategy, reason)
    session.base_wps, session.full_replan, session.forced_plans = base_wps, full, forced
    session.dependencies, session.reassignments = deps, reassignments
    for rid, prio in priority_updates:  # VALUE/PRIORITY_UPDATE: coordinator raises the emergency robot's priority
        session.bus.send("PRIORITY_UPDATE", "COORDINATOR", rid, new_priority=prio, reason="emergency task")
    return session.run(direct)


def repair_invalidated(ctx: RepairContext, robot_ids: list[str], strategy: str = "local") -> RepairResult:
    """Safety-net repair for plans that turned out invalid at execution time (should not normally happen)."""
    direct = {rid: "next planned step is invalid at execution time" for rid in robot_ids}
    if strategy == "global":
        return global_replan(ctx, direct, {}, [], "PLAN_INVALIDATED")
    session = _make_session(ctx, strategy, "PLAN_INVALIDATED")
    return session.run(direct)
