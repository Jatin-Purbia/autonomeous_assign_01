from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .grid import Position
from .task import Task


class DisruptionType(str, Enum):
    CELL_BLOCKAGE = "cell_blockage"
    ROBOT_BREAKDOWN = "robot_breakdown"
    EMERGENCY_TASK = "emergency_task"


@dataclass
class Disruption:
    disruption_id: str
    type: DisruptionType
    activation_time: int
    affected_position: Optional[Position] = None
    affected_robot_id: Optional[str] = None
    emergency_task: Optional[Task] = None
    duration: Optional[int] = None  # cell blockage only; None = permanent
