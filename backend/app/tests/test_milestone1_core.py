from app.domain.grid import DynamicObstacle, Grid, ObstacleMap, Position as P
from app.domain.robot import make_plan
from app.planning.collision_detection import check_adjacent_steps, find_conflicts
from app.planning.reservation_table import ReservationTable


def plan(*cells, t0=0):
    return make_plan([P(*c) for c in cells], t0)


def test_grid_neighbors_and_bounds():
    g = Grid.from_ascii(["...", ".#.", "..."])
    assert g.width == 3 and g.height == 3
    assert not g.is_traversable(P(1, 1))
    assert set(g.neighbors(P(0, 0))) == {P(1, 0), P(0, 1)}
    assert g.traversable_count == 8
    assert g.reachable(P(0, 0), P(2, 2))


def test_obstacle_map_intervals():
    m = ObstacleMap()
    m.add(DynamicObstacle("o1", P(1, 1), 3, 5))
    m.add(DynamicObstacle("o2", P(2, 2), 4, None))
    assert not m.is_blocked(P(1, 1), 2)
    assert m.is_blocked(P(1, 1), 3) and m.is_blocked(P(1, 1), 5)
    assert not m.is_blocked(P(1, 1), 6)
    assert m.is_blocked(P(2, 2), 1000)
    m.remove("o1")
    assert not m.is_blocked(P(1, 1), 4)


def test_reservation_vertex_and_edge():
    rt = ReservationTable()
    rt.reserve_path("A", plan((0, 0), (1, 0), (2, 0)))
    assert rt.vertex_owner(P(1, 0), 1) == "A"
    assert not rt.is_vertex_free(P(1, 0), 1, "B")
    assert rt.is_vertex_free(P(1, 0), 1, "A")
    # B moving (1,0)->(0,0) at t=0 would swap with A's (0,0)->(1,0)
    assert not rt.is_edge_free(P(1, 0), P(0, 0), 0, "B")
    assert rt.is_edge_free(P(1, 0), P(0, 0), 1, "B")


def test_release_keeps_prefix():
    rt = ReservationTable()
    rt.reserve_path("A", plan((0, 0), (1, 0), (2, 0), (3, 0)))
    rt.release_robot("A", after_time=1)
    assert rt.vertex_owner(P(1, 0), 1) == "A"
    assert rt.vertex_owner(P(2, 0), 2) is None
    assert rt.is_edge_free(P(2, 0), P(1, 0), 1, "B")  # edge departing at t=1 released


def test_conflict_detection():
    a = plan((0, 0), (1, 0), (2, 0))
    b = plan((2, 0), (1, 0), (0, 0))  # vertex conflict at t=1 and swap-free
    kinds = {c.kind for c in find_conflicts({"A": a, "B": b})}
    assert "vertex" in kinds
    c = plan((0, 0), (1, 0))
    d = plan((1, 0), (0, 0))
    kinds = {x.kind for x in find_conflicts({"C": c, "D": d})}
    assert kinds == {"edge_swap"}
    e = plan((0, 0), (1, 0), (2, 0))
    f = plan((0, 1), (1, 1), (2, 1))
    assert find_conflicts({"E": e, "F": f}) == []


def test_conflict_with_obstacle_and_following_allowed():
    m = ObstacleMap()
    m.add(DynamicObstacle("o", P(1, 0), 1, 1))
    a = plan((0, 0), (1, 0), (2, 0))
    assert [c.kind for c in find_conflicts({"A": a}, obstacles=m)] == ["obstacle"]
    # following in a line is allowed
    x = plan((1, 0), (2, 0), (3, 0))
    y = plan((0, 0), (1, 0), (2, 0))
    assert find_conflicts({"X": x, "Y": y}) == []


def test_adjacent_steps():
    assert check_adjacent_steps(plan((0, 0), (0, 0), (1, 0)))
    assert not check_adjacent_steps(plan((0, 0), (2, 0)))
