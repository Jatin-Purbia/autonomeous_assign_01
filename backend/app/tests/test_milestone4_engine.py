import pytest

from app.domain.metrics import (flowtime, impact, impact_ratio, makespan, mean, modified_agents,
                                obstacle_density, sample_std, success_rate)
from app.domain.grid import Position as P
from app.domain.robot import make_plan
from app.simulation.engine import EngineConfig, SimulationEngine
from app.simulation.scenario_loader import ScenarioError, build_scenario


def spec(rows, robots, disruptions=()):
    return {"id": "t", "name": "t", "map": rows, "robots": robots, "disruptions": list(disruptions)}


def rb(rid, start, tasks):
    return {"id": rid, "start": start,
            "tasks": [{"id": f"{rid}-T{i}", "pickup": pu, "delivery": de} for i, (pu, de) in enumerate(tasks)]}


def test_execution_completes_and_metrics_from_trajectories():
    eng = SimulationEngine(spec(["......"] * 3, [rb("A", [0, 0], [([2, 0], [5, 0])]),
                                                 rb("B", [5, 2], [([5, 1], [0, 2])])]))
    res = eng.run()
    assert res.success and res.status == "completed"
    assert res.completion_times == {"A": 5, "B": 7}
    assert res.flowtime == 12 and res.makespan == 7
    assert res.collisions == 0 and res.num_modified == 0
    assert res.total_path_length == 12 and res.additional_path_length == 0
    types = {e.event_type for e in eng.log.events}
    assert {"INITIAL_PLAN_CREATED", "ROBOT_MOVED", "PICKUP_COMPLETED", "DELIVERY_COMPLETED",
            "SIMULATION_COMPLETED"} <= types


def test_step_by_step_positions_match_plan_and_prefix_recorded():
    eng = SimulationEngine(spec(["....."], [rb("A", [0, 0], [([0, 0], [4, 0])])]))
    plan = [tp.position for tp in eng.robots["A"].active_plan]
    for t in range(1, 5):
        eng.step()
        assert eng.robots["A"].current_position == plan[t]
        assert [tp.position for tp in eng.robots["A"].executed_prefix] == plan[: t + 1]


def test_pickup_at_start_and_robot_without_tasks():
    eng = SimulationEngine(spec(["...."], [rb("A", [0, 0], [([0, 0], [2, 0])]), rb("Z", [3, 0], [])]))
    assert eng.robots["A"].tasks[0].status.value == "picked"
    res = eng.run()
    assert res.completion_times["Z"] == 0 and res.completion_times["A"] == 2


def test_two_robots_never_share_cells_even_when_crossing():
    rows = ["...", "...", "..."]
    eng = SimulationEngine(spec(rows, [rb("A", [0, 1], [([0, 1], [2, 1])]),
                                       rb("B", [2, 1], [([2, 1], [0, 1])]),
                                       rb("C", [1, 0], [([1, 0], [1, 2])]),
                                       rb("D", [1, 2], [([1, 2], [1, 0])])]))
    res = eng.run()
    assert res.success and res.collisions == 0


def test_initial_planning_failure_reported():
    eng = SimulationEngine(spec([".#."], [rb("A", [0, 0], [([0, 0], [2, 0])])]))
    assert eng.status == "failed" and "initial planning" in eng.failure_reason


def test_scenario_validation():
    with pytest.raises(ScenarioError):
        build_scenario(spec(["..#"], [rb("A", [2, 0], [])]))
    with pytest.raises(ScenarioError):
        build_scenario(spec(["..."], [rb("A", [0, 0], []), rb("B", [0, 0], [])]))


def test_metric_functions():
    assert flowtime([3, 5, 7]) == 15
    assert makespan([3, 5, 7]) == 7
    old = {"A": make_plan([P(0, 0), P(1, 0)]), "B": make_plan([P(0, 1), P(1, 1)])}
    new = {"A": make_plan([P(0, 0), P(0, 0), P(1, 0)]), "B": make_plan([P(0, 1), P(1, 1)])}
    assert modified_agents(old, new) == ["A"] and impact(old, new) == 1
    assert impact_ratio(1, 4) == 0.25
    assert obstacle_density(6, 60) == pytest.approx(0.1)
    assert success_rate([True, False, True, True]) == 0.75
    assert mean([1, 2, 3]) == 2 and sample_std([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(2.13809, rel=1e-4)
    assert sample_std([5]) == 0.0


def test_events_are_structured():
    eng = SimulationEngine(spec(["..."], [rb("A", [0, 0], [([0, 0], [2, 0])])]))
    eng.run()
    d = eng.log.events[0].to_dict()
    assert set(d) == {"index", "time", "event_type", "robot_ids", "reason", "details"}
