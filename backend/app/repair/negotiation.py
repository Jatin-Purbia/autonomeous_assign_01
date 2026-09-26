"""Contract-Net-inspired neighbour negotiation.

Protocol for a conflict between initiator ``a`` and a neighbour ``j``:
  1. a -> j  REPAIR_REQUEST   (a's intended route conflicts with j's reserved route)
  2. j -> a  BID              (cost of j yielding);   a -> j BID (cost of a yielding)
  3. the lower total bid yields:  winner's yield gets   ACCEPT,  the other gets REJECT
  4. VALUE/PRIORITY_UPDATE tells a robot that the relative priority for this repair was changed
  5. REPAIR_COMMITTED tells every modified robot that its new plan is now active.

    Bid_i = w1*dC_i + w2*dL_i + w3*P_i + w4*M_i
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Optional

from ..domain.robot import Robot, RobotStatus
from ..simulation.event_log import EventType
from .models import Message, RepairConfig

INF = math.inf

_KIND_TO_EVENT = {
    "REPAIR_REQUEST": EventType.REPAIR_REQUEST,
    "BID": EventType.BID_SUBMITTED,
    "ACCEPT": EventType.BID_ACCEPTED,
    "REJECT": EventType.BID_REJECTED,
    "PRIORITY_UPDATE": EventType.PRIORITY_UPDATE,
}


@dataclass
class Bid:
    robot_id: str
    delta_c: float
    delta_l: float
    priority_penalty: float
    modification_penalty: float
    cost: float
    feasible: bool = True

    def to_dict(self) -> dict[str, Any]:
        fin = lambda v: None if math.isinf(v) else v  # JSON has no infinity
        return {"robot": self.robot_id, "delta_c": fin(self.delta_c), "delta_l": fin(self.delta_l),
                "P": self.priority_penalty, "M": self.modification_penalty,
                "cost": None if math.isinf(self.cost) else round(self.cost, 3), "feasible": self.feasible}


def is_emergency(robot: Robot) -> bool:
    return robot.status == RobotStatus.EMERGENCY or any(t.emergency and t.status.value in ("pending", "picked")
                                                         for t in robot.tasks)


def priority_penalty(robot: Robot, cfg: RepairConfig) -> float:
    """P_i: cost of delaying agent i; huge for emergency robots so that they never yield willingly."""
    return float(max(robot.planning_priority, 0)) + (cfg.emergency_priority_penalty if is_emergency(robot) else 0.0)


def compute_bid(cfg: RepairConfig, robot: Robot, delta_c: Optional[float], delta_l: Optional[float],
                already_modified: bool) -> Bid:
    """Bid_i = w1*dC + w2*dL + w3*P + w4*M.  ``delta_c=None`` means i cannot yield locally (infinite bid)."""
    p = priority_penalty(robot, cfg)
    m = 0.0 if already_modified else 1.0
    if delta_c is None:
        return Bid(robot.robot_id, INF, INF, p, m, INF, feasible=False)
    dl = delta_l or 0.0
    cost = cfg.w1 * delta_c + cfg.w2 * dl + cfg.w3 * p + cfg.w4 * m
    return Bid(robot.robot_id, delta_c, dl, p, m, cost, True)


class MessageBus:
    """Records every negotiation message (the message count is an evaluation metric)."""

    def __init__(self, time: int, emit: Callable[..., Any]) -> None:
        self.time = time
        self.emit = emit
        self.messages: list[Message] = []

    def send(self, kind: str, sender: str, receiver: str, **details: Any) -> Message:
        msg = Message(self.time, kind, sender, receiver, details)
        self.messages.append(msg)
        ev = _KIND_TO_EVENT.get(kind)
        if ev is not None:
            self.emit(ev, [sender, receiver], kind, {"sender": sender, "receiver": receiver, **details})
        return msg

    def __len__(self) -> int:
        return len(self.messages)
