"""Data models shared by the repair modules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..domain.grid import Grid, ObstacleMap, TimedPosition
from ..domain.robot import Robot
from ..planning.reservation_table import ReservationTable

Plan = list[TimedPosition]


@dataclass
class RepairConfig:
    """All tunable parameters of the repair mechanism (documented in docs/algorithm.md)."""

    # local repair strategies
    max_delay: int = 12           # strategy 1: longest wait / whole-suffix delay
    detour_window: int = 14       # strategy 2: how far ahead a detour may rejoin the old plan
    max_order_retries: int = 6    # group repair: priority orders tried
    max_expansions: int = 250_000 # per A* call
    # task reassignment  Cost = d(pos,pickup) + d(pickup,delivery) + lambda*Load + mu*RepairImpact
    lambda_load: float = 4.0
    mu_impact: float = 2.0
    # negotiation bid  Bid = w1*dC + w2*dL + w3*P + w4*M
    w1: float = 1.0               # completion-time increase
    w2: float = 0.5               # extra path length
    w3: float = 1.0               # priority penalty per priority level of the yielding robot
    w4: float = 30.0              # penalty for changing an unmodified robot's plan
    emergency_priority_penalty: float = 1000.0
    emergency_priority_boost: int = 1000
    negotiation_trigger_delay: int = 12  # own yield delay above which negotiation is considered
    # objective  J = W1|A| + W2*sum(dC) + W3*messages + W4*runtime   (W1 >> W2 >> W3,W4)
    W1: float = 10_000.0
    W2: float = 100.0
    W3: float = 1.0
    W4: float = 0.1
    # mode switches used by the baselines
    allow_expansion: bool = True
    allow_negotiation: bool = True


@dataclass
class Message:
    time: int
    kind: str  # REPAIR_REQUEST | BID | ACCEPT | REJECT | PRIORITY_UPDATE | REPAIR_COMMITTED
    sender: str
    receiver: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"time": self.time, "kind": self.kind, "sender": self.sender,
                "receiver": self.receiver, "details": self.details}


@dataclass
class RepairContext:
    grid: Grid
    robots: dict[str, Robot]
    obstacles: ObstacleMap
    table: ReservationTable          # live table (read only for repair; sessions work on a copy)
    time: int                        # disruption time t_d
    config: RepairConfig
    emit: Callable[..., Any] = lambda *a, **k: None  # emit(event_type, robot_ids, reason, details)


@dataclass
class RepairResult:
    success: bool
    strategy: str = "local"
    failure_reason: Optional[str] = None
    new_plans: dict[str, Plan] = field(default_factory=dict)   # only robots whose plan changed
    direct: list[str] = field(default_factory=list)            # A_d^0
    affected: list[str] = field(default_factory=list)          # final A_d
    modified: list[str] = field(default_factory=list)          # plan actually changed
    expansions: list[dict[str, Any]] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)      # why each agent was modified
    methods: dict[str, str] = field(default_factory=dict)      # delay|detour|replan|group|extension
    messages: list[Message] = field(default_factory=list)
    diffs: dict[str, dict[str, Any]] = field(default_factory=dict)
    conflicts_avoided: int = 0
    runtime_ms: float = 0.0
    delta_completion: dict[str, int] = field(default_factory=dict)
    reassignments: list[dict[str, Any]] = field(default_factory=list)
    objective: float = 0.0
    deadlock: bool = False

    def summary(self) -> dict[str, Any]:
        return {
            "success": self.success, "strategy": self.strategy, "failure_reason": self.failure_reason,
            "direct": self.direct, "affected": self.affected, "modified": self.modified,
            "expansions": self.expansions, "reasons": self.reasons, "methods": self.methods,
            "messages": [m.to_dict() for m in self.messages],
            "diffs": self.diffs, "conflicts_avoided": self.conflicts_avoided,
            "runtime_ms": round(self.runtime_ms, 3), "delta_completion": self.delta_completion,
            "reassignments": self.reassignments, "objective": self.objective,
        }
