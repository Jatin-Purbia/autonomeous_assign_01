from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .grid import Position


class TaskStatus(str, Enum):
    PENDING = "pending"
    PICKED = "picked"
    DELIVERED = "delivered"
    REASSIGNED = "reassigned"


@dataclass
class Task:
    task_id: str
    pickup: Position
    delivery: Position
    priority: int = 1
    status: TaskStatus = TaskStatus.PENDING
    emergency: bool = False
    completed_at: int | None = None

    def copy(self) -> "Task":
        return Task(self.task_id, self.pickup, self.delivery, self.priority,
                    self.status, self.emergency, self.completed_at)


@dataclass(frozen=True)
class Waypoint:
    """One location a robot must visit, in order. Pickup of a task precedes its delivery."""

    task_id: str
    kind: str  # "pickup" | "delivery"
    position: Position
