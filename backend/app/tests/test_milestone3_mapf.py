import random

from app.domain.grid import Position as P
from app.planning.collision_detection import check_adjacent_steps, find_conflicts
from app.planning.heuristics import waypoint_times
from app.planning.prioritized_mapf import apply_initial_plans, plan_all
from app.tests.helpers import grid_of, mk_robot


def test_plans_are_collision_free_head_on_corridor_with_pocket():
    g = grid_of(["########.##",
                 "...........",
                 "########.##"])
    a = mk_robot("A", (0, 1), [((0, 1), (10, 1))], priority=2)
    b = mk_robot("B", (10, 1), [((10, 1), (0, 1))], priority=1)
    res = plan_all(g, [a, b])
    assert res.success and res.phase == "INITIAL_PLANNING"
    assert find_conflicts(res.plans) == []
    assert all(check_adjacent_steps(p) for p in res.plans.values())


def test_priority_order_respected():
    g = grid_of(["....."] * 3)
    hi = mk_robot("HI", (0, 1), [((0, 1), (4, 1))], priority=5)
    lo = mk_robot("LO", (4, 1), [((4, 1), (0, 1))], priority=1)
    res = plan_all(g, [lo, hi])
    assert res.order[0] == "HI"
    assert len(res.plans["HI"]) - 1 == 4  # highest priority gets its shortest path
    assert find_conflicts(res.plans) == []


def test_multiple_pickups_and_deliveries():
    g = grid_of(["......"] * 4)
    r = mk_robot("R", (0, 0), [((2, 0), (5, 0)), ((5, 3), (0, 3))])
    res = plan_all(g, [r])
    assert res.success
    wps = [w.position for w in r.remaining_waypoints()]
    times, q = waypoint_times([tp.position for tp in res.plans["R"]], 0, wps)
    assert q == 4 and times == sorted(times)


def test_detects_unsolvable():
    g = grid_of([".#.", ".#.", ".#."])
    a = mk_robot("A", (0, 0), [((0, 1), (2, 2))])
    res = plan_all(g, [a])
    assert not res.success and res.failed_robot == "A" and res.failure_reason == "unreachable"


def test_priority_retry_used_for_deadlocking_order():
    # A (highest priority) sits in a dead-end pocket waiting for nothing; B must cross A's start.
    g = grid_of(["#.#",
                 "...",
                 "#.#"])
    a = mk_robot("A", (1, 1), [((1, 1), (1, 0))], priority=3)
    b = mk_robot("B", (1, 2), [((1, 2), (1, 0))], priority=2)
    res = plan_all(g, [a, b])
    # (1,0) can only be a final delivery cell for one robot at a time, both still succeed
    assert res.success and find_conflicts(res.plans) == []


def test_random_many_robots_collision_free():
    rng = random.Random(3)
    g = grid_of(["." * 12] * 12)
    cells = [P(x, y) for x in range(12) for y in range(12)]
    starts = rng.sample(cells, 15)
    robots = []
    for i, s in enumerate(starts):
        pu, de = rng.sample(cells, 2)
        robots.append(mk_robot(f"R{i}", tuple(s), [(tuple(pu), tuple(de))], priority=15 - i))
    res = plan_all(g, robots)
    assert res.success
    assert find_conflicts(res.plans) == []
    apply_initial_plans(robots, res)
    assert all(r.original_plan[0].position == r.initial_position for r in robots)


def test_tight_head_on_corridor_is_reported_as_failure_not_collision():
    # Single pocket at the exact meeting point: prioritized planning is incomplete here.
    g = grid_of(["#####.#####",
                 "...........",
                 "#####.#####"])
    a = mk_robot("A", (0, 1), [((0, 1), (10, 1))], priority=2)
    b = mk_robot("B", (10, 1), [((10, 1), (0, 1))], priority=1)
    res = plan_all(g, [a, b], max_retries=3)
    assert not res.success and res.failed_robot in ("A", "B")
    assert res.retries >= 1
