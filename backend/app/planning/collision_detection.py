"""Conflict detection between complete plans (used for validation and the conflict graph)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

from ..domain.grid import ObstacleMap, Position, TimedPosition


@dataclass(frozen=True)
class Conflict:
    kind: str  # "vertex" | "edge_swap" | "obstacle"
    robots: tuple[str, ...]
    time: int
    position: Position
    other_position: Optional[Position] = None


def _pos(plan: Sequence[TimedPosition], t: int) -> Optional[Position]:
    return plan[t].position if 0 <= t < len(plan) else None


def find_conflicts(
    plans: Mapping[str, Sequence[TimedPosition]],
    from_time: int = 0,
    obstacles: Optional[ObstacleMap] = None,
    limit: Optional[int] = None,
    persistent: Optional[Mapping[str, Position]] = None,
) -> list[Conflict]:
    """All vertex and edge-swap conflicts at times >= from_time.

    Robots are assumed to leave the grid after their plan ends (no conflicts afterwards).
    ``persistent`` maps robot ids (broken robots) to the cell they occupy forever.
    """
    out: list[Conflict] = []
    occupancy: dict[tuple[Position, int], str] = {}
    for rid, plan in plans.items():
        for tp in plan:
            if tp.time < from_time:
                continue
            key = (tp.position, tp.time)
            other = occupancy.get(key)
            if other is not None and other != rid:
                out.append(Conflict("vertex", (other, rid), tp.time, tp.position))
                if limit and len(out) >= limit:
                    return out
            else:
                occupancy[key] = rid
            if obstacles is not None and tp.time > from_time - 1 and obstacles.is_blocked(tp.position, tp.time):
                # a robot standing on its own broken cell is not an obstacle violation
                if not (persistent and persistent.get(rid) == tp.position):
                    out.append(Conflict("obstacle", (rid,), tp.time, tp.position))
    # edge swaps
    moves: dict[tuple[Position, Position, int], str] = {}
    for rid, plan in plans.items():
        for i in range(len(plan) - 1):
            a, b = plan[i], plan[i + 1]
            if a.time < from_time or a.position == b.position:
                continue
            moves[(a.position, b.position, a.time)] = rid
    for (u, v, t), rid in moves.items():
        other = moves.get((v, u, t))
        if other is not None and other != rid and rid < other:
            out.append(Conflict("edge_swap", (rid, other), t, u, v))
            if limit and len(out) >= limit:
                return out
    return out


def has_conflicts(plans: Mapping[str, Sequence[TimedPosition]], from_time: int = 0,
                  obstacles: Optional[ObstacleMap] = None) -> bool:
    return bool(find_conflicts(plans, from_time, obstacles, limit=1))


def check_adjacent_steps(plan: Sequence[TimedPosition]) -> bool:
    """Every step is a wait or a unit N/S/E/W move and times are consecutive."""
    for a, b in zip(plan, plan[1:]):
        if b.time != a.time + 1:
            return False
        if abs(a.position.x - b.position.x) + abs(a.position.y - b.position.y) > 1:
            return False
    return True
