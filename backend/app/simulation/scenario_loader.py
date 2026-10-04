"""Scenario specification (JSON-friendly dict) <-> domain objects."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from ..domain.disruption import Disruption, DisruptionType
from ..domain.grid import Grid, Position
from ..domain.robot import Robot
from ..domain.task import Task


class ScenarioError(ValueError):
    pass


def _pos(v) -> Position:
    return Position(int(v[0]), int(v[1]))


def task_from_spec(s: dict[str, Any], default_id: str = "T") -> Task:
    return Task(str(s.get("id", default_id)), _pos(s["pickup"]), _pos(s["delivery"]),
                int(s.get("priority", 1)), emergency=bool(s.get("emergency", False)))


def task_to_spec(t: Task) -> dict[str, Any]:
    return {"id": t.task_id, "pickup": [t.pickup.x, t.pickup.y], "delivery": [t.delivery.x, t.delivery.y],
            "priority": t.priority, "emergency": t.emergency}


@dataclass
class Scenario:
    spec: dict[str, Any]
    grid: Grid
    robots: list[Robot]
    disruptions: list[Disruption]

    @property
    def scenario_id(self) -> str:
        return self.spec.get("id", "custom")


def build_scenario(spec: dict[str, Any]) -> Scenario:
    """Build fresh (mutable) domain objects from a spec.  Validates positions."""
    spec = copy.deepcopy(spec)
    rows = spec["map"]
    if len({len(r) for r in rows}) != 1:
        raise ScenarioError("map rows must have equal length")
    grid = Grid.from_ascii(rows)
    robots: list[Robot] = []
    n = len(spec.get("robots", []))
    seen_starts: set[Position] = set()
    for i, rs in enumerate(spec.get("robots", [])):
        start = _pos(rs["start"])
        if not grid.is_traversable(start):
            raise ScenarioError(f"robot {rs['id']} starts on a non-traversable cell {start}")
        if start in seen_starts:
            raise ScenarioError(f"two robots share start cell {start}")
        seen_starts.add(start)
        tasks = [task_from_spec(ts, f"{rs['id']}-T{j + 1}") for j, ts in enumerate(rs.get("tasks", []))]
        for t in tasks:
            for p in (t.pickup, t.delivery):
                if not grid.is_traversable(p):
                    raise ScenarioError(f"task {t.task_id} uses non-traversable cell {p}")
        robots.append(Robot(robot_id=str(rs["id"]), initial_position=start, current_position=start,
                            tasks=tasks, planning_priority=int(rs.get("priority", n - i))))
    disruptions: list[Disruption] = []
    for j, ds in enumerate(spec.get("disruptions", [])):
        dtype = DisruptionType(ds["type"])
        d = Disruption(
            disruption_id=str(ds.get("id", f"D{j + 1}")), type=dtype, activation_time=int(ds["time"]),
            affected_position=_pos(ds["position"]) if ds.get("position") else None,
            affected_robot_id=ds.get("robot_id"),
            emergency_task=task_from_spec({**ds["task"], "emergency": True}, f"E{j + 1}") if ds.get("task") else None,
            duration=ds.get("duration"),
        )
        disruptions.append(d)
    return Scenario(spec, grid, robots, disruptions)


def disruption_to_spec(d: Disruption) -> dict[str, Any]:
    out: dict[str, Any] = {"id": d.disruption_id, "type": d.type.value, "time": d.activation_time}
    if d.affected_position:
        out["position"] = [d.affected_position.x, d.affected_position.y]
    if d.affected_robot_id:
        out["robot_id"] = d.affected_robot_id
    if d.emergency_task:
        out["task"] = task_to_spec(d.emergency_task)
    if d.duration is not None:
        out["duration"] = d.duration
    return out
