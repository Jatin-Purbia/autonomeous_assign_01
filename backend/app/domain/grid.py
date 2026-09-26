"""Warehouse grid, timed positions and the dynamic-obstacle index.

Coordinates: ``x`` grows east, ``y`` grows south (row index), origin top-left.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, NamedTuple, Optional


class Position(NamedTuple):
    x: int
    y: int

    def __repr__(self) -> str:  # compact for logs
        return f"({self.x},{self.y})"


class TimedPosition(NamedTuple):
    position: Position
    time: int


# Move deltas: north, south, east, west (y grows southwards). Wait is (0, 0).
MOVES: tuple[tuple[int, int], ...] = ((0, -1), (0, 1), (1, 0), (-1, 0))


def manhattan(a: Position, b: Position) -> int:
    return abs(a.x - b.x) + abs(a.y - b.y)


class CellState(str, Enum):
    FREE = "free"
    STATIC_OBSTACLE = "static_obstacle"
    DYNAMIC_OBSTACLE = "dynamic_obstacle"
    PICKUP = "pickup"
    DELIVERY = "delivery"
    ROBOT = "robot"
    RESERVED = "reserved"
    BROKEN_ROBOT = "broken_robot"


@dataclass
class Grid:
    """Finite 2D grid G=(V,E). V = in-bounds cells that are not static obstacles."""

    width: int
    height: int
    static_obstacles: frozenset[Position] = field(default_factory=frozenset)
    _dist_cache: dict = field(default_factory=dict, repr=False, compare=False)

    def in_bounds(self, p: Position) -> bool:
        return 0 <= p.x < self.width and 0 <= p.y < self.height

    def is_traversable(self, p: Position) -> bool:
        return self.in_bounds(p) and p not in self.static_obstacles

    def neighbors(self, p: Position) -> list[Position]:
        out = []
        for dx, dy in MOVES:
            q = Position(p.x + dx, p.y + dy)
            if self.is_traversable(q):
                out.append(q)
        return out

    def traversable_cells(self) -> list[Position]:
        return [
            Position(x, y)
            for y in range(self.height)
            for x in range(self.width)
            if Position(x, y) not in self.static_obstacles
        ]

    @property
    def traversable_count(self) -> int:
        return self.width * self.height - len(self.static_obstacles)

    def bfs_distances(self, source: Position) -> dict[Position, int]:
        """Static shortest-path distances (ignores dynamic obstacles/robots)."""
        dist = {source: 0}
        q = deque([source])
        while q:
            u = q.popleft()
            for v in self.neighbors(u):
                if v not in dist:
                    dist[v] = dist[u] + 1
                    q.append(v)
        return dist

    def distance_map(self, source: Position) -> dict[Position, int]:
        """Cached static BFS distances from ``source``."""
        d = self._dist_cache.get(source)
        if d is None:
            d = self.bfs_distances(source)
            self._dist_cache[source] = d
        return d

    def reachable(self, a: Position, b: Position) -> bool:
        return b in self.distance_map(a)

    @staticmethod
    def from_ascii(rows: Iterable[str]) -> "Grid":
        rows = list(rows)
        obstacles = set()
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == "#":
                    obstacles.add(Position(x, y))
        return Grid(len(rows[0]), len(rows), frozenset(obstacles))


@dataclass
class DynamicObstacle:
    """A cell blocked during [start_time, end_time] (inclusive). ``end_time=None`` is permanent.

    ``owner_robot_id`` is set for cells blocked by a broken robot.
    """

    obstacle_id: str
    position: Position
    start_time: int
    end_time: Optional[int] = None
    owner_robot_id: Optional[str] = None

    def blocks(self, t: int) -> bool:
        return t >= self.start_time and (self.end_time is None or t <= self.end_time)

    def active_at(self, t: int) -> bool:
        return self.blocks(t)


class ObstacleMap:
    """Index of dynamic obstacles known to the system (activated so far)."""

    def __init__(self) -> None:
        self._by_cell: dict[Position, list[DynamicObstacle]] = {}
        self._by_id: dict[str, DynamicObstacle] = {}

    def add(self, obs: DynamicObstacle) -> None:
        self._by_cell.setdefault(obs.position, []).append(obs)
        self._by_id[obs.obstacle_id] = obs

    def remove(self, obstacle_id: str) -> Optional[DynamicObstacle]:
        obs = self._by_id.pop(obstacle_id, None)
        if obs:
            self._by_cell[obs.position].remove(obs)
            if not self._by_cell[obs.position]:
                del self._by_cell[obs.position]
        return obs

    def get(self, obstacle_id: str) -> Optional[DynamicObstacle]:
        return self._by_id.get(obstacle_id)

    def is_blocked(self, p: Position, t: int) -> bool:
        lst = self._by_cell.get(p)
        if not lst:
            return False
        for o in lst:
            if o.blocks(t):
                return True
        return False

    def blocked_ever_after(self, p: Position, t: int) -> bool:
        """True if ``p`` is blocked at some time >= t."""
        for o in self._by_cell.get(p, ()):
            if o.end_time is None or o.end_time >= t:
                return True
        return False

    def all(self) -> list[DynamicObstacle]:
        return list(self._by_id.values())

    def active_at(self, t: int) -> list[DynamicObstacle]:
        return [o for o in self._by_id.values() if o.blocks(t)]

    def latest_finite_end(self) -> int:
        ends = [o.end_time for o in self._by_id.values() if o.end_time is not None]
        return max(ends) if ends else 0

    def copy(self) -> "ObstacleMap":
        m = ObstacleMap()
        for o in self._by_id.values():
            m.add(o)
        return m

    def __len__(self) -> int:
        return len(self._by_id)
