from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException

from ..domain.disruption import Disruption, DisruptionType
from ..domain.grid import Position
from ..domain.task import Task
from ..repair.models import RepairConfig
from ..simulation.scenario_generator import generate_random_scenario
from ..simulation.scenario_loader import ScenarioError
from .schemas import (BlockCellRequest, BreakRobotRequest, CommandResponse, DisruptionResponse,
                      EmergencyTaskRequest, InitializeRequest, RandomScenarioRequest, ScenarioSpecModel,
                      ScenarioSummary, SpeedRequest)
from .state import sim

router = APIRouter(prefix="/api")


def _bad(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _cmd(msg: str = "") -> CommandResponse:
    eng = sim.require()
    return CommandResponse(status=eng.status, time=eng.time, running=sim.running, message=msg)


def _summary(sid: str, spec: dict[str, Any]) -> ScenarioSummary:
    rows = spec["map"]
    return ScenarioSummary(id=sid, name=spec.get("name", sid), description=spec.get("description", ""),
                           n_robots=len(spec.get("robots", [])), width=len(rows[0]), height=len(rows),
                           builtin=sim.is_builtin(sid), expected_impact=spec.get("expected_impact"))


# ------------------------------------------------------------------ scenarios
@router.get("/scenarios", response_model=list[ScenarioSummary])
def list_scenarios():
    return [_summary(k, v) for k, v in sim.all_scenarios().items()]


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str):
    spec = sim.all_scenarios().get(scenario_id)
    if spec is None:
        raise HTTPException(404, "unknown scenario")
    return spec


@router.post("/scenarios", response_model=ScenarioSummary)
def save_scenario(body: ScenarioSpecModel):
    try:
        spec = sim.save_scenario(body.model_dump(exclude_none=True))
    except (ScenarioError, KeyError, ValueError) as exc:
        raise _bad(exc)
    return _summary(spec["id"], spec)


@router.post("/scenarios/random")
def random_scenario(body: RandomScenarioRequest):
    try:
        spec = generate_random_scenario(body.n_agents, body.seed, body.width, body.height, body.tasks_per_robot)
        if body.save:
            sim.save_scenario(spec)
    except ValueError as exc:
        raise _bad(exc)
    return spec


@router.get("/config/defaults")
def repair_defaults():
    from dataclasses import asdict
    return asdict(RepairConfig())


# ------------------------------------------------------------------ simulation control
@router.post("/simulation/initialize")
async def initialize(body: InitializeRequest):
    async with sim.lock:
        try:
            if body.scenario is not None:
                spec = body.scenario.model_dump(exclude_none=True)
            elif body.random is not None:
                r = body.random
                spec = generate_random_scenario(r.n_agents, r.seed, r.width, r.height, r.tasks_per_robot)
                if r.save:
                    sim.save_scenario(spec)
            elif body.scenario_id:
                spec = sim.all_scenarios().get(body.scenario_id)
                if spec is None:
                    raise HTTPException(404, "unknown scenario")
            else:
                raise ValueError("provide scenario_id, scenario or random")
            sim.initialize(spec, body.strategy, body.seed, body.dev_checks, body.repair_config)
        except (ScenarioError, ValueError, KeyError) as exc:
            raise _bad(exc)
    await sim.broadcast()
    return sim.payload(include_events=False)


@router.post("/simulation/start", response_model=CommandResponse)
async def start():
    try:
        sim.start()
    except ValueError as exc:
        raise _bad(exc)
    return _cmd("started")


@router.post("/simulation/pause", response_model=CommandResponse)
async def pause():
    sim.require()
    sim.pause()
    return _cmd("paused")


@router.post("/simulation/step", response_model=CommandResponse)
async def step():
    async with sim.lock:
        try:
            sim.require().step()
        except ValueError as exc:
            raise _bad(exc)
    await sim.broadcast()
    return _cmd("stepped")


@router.post("/simulation/reset", response_model=CommandResponse)
async def reset():
    async with sim.lock:
        try:
            sim.reset()
        except ValueError as exc:
            raise _bad(exc)
    await sim.broadcast()
    return _cmd("reset")


@router.post("/simulation/speed", response_model=CommandResponse)
async def speed(body: SpeedRequest):
    sim.speed = body.steps_per_second
    return _cmd(f"speed={sim.speed}")


@router.get("/simulation/state")
def state(events: bool = False):
    try:
        return sim.payload(include_events=False) if not events else sim.payload()
    except ValueError as exc:
        raise _bad(exc)


@router.get("/simulation/metrics")
def metrics():
    try:
        return sim.require().result().to_dict()
    except ValueError as exc:
        raise _bad(exc)


@router.get("/simulation/events")
def events(since: int = 0, include_movement: bool = False):
    try:
        evs = sim.require().log.since(since)
    except ValueError as exc:
        raise _bad(exc)
    return [e.to_dict() for e in evs if include_movement or e.event_type not in ("ROBOT_MOVED", "ROBOT_WAITED")]


# ------------------------------------------------------------------ disruptions
async def _apply(d: Disruption, activation: Optional[int]) -> DisruptionResponse:
    async with sim.lock:
        try:
            scheduled, result = sim.add_disruption(d, activation)
        except ValueError as exc:
            raise _bad(exc)
    await sim.broadcast()
    if scheduled:
        return DisruptionResponse(ok=True, scheduled=True, disruption_id=d.disruption_id,
                                  message=f"scheduled for t={d.activation_time}")
    ok = bool(result and result.success)
    return DisruptionResponse(ok=ok, scheduled=False, disruption_id=d.disruption_id,
                              message="repair committed" if ok else f"repair failed: {result.failure_reason}",
                              repair=result.summary() if result else None)


@router.post("/disruptions/block-cell", response_model=DisruptionResponse)
async def block_cell(body: BlockCellRequest):
    d = Disruption(sim.next_id("UI-B"), DisruptionType.CELL_BLOCKAGE, 0, Position(body.x, body.y),
                   duration=body.duration)
    return await _apply(d, body.activation_time)


@router.post("/disruptions/break-robot", response_model=DisruptionResponse)
async def break_robot(body: BreakRobotRequest):
    d = Disruption(sim.next_id("UI-X"), DisruptionType.ROBOT_BREAKDOWN, 0, affected_robot_id=body.robot_id)
    return await _apply(d, body.activation_time)


@router.post("/disruptions/emergency-task", response_model=DisruptionResponse)
async def emergency_task(body: EmergencyTaskRequest):
    tid = sim.next_id("UI-E")
    task = Task(tid, Position(body.pickup.x, body.pickup.y), Position(body.delivery.x, body.delivery.y),
                body.priority, emergency=True)
    d = Disruption(sim.next_id("UI-D"), DisruptionType.EMERGENCY_TASK, 0, affected_robot_id=body.robot_id,
                   emergency_task=task)
    return await _apply(d, body.activation_time)


@router.delete("/disruptions/obstacle/{obstacle_id}")
async def remove_obstacle(obstacle_id: str):
    async with sim.lock:
        ok = sim.require().remove_obstacle(obstacle_id)
    if not ok:
        raise HTTPException(404, "obstacle not found or belongs to a broken robot")
    await sim.broadcast()
    return {"ok": True}


@router.delete("/disruptions/scheduled/{disruption_id}")
async def cancel_scheduled(disruption_id: str):
    async with sim.lock:
        ok = sim.require().scheduler.cancel(disruption_id)
    if not ok:
        raise HTTPException(404, "no such scheduled disruption")
    await sim.broadcast()
    return {"ok": True}
