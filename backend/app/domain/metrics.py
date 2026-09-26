"""Metric definitions.  Every metric is computed from actual executed trajectories / plans."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Iterable, Mapping, Optional, Sequence

from .grid import TimedPosition


def flowtime(completion_times: Iterable[int]) -> int:
    """Flowtime = sum_i C_i."""
    return int(sum(completion_times))


def makespan(completion_times: Iterable[int]) -> int:
    """Makespan = max_i C_i."""
    vals = list(completion_times)
    return int(max(vals)) if vals else 0


def plan_key(plan: Sequence[TimedPosition]) -> tuple:
    return tuple((tp.position.x, tp.position.y, tp.time) for tp in plan)


def modified_agents(old: Mapping[str, Sequence[TimedPosition]],
                    new: Mapping[str, Sequence[TimedPosition]]) -> list[str]:
    """Impact set {a_i : pi_i' != pi_i}.  Robots that only exchanged messages are not included."""
    return sorted(rid for rid in new if rid in old and plan_key(old[rid]) != plan_key(new[rid]))


def impact(old: Mapping[str, Sequence[TimedPosition]], new: Mapping[str, Sequence[TimedPosition]]) -> int:
    return len(modified_agents(old, new))


def impact_ratio(impact_count: int, n_agents: int) -> float:
    return impact_count / n_agents if n_agents else 0.0


def obstacle_density(n_dynamic_blocked: int, n_traversable: int) -> float:
    return n_dynamic_blocked / n_traversable if n_traversable else 0.0


def success_rate(outcomes: Iterable[bool]) -> float:
    vals = list(outcomes)
    return sum(1 for v in vals if v) / len(vals) if vals else 0.0


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def sample_std(values: Sequence[float]) -> float:
    """s = sqrt(1/(R-1) * sum (x_r - mean)^2)."""
    r = len(values)
    if r < 2:
        return 0.0
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (r - 1))


@dataclass
class DisruptionImpact:
    disruption_id: str
    type: str
    time: int
    direct_agents: list[str] = field(default_factory=list)
    affected_agents: list[str] = field(default_factory=list)
    modified_agents: list[str] = field(default_factory=list)
    impact: int = 0
    messages: int = 0
    runtime_ms: float = 0.0
    success: bool = True
    strategy: str = ""
    expansions: int = 0  # robots added to the affected set beyond the direct set


@dataclass
class SimulationResult:
    success: bool = False
    status: str = "ready"
    failure_reason: Optional[str] = None
    time: int = 0
    completion_times: dict[str, int] = field(default_factory=dict)
    flowtime: int = 0
    makespan: int = 0
    original_flowtime: int = 0
    original_makespan: int = 0
    delta_flowtime: int = 0
    n_agents: int = 0
    num_modified: int = 0
    modified_ids: list[str] = field(default_factory=list)
    modified_ratio: float = 0.0
    total_path_length: int = 0
    original_path_length: int = 0
    additional_path_length: int = 0
    total_waits: int = 0
    repair_time_ms: float = 0.0
    messages: int = 0
    collisions: int = 0
    deadlocks: int = 0
    conflicts_avoided: int = 0
    affected_expansions: int = 0   # total affected-set expansions over all repairs
    max_affected_size: int = 0     # largest |A_d| of any repair
    remaining_tasks: int = 0
    n_disruptions: int = 0
    n_repairs_failed: int = 0
    per_disruption: list[DisruptionImpact] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
