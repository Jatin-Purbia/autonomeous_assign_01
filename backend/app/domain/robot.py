from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .grid import Position, TimedPosition
from .task import Task, TaskStatus, Waypoint


class RobotStatus(str, Enum):
    ACTIVE = "active"
    WAITING = "waiting"
    BROKEN = "broken"
    EMERGENCY = "emergency"
    DONE = "done"  # finished every task and left the workspace


@dataclass
class Robot:
    """A robot with its tasks and plans.

    Plans are indexed by absolute time: ``plan[t].time == t`` and ``plan[t].position`` is
    the cell occupied at time ``t``.  ``executed_prefix`` is the immutable history.
    """

    robot_id: str
    initial_position: Position
    current_position: Position
    tasks: list[Task] = field(default_factory=list)
    current_task_index: int = 0
    original_plan: list[TimedPosition] = field(default_factory=list)
    active_plan: list[TimedPosition] = field(default_factory=list)
    executed_prefix: list[TimedPosition] = field(default_factory=list)
    status: RobotStatus = RobotStatus.ACTIVE
    planning_priority: int = 0  # larger = more important
    completion_time: Optional[int] = None
    broken_at: Optional[int] = None
    on_grid: bool = True  # False once the robot has exited after finishing

    # -- task / waypoint helpers -------------------------------------------------
    def remaining_waypoints(self) -> list[Waypoint]:
        """Ordered waypoints still to be visited (capacity-1 semantics: pickup then delivery)."""
        wps: list[Waypoint] = []
        for task in self.tasks:
            if task.status == TaskStatus.PENDING:
                wps.append(Waypoint(task.task_id, "pickup", task.pickup))
                wps.append(Waypoint(task.task_id, "delivery", task.delivery))
            elif task.status == TaskStatus.PICKED:
                wps.append(Waypoint(task.task_id, "delivery", task.delivery))
        return wps

    def unfinished_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.status in (TaskStatus.PENDING, TaskStatus.PICKED)]

    @property
    def load(self) -> int:
        return len(self.unfinished_tasks())

    @property
    def is_active(self) -> bool:
        return self.status not in (RobotStatus.BROKEN, RobotStatus.DONE)

    def plan_end_time(self) -> int:
        return self.active_plan[-1].time if self.active_plan else 0


def pos_at(plan: list[TimedPosition], t: int) -> Optional[Position]:
    """Position at absolute time ``t`` or None if the plan does not cover it."""
    if 0 <= t < len(plan):
        return plan[t].position
    return None


def make_plan(positions: list[Position], start_time: int = 0) -> list[TimedPosition]:
    return [TimedPosition(p, start_time + i) for i, p in enumerate(positions)]


def plan_positions(plan: list[TimedPosition]) -> list[Position]:
    return [tp.position for tp in plan]
