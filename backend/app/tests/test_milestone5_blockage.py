import pytest

from app.domain.metrics import plan_key
from app.simulation.engine import EngineConfig, SimulationEngine
from app.tests.test_milestone4_engine import rb, spec


def block(t, x, y, duration=None, did="D1"):
    return {"id": did, "type": "cell_blockage", "time": t, "position": [x, y], "duration": duration}


def snapshot_plans(eng):
    return {rid: plan_key(r.active_plan) for rid, r in eng.robots.items()}


def test_detour_around_permanent_blockage_only_one_agent_modified():
    rows = ["......."] * 5
    eng = SimulationEngine(spec(rows, [rb("A", [0, 1], [([0, 1], [6, 1])]),
                                       rb("B", [0, 4], [([0, 4], [6, 4])])],
                                [block(1, 3, 1)]))
    original = snapshot_plans(eng)
    res = eng.run()
    assert res.success and res.collisions == 0
    assert res.modified_ids == ["A"] and res.num_modified == 1
    assert plan_key(eng.robots["B"].active_plan) == original["B"]          # unaffected plan identical
    assert res.completion_times["A"] == 8 and res.additional_path_length == 2
    d = res.per_disruption[0]
    assert d.direct_agents == ["A"] and d.affected_agents == ["A"] and d.impact == 1
    assert eng.repairs[0]["methods"]["A"] in ("detour", "replan")
    assert res.messages == 0
    # the robot never entered the blocked cell
    assert all(tp.position.x != 3 or tp.position.y != 1 for tp in eng.robots["A"].executed_prefix if tp.time >= 1)


def test_wait_strategy_in_one_wide_corridor():
    eng = SimulationEngine(spec(["......."], [rb("A", [0, 0], [([0, 0], [6, 0])])], [block(1, 3, 0, duration=3)]))
    res = eng.run()
    assert res.success
    assert res.completion_times["A"] == 8
    assert eng.repairs[0]["methods"]["A"] == "delay"
    assert res.total_waits == 2


def test_executed_prefix_is_immutable():
    eng = SimulationEngine(spec(["......."] * 3, [rb("A", [0, 1], [([0, 1], [6, 1])])], [block(3, 4, 1)]))
    before = [tp.position for tp in eng.robots["A"].active_plan[:4]]
    eng.run(max_steps=3)
    eng.step()  # disruption at t=3 activates here
    assert [tp.position for tp in eng.robots["A"].active_plan[:4]] == before
    assert [tp.position for tp in eng.robots["A"].executed_prefix[:4]] == before


def test_blockage_that_touches_no_plan_causes_no_repair_work():
    eng = SimulationEngine(spec(["......."] * 3, [rb("A", [0, 0], [([0, 0], [6, 0])])], [block(1, 3, 2)]))
    orig = snapshot_plans(eng)
    res = eng.run()
    assert res.num_modified == 0 and snapshot_plans(eng) == orig
    assert res.per_disruption[0].direct_agents == []


def test_blockage_on_current_cell_forces_robot_to_leave():
    eng = SimulationEngine(spec(["......."] * 3, [rb("A", [0, 1], [([0, 1], [6, 1])])], [block(2, 2, 1)]))
    res = eng.run()  # A is standing on (2,1) at t=2 when it becomes blocked
    assert res.success
    assert all(not (tp.position.x == 2 and tp.position.y == 1) for tp in eng.robots["A"].executed_prefix if tp.time > 2)


def test_impossible_blockage_fails_cleanly():
    # permanently blocking the only cell of a 1-wide corridor makes the delivery impossible
    eng = SimulationEngine(spec(["......."], [rb("A", [0, 0], [([0, 0], [6, 0])])], [block(1, 3, 0)]))
    res = eng.run()
    assert not res.success and res.status == "failed" and res.n_repairs_failed == 1
    assert "repair failed" in res.failure_reason
    assert any(e.event_type == "REPAIR_FAILED" for e in eng.log.events)


def test_events_logged_for_repair():
    eng = SimulationEngine(spec(["......."] * 3, [rb("A", [0, 1], [([0, 1], [6, 1])])], [block(1, 3, 1)]))
    eng.run()
    kinds = [e.event_type for e in eng.log.events]
    for k in ("DISRUPTION_ACTIVATED", "REPAIR_STARTED", "PLAN_INVALIDATED", "PLAN_SUFFIX_REPAIRED", "REPAIR_COMMITTED"):
        assert k in kinds
    assert kinds.index("DISRUPTION_ACTIVATED") < kinds.index("REPAIR_STARTED") < kinds.index("REPAIR_COMMITTED")
