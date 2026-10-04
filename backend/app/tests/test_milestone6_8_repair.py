import random

import pytest

from app.domain.metrics import plan_key
from app.domain.robot import RobotStatus
from app.domain.task import TaskStatus
from app.planning.collision_detection import find_conflicts
from app.simulation.builtin_scenarios import builtin_scenarios, get_builtin
from app.simulation.engine import EngineConfig, SimulationEngine
from app.tests.test_milestone4_engine import rb, spec

NEG_KINDS = {"REPAIR_REQUEST", "BID_SUBMITTED", "BID_ACCEPTED", "AFFECTED_SET_EXPANDED"}


def run(sid, strategy="local", **kw):
    eng = SimulationEngine(get_builtin(sid), EngineConfig(strategy=strategy, **kw))
    return eng, eng.run()


# ------------------------------------------------------------------ scenario 1
def test_scenario1_impact_one_and_affected_set_not_expanded():
    eng, res = run("s1-cell-blockage")
    assert res.success and res.num_modified == 1 and res.modified_ids == ["R1"]
    d = res.per_disruption[0]
    assert d.direct_agents == ["R1"] and d.affected_agents == ["R1"]      # no expansion needed
    assert not eng.log.of_type("AFFECTED_SET_EXPANDED")
    assert res.messages == 0


# ------------------------------------------------------------------ scenario 2 / negotiation
def test_scenario2_negotiated_repair_impact_two():
    eng, res = run("s2-negotiated-repair")
    assert res.success and res.num_modified == 2 and res.collisions == 0
    d = res.per_disruption[0]
    assert len(d.direct_agents) == 1 and len(d.affected_agents) == 2
    assert d.modified_agents == res.modified_ids
    kinds = {e.event_type for e in eng.log.events}
    assert NEG_KINDS <= kinds
    untouched = ({"R1", "R2", "R3"} - set(res.modified_ids)).pop()
    assert plan_key(eng.robots[untouched].active_plan) == plan_key(eng.robots[untouched].original_plan)


def test_message_only_agents_are_not_counted_as_modified():
    eng, res = run("s4-emergency-task")
    bidders = {r for m in eng.repairs[0]["messages"] for r in (m["sender"], m["receiver"])} - {"COORDINATOR"}
    assert bidders >= set(res.modified_ids)
    # the emergency robot's own bid is rejected-free; robots that only got messages would not be in modified
    assert set(res.modified_ids) == {r for r in eng.robots if plan_key(eng.robots[r].active_plan)
                                     != plan_key(eng.robots[r].original_plan)}


def test_baseline_a_rejects_conflicting_repair():
    eng, res = run("s2-negotiated-repair", "single_agent")
    assert not res.success and res.n_repairs_failed == 1
    assert res.collisions == 0  # failing is safe: nothing conflicting was committed
    assert all(plan_key(r.active_plan) == plan_key(r.original_plan) for r in eng.robots.values())


def test_tentative_repair_never_replaces_plans_on_failure():
    eng = SimulationEngine(spec(["......."], [rb("A", [0, 0], [([0, 0], [6, 0])])],
                                [{"id": "D", "type": "cell_blockage", "time": 1, "position": [3, 0]}]))
    before = plan_key(eng.robots["A"].active_plan)
    eng.run()
    assert plan_key(eng.robots["A"].active_plan) == before and eng.status == "failed"


# ------------------------------------------------------------------ scenario 3 / breakdown
def test_scenario3_breakdown_reassigns_and_blocks_cell():
    eng, res = run("s3-robot-breakdown")
    r2 = eng.robots["R2"]
    assert res.success and r2.status == RobotStatus.BROKEN
    pos = r2.current_position
    assert all(tp.position == pos for tp in r2.executed_prefix[r2.broken_at:]) or len(r2.executed_prefix) == r2.broken_at + 1
    # a broken robot never moves and nobody enters its cell afterwards
    for r in eng.robots.values():
        if r.robot_id != "R2":
            assert all(tp.position != pos for tp in r.executed_prefix if tp.time > r2.broken_at)
    assert eng.log.of_type("TASK_REASSIGNED")
    assert [t.status for t in r2.tasks].count(TaskStatus.REASSIGNED) >= 1
    delivered = {t.task_id for r in eng.robots.values() for t in r.tasks if t.status == TaskStatus.DELIVERED}
    assert "R2-T2" in delivered and res.remaining_tasks == 0
    assert r2.robot_id in res.modified_ids and "R3" not in res.modified_ids


def test_breakdown_with_parcel_on_board_is_transferred():
    sp = spec(["........", "........"],
              [rb("A", [0, 0], [([0, 0], [7, 0])]), rb("B", [0, 1], [([0, 1], [7, 1])])],
              [{"id": "D", "type": "robot_breakdown", "time": 3, "robot_id": "A"}])
    eng = SimulationEngine(sp)
    res = eng.run()
    assert res.success and res.remaining_tasks == 0
    rec = eng.log.of_type("TASK_REASSIGNED")[0].details
    assert rec["to"] == "B" and rec["recovered_from_broken_robot"]
    assert eng.robots["A"].current_position.x == 3


def test_breakdown_with_no_capable_robot_fails_cleanly():
    sp = spec(["........"], [rb("A", [0, 0], [([0, 0], [7, 0])])],
              [{"id": "D", "type": "robot_breakdown", "time": 3, "robot_id": "A"}])
    res = SimulationEngine(sp).run()
    assert not res.success and "no active robot" in res.failure_reason


