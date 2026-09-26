"""Single-agent Space-Time A* over states n = (x, y, t, q).

* (x, y)  grid cell
* t       timestep
* q       index of the next waypoint (task progress: pickup, delivery, pickup, ...)

f(n) = g(n) + h(n), g(n) = t - t_start (each move or wait costs one step) and
h(n) = Manhattan distance to the next waypoint plus the distances through the remaining ordered
waypoints (admissible and consistent).  Waiting is allowed.  Robots leave the workspace at
their final waypoint, so the goal test is simply q == len(waypoints).
"""
from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Sequence

from ..domain.grid import MOVES, Grid, ObstacleMap, Position
from .heuristics import advance_waypoints, chain_heuristic, chain_tail
from .reservation_table import ReservationTable


@dataclass
class PlanningContext:
    """Everything the planner must respect: static map, dynamic obstacles, reservations."""

    grid: Grid
    obstacles: ObstacleMap
    table: ReservationTable

    def can_step(self, u: Position, v: Position, t: int, robot_id: Optional[str]) -> bool:
        """May ``robot_id`` go from u@t to v@t+1 (v == u is a wait)?"""
        if not self.grid.is_traversable(v):
            return False
        if self.obstacles.is_blocked(v, t + 1):
            return False
        return self.table.can_move(u, v, t, robot_id)

    def horizon_for(self, start_time: int, static_len: int) -> int:
        latest = max(self.table.max_time, self.obstacles.latest_finite_end(), start_time)
        return max(start_time + 2 * static_len + 40, latest + static_len + 10)


@dataclass
class SoftConstraints:
    """Reservations that may be violated at a price (used to find an 'ideal' route that disturbs
    as few neighbours as possible).  Each step that conflicts with ``table`` costs ``penalty`` extra."""

    table: ReservationTable
    penalty: float = 10.0


@dataclass
class SearchResult:
    path: Optional[list[Position]]  # positions at times start_time, start_time+1, ...
    expansions: int = 0
    failure: Optional[str] = None  # "unreachable" | "no_path" | "expansion_limit"

    @property
    def found(self) -> bool:
        return self.path is not None


def _permanent_blocked(ctx: PlanningContext) -> set[Position]:
    return {o.position for o in ctx.obstacles.all() if o.end_time is None}


def statically_reachable(ctx: PlanningContext, start: Position, waypoints: Sequence[Position]) -> bool:
    """Cheap necessary condition: every leg is connected ignoring finite obstacles/robots."""
    banned = _permanent_blocked(ctx)
    legs = [start, *waypoints]
    for a, b in zip(legs, legs[1:]):
        if a == b:
            continue
        if b in banned:
            return False
        seen = {a}
        dq = deque([a])
        found = False
        while dq and not found:
            u = dq.popleft()
            for v in ctx.grid.neighbors(u):
                if v not in seen and v not in banned:
                    if v == b:
                        found = True
                        break
                    seen.add(v)
                    dq.append(v)
        if not found:
            return False
    return True


def static_path_length(grid: Grid, start: Position, waypoints: Sequence[Position]) -> int:
    total, cur = 0, start
    for w in waypoints:
        d = grid.distance_map(cur).get(w)
        if d is None:
            return 10 ** 6
        total += d
        cur = w
    return total


def space_time_astar(
    ctx: PlanningContext,
    robot_id: Optional[str],
    start: Position,
    start_time: int,
    waypoints: Sequence[Position],
    *,
    horizon: Optional[int] = None,
    max_expansions: int = 400_000,
    soft: Optional[SoftConstraints] = None,
) -> SearchResult:
    """Earliest-completion collision-free path visiting ``waypoints`` in order.

    Returns positions for times start_time, start_time+1, ... (the first entry is ``start``).
    """
    waypoints = list(waypoints)
    q0 = advance_waypoints(0, start, waypoints)
    if q0 == len(waypoints):
        return SearchResult([start])
    if not statically_reachable(ctx, start, waypoints):
        return SearchResult(None, 0, "unreachable")
    tail = chain_tail(waypoints)
    if horizon is None:
        horizon = ctx.horizon_for(start_time, static_path_length(ctx.grid, start, waypoints))

    n = len(waypoints)
    h0 = chain_heuristic(start, q0, waypoints, tail)
    counter = 0
    open_heap: list[tuple[float, int, int, int, int, int, int, float]] = []
    heapq.heappush(open_heap, (start_time + h0, h0, counter, start.x, start.y, start_time, q0, 0.0))
    first = (start.x, start.y, start_time, q0)
    parent: dict[tuple[int, int, int, int], Optional[tuple[int, int, int, int]]] = {first: None}
    best_g: dict[tuple[int, int, int, int], float] = {first: 0.0}
    closed: set[tuple[int, int, int, int]] = set()
    expansions = 0
    while open_heap:
        _, _, _, x, y, t, q, g = heapq.heappop(open_heap)
        state = (x, y, t, q)
        if state in closed:
            continue
        closed.add(state)
        if q == n:
            path: list[Position] = []
            cur: Optional[tuple[int, int, int, int]] = state
            while cur is not None:
                path.append(Position(cur[0], cur[1]))
                cur = parent[cur]
            path.reverse()
            return SearchResult(path, expansions)
        expansions += 1
        if expansions > max_expansions:
            return SearchResult(None, expansions, "expansion_limit")
        if t >= horizon:
            continue
        u = Position(x, y)
        for dx, dy in ((0, 0), *MOVES):
            v = Position(x + dx, y + dy)
            if not ctx.can_step(u, v, t, robot_id):
                continue
            nq = advance_waypoints(q, v, waypoints)
            ns = (v.x, v.y, t + 1, nq)
            if ns in closed:
                continue
            ng = g + 1.0
            if soft is not None and not soft.table.can_move(u, v, t, robot_id):
                ng += soft.penalty
            if ng >= best_g.get(ns, float("inf")):
                continue
            best_g[ns] = ng
            parent[ns] = state
            h = chain_heuristic(v, nq, waypoints, tail)
            counter += 1
            heapq.heappush(open_heap, (ng + h, h, counter, v.x, v.y, t + 1, nq, ng))
    return SearchResult(None, expansions, "no_path")
