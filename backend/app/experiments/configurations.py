from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

STRATEGIES = ("single_agent", "local")
DISRUPTION_KINDS = ("cell_blockage", "robot_breakdown", "emergency_task", "mixed")


@dataclass
class ExperimentConfig:
    agent_counts: list[int] = field(default_factory=lambda: [5, 20, 40])
    densities: list[float] = field(default_factory=lambda: [0.0, 0.10, 0.20])
    disruption_type: str = "cell_blockage"
    repetitions: int = 5
    seed: int = 0                       # first seed; run r uses seed + r
    seeds: Optional[list[int]] = None   # explicit seed sequence (overrides seed/repetitions)
    strategies: list[str] = field(default_factory=lambda: list(STRATEGIES))
    width: int = 20
    height: int = 14
    tasks_per_robot: int = 1
    block_duration_min: int = 6
    block_duration_max: int = 14
    targeted_fraction: float = 0.5      # share of blockages placed on cells that planned paths use
    n_breakdowns: int = 1
    n_emergencies: int = 1
    max_time: int = 500

    def __post_init__(self) -> None:
        # 0 and 0.0 must give identical runs (seeds are derived from a string built from rho)
        self.densities = [float(d) for d in self.densities]

    def seed_list(self) -> list[int]:
        return list(self.seeds) if self.seeds else [self.seed + r for r in range(self.repetitions)]

    def validate(self) -> None:
        if self.disruption_type not in DISRUPTION_KINDS:
            raise ValueError(f"disruption_type must be one of {DISRUPTION_KINDS}")
        for s in self.strategies:
            if s not in STRATEGIES:
                raise ValueError(f"unknown strategy {s}")
        if not self.agent_counts or not self.densities:
            raise ValueError("agent_counts and densities must not be empty")
        if any(not (0 <= d <= 1) for d in self.densities):
            raise ValueError("densities must be in [0, 1]")
        if not (0 <= self.targeted_fraction <= 1):
            raise ValueError("targeted_fraction must be in [0, 1]")
        if self.block_duration_min > self.block_duration_max:
            raise ValueError("block_duration_min > block_duration_max")

    def total_runs(self) -> int:
        return len(self.agent_counts) * len(self.densities) * len(self.seed_list()) * len(self.strategies)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ExperimentConfig":
        known = {k: v for k, v in d.items() if k in ExperimentConfig.__dataclass_fields__ and v is not None}
        cfg = ExperimentConfig(**known)
        cfg.validate()
        return cfg
