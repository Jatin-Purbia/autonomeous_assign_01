"""Affected-set tracking A_d and detection of the initial (direct) affected set A_d^0."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from ..domain.grid import ObstacleMap
from ..domain.robot import Robot, RobotStatus


def find_directly_invalidated(robots: Mapping[str, Robot], obstacles: ObstacleMap, td: int) -> dict[str, str]:
    """A_d^0 : robots whose *remaining* plan enters an active obstacle cell during its blocked interval."""
    out: dict[str, str] = {}
    for rid, r in robots.items():
        if not r.on_grid or r.status in (RobotStatus.BROKEN, RobotStatus.DONE):
            continue
        for tp in r.active_plan[td + 1:]:
            if obstacles.is_blocked(tp.position, tp.time):
                out[rid] = f"remaining plan enters blocked cell {tp.position} at t={tp.time}"
                break
    return out


@dataclass
class AffectedInfo:
    robot_id: str
    kind: str            # "direct" | "indirect"
    reason: str
    added_by: Optional[str] = None
    order: int = 0


class AffectedSet:
    """Ordered membership with a history of expansions (for the UI and the report)."""

    def __init__(self) -> None:
        self.members: dict[str, AffectedInfo] = {}
        self.history: list[dict[str, Any]] = []

    def add_direct(self, rid: str, reason: str) -> None:
        if rid not in self.members:
            self.members[rid] = AffectedInfo(rid, "direct", reason, None, len(self.members))

    def expand(self, rid: str, via: str, reason: str, added_by: Optional[str], time: int) -> bool:
        """A_d <- A_d U {rid}.  Returns False if it was already a member."""
        if rid in self.members:
            return False
        self.members[rid] = AffectedInfo(rid, "indirect", reason, added_by, len(self.members))
        self.history.append({"time": time, "robot": rid, "added_by": added_by, "via": via, "reason": reason,
                             "size": len(self.members)})
        return True

    def __contains__(self, rid: str) -> bool:
        return rid in self.members

    def __len__(self) -> int:
        return len(self.members)

    def ids(self) -> list[str]:
        return list(self.members)

    def direct_ids(self) -> list[str]:
        return [r for r, i in self.members.items() if i.kind == "direct"]
