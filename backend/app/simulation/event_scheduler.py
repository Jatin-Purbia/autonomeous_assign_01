from __future__ import annotations

from ..domain.disruption import Disruption


class DisruptionScheduler:
    """Time-ordered queue of disruptions (stable for equal activation times)."""

    def __init__(self, disruptions: list[Disruption] | None = None) -> None:
        self._pending: list[Disruption] = []
        self.activated: list[Disruption] = []
        for d in disruptions or []:
            self.schedule(d)

    def schedule(self, d: Disruption) -> None:
        self._pending.append(d)
        self._pending.sort(key=lambda x: x.activation_time)  # stable sort

    def cancel(self, disruption_id: str) -> bool:
        before = len(self._pending)
        self._pending = [d for d in self._pending if d.disruption_id != disruption_id]
        return len(self._pending) < before

    def pop_due(self, t: int) -> list[Disruption]:
        due = [d for d in self._pending if d.activation_time <= t]
        self._pending = [d for d in self._pending if d.activation_time > t]
        self.activated.extend(due)
        return due

    @property
    def pending(self) -> list[Disruption]:
        return list(self._pending)
