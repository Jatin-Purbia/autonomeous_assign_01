import time

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def init(sid="s1-cell-blockage", **kw):
    r = client.post("/api/simulation/initialize", json={"scenario_id": sid, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def test_scenarios_listed():
    r = client.get("/api/scenarios")
    ids = [s["id"] for s in r.json()]
    assert len(ids) >= 5 and "s1-cell-blockage" in ids and "s5-stress" in ids


def test_initialize_step_and_state():
    st = init()
    assert st["state"]["time"] == 0 and len(st["state"]["robots"]) == 3
    r = client.post("/api/simulation/step")
    assert r.json()["time"] == 1
    assert client.get("/api/simulation/state").json()["state"]["time"] == 1
    m = client.get("/api/simulation/metrics").json()
    assert m["collisions"] == 0 and m["n_agents"] == 3


def test_dynamic_block_now_triggers_repair_and_reports_it():
    init("s1-cell-blockage")
    # scenario's own disruption is scheduled at t=1; run to t=3 then block another cell live
    for _ in range(3):
        client.post("/api/simulation/step")
    state = client.get("/api/simulation/state").json()["state"]
    r1 = next(r for r in state["robots"] if r["id"] == "R3")
    target = r1["active_plan"][5]
    r = client.post("/api/disruptions/block-cell", json={"x": target[0], "y": target[1], "duration": 6})
    assert r.status_code == 200 and r.json()["ok"], r.text
    st = client.get("/api/simulation/state").json()["state"]
    assert st["last_repair"] is not None and st["obstacles"]


def test_break_robot_emergency_and_schedule():
    init("s3-robot-breakdown")
    r = client.post("/api/disruptions/emergency-task",
                    json={"pickup": {"x": 0, "y": 0}, "delivery": {"x": 5, "y": 0}, "activation_time": 4})
    assert r.json()["scheduled"] is True
    assert len(client.get("/api/simulation/state").json()["state"]["scheduled"]) >= 2
    r = client.post("/api/disruptions/break-robot", json={"robot_id": "NOPE"})
    assert r.status_code == 400


def test_random_scenario_and_run_to_completion_via_steps():
    r = client.post("/api/simulation/initialize", json={"random": {"n_agents": 6, "seed": 3}})
    assert r.status_code == 200
    for _ in range(300):
        c = client.post("/api/simulation/step").json()
        if c["status"] in ("completed", "failed"):
            break
    assert c["status"] == "completed"


def test_reset_restores_time_zero():
    init()
    client.post("/api/simulation/step")
    client.post("/api/simulation/reset")
    assert client.get("/api/simulation/state").json()["state"]["time"] == 0


def test_websocket_pushes_state():
    init()
    with client.websocket_connect("/ws/simulation") as ws:
        first = ws.receive_json()
        assert first["type"] == "state"
        ws.send_json({"cmd": "step"})
        msg = ws.receive_json()
        assert msg["state"]["time"] == 1 and "events" in msg


def test_invalid_requests_are_400():
    assert client.post("/api/simulation/initialize", json={}).status_code == 400
    assert client.post("/api/simulation/initialize",
                       json={"scenario_id": "s1-cell-blockage", "repair_config": {"bogus": 1}}).status_code == 400
    assert client.post("/api/experiments/run", json={"disruption_type": "nope"}).status_code == 422


def test_experiment_job_runs_and_exports(tmp_path, monkeypatch):
    from app.api import state as api_state
    monkeypatch.setattr(api_state, "OUTPUT_DIR", tmp_path)
    r = client.post("/api/experiments/run", json={"agent_counts": [4], "densities": [0.0, 0.1],
                                                  "repetitions": 2, "disruption_type": "cell_blockage"})
    assert r.status_code == 200
    eid = r.json()["experiment_id"]
    for _ in range(120):
        j = client.get(f"/api/experiments/{eid}").json()
        if j["status"] in ("done", "failed"):
            break
        time.sleep(0.5)
    assert j["status"] == "done", j
    assert j["result"]["summary"] and j["done"] == j["total"] == 12
    csv = client.get(f"/api/experiments/{eid}/export?format=csv")
    assert csv.status_code == 200 and "success_rate" in csv.text
    assert client.get(f"/api/experiments/{eid}/export?format=json").json()["config"]["agent_counts"] == [4]
