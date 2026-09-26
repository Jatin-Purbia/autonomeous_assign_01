"""Built-in demonstration scenarios (plain spec dicts, see scenario_loader)."""
from __future__ import annotations

import copy
from typing import Any

from .scenario_generator import generate_random_scenario

WH = [
    "............",
    ".##..##..##.",
    ".##..##..##.",
    "............",
    ".##..##..##.",
    ".##..##..##.",
    "............",
]


def _r(rid, start, tasks, priority=None):
    d = {"id": rid, "start": list(start),
         "tasks": [{"id": f"{rid}-T{i + 1}", "pickup": list(p), "delivery": list(q), "priority": 1}
                   for i, (p, q) in enumerate(tasks)]}
    if priority is not None:
        d["priority"] = priority
    return d


def scenario_1_cell_blockage() -> dict[str, Any]:
    return {
        "id": "s1-cell-blockage", "name": "1. Cell blockage - small detour",
        "description": "R1 drives down the 2-wide aisle at x=3. At t=1 cell (3,3) is blocked for good. R1 finds a "
                       "2-step detour through the neighbouring aisle lane; every other plan stays identical "
                       "(expected Impact = 1).",
        "expected_impact": 1, "map": WH, "seed": 1,
        "robots": [_r("R1", (3, 0), [((3, 0), (3, 6))]),
                   _r("R2", (8, 0), [((8, 0), (11, 0))]),
                   _r("R3", (0, 6), [((0, 6), (5, 6))])],
        "disruptions": [{"id": "D1", "type": "cell_blockage", "time": 1, "position": [3, 3]}],
    }


def scenario_2_negotiated_repair() -> dict[str, Any]:
    return {
        "id": "s2-negotiated-repair", "name": "2. Negotiated repair - a neighbour yields",
        "description": "Cell (0,3) becomes blocked at t=6, invalidating R1's route. R1's only repaired route cuts "
                       "through R3's reserved route, so R1 negotiates (REPAIR_REQUEST / BID / ACCEPT) and R3 yields "
                       "with a short shift (expected Impact = 2); R2 stays untouched.",
        "expected_impact": 2,
        "map": ["............", ".####..####.", "............", ".####..####.", "............"], "seed": 2,
        "robots": [_r("R1", (5, 1), [((1, 4), (3, 0))]),
                   _r("R2", (0, 3), [((1, 2), (9, 0))]),
                   _r("R3", (10, 2), [((8, 2), (0, 4))])],
        "disruptions": [{"id": "D1", "type": "cell_blockage", "time": 6, "position": [0, 3]}],
    }


def scenario_3_robot_breakdown() -> dict[str, Any]:
    return {
        "id": "s3-robot-breakdown", "name": "3. Robot breakdown in a narrow aisle",
        "description": "R2 breaks down at t=3 in the 1-wide aisle at y=3. Its cell becomes blocked, its unfinished "
                       "task is reassigned to the best active robot, and only the robots whose paths conflict "
                       "are repaired.",
        "map": WH, "seed": 3,
        "robots": [_r("R1", (0, 3), [((0, 3), (11, 3))]),
                   _r("R2", (11, 3), [((11, 3), (0, 3)), ((0, 0), (5, 0))]),
                   _r("R3", (0, 6), [((0, 6), (11, 6))]),
                   _r("R4", (6, 0), [((6, 0), (6, 6))])],
        "disruptions": [{"id": "D1", "type": "robot_breakdown", "time": 3, "robot_id": "R2"}],
    }


def scenario_4_emergency_task() -> dict[str, Any]:
    return {
        "id": "s4-emergency-task", "name": "4. Emergency task",
        "description": "R1 has a short task. At t=1 an emergency task (pickup (1,3) -> delivery (11,3)) is inserted "
                       "into R1's plan and its priority is raised. Its shortest route runs head-on into R2 in the "
                       "1-wide aisle: R1's own yield bid is huge (priority penalty), so R2 yields with a detour. "
                       "R3-R5 are not touched.",
        "map": WH, "seed": 4,
        "robots": [_r("R1", (0, 0), [((0, 0), (0, 2))]),
                   _r("R2", (11, 3), [((11, 3), (0, 3))]),
                   _r("R3", (3, 0), [((3, 0), (3, 6))]),
                   _r("R4", (8, 6), [((8, 6), (8, 0))]),
                   _r("R5", (11, 6), [((11, 6), (6, 6))])],
        "disruptions": [{"id": "D1", "type": "emergency_task", "time": 1, "robot_id": "R1",
                         "task": {"id": "E1", "pickup": [1, 3], "delivery": [11, 3], "priority": 10}}],
    }


def scenario_5_stress() -> dict[str, Any]:
    spec = generate_random_scenario(30, seed=5, width=20, height=14)
    spec.update({"id": "s5-stress", "name": "5. Stress - 30 robots, many blockages",
                 "description": "30 robots on a 20x14 warehouse with 12 dynamic blockages (~ 6% of free cells) "
                                "and a robot breakdown. Watch the affected set grow."})
    spec["disruptions"] = [
        {"id": f"D{i + 1}", "type": "cell_blockage", "time": 3 + 2 * i, "position": p, "duration": 12}
        for i, p in enumerate([[3, 0], [8, 3], [13, 0], [6, 7], [10, 7], [3, 10], [15, 3], [18, 7], [8, 11],
                               [13, 10], [1, 7], [16, 11]])
    ]
    spec["disruptions"].append({"id": "D13", "type": "robot_breakdown", "time": 8, "robot_id": "R6"})
    return spec


def builtin_scenarios() -> dict[str, dict[str, Any]]:
    fns = [scenario_1_cell_blockage, scenario_2_negotiated_repair, scenario_3_robot_breakdown,
           scenario_4_emergency_task, scenario_5_stress]
    return {s["id"]: s for s in (f() for f in fns)}


def get_builtin(scenario_id: str) -> dict[str, Any]:
    return copy.deepcopy(builtin_scenarios()[scenario_id])
