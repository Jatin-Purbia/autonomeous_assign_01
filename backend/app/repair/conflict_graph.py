"""Temporary conflict graph C = (A, E_C) over robots' remaining plans.

Edges:  vertex conflict | edge-swap conflict | shared-resource (same cell used within ``window`` steps)
        | dependency (breakdown / reassigned task).
Strong edges (vertex, edge_swap, dependency) define the *local component* around the disrupted robot.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence

from ..domain.grid import Position, TimedPosition
from ..planning.collision_detection import find_conflicts

STRONG = {"vertex", "edge_swap", "dependency"}


@dataclass
class ConflictEdge:
    a: str
    b: str
    kind: str
    time: Optional[int] = None
    position: Optional[Position] = None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"a": self.a, "b": self.b, "kind": self.kind, "time": self.time,
                "position": [self.position.x, self.position.y] if self.position else None, "note": self.note}


@dataclass
class ConflictGraph:
    nodes: list[str] = field(default_factory=list)
    edges: list[ConflictEdge] = field(default_factory=list)
    label: str = ""
    time: int = 0

    def neighbours(self, rid: str, kinds: Optional[set[str]] = None) -> set[str]:
        out = set()
        for e in self.edges:
            if kinds is not None and e.kind not in kinds:
                continue
            if e.a == rid:
                out.add(e.b)
            elif e.b == rid:
                out.add(e.a)
        return out

    def to_dict(self, affected: Optional[Iterable[str]] = None, direct: Optional[Iterable[str]] = None) -> dict[str, Any]:
        return {"label": self.label, "time": self.time, "nodes": self.nodes,
                "edges": [e.to_dict() for e in self.edges],
                "affected": list(affected or []), "direct": list(direct or [])}


def build_conflict_graph(
    plans: Mapping[str, Sequence[TimedPosition]],
    td: int,
    dependencies: Sequence[tuple[str, str, str]] = (),
    window: int = 2,
    label: str = "",
    include_shared: bool = True,
) -> ConflictGraph:
    """``plans`` may contain tentative plans that conflict with each other."""
    g = ConflictGraph(nodes=sorted(plans), label=label, time=td)
    seen = set()
    for c in find_conflicts(plans, from_time=td + 1):
        if c.kind == "obstacle" or len(c.robots) < 2:
            continue
        key = (c.robots, c.kind)
        if key in seen:
            continue
        seen.add(key)
        g.edges.append(ConflictEdge(c.robots[0], c.robots[1], c.kind, c.time, c.position))
    for a, b, note in dependencies:
        if a in plans and b in plans:
            g.edges.append(ConflictEdge(a, b, "dependency", None, None, note))
    if include_shared:
        cell_use: dict[Position, list[tuple[str, int]]] = defaultdict(list)
        for rid, plan in plans.items():
            for tp in plan:
                if tp.time > td:
                    cell_use[tp.position].append((rid, tp.time))
        pairs: dict[tuple[str, str], tuple[int, Position]] = {}
        for pos, uses in cell_use.items():
            if len(uses) < 2:
                continue
            uses.sort(key=lambda x: x[1])
            for i, (ra, ta) in enumerate(uses):
                for rb, tb in uses[i + 1:]:
                    if tb - ta > window:
                        break
                    if ra != rb and ta != tb:
                        key2 = tuple(sorted((ra, rb)))
                        pairs.setdefault(key2, (ta, pos))  # type: ignore[arg-type]
        strong_pairs = {tuple(sorted((e.a, e.b))) for e in g.edges}
        for (ra, rb), (ta, pos) in pairs.items():
            if (ra, rb) not in strong_pairs:
                g.edges.append(ConflictEdge(ra, rb, "shared_resource", ta, pos))
    return g
