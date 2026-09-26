from app.domain.grid import DynamicObstacle, Grid, ObstacleMap, Position as P
from app.domain.robot import make_plan
from app.planning.collision_detection import check_adjacent_steps
from app.planning.heuristics import advance_waypoints, chain_heuristic, chain_tail, waypoint_times
from app.planning.reservation_table import ReservationTable
from app.planning.space_time_astar import PlanningContext, space_time_astar


def ctx_for(rows, table=None, obstacles=None):
    return PlanningContext(Grid.from_ascii(rows), obstacles or ObstacleMap(), table or ReservationTable())


def test_empty_grid_shortest_path():
    ctx = ctx_for(["....."] * 5)
    r = space_time_astar(ctx, "A", P(0, 0), 0, [P(4, 4)])
    assert r.found and len(r.path) == 9  # 8 moves
    assert r.path[0] == P(0, 0) and r.path[-1] == P(4, 4)
    assert check_adjacent_steps(make_plan(r.path))


def test_avoids_static_obstacles():
    ctx = ctx_for(["...", ".#.", "..."])
    r = space_time_astar(ctx, "A", P(0, 1), 0, [P(2, 1)])
    assert r.found and P(1, 1) not in r.path and len(r.path) == 5


def test_no_path_returns_failure():
    ctx = ctx_for([".#.", ".#.", ".#."])
    r = space_time_astar(ctx, "A", P(0, 0), 0, [P(2, 0)])
    assert not r.found and r.failure == "unreachable"


def test_permanent_dynamic_block_returns_failure():
    obs = ObstacleMap()
    obs.add(DynamicObstacle("o", P(1, 0), 0, None))
    ctx = ctx_for(["...", "###", "..."][:1] + ["###"], obstacles=obs)
    r = space_time_astar(ctx, "A", P(0, 0), 0, [P(2, 0)])
    assert not r.found


def test_waits_when_necessary():
    # one-wide corridor; another robot occupies the middle at t=1 -> must wait
    tbl = ReservationTable()
    tbl.reserve_path("B", make_plan([P(1, 0), P(1, 0), P(1, 0)]))  # B sits at (1,0) t=0..2
    ctx = ctx_for(["..."], table=tbl)
    # A starts at (0,0)... B occupies (1,0) t=0..2; corridor is 1-wide so A must wait until t=3
    r = space_time_astar(ctx, "A", P(0, 0), 0, [P(2, 0)])
    assert r.found
    assert r.path == [P(0, 0), P(0, 0), P(0, 0), P(1, 0), P(2, 0)][: len(r.path)]
    assert r.path[3] == P(0, 0) or r.path[3] == P(1, 0)
    assert len(r.path) == 5 and r.path[-1] == P(2, 0)


def test_respects_vertex_reservation():
    tbl = ReservationTable()
    tbl.reserve_path("B", make_plan([P(1, 0), P(2, 0), P(2, 0)]))
    ctx = ctx_for([".....", "....."], table=tbl)
    r = space_time_astar(ctx, "A", P(0, 0), 0, [P(4, 0)])
    assert r.found
    for t, p in enumerate(r.path):
        assert tbl.is_vertex_free(p, t, "A")


def test_prevents_edge_swap():
    tbl = ReservationTable()
    tbl.reserve_path("B", make_plan([P(1, 0), P(0, 0)]))  # B: (1,0)->(0,0) at t=0
    ctx = ctx_for(["..", ".."], table=tbl)
    # A at (0,0) wants (1,0): direct move at t=0 would swap with B. But also vertex (1,0)@1 free,
    # so only the swap check blocks it.
    r = space_time_astar(ctx, "A", P(0, 0), 0, [P(1, 0)])
    assert r.found
    assert not (r.path[0] == P(0, 0) and r.path[1] == P(1, 0))


def test_pickup_before_delivery_order():
    ctx = ctx_for(["......"])
    # delivery cell lies between start and pickup; must still reach pickup first
    r = space_time_astar(ctx, "A", P(0, 0), 0, [P(5, 0), P(2, 0)])
    assert r.found
    times, q = waypoint_times(r.path, 0, [P(5, 0), P(2, 0)])
    assert q == 2 and times[0] < times[1] and times[0] == 5 and times[1] == 8


def test_multi_waypoint_and_heuristic_admissible():
    wps = [P(3, 0), P(3, 3), P(0, 3)]
    tail = chain_tail(wps)
    assert chain_heuristic(P(0, 0), 0, wps, tail) == 3 + 3 + 3
    ctx = ctx_for(["....", "....", "....", "...."])
    r = space_time_astar(ctx, "A", P(0, 0), 0, wps)
    assert r.found and len(r.path) - 1 == 9  # heuristic is exact on an empty grid


def test_blocked_interval_waited_out():
    obs = ObstacleMap()
    obs.add(DynamicObstacle("o", P(1, 0), 1, 4))
    ctx = ctx_for(["..."], obstacles=obs)
    r = space_time_astar(ctx, "A", P(0, 0), 0, [P(2, 0)])
    assert r.found
    for t, p in enumerate(r.path):
        assert not obs.is_blocked(p, t)
    assert len(r.path) - 1 == 6  # wait until t=5 to enter (1,0), then arrive at t=6


def test_start_on_waypoint_and_advance():
    assert advance_waypoints(0, P(1, 1), [P(1, 1), P(1, 1), P(2, 2)]) == 2
    ctx = ctx_for(["..."])
    r = space_time_astar(ctx, "A", P(0, 0), 0, [P(0, 0)])
    assert r.path == [P(0, 0)]
