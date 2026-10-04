"""Discrete-time, synchronous execution engine.

One call to :meth:`SimulationEngine.step` performs, in order:
  1. activate scheduled disruptions            (repair happens here, never a global restart)
  2. observe robot / obstacle state
  3. validate each robot's next planned step   (safety net; triggers repair if a plan is invalid)
  4. detect new vertex / edge conflicts        (same safety net)
  5. execute all valid actions simultaneously  (with collision assertions)
  6. update pickup / delivery status
  7. log events
The engine is independent of the frontend: the API layer only calls ``step``/``snapshot``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..domain.disruption import Disruption
from ..domain.grid import ObstacleMap, Position, TimedPosition
from ..domain.metrics import (DisruptionImpact, SimulationResult, flowtime, makespan, modified_agents,
                              plan_key)
from ..domain.robot import Robot, RobotStatus, pos_at
from ..domain.task import TaskStatus
from ..planning.collision_detection import check_adjacent_steps, find_conflicts
from ..planning.prioritized_mapf import apply_initial_plans, plan_all
from ..planning.reservation_table import ReservationTable
from ..repair.models import RepairConfig, RepairContext, RepairResult
from .event_log import EventLog, EventType
from .event_scheduler import DisruptionScheduler
from .scenario_loader import Scenario, build_scenario, disruption_to_spec, task_to_spec


class CollisionError(AssertionError):
    """Raised when the engine detects an (accidental) vertex or edge collision."""


class InvariantError(AssertionError):
    pass


@dataclass
class EngineConfig:
    strategy: str = "local"         # "local" (proposed) | "single_agent" (baseline A)
    max_time: int = 800
    dev_checks: bool = True         # run invariant checks after every timestep
    record_movement: bool = True    # ROBOT_MOVED / ROBOT_WAITED events
    planning_retries: int = 5
    seed: int = 0
    repair: RepairConfig = field(default_factory=RepairConfig)


class SimulationEngine:
    def __init__(self, scenario: Scenario | dict[str, Any], config: Optional[EngineConfig] = None) -> None:
        self.config = config or EngineConfig()
        self.scenario = build_scenario(scenario) if isinstance(scenario, dict) else scenario
        self.reset()

    # ------------------------------------------------------------------ lifecycle
    def reset(self) -> None:
        sc = build_scenario(self.scenario.spec)
        self.scenario = sc
        self.grid = sc.grid
        self.robots: dict[str, Robot] = {r.robot_id: r for r in sc.robots}
        self.obstacles = ObstacleMap()
        self.table = ReservationTable()
        self.scheduler = DisruptionScheduler(sc.disruptions)
        self.log = EventLog(self.config.record_movement)
        self.time = 0
        self.status = "ready"  # ready | running | completed | failed
        self.failure_reason: Optional[str] = None
        self.repairs: list[dict[str, Any]] = []
        self.disruption_impacts: list[DisruptionImpact] = []
        self.modified_ids: set[str] = set()
        self.pickup_times: dict[str, int] = {}
        self.delivery_times: dict[str, int] = {}
        self.collisions = 0
        self.total_repair_ms = 0.0
        self.total_messages = 0
        self.conflicts_avoided = 0
        self.total_expansions = 0
        self.max_affected = 0
        self.n_repairs_failed = 0
        self.deadlocks = 0
        self.original_flowtime = 0
        self.original_makespan = 0
        self.original_path_length = 0
        self.last_repair: Optional[dict[str, Any]] = None
        self.initial_plan_info: dict[str, Any] = {}
        self.initialize()

    def initialize(self) -> None:
        """Initial prioritized Space-Time A* planning (this is *not* disruption repair)."""
        robots = list(self.robots.values())
        res = plan_all(self.grid, robots, self.obstacles, self.config.planning_retries, self.config.seed)
        self.initial_plan_info = {"phase": res.phase, "order": res.order, "retries": res.retries,
                                  "runtime_ms": round(res.runtime_ms, 3), "success": res.success}
        if not res.success:
            self.status = "failed"
            self.failure_reason = f"initial planning failed for {res.failed_robot} ({res.failure_reason})"
            self.log.add(0, EventType.SIMULATION_FAILED, [res.failed_robot] if res.failed_robot else [],
                         "INITIAL_PLANNING_FAILED", self.initial_plan_info)
            for r in robots:  # keep robots drawable
                r.active_plan = [TimedPosition(r.current_position, 0)]
                r.original_plan = list(r.active_plan)
                r.executed_prefix = list(r.active_plan)
            return
        apply_initial_plans(robots, res)
        self.rebuild_table()
        for r in robots:
            ops = len(r.original_plan) - 1
            self.original_flowtime += ops
            self.original_makespan = max(self.original_makespan, ops)
            self.original_path_length += sum(1 for a, b in zip(r.original_plan, r.original_plan[1:])
                                             if a.position != b.position)
        self.log.add(0, EventType.INITIAL_PLAN_CREATED, [r.robot_id for r in robots], "INITIAL_PLANNING",
                     {**self.initial_plan_info,
                      "plan_lengths": {r.robot_id: len(r.original_plan) - 1 for r in robots}})
        for r in robots:
            self._process_waypoints(r, 0)
        self._finalize_done(0)
        self._check_completion()

    def rebuild_table(self) -> None:
        """Rebuild the live reservation table from all on-grid robots' active plans."""
        self.table = ReservationTable()
        for r in self.robots.values():
            if r.on_grid and r.status != RobotStatus.BROKEN:
                self.table.reserve_path(r.robot_id, r.active_plan, from_time=self.time)

    # ------------------------------------------------------------------ waypoint / task progress
    def _process_waypoints(self, robot: Robot, t: int) -> None:
        while True:
            wps = robot.remaining_waypoints()
            if not wps or wps[0].position != robot.current_position:
                break
            w = wps[0]
            task = next(tk for tk in robot.tasks if tk.task_id == w.task_id)
            if w.kind == "pickup":
                task.status = TaskStatus.PICKED
                self.pickup_times[task.task_id] = t
                self.log.add(t, EventType.PICKUP_COMPLETED, [robot.robot_id], "TASK_PROGRESS",
                             {"task_id": task.task_id, "position": list(robot.current_position)})
            else:
                task.status = TaskStatus.DELIVERED
                task.completed_at = t
                self.delivery_times[task.task_id] = t
                self.log.add(t, EventType.DELIVERY_COMPLETED, [robot.robot_id], "TASK_PROGRESS",
                             {"task_id": task.task_id, "position": list(robot.current_position)})
        unfinished = [i for i, tk in enumerate(robot.tasks) if tk.status in (TaskStatus.PENDING, TaskStatus.PICKED)]
        robot.current_task_index = unfinished[0] if unfinished else len(robot.tasks)

    def _finalize_done(self, t: int) -> None:
        for r in self.robots.values():
            if r.on_grid and r.status not in (RobotStatus.BROKEN, RobotStatus.DONE) and not r.remaining_waypoints():
                r.status = RobotStatus.DONE
                r.completion_time = t
                if r.active_plan and r.active_plan[-1].time > t:  # drop superfluous tail
                    r.active_plan = r.active_plan[: t + 1]
                self.log.add(t, EventType.ROBOT_FINISHED, [r.robot_id], "ALL_TASKS_DELIVERED", {"completion_time": t})

    def _check_completion(self) -> None:
        if self.status in ("completed", "failed"):
            return
        if all(r.status in (RobotStatus.DONE, RobotStatus.BROKEN) for r in self.robots.values()):
            left = sum(1 for r in self.robots.values() for tk in r.tasks
                       if tk.status in (TaskStatus.PENDING, TaskStatus.PICKED) and r.status != RobotStatus.BROKEN)
            self.status = "completed"
            self.log.add(self.time, EventType.SIMULATION_COMPLETED, [], "ALL_TASKS_DONE",
                         {"flowtime": self._flowtime(), "makespan": self._makespan(), "remaining": left})

    def _fail(self, reason: str, code: str, robot_ids: Optional[list[str]] = None) -> None:
        self.status = "failed"
        self.failure_reason = reason
        self.log.add(self.time, EventType.SIMULATION_FAILED, robot_ids or [], code, {"message": reason})

    # ------------------------------------------------------------------ disruptions
    def schedule_disruption(self, d: Disruption) -> None:
        self.scheduler.schedule(d)

    def inject(self, d: Disruption) -> Optional[RepairResult]:
        """Apply a disruption *now* (at the current, paused timestep)."""
        if self.status in ("completed", "failed"):
            raise ValueError("simulation is not running")
        d.activation_time = self.time
        self.scheduler.activated.append(d)
        result = self._activate(d)
        self._check_completion()
        return result

    def remove_obstacle(self, obstacle_id: str) -> bool:
        obs = self.obstacles.get(obstacle_id)
        if obs is None or obs.owner_robot_id is not None:
            return False
        # the obstacle disappears from the *next* timestep on; plans stay valid (they only got more freedom)
        self.obstacles.remove(obstacle_id)
        return True

    def _activate(self, d: Disruption) -> Optional[RepairResult]:
        from ..repair.dispatcher import apply_disruption  # local import: repair depends on models only

        t = self.time
        self.log.add(t, EventType.DISRUPTION_ACTIVATED, [d.affected_robot_id] if d.affected_robot_id else [],
                     d.type.value.upper(), {"disruption_id": d.disruption_id,
                                            **disruption_to_spec(d)})
        ctx = self._repair_context()
        before = {rid: list(r.active_plan) for rid, r in self.robots.items()}
        try:
            result = apply_disruption(ctx, d, self.config.strategy)
        except ValueError as exc:  # invalid request (e.g. robot already finished)
            self.log.add(t, EventType.REPAIR_FAILED, [], "INVALID_DISRUPTION", {"message": str(exc)})
            raise
        self._finish_repair(result, before, d)
        return result

    def _repair_context(self) -> RepairContext:
        return RepairContext(self.grid, self.robots, self.obstacles, self.table, self.time,
                             self.config.repair, self._emit)

    def _emit(self, event_type, robot_ids=None, reason=None, details=None) -> None:
        self.log.add(self.time, event_type, robot_ids, reason, details)

    def _finish_repair(self, result: RepairResult, before: dict[str, list[TimedPosition]],
                       d: Optional[Disruption]) -> None:
        t = self.time
        self.total_repair_ms += result.runtime_ms
        self.total_messages += len(result.messages)
        self.conflicts_avoided += result.conflicts_avoided
        self.total_expansions += len(result.expansions)
        self.max_affected = max(self.max_affected, len(result.affected))
        imp = DisruptionImpact(
            d.disruption_id if d else "reactive", d.type.value if d else "plan_invalidation", t,
            direct_agents=list(result.direct), affected_agents=list(result.affected),
            messages=len(result.messages), runtime_ms=result.runtime_ms, success=result.success,
            strategy=result.strategy, expansions=len(result.expansions))
        if not result.success:
            self.n_repairs_failed += 1
            self.deadlocks += 1 if result.deadlock else 0
            self.disruption_impacts.append(imp)
            self.last_repair = result.summary()
            self.repairs.append({"time": t, "disruption_id": imp.disruption_id, **result.summary()})
            self.log.add(t, EventType.REPAIR_FAILED, result.affected or result.direct, "NO_REPAIR_FOUND",
                         {"reason": result.failure_reason, "strategy": result.strategy})
            self._fail(f"repair failed: {result.failure_reason}", "REPAIR_FAILED", result.affected)
            return
        # ---- atomic commit -------------------------------------------------------------
        unchanged_before = {rid: plan_key(p) for rid, p in before.items() if rid not in result.new_plans}
        for rid, plan in result.new_plans.items():
            robot = self.robots[rid]
            self._assert([tp.position for tp in plan[: t + 1]]
                         == [tp.position for tp in robot.executed_prefix[: t + 1]],
                         f"executed prefix of {rid} would change")
            robot.active_plan = list(plan)
        for rid, plan in before.items():
            if rid not in result.new_plans:
                self._assert(plan_key(self.robots[rid].active_plan) == unchanged_before[rid],
                             f"unaffected plan of {rid} changed")
        modified = modified_agents(before, {rid: r.active_plan for rid, r in self.robots.items()})
        result.modified = modified
        self.modified_ids.update(modified)
        imp.modified_agents = modified
        imp.impact = len(modified)
        self.disruption_impacts.append(imp)
        self.rebuild_table()
        for r in self.robots.values():  # a new waypoint on the robot's current cell completes immediately
            if r.on_grid and r.status not in (RobotStatus.BROKEN, RobotStatus.DONE):
                self._process_waypoints(r, t)
        live = {rid: r.active_plan for rid, r in self.robots.items()
                if r.on_grid and r.status != RobotStatus.BROKEN}
        persistent = {rid: r.current_position for rid, r in self.robots.items() if r.status == RobotStatus.BROKEN}
        conflicts = find_conflicts(live, from_time=t + 1, obstacles=self.obstacles, persistent=persistent)
        self._assert(not conflicts, f"committed repair created conflicts: {conflicts[:3]}")
        for rid in modified:
            self.log.add(t, EventType.PLAN_SUFFIX_REPAIRED, [rid], result.reasons.get(rid, "REPAIR"),
                         {"method": result.methods.get(rid), "old_end": before[rid][-1].time if before[rid] else None,
                          "new_end": self.robots[rid].active_plan[-1].time})
        self.log.add(t, EventType.REPAIR_COMMITTED, modified, "REPAIR_COMMITTED",
                     {"impact": len(modified), "messages": len(result.messages),
                      "affected": result.affected, "runtime_ms": round(result.runtime_ms, 3)})
        self.last_repair = result.summary()
        self.repairs.append({"time": t, "disruption_id": imp.disruption_id, **result.summary()})

    @staticmethod
    def _assert(cond: bool, msg: str) -> None:
        if not cond:
            raise InvariantError(msg)

    # ------------------------------------------------------------------ stepping
    def step(self) -> bool:
        """Advance one timestep. Returns False if the simulation is over."""
        if self.status in ("completed", "failed"):
            return False
        self.status = "running"
        t = self.time
        if t >= self.config.max_time:
            self._fail("timeout", "TIMEOUT")
            return False
        # 1. activate scheduled disruptions (repair happens inside)
        for d in self.scheduler.pop_due(t):
            try:
                self._activate(d)
            except ValueError as exc:  # e.g. the target robot already finished: skip, keep running
                self.log.add(t, "DISRUPTION_REJECTED", [], "INVALID_DISRUPTION",
                             {"disruption_id": d.disruption_id, "message": str(exc)})
            if self.status == "failed":
                return False
        # 2-4. observe / validate next step (safety net)
        invalid = self._invalid_next_steps(t)
        if invalid:
            self._reactive_repair(invalid)
            if self.status == "failed":
                return False
        # 5. execute simultaneously
        self._execute(t)
        # 6. task status
        for r in self.robots.values():
            if r.on_grid and r.status != RobotStatus.BROKEN:
                self._process_waypoints(r, self.time)
        self._finalize_done(self.time)
        if self.config.dev_checks:
            self.check_invariants()
        self._check_completion()
        return self.status == "running"

    def run(self, max_steps: Optional[int] = None) -> SimulationResult:
        n = 0
        while self.step():
            n += 1
            if max_steps is not None and n >= max_steps:
                break
        return self.result()

    def _active_robots(self) -> list[Robot]:
        return [r for r in self.robots.values() if r.on_grid and r.status not in (RobotStatus.BROKEN,)]

    def _invalid_next_steps(self, t: int) -> list[str]:
        """Robots whose plan for t+1 is unusable: exhausted, blocked, or in conflict."""
        bad: set[str] = set()
        nxt: dict[str, Position] = {}
        cur: dict[str, Position] = {}
        for r in self._active_robots():
            if r.status == RobotStatus.DONE:
                continue
            p = pos_at(r.active_plan, t + 1)
            cur[r.robot_id] = r.current_position
            if p is None or self.obstacles.is_blocked(p, t + 1) or \
                    abs(p.x - r.current_position.x) + abs(p.y - r.current_position.y) > 1 or \
                    not self.grid.is_traversable(p):
                bad.add(r.robot_id)
                continue
            nxt[r.robot_id] = p
        occupied: dict[Position, str] = {}
        for rid, p in nxt.items():
            if p in occupied:
                bad.update((rid, occupied[p]))
            occupied[p] = rid
        for r in self.robots.values():  # broken robots keep their cell
            if r.status == RobotStatus.BROKEN and r.current_position in occupied:
                bad.add(occupied[r.current_position])
        for a, pa in nxt.items():
            for b, pb in nxt.items():
                if a < b and pa == cur[b] and pb == cur[a] and pa != cur[a]:
                    bad.update((a, b))
        return sorted(bad)

    def _reactive_repair(self, robot_ids: list[str]) -> None:
        from ..repair.dispatcher import repair_invalidated

        self.log.add(self.time, EventType.PLAN_INVALIDATED, robot_ids, "UNEXPECTED_INVALID_NEXT_STEP", {})
        before = {rid: list(r.active_plan) for rid, r in self.robots.items()}
        result = repair_invalidated(self._repair_context(), robot_ids, self.config.strategy)
        self._finish_repair(result, before, None)

    def _execute(self, t: int) -> None:
        nxt_positions: dict[str, Optional[Position]] = {}
        for r in self.robots.values():
            if not r.on_grid:
                continue
            if r.status == RobotStatus.BROKEN:
                nxt_positions[r.robot_id] = r.current_position
            elif r.status == RobotStatus.DONE:
                nxt_positions[r.robot_id] = None  # leaves the workspace
                r.on_grid = False
            else:
                nxt_positions[r.robot_id] = pos_at(r.active_plan, t + 1)
        # collision assertions (vertex + edge swap)
        seen: dict[Position, str] = {}
        for rid, p in nxt_positions.items():
            if p is None:
                continue
            if p in seen:
                self.collisions += 1
                raise CollisionError(f"vertex collision at t={t + 1} cell {p}: {seen[p]} and {rid}")
            seen[p] = rid
        for a, pa in nxt_positions.items():
            for b, pb in nxt_positions.items():
                if a < b and pa is not None and pb is not None and pa != pb:
                    if pa == self.robots[b].current_position and pb == self.robots[a].current_position:
                        self.collisions += 1
                        raise CollisionError(f"edge swap at t={t + 1}: {a} and {b}")
        self.time = t + 1
        for rid, p in nxt_positions.items():
            r = self.robots[rid]
            if r.status in (RobotStatus.BROKEN, RobotStatus.DONE):
                continue
            if p is None:
                raise InvariantError(f"{r.robot_id} has no planned position at t={t + 1} but unfinished tasks")
            moved = p != r.current_position
            if self.config.record_movement:
                self.log.add(self.time, EventType.ROBOT_MOVED if moved else EventType.ROBOT_WAITED, [rid],
                             None, {"from": list(r.current_position), "to": list(p)})
            r.current_position = p
            r.executed_prefix.append(TimedPosition(p, self.time))
            if r.status == RobotStatus.WAITING:
                r.status = RobotStatus.ACTIVE

    # ------------------------------------------------------------------ invariants
    def check_invariants(self) -> None:
        t = self.time
        occ: dict[Position, str] = {}
        for r in self.robots.values():
            if not r.on_grid:
                continue
            p = r.current_position
            if p in occ:
                raise InvariantError(f"two robots on {p}: {occ[p]}, {r.robot_id}")
            occ[p] = r.robot_id
            if self.obstacles.is_blocked(p, t) and not (r.status == RobotStatus.BROKEN):
                if not any(o.start_time == t for o in self.obstacles.all() if o.position == p):
                    raise InvariantError(f"{r.robot_id} inside an active obstacle at {p}, t={t}")
            if r.status == RobotStatus.BROKEN:
                if r.executed_prefix[-1].position != p or r.current_position != r.executed_prefix[-1].position:
                    raise InvariantError(f"broken robot {r.robot_id} moved")
            if len(r.executed_prefix) != (t + 1 if r.status != RobotStatus.BROKEN else len(r.executed_prefix)):
                raise InvariantError(f"executed prefix length mismatch for {r.robot_id}")
            if r.status not in (RobotStatus.BROKEN,):
                if [tp.position for tp in r.active_plan[: t + 1]] != [tp.position for tp in r.executed_prefix[: t + 1]]:
                    raise InvariantError(f"executed prefix of {r.robot_id} diverged from active plan")
                if not check_adjacent_steps(r.active_plan):
                    raise InvariantError(f"non-adjacent step in plan of {r.robot_id}")
        for tid, dt in self.delivery_times.items():
            if tid not in self.pickup_times or self.pickup_times[tid] > dt:
                raise InvariantError(f"task {tid} delivered before pickup")
        carried: dict[str, str] = {}
        for r in self.robots.values():
            for tk in r.tasks:
                if tk.status in (TaskStatus.PENDING, TaskStatus.PICKED):
                    if tk.task_id in carried:
                        raise InvariantError(f"task {tk.task_id} owned by {carried[tk.task_id]} and {r.robot_id}")
                    carried[tk.task_id] = r.robot_id
        live = {rid: r.active_plan for rid, r in self.robots.items() if r.on_grid and r.status != RobotStatus.BROKEN}
        persistent = {rid: r.current_position for rid, r in self.robots.items() if r.status == RobotStatus.BROKEN}
        c = find_conflicts(live, from_time=t + 1, obstacles=self.obstacles, persistent=persistent)
        if c:
            raise InvariantError(f"future plans conflict: {c[:3]}")

    # ------------------------------------------------------------------ metrics
    def _completion_time(self, r: Robot) -> int:
        if r.status == RobotStatus.BROKEN:
            return r.broken_at if r.broken_at is not None else self.time
        if r.status == RobotStatus.DONE and r.completion_time is not None:
            return r.completion_time
        if r.on_grid and r.active_plan:
            return r.active_plan[-1].time  # still running: projected completion of the active plan
        return self.time

    def _flowtime(self) -> int:
        return flowtime(self._completion_time(r) for r in self.robots.values())

    def _makespan(self) -> int:
        return makespan(self._completion_time(r) for r in self.robots.values())

    def result(self) -> SimulationResult:
        robots = list(self.robots.values())
        moves = sum(sum(1 for a, b in zip(r.executed_prefix, r.executed_prefix[1:]) if a.position != b.position)
                    for r in robots)
        waits = sum(sum(1 for a, b in zip(r.executed_prefix, r.executed_prefix[1:]) if a.position == b.position)
                    for r in robots)
        ct = {r.robot_id: self._completion_time(r) for r in robots}
        remaining = sum(1 for r in robots for tk in r.tasks
                        if tk.status in (TaskStatus.PENDING, TaskStatus.PICKED))
        n = len(robots)
        res = SimulationResult(
            success=self.status == "completed", status=self.status, failure_reason=self.failure_reason,
            time=self.time, completion_times=ct, flowtime=flowtime(ct.values()), makespan=makespan(ct.values()),
            original_flowtime=self.original_flowtime, original_makespan=self.original_makespan,
            delta_flowtime=flowtime(ct.values()) - self.original_flowtime, n_agents=n,
            num_modified=len(self.modified_ids), modified_ids=sorted(self.modified_ids),
            modified_ratio=len(self.modified_ids) / n if n else 0.0, total_path_length=moves,
            original_path_length=self.original_path_length,
            additional_path_length=moves - self.original_path_length, total_waits=waits,
            repair_time_ms=self.total_repair_ms, messages=self.total_messages, collisions=self.collisions,
            deadlocks=self.deadlocks, conflicts_avoided=self.conflicts_avoided,
            affected_expansions=self.total_expansions, max_affected_size=self.max_affected, remaining_tasks=remaining,
            n_disruptions=len(self.scheduler.activated), n_repairs_failed=self.n_repairs_failed,
            per_disruption=list(self.disruption_impacts),
        )
        return res

    # ------------------------------------------------------------------ serialisation
    def snapshot(self) -> dict[str, Any]:
        def pl(plan: list[TimedPosition]) -> list[list[int]]:
            return [[tp.position.x, tp.position.y] for tp in plan]

        robots = []
        for i, r in enumerate(self.robots.values()):
            robots.append({
                "id": r.robot_id, "index": i,
                "position": [r.current_position.x, r.current_position.y] if r.on_grid else None,
                "status": r.status.value, "on_grid": r.on_grid, "priority": r.planning_priority,
                "completion_time": r.completion_time, "broken_at": r.broken_at,
                "tasks": [{**task_to_spec(tk), "status": tk.status.value, "completed_at": tk.completed_at}
                          for tk in r.tasks],
                "waypoints": [{"task_id": w.task_id, "kind": w.kind, "position": [w.position.x, w.position.y]}
                              for w in r.remaining_waypoints()],
                "original_plan": pl(r.original_plan), "active_plan": pl(r.active_plan),
                "executed": pl(r.executed_prefix),
            })
        obstacles = [{"id": o.obstacle_id, "position": [o.position.x, o.position.y], "start": o.start_time,
                      "end": o.end_time, "owner": o.owner_robot_id, "active": o.blocks(self.time)}
                     for o in self.obstacles.all()]
        res = self.result()
        return {
            "time": self.time, "status": self.status, "failure_reason": self.failure_reason,
            "grid": {"width": self.grid.width, "height": self.grid.height,
                     "static": [[p.x, p.y] for p in sorted(self.grid.static_obstacles)]},
            "robots": robots, "obstacles": obstacles,
            "scheduled": [disruption_to_spec(d) for d in self.scheduler.pending],
            "metrics": res.to_dict(), "last_repair": self.last_repair,
            "repairs": [{"time": r["time"], "disruption_id": r["disruption_id"], "modified": r["modified"],
                         "affected": r["affected"], "success": r["success"]} for r in self.repairs],
            "initial_plan": self.initial_plan_info, "events_total": len(self.log),
            "scenario": {"id": self.scenario.scenario_id, "name": self.scenario.spec.get("name", ""),
                         "description": self.scenario.spec.get("description", "")},
        }
