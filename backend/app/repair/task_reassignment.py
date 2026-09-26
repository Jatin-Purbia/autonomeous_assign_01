"""Task pool handling for robot breakdowns and emergency tasks.

Assignment cost (lower is better):
    Cost(a_j, tau) = d(pos_j, pickup) + d(pickup, delivery) + lambda * Load(a_j) + mu * RepairImpact(a_j)
RepairImpact(a_j) = number of *other* robots whose remaining plan passes through the bounding box of
{pos_j, pickup, delivery}: a cheap proxy for how many neighbours a route of a_j would disturb.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from ..domain.grid import Position, manhattan
from ..domain.robot import Robot, RobotStatus
from ..domain.task import Task, TaskStatus
from ..simulation.event_log import EventType
from .models import RepairContext


class NoCapableRobot(ValueError):
    pass


def candidates(ctx: RepairContext, exclude: set[str] = frozenset()) -> list[Robot]:
    return [r for r in ctx.robots.values()
            if r.on_grid and r.status not in (RobotStatus.BROKEN, RobotStatus.DONE) and r.robot_id not in exclude]


def repair_impact(ctx: RepairContext, robot: Robot, pickup: Position, delivery: Position) -> int:
    xs = [robot.current_position.x, pickup.x, delivery.x]
    ys = [robot.current_position.y, pickup.y, delivery.y]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    count = 0
    for other in candidates(ctx):
        if other.robot_id == robot.robot_id:
            continue
        for tp in other.active_plan[ctx.time:]:
            p = tp.position
            if x0 <= p.x <= x1 and y0 <= p.y <= y1:
                count += 1
                break
    return count


def assignment_cost(ctx: RepairContext, robot: Robot, pickup: Position, delivery: Position) -> tuple[float, dict[str, float]]:
    cfg = ctx.config
    d1 = manhattan(robot.current_position, pickup)
    d2 = manhattan(pickup, delivery)
    load = robot.load
    impact = repair_impact(ctx, robot, pickup, delivery)
    total = d1 + d2 + cfg.lambda_load * load + cfg.mu_impact * impact
    return total, {"d_to_pickup": d1, "d_pickup_delivery": d2, "load": load, "repair_impact": impact}


def select_robot(ctx: RepairContext, pickup: Position, delivery: Position,
                 exclude: set[str] = frozenset()) -> tuple[Robot, float, dict[str, float]]:
    """a_j* = argmin Cost(a_j, tau); ties broken by robot id (deterministic)."""
    best: Optional[tuple[float, str, Robot, dict[str, float]]] = None
    for r in candidates(ctx, exclude):
        c, parts = assignment_cost(ctx, r, pickup, delivery)
        key = (c, r.robot_id)
        if best is None or key < (best[0], best[1]):
            best = (c, r.robot_id, r, parts)
    if best is None:
        raise NoCapableRobot("no active robot available")
    return best[2], best[0], best[3]


def transfer_cell(ctx: RepairContext, broken: Position, delivery: Position) -> Optional[Position]:
    """Item carried by a broken robot is handed over from a free neighbouring cell."""
    best: Optional[tuple[int, Position]] = None
    for n in ctx.grid.neighbors(broken):
        if any(o.end_time is None for o in ctx.obstacles.all() if o.position == n):
            continue  # permanently blocked neighbour
        d = manhattan(n, delivery)
        if best is None or (d, n) < (best[0], best[1]):
            best = (d, n)
    return best[1] if best else None


def reassign_unfinished(ctx: RepairContext, broken: Robot) -> list[dict[str, Any]]:
    """Return the broken robot's unfinished tasks to the pool and give each to the best active robot."""
    records: list[dict[str, Any]] = []
    for task in list(broken.tasks):
        if task.status not in (TaskStatus.PENDING, TaskStatus.PICKED):
            continue
        new = task.copy()
        new.status = TaskStatus.PENDING
        if task.status == TaskStatus.PICKED:  # parcel is stuck on the broken robot
            tc = transfer_cell(ctx, broken.current_position, task.delivery)
            if tc is None:
                raise NoCapableRobot(f"parcel of {task.task_id} cannot be recovered from {broken.current_position}")
            new.pickup = tc
        task.status = TaskStatus.REASSIGNED
        target, cost, parts = select_robot(ctx, new.pickup, new.delivery, exclude={broken.robot_id})
        target.tasks.append(new)
        rec = {"task_id": task.task_id, "from": broken.robot_id, "to": target.robot_id, "cost": round(cost, 2),
               "cost_terms": parts, "new_pickup": [new.pickup.x, new.pickup.y],
               "recovered_from_broken_robot": new.pickup != task.pickup}
        records.append(rec)
        ctx.emit(EventType.TASK_REASSIGNED, [broken.robot_id, target.robot_id], "ROBOT_BREAKDOWN", rec)
    return records


def insert_emergency(ctx: RepairContext, task: Task, preferred: Optional[str] = None) -> tuple[Robot, dict[str, Any]]:
    """Insert the emergency pickup/delivery into the chosen robot's remaining sequence (capacity 1:
    a parcel already on board is delivered first) and raise its planning priority."""
    if preferred:
        robot = ctx.robots[preferred]
        if not (robot.on_grid and robot.status not in (RobotStatus.BROKEN, RobotStatus.DONE)):
            raise ValueError(f"robot {preferred} cannot take the emergency task")
        cost, parts = assignment_cost(ctx, robot, task.pickup, task.delivery)
    else:
        robot, cost, parts = select_robot(ctx, task.pickup, task.delivery)
    task.emergency = True
    task.status = TaskStatus.PENDING
    idx = len(robot.tasks)
    for i, tk in enumerate(robot.tasks):
        if tk.status == TaskStatus.PICKED:
            idx = i + 1
            break
        if tk.status == TaskStatus.PENDING:
            idx = i
            break
    robot.tasks.insert(idx, task)
    robot.planning_priority += ctx.config.emergency_priority_boost
    robot.status = RobotStatus.EMERGENCY
    rec = {"task_id": task.task_id, "to": robot.robot_id, "cost": round(cost, 2), "cost_terms": parts,
           "inserted_at": idx, "new_priority": robot.planning_priority}
    ctx.emit(EventType.TASK_REASSIGNED, [robot.robot_id], "EMERGENCY_TASK", rec)
    return robot, rec