def test_disruption_on_finished_robot_is_rejected_not_crashing():
    sp = spec(["...."], [rb("A", [0, 0], [([0, 0], [1, 0])])],
              [{"id": "D", "type": "robot_breakdown", "time": 5, "robot_id": "A"}])
    eng = SimulationEngine(sp)
    res = eng.run()
    assert res.success and eng.status == "completed"


# ------------------------------------------------------------------ scenario 4 / emergency
def test_scenario4_emergency_priority_and_yielding():
    eng, res = run("s4-emergency-task")
    r1 = eng.robots["R1"]
    assert res.success and r1.planning_priority > 1000
    assert {"E1"} <= {t.task_id for t in r1.tasks if t.status == TaskStatus.DELIVERED}
    assert res.modified_ids == ["R1", "R2"]                   # R2 yielded, R3-R5 untouched
    bids = [e.details for e in eng.log.of_type("BID_SUBMITTED")]
    emergency_bid = next(b for b in bids if b["robot"] == "R1")
    other_bid = next(b for b in bids if b["robot"] == "R2")
    assert emergency_bid["cost"] > 10 * other_bid["cost"]     # yielding is very expensive for the emergency robot
    assert eng.log.of_type("PRIORITY_UPDATE")


def test_emergency_is_inserted_after_parcel_on_board():
    sp = spec(["........"], [rb("A", [0, 0], [([0, 0], [7, 0])])],
              [{"id": "E", "type": "emergency_task", "time": 2, "robot_id": "A",
                "task": {"id": "E1", "pickup": [3, 0], "delivery": [1, 0]}}])
    eng = SimulationEngine(sp)
    eng.run()
    order = [(e.event_type, e.details["task_id"]) for e in eng.log.events
             if e.event_type in ("PICKUP_COMPLETED", "DELIVERY_COMPLETED")]
    assert order.index(("DELIVERY_COMPLETED", "A-T0")) < order.index(("PICKUP_COMPLETED", "E1"))


# ------------------------------------------------------------------ fuzz: invariants after every timestep
@pytest.mark.parametrize("seed", range(4))
def test_fuzz_random_disruptions_keep_all_invariants(seed):
    from app.simulation.scenario_generator import generate_random_scenario
    rng = random.Random(seed)
    for k in range(6):
        sp = generate_random_scenario(rng.randint(4, 10), seed=seed * 100 + k, width=12, height=8)
        eng = SimulationEngine(sp, EngineConfig(record_movement=False))
        if eng.status == "failed":
            continue
        ds = []
        for i in range(rng.randint(1, 4)):
            rid = rng.choice(list(eng.robots))
            plan = eng.robots[rid].original_plan
            if len(plan) < 5:
                continue
            tp = plan[rng.randint(2, len(plan) - 2)]
            kind = rng.choice(["cell", "cell", "break", "emergency"])
            t = max(1, tp.time - rng.randint(1, 3))
            if kind == "cell":
                ds.append({"id": f"D{i}", "type": "cell_blockage", "time": t,
                           "position": [tp.position.x, tp.position.y], "duration": rng.choice([None, 4, 8])})
            elif kind == "break":
                ds.append({"id": f"D{i}", "type": "robot_breakdown", "time": t, "robot_id": rid})
            else:
                cells = eng.grid.traversable_cells()
                pu, de = rng.sample(cells, 2)
                ds.append({"id": f"D{i}", "type": "emergency_task", "time": t,
                           "task": {"id": f"E{i}", "pickup": [pu.x, pu.y], "delivery": [de.x, de.y]}})
        sp["disruptions"] = ds
        eng = SimulationEngine(sp, EngineConfig(record_movement=False, dev_checks=True))
        res = eng.run()  # raises CollisionError / InvariantError on any violation
        assert res.collisions == 0
        live = {r.robot_id: r.executed_prefix for r in eng.robots.values()}
        assert find_conflicts(live) == []  # executed trajectories are collision-free


def test_emergency_pickup_on_robots_current_cell_completes_immediately():
    # regression: waypoint on the robot's own cell must be registered when the repair commits
    sp = spec(["........"], [rb("A", [0, 0], [([0, 0], [7, 0])])],
              [{"id": "E", "type": "emergency_task", "time": 2, "robot_id": "A",
                "task": {"id": "E1", "pickup": [2, 0], "delivery": [0, 0]}}])
    eng = SimulationEngine(sp)
    res = eng.run()
    assert res.success and res.remaining_tasks == 0
    assert all(t.status == TaskStatus.DELIVERED for t in eng.robots["A"].tasks)


def test_message_only_neighbour_is_not_counted_as_modified():
    """With no emergency priority bias the emergency robot's own yield is cheaper than R2's, so R2 receives
    REPAIR_REQUEST / BID / REJECT messages but its plan is never changed -> it must not count as modified."""
    from app.repair.models import RepairConfig
    cfg = EngineConfig(repair=RepairConfig(emergency_priority_penalty=0.0, emergency_priority_boost=0))
    eng = SimulationEngine(get_builtin("s4-emergency-task"), cfg)
    res = eng.run()
    assert res.success
    kinds = [(m["kind"], m["receiver"]) for m in eng.repairs[0]["messages"]]
    assert ("REPAIR_REQUEST", "R2") in kinds and ("REJECT", "R2") in kinds   # R2 exchanged messages ...
    assert res.messages >= 3
    assert "R2" not in res.modified_ids and res.modified_ids == ["R1"]      # ... but was not modified
    assert plan_key(eng.robots["R2"].active_plan) == plan_key(eng.robots["R2"].original_plan)
