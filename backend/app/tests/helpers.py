"""Shared helpers for tests."""
from __future__ import annotations

from app.domain.grid import Grid, Position as P
from app.domain.robot import Robot
from app.domain.task import Task


def mk_robot(rid: str, start, tasks=(), priority=0) -> Robot:
    """tasks: iterable of (pickup, delivery) coordinate tuples."""
    ts = [Task(f"{rid}-T{i+1}", P(*pu), P(*de)) for i, (pu, de) in enumerate(tasks)]
    return Robot(robot_id=rid, initial_position=P(*start), current_position=P(*start),
                 tasks=ts, planning_priority=priority)


def grid_of(rows) -> Grid:
    return Grid.from_ascii(rows)
