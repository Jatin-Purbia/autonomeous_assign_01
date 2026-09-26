"""Validation of tentative repairs.  Nothing replaces an active plan before passing these checks."""
from __future__ import annotations

from typing import Mapping, Optional, Sequence

from ..domain.grid import ObstacleMap, Position, TimedPosition
from ..planning.collision_detection import Conflict, check_adjacent_steps, find_conflicts
from ..planning.heuristics import completes_waypoints
from ..planning.space_time_astar import PlanningContext


def first_invalid_index(pctx: PlanningContext, robot_id: str, positions: Sequence[Position], td: int) -> Optional[int]:
    """Index i>=1 of the first step (positions[i-1]@td+i-1 -> positions[i]@td+i) that is illegal
    against static/dynamic obstacles and the reservations in ``pctx.table``; None if all legal."""
    for i in range(1, len(positions)):
        u, v = positions[i - 1], positions[i]
        if abs(u.x - v.x) + abs(u.y - v.y) > 1:
            return i
        if not pctx.can_step(u, v, td + i - 1, robot_id):
            return i
    return None


def suffix_valid(pctx: PlanningContext, robot_id: str, positions: Sequence[Position], td: int,
                 required_waypoints: Optional[Sequence[Position]] = None) -> bool:
    if first_invalid_index(pctx, robot_id, positions, td) is not None:
        return False
    if required_waypoints is not None and not completes_waypoints(positions, required_waypoints):
        return False
    return True


def prefixes_preserved(old: Mapping[str, Sequence[TimedPosition]], new: Mapping[str, Sequence[TimedPosition]],
                       td: int) -> bool:
    """Executed prefixes (times <= td) are immutable."""
    for rid, plan in new.items():
        o = old.get(rid)
        if o is None:
            continue
        if [tp.position for tp in plan[: td + 1]] != [tp.position for tp in o[: td + 1]]:
            return False
    return True


def validate_all(plans: Mapping[str, Sequence[TimedPosition]], obstacles: ObstacleMap, td: int,
                 persistent: Optional[Mapping[str, Position]] = None) -> list[Conflict]:
    """Every remaining plan against every other plan and every active obstacle (times > td)."""
    bad_steps = [Conflict("adjacency", (rid,), 0, plan[0].position) for rid, plan in plans.items()
                 if not check_adjacent_steps(plan)]
    return bad_steps + find_conflicts(plans, from_time=td + 1, obstacles=obstacles, persistent=persistent)
