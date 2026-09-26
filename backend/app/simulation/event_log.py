from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class EventType(str, Enum):
    INITIAL_PLAN_CREATED = "INITIAL_PLAN_CREATED"
    ROBOT_MOVED = "ROBOT_MOVED"
    ROBOT_WAITED = "ROBOT_WAITED"
    PICKUP_COMPLETED = "PICKUP_COMPLETED"
    DELIVERY_COMPLETED = "DELIVERY_COMPLETED"
    DISRUPTION_ACTIVATED = "DISRUPTION_ACTIVATED"
    PLAN_INVALIDATED = "PLAN_INVALIDATED"
    REPAIR_STARTED = "REPAIR_STARTED"
    REPAIR_REQUEST = "REPAIR_REQUEST"
    BID_SUBMITTED = "BID_SUBMITTED"
    BID_ACCEPTED = "BID_ACCEPTED"
    BID_REJECTED = "BID_REJECTED"
    PRIORITY_UPDATE = "PRIORITY_UPDATE"
    AFFECTED_SET_EXPANDED = "AFFECTED_SET_EXPANDED"
    PLAN_SUFFIX_REPAIRED = "PLAN_SUFFIX_REPAIRED"
    TASK_REASSIGNED = "TASK_REASSIGNED"
    REPAIR_COMMITTED = "REPAIR_COMMITTED"
    REPAIR_FAILED = "REPAIR_FAILED"
    ROBOT_FINISHED = "ROBOT_FINISHED"
    SIMULATION_COMPLETED = "SIMULATION_COMPLETED"
    SIMULATION_FAILED = "SIMULATION_FAILED"


@dataclass
class Event:
    time: int
    event_type: str
    robot_ids: list[str] = field(default_factory=list)
    reason: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)
    index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"index": self.index, "time": self.time, "event_type": self.event_type,
                "robot_ids": self.robot_ids, "reason": self.reason, "details": self.details}


class EventLog:
    def __init__(self, record_movement: bool = True) -> None:
        self.events: list[Event] = []
        self.record_movement = record_movement

    def add(self, time: int, event_type: EventType | str, robot_ids: Optional[list[str]] = None,
            reason: Optional[str] = None, details: Optional[dict[str, Any]] = None) -> Event:
        et = event_type.value if isinstance(event_type, EventType) else event_type
        ev = Event(time, et, list(robot_ids or []), reason, dict(details or {}), len(self.events))
        self.events.append(ev)
        return ev

    def since(self, index: int) -> list[Event]:
        return self.events[index:]

    def of_type(self, *types: EventType | str) -> list[Event]:
        names = {t.value if isinstance(t, EventType) else t for t in types}
        return [e for e in self.events if e.event_type in names]

    def __len__(self) -> int:
        return len(self.events)
