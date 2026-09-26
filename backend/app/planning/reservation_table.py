"""Space-time reservation table.

* Vertex reservations  R_V(v, t):  robot occupies cell v at time t.
* Edge reservations    R_E(u, v, t): robot moves u -> v during the interval [t, t+1].

A move u->v at time t is rejected when another robot holds R_E(v, u, t) (edge swap).
"""
from __future__ import annotations

from typing import Iterable, Optional

from ..domain.grid import Position, TimedPosition


class ReservationTable:
    def __init__(self) -> None:
        self.vertex: dict[Position, dict[int, str]] = {}
        self.edge: dict[tuple[Position, Position, int], str] = {}
        self._v_by_robot: dict[str, list[tuple[Position, int]]] = {}
        self._e_by_robot: dict[str, list[tuple[Position, Position, int]]] = {}
        self.max_time = 0

    # -- queries ------------------------------------------------------------------
    def vertex_owner(self, pos: Position, t: int) -> Optional[str]:
        d = self.vertex.get(pos)
        return d.get(t) if d else None

    def is_vertex_free(self, pos: Position, t: int, robot_id: Optional[str] = None) -> bool:
        owner = self.vertex_owner(pos, t)
        return owner is None or owner == robot_id

    def is_edge_free(self, u: Position, v: Position, t: int, robot_id: Optional[str] = None) -> bool:
        """Is the move u->v during [t, t+1] free of a head-on swap?"""
        if u == v:
            return True
        owner = self.edge.get((v, u, t))
        return owner is None or owner == robot_id

    def can_move(self, u: Position, v: Position, t: int, robot_id: Optional[str] = None) -> bool:
        """Check the transition u@t -> v@t+1 (v may equal u for a wait)."""
        return self.is_vertex_free(v, t + 1, robot_id) and self.is_edge_free(u, v, t, robot_id)

    def robot_ids(self) -> list[str]:
        return list(self._v_by_robot)

    # -- mutation -----------------------------------------------------------------
    def reserve_path(self, robot_id: str, path: Iterable[TimedPosition], from_time: int = 0) -> None:
        """Reserve every vertex (time >= from_time) and every edge departing at time >= from_time."""
        vs = self._v_by_robot.setdefault(robot_id, [])
        es = self._e_by_robot.setdefault(robot_id, [])
        prev: Optional[TimedPosition] = None
        for tp in path:
            if tp.time >= from_time:
                self.vertex.setdefault(tp.position, {})[tp.time] = robot_id
                vs.append((tp.position, tp.time))
                if tp.time > self.max_time:
                    self.max_time = tp.time
                if prev is not None and prev.position != tp.position and prev.time >= from_time:
                    key = (prev.position, tp.position, prev.time)
                    self.edge[key] = robot_id
                    es.append(key)
            prev = tp

    def release_robot(self, robot_id: str, after_time: int = -1) -> None:
        """Drop reservations of the robot for vertex times > after_time and edges departing >= after_time."""
        vs = self._v_by_robot.get(robot_id, [])
        keep_v = []
        for pos, t in vs:
            if t > after_time:
                d = self.vertex.get(pos)
                if d is not None and d.get(t) == robot_id:
                    del d[t]
                    if not d:
                        del self.vertex[pos]
            else:
                keep_v.append((pos, t))
        self._v_by_robot[robot_id] = keep_v
        es = self._e_by_robot.get(robot_id, [])
        keep_e = []
        for key in es:
            if key[2] >= after_time:
                if self.edge.get(key) == robot_id:
                    del self.edge[key]
            else:
                keep_e.append(key)
        self._e_by_robot[robot_id] = keep_e

    def copy(self) -> "ReservationTable":
        c = ReservationTable()
        c.vertex = {p: dict(d) for p, d in self.vertex.items()}
        c.edge = dict(self.edge)
        c._v_by_robot = {r: list(v) for r, v in self._v_by_robot.items()}
        c._e_by_robot = {r: list(v) for r, v in self._e_by_robot.items()}
        c.max_time = self.max_time
        return c
