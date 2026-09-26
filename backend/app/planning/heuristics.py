"""Admissible heuristics and waypoint-progress helpers shared by planner, repair and engine."""
from __future__ import annotations

from typing import Optional, Sequence

from ..domain.grid import Position, manhattan


def advance_waypoints(q: int, pos: Position, waypoints: Sequence[Position]) -> int:
    """Waypoint index after standing on ``pos``.

    Arrival at the *next* required waypoint completes it (pickup/delivery is instantaneous);
    consecutive waypoints on the same cell all complete together.  Visiting a later waypoint's
    cell early does not count, which enforces pickup-before-delivery ordering.
    """
    n = len(waypoints)
    while q < n and waypoints[q] == pos:
        q += 1
    return q


def chain_tail(waypoints: Sequence[Position]) -> list[int]:
    """tail[q] = sum of Manhattan distances between waypoints q, q+1, ..., n-1 (tail[n]=0)."""
    n = len(waypoints)
    tail = [0] * (n + 1)
    for q in range(n - 2, -1, -1):
        tail[q] = tail[q + 1] + manhattan(waypoints[q], waypoints[q + 1])
    return tail


def chain_heuristic(pos: Position, q: int, waypoints: Sequence[Position], tail: Sequence[int]) -> int:
    """h(n) = |pos - w_q| + sum of remaining leg lengths.  Admissible and consistent."""
    if q >= len(waypoints):
        return 0
    return manhattan(pos, waypoints[q]) + tail[q]


def waypoint_times(positions: Sequence[Position], start_time: int, waypoints: Sequence[Position],
                   q0: int = 0) -> tuple[list[Optional[int]], int]:
    """Simulate waypoint progress along a path.

    Returns (arrival time for every waypoint (None if not reached), final q).
    """
    times: list[Optional[int]] = [None] * len(waypoints)
    q = q0
    for i, pos in enumerate(positions):
        nq = advance_waypoints(q, pos, waypoints)
        for k in range(q, nq):
            times[k] = start_time + i
        q = nq
    return times, q


def completes_waypoints(positions: Sequence[Position], waypoints: Sequence[Position]) -> bool:
    return waypoint_times(positions, 0, waypoints)[1] == len(waypoints)
