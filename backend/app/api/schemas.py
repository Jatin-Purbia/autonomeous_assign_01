"""Typed request / response schemas for the REST and WebSocket API."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class XY(BaseModel):
    x: int
    y: int


class TaskSpec(BaseModel):
    id: str
    pickup: list[int] = Field(min_length=2, max_length=2)
    delivery: list[int] = Field(min_length=2, max_length=2)
    priority: int = 1


class RobotSpec(BaseModel):
    id: str
    start: list[int] = Field(min_length=2, max_length=2)
    priority: Optional[int] = None
    tasks: list[TaskSpec] = []


class DisruptionSpec(BaseModel):
    id: Optional[str] = None
    type: Literal["cell_blockage", "robot_breakdown", "emergency_task"]
    time: int
    position: Optional[list[int]] = None
    robot_id: Optional[str] = None
    duration: Optional[int] = None
    task: Optional[TaskSpec] = None


class ScenarioSpecModel(BaseModel):
    id: str
    name: str = ""
    description: str = ""
    map: list[str]
    robots: list[RobotSpec]
    disruptions: list[DisruptionSpec] = []
    seed: int = 0
    expected_impact: Optional[int] = None


class ScenarioSummary(BaseModel):
    id: str
    name: str
    description: str
    n_robots: int
    width: int
    height: int
    builtin: bool
    expected_impact: Optional[int] = None


class RandomScenarioRequest(BaseModel):
    n_agents: int = Field(10, ge=1, le=80)
    seed: int = 0
    width: int = Field(20, ge=6, le=60)
    height: int = Field(14, ge=6, le=60)
    tasks_per_robot: int = Field(1, ge=1, le=5)
    save: bool = True


class InitializeRequest(BaseModel):
    scenario_id: Optional[str] = None
    scenario: Optional[ScenarioSpecModel] = None
    random: Optional[RandomScenarioRequest] = None
    strategy: Literal["local", "single_agent", "global"] = "local"
    seed: int = 0
    dev_checks: bool = True
    repair_config: dict[str, float] = {}


class SpeedRequest(BaseModel):
    steps_per_second: float = Field(2.0, gt=0, le=60)


class BlockCellRequest(BaseModel):
    x: int
    y: int
    duration: Optional[int] = Field(None, ge=1, description="None = permanent")
    activation_time: Optional[int] = Field(None, ge=0, description="None = now")


class BreakRobotRequest(BaseModel):
    robot_id: str
    activation_time: Optional[int] = Field(None, ge=0)


class EmergencyTaskRequest(BaseModel):
    pickup: XY
    delivery: XY
    robot_id: Optional[str] = None
    activation_time: Optional[int] = Field(None, ge=0)
    priority: int = 10


class DisruptionResponse(BaseModel):
    ok: bool
    scheduled: bool
    disruption_id: str
    message: str = ""
    repair: Optional[dict[str, Any]] = None


class CommandResponse(BaseModel):
    ok: bool = True
    status: str
    time: int
    running: bool
    message: str = ""


class ExperimentRunRequest(BaseModel):
    agent_counts: list[int] = [5, 10, 20, 30, 40]
    densities: list[float] = [0.0, 0.05, 0.10, 0.15, 0.20]
    disruption_type: Literal["cell_blockage", "robot_breakdown", "emergency_task", "mixed"] = "cell_blockage"
    repetitions: int = Field(20, ge=1, le=200)
    seed: int = 0
    seeds: Optional[list[int]] = None
    strategies: list[Literal["single_agent", "local", "global"]] = ["single_agent", "local", "global"]
    width: int = 20
    height: int = 14
    tasks_per_robot: int = 1
    block_duration_min: int = 6
    block_duration_max: int = 14


class ExperimentStatus(BaseModel):
    experiment_id: str
    status: Literal["queued", "running", "done", "failed"]
    done: int = 0
    total: int = 0
    error: Optional[str] = None
    config: dict[str, Any] = {}
    result: Optional[dict[str, Any]] = None
