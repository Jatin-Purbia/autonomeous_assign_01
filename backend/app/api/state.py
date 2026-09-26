"""Process-wide simulation session (single interactive simulation) and experiment job registry."""
from __future__ import annotations

import asyncio
import copy
import threading
import uuid
from dataclasses import fields, replace
from pathlib import Path
from typing import Any, Optional

from fastapi import WebSocket

from ..domain.disruption import Disruption, DisruptionType
from ..domain.grid import Position
from ..domain.task import Task
from ..experiments.batch_runner import export_results, run_experiment
from ..experiments.configurations import ExperimentConfig
from ..repair.models import RepairConfig
from ..simulation.builtin_scenarios import builtin_scenarios
from ..simulation.engine import EngineConfig, SimulationEngine
from ..simulation.scenario_generator import generate_random_scenario
from ..simulation.scenario_loader import ScenarioError, build_scenario

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "experiment_outputs"


class SimulationManager:
    def __init__(self) -> None:
        self.engine: Optional[SimulationEngine] = None
        self.custom_scenarios: dict[str, dict[str, Any]] = {}
        self.running = False
        self.speed = 2.0
        self.sockets: set[WebSocket] = set()
        self.lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None
        self._sent_events = 0
        self._counter = 0
        self.last_init: dict[str, Any] = {}

    # ------------------------------------------------------------ scenarios
    def all_scenarios(self) -> dict[str, dict[str, Any]]:
        out = dict(builtin_scenarios())
        out.update(self.custom_scenarios)
        return out

    def is_builtin(self, sid: str) -> bool:
        return sid in builtin_scenarios()

    def save_scenario(self, spec: dict[str, Any]) -> dict[str, Any]:
        build_scenario(spec)  # validates
        self.custom_scenarios[spec["id"]] = copy.deepcopy(spec)
        return spec

    # ------------------------------------------------------------ lifecycle
    def initialize(self, spec: dict[str, Any], strategy: str, seed: int, dev_checks: bool,
                   repair_overrides: dict[str, float]) -> None:
        cfg = RepairConfig()
        valid = {f.name for f in fields(RepairConfig)}
        bad = set(repair_overrides) - valid
        if bad:
            raise ValueError(f"unknown repair parameters: {sorted(bad)}")
        cfg = replace(cfg, **{k: type(getattr(cfg, k))(v) for k, v in repair_overrides.items()})
        self.running = False
        self.engine = SimulationEngine(spec, EngineConfig(strategy=strategy, seed=seed, dev_checks=dev_checks,
                                                          repair=cfg))
        self._sent_events = 0
        self.last_init = {"spec": copy.deepcopy(spec), "strategy": strategy, "seed": seed,
                          "dev_checks": dev_checks, "repair_overrides": dict(repair_overrides)}

    def reset(self) -> None:
        if self.engine is None:
            raise ValueError("no simulation initialised")
        li = self.last_init
        self.initialize(li["spec"], li["strategy"], li["seed"], li["dev_checks"], li["repair_overrides"])

    def require(self) -> SimulationEngine:
        if self.engine is None:
            raise ValueError("no simulation initialised: call /api/simulation/initialize")
        return self.engine

    def next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}{self._counter}"

    # ------------------------------------------------------------ disruptions
    def add_disruption(self, d: Disruption, activation: Optional[int]) -> tuple[bool, Any]:
        eng = self.require()
        if eng.status in ("completed", "failed"):
            raise ValueError("simulation already finished")
        if activation is None or activation <= eng.time:
            return False, eng.inject(d)
        d.activation_time = activation
        eng.schedule_disruption(d)
        return True, None

    # ------------------------------------------------------------ push
    def payload(self, include_events: bool = True) -> dict[str, Any]:
        eng = self.require()
        msg: dict[str, Any] = {"type": "state", "running": self.running, "speed": self.speed,
                               "state": eng.snapshot(), "strategy": eng.config.strategy}
        if include_events:
            evs = eng.log.since(self._sent_events)
            msg["events"] = [e.to_dict() for e in evs if e.event_type not in ("ROBOT_MOVED", "ROBOT_WAITED")]
            self._sent_events = len(eng.log)
        return msg

    async def broadcast(self) -> None:
        if not self.sockets or self.engine is None:
            return
        msg = self.payload()
        dead = []
        for ws in list(self.sockets):
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.sockets.discard(ws)

    async def _loop(self) -> None:
        try:
            while self.running:
                async with self.lock:
                    eng = self.require()
                    alive = eng.step()
                    if not alive:
                        self.running = False
                await self.broadcast()
                if not self.running:
                    break
                await asyncio.sleep(1.0 / self.speed)
        finally:
            self.running = False

    def start(self) -> None:
        eng = self.require()
        if eng.status in ("completed", "failed") or self.running:
            return
        self.running = True
        self._task = asyncio.get_event_loop().create_task(self._loop())

    def pause(self) -> None:
        self.running = False


class ExperimentManager:
    def __init__(self) -> None:
        self.jobs: dict[str, dict[str, Any]] = {}

    def submit(self, cfg: ExperimentConfig) -> str:
        eid = uuid.uuid4().hex[:10]
        self.jobs[eid] = {"experiment_id": eid, "status": "queued", "done": 0, "total": cfg.total_runs(),
                          "error": None, "config": cfg.to_dict(), "result": None, "files": {}}
        threading.Thread(target=self._run, args=(eid, cfg), daemon=True).start()
        return eid

    def _run(self, eid: str, cfg: ExperimentConfig) -> None:
        job = self.jobs[eid]
        job["status"] = "running"

        def prog(done: int, total: int) -> None:
            job["done"], job["total"] = done, total

        try:
            res = run_experiment(cfg, prog)
            job["files"] = export_results(res, OUTPUT_DIR, f"experiment_{eid}")
            job["result"] = res
            job["status"] = "done"
        except Exception as exc:  # pragma: no cover
            job["status"] = "failed"
            job["error"] = f"{type(exc).__name__}: {exc}"


sim = SimulationManager()
experiments = ExperimentManager()
