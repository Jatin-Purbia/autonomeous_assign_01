"""Incremental local plan repair with neighbour negotiation and affected-set expansion.

Behaviour (see docs/algorithm.md):

    LOCAL_PLAN_REPAIR(d, t_d):
        A <- directly invalidated agents;  release only their future reservations
        for each pending agent a (by priority):
            1 temporal delay  2 local detour / single-agent replan   (unchanged agents stay fixed)
            if none valid (or a is an emergency robot / its own delay is large):
                negotiate with the neighbours whose routes block a's *ideal* route  (Contract-Net bids)
                    - cheaper side yields (delay / detour) -> neighbour joins A
                    - neighbours that cannot yield locally -> priority exchange, expand A, group replan
        validate everything, commit atomically (done by the engine) or fail.

Robots never restart planning from t=0 and no unaffected plan is touched.
"""
from __future__ import annotations

import random
import time as _time
from collections import Counter
from typing import Any, Optional, Sequence

from ..domain.grid import Position
from ..domain.metrics import plan_key
from ..domain.robot import RobotStatus, make_plan
from ..planning.heuristics import completes_waypoints, waypoint_times
from ..planning.reservation_table import ReservationTable
from ..planning.space_time_astar import PlanningContext, SoftConstraints, space_time_astar
from ..simulation.event_log import EventType
from .affected_set import AffectedSet
from .models import Plan, RepairConfig, RepairContext, RepairResult
from .negotiation import Bid, MessageBus, compute_bid, is_emergency, priority_penalty
from .repair_validation import first_invalid_index, prefixes_preserved, suffix_valid, validate_all

Positions = list[Position]


def count_moves(positions: Sequence[Position]) -> int:
    return sum(1 for a, b in zip(positions, positions[1:]) if a != b)


class RepairSession:
    """One repair episode for one disruption at time t_d.  All work happens on a *copy* of the
    reservation table; nothing is applied to robots until the caller commits ``RepairResult``."""

    def __init__(self, ctx: RepairContext, strategy: str = "local", reason_code: str = "DISRUPTION") -> None:
        self.ctx = ctx
        self.cfg: RepairConfig = ctx.config
        self.td = ctx.time
        self.robots = ctx.robots
        self.strategy = strategy
        self.reason_code = reason_code
        self.work: ReservationTable = ctx.table.copy()
        self.affected = AffectedSet()
        self.new_plans: dict[str, Plan] = {}
        self.methods: dict[str, str] = {}
        self.reasons: dict[str, str] = {}
        self.bus = MessageBus(self.td, ctx.emit)
        self.base_wps: dict[str, list[Position]] = {}   # append-mode robots (breakdown recipients)
        self.full_replan: set[str] = set()              # insert-mode robots (emergency)
        self.forced_plans: dict[str, Plan] = {}         # e.g. truncated plan of a broken robot
        self.reassignments: list[dict[str, Any]] = []
        self.conflicts_avoided = 0
        self.failure: Optional[str] = None
        self.deadlock = False
        self.initiator: Optional[str] = None
        self.direct_ids: list[str] = []

    # ------------------------------------------------------------------ helpers
    @property
    def pctx(self) -> PlanningContext:
        return PlanningContext(self.ctx.grid, self.ctx.obstacles, self.work)

    def _ptx(self, table: ReservationTable) -> PlanningContext:
        return PlanningContext(self.ctx.grid, self.ctx.obstacles, table)

    def _old(self, rid: str) -> Plan:
        return self.robots[rid].active_plan

    def _suffix(self, rid: str) -> Positions:
        plan = self._old(rid)
        if len(plan) <= self.td:
            return [self.robots[rid].current_position]
        return [tp.position for tp in plan[self.td:]]

    def _all_wps(self, rid: str) -> Positions:
        return [w.position for w in self.robots[rid].remaining_waypoints()]

    def _req_wps(self, rid: str) -> Positions:
        return self.base_wps[rid] if rid in self.base_wps else self._all_wps(rid)

    def _ext_wps(self, rid: str) -> Positions:
        base = self.base_wps.get(rid)
        return self._all_wps(rid)[len(base):] if base is not None else []

    def _compose(self, rid: str, positions: Sequence[Position]) -> Plan:
        """executed prefix (immutable) ++ repaired suffix."""
        return list(self._old(rid)[: self.td]) + make_plan(list(positions), self.td)

    def _sorted(self, ids: Sequence[str]) -> list[str]:
        return sorted(ids, key=lambda r: (not is_emergency(self.robots[r]), -self.robots[r].planning_priority, r))

    def _release(self, rid: str) -> None:
        self.work.release_robot(rid, self.td)

    def _active_ids(self) -> list[str]:
        return [rid for rid, r in self.robots.items()
                if r.on_grid and r.status not in (RobotStatus.BROKEN, RobotStatus.DONE)]

    # ------------------------------------------------------------------ strategies 1-2 (+ replan)
    def _try_delay(self, rid: str, pctx: PlanningContext, suffix: Positions, req: Positions) -> Optional[Positions]:
        """Strategy 1: temporal delay. Insert a short wait just before the first illegal step; if that does not
        help, delay the whole remaining plan by k timesteps."""
        i = first_invalid_index(pctx, rid, suffix, self.td)
        if i is None:
            return list(suffix) if completes_waypoints(suffix, req) else None
        for w in range(1, self.cfg.max_delay + 1):
            cand = suffix[:i] + [suffix[i - 1]] * w + suffix[i:]
            if suffix_valid(pctx, rid, cand, self.td, req):
                return cand
        for k in range(1, self.cfg.max_delay + 1):
            cand = [suffix[0]] * k + suffix
            if suffix_valid(pctx, rid, cand, self.td, req):
                return cand
        self.conflicts_avoided += 1
        return None

    def _try_detour(self, rid: str, pctx: PlanningContext, suffix: Positions, req: Positions) -> Optional[Positions]:
        """Strategy 3: replace a short window of the plan by a Space-Time A* detour that rejoins the old plan."""
        i = first_invalid_index(pctx, rid, suffix, self.td)
        if i is None:
            return list(suffix) if completes_waypoints(suffix, req) else None
        n = len(suffix)
        arrivals, _ = waypoint_times(suffix, 0, req)
        pairs = []
        for s in range(max(0, i - 4), i):
            for j in range(i + 1, min(n - 1, i + self.cfg.detour_window) + 1):
                pairs.append((j - s, -s, s, j))
        pairs.sort()
        for _, _, s, j in pairs:
            seg = [req[k] for k in range(len(req)) if arrivals[k] is not None and s < arrivals[k] <= j]
            if not seg or seg[-1] != suffix[j]:
                seg.append(suffix[j])
            res = space_time_astar(pctx, rid, suffix[s], self.td + s, seg,
                                   horizon=self.td + s + 2 * (j - s) + 12, max_expansions=12_000)
            if not res.found:
                continue
            cand = suffix[:s] + res.path + suffix[j + 1:]
            if suffix_valid(pctx, rid, cand, self.td, req):
                return cand
        self.conflicts_avoided += 1
        return None

    def _replan(self, rid: str, pctx: PlanningContext) -> Optional[tuple[str, Positions]]:
        """Single-agent Space-Time A* over all remaining waypoints (all other plans stay fixed)."""
        res = space_time_astar(pctx, rid, self.robots[rid].current_position, self.td, self._all_wps(rid),
                               max_expansions=self.cfg.max_expansions)
        return ("replan", res.path) if res.found and res.path else None

    def _extend(self, rid: str, pctx: PlanningContext, cand: Positions, ext: Positions) -> Optional[Positions]:
        """Append the path for newly assigned waypoints after the (repaired) old plan."""
        res = space_time_astar(pctx, rid, cand[-1], self.td + len(cand) - 1, ext,
                               max_expansions=self.cfg.max_expansions)
        if not res.found or not res.path:
            return None
        return cand + res.path[1:]

    def _local(self, rid: str, pctx: Optional[PlanningContext] = None) -> Optional[tuple[str, Positions]]:
        """Strategies 1-3 in order, falling back to single-agent replanning.  None if nothing is valid
        against the fixed plans in ``pctx``."""
        pctx = pctx or self.pctx
        if rid in self.full_replan:
            return self._replan(rid, pctx)
        suffix = self._suffix(rid)
        req, ext = self._req_wps(rid), self._ext_wps(rid)
        for name, fn in (("delay", self._try_delay), ("detour", self._try_detour)):
            cand = fn(rid, pctx, suffix, req)
            if cand is None:
                continue
            if ext:
                cand = self._extend(rid, pctx, cand, ext)
                if cand is None:
                    continue
                if name == "delay" and len(cand) > 0 and cand[: len(suffix)] == suffix:
                    name = "extension"
            return name, cand
        return self._replan(rid, pctx)

    # ------------------------------------------------------------------ bookkeeping of a decision
    def _register(self, rid: str, method: str, positions: Positions, reserve: bool = True) -> None:
        plan = self._compose(rid, positions)
        self.new_plans[rid] = plan
        self.methods[rid] = method
        if reserve:
            self.work.release_robot(rid, self.td)
            self.work.reserve_path(rid, plan, from_time=self.td)

    def _expand(self, rid: str, via: str, reason: str, added_by: Optional[str]) -> None:
        if self.affected.expand(rid, via, reason, added_by, self.td):
            self.reasons[rid] = reason
            self.ctx.emit(EventType.AFFECTED_SET_EXPANDED, [rid] + ([added_by] if added_by else []), via.upper(),
                          {"added": rid, "added_by": added_by, "via": via, "size": len(self.affected),
                           "reason": reason})

    # ------------------------------------------------------------------ ideal route / blockers
    def _yieldable(self, a: str, excluded: set[str], include_affected: bool = False) -> list[str]:
        a_em = is_emergency(self.robots[a])
        out = []
        for rid in self._active_ids():
            if rid == a or rid in excluded or (rid in self.affected and not include_affected):
                continue
            if is_emergency(self.robots[rid]) and not a_em:
                continue  # emergency robots never yield to ordinary robots
            out.append(rid)
        return out

    def _soft_ideal(self, a: str, excluded: Sequence[str] = (),
                    include_affected: bool = False) -> Optional[tuple[Positions, list[str]]]:
        """Shortest route for ``a`` if neighbours are willing to move: stepping through a neighbour's
        reservation costs a penalty ~ (w4/w1) time units.  Returns (route, blockers ordered by conflict time)."""
        ex = set(excluded)
        yl = self._yieldable(a, ex, include_affected)
        hard = self.work.copy()
        soft = ReservationTable()
        for j in yl:
            hard.release_robot(j, self.td)
            soft.reserve_path(j, self._old(j), from_time=self.td)
        for m in ex:
            hard.release_robot(m, self.td)
        penalty = 2.0 if is_emergency(self.robots[a]) else max(1.0, self.cfg.w4 / max(self.cfg.w1, 1e-9))
        res = space_time_astar(self._ptx(hard), a, self.robots[a].current_position, self.td, self._all_wps(a),
                               soft=SoftConstraints(soft, penalty), max_expansions=self.cfg.max_expansions)
        if not res.found or not res.path:
            return None
        blockers: list[str] = []
        for i in range(1, len(res.path)):
            u, v, t = res.path[i - 1], res.path[i], self.td + i - 1
            for owner in (soft.vertex_owner(v, t + 1), soft.edge.get((v, u, t)) if u != v else None):
                if owner and owner != a and owner not in blockers:
                    blockers.append(owner)
        return res.path, blockers

    # ------------------------------------------------------------------ main loop
    def run(self, direct: dict[str, str]) -> RepairResult:
        t0 = _time.perf_counter()
        self.direct_ids = self._sorted(list(direct))
        for rid in self.direct_ids:
            self.affected.add_direct(rid, "DIRECT: " + direct[rid])
            self.reasons[rid] = "DIRECT: " + direct[rid]
        self.initiator = self.direct_ids[0] if self.direct_ids else None
        self.ctx.emit(EventType.REPAIR_STARTED, list(self.direct_ids), self.reason_code,
                      {"strategy": self.strategy, "direct": list(self.direct_ids)})
        if self.direct_ids:
            self.ctx.emit(EventType.PLAN_INVALIDATED, list(self.direct_ids), self.reason_code,
                          {rid: direct[rid] for rid in self.direct_ids})
        for rid, plan in self.forced_plans.items():
            self.new_plans[rid] = plan
            self.methods[rid] = "stopped"
            self.reasons.setdefault(rid, "BREAKDOWN: robot stopped at its current cell")
            self.work.release_robot(rid, self.td)
        for rid in self.direct_ids:
            self._release(rid)
        pending = list(self.direct_ids)
        ok = True
        while pending and ok:
            a = pending.pop(0)
            if a in self.new_plans:
                continue
            ok = self._repair_agent(a)
            pending = [p for p in pending if p not in self.new_plans]
        if ok:
            return self._finalize(t0)
        return self._failure(t0)

    def _repair_agent(self, a: str) -> bool:
        robot = self.robots[a]
        fallback = self._local(a)
        emergency = is_emergency(robot)
        if fallback is not None and not emergency:
            delay = len(fallback[1]) - len(self._suffix(a)) if a not in self.full_replan and a not in self.base_wps else 0
            if delay <= self.cfg.negotiation_trigger_delay or not self.cfg.allow_negotiation:
                self._register(a, fallback[0], fallback[1])
                return True
        if not self.cfg.allow_negotiation:
            if fallback is not None:
                self._register(a, fallback[0], fallback[1])
                return True
            self.failure = f"{a}: no local repair; negotiation disabled (single-agent repair)"
            return False
        return self._negotiate(a, fallback)

    # ------------------------------------------------------------------ negotiation (Contract-Net style)
    def _negotiate(self, a: str, fallback: Optional[tuple[str, Positions]]) -> bool:
        cfg = self.cfg
        robot = self.robots[a]
        ideal = self._soft_ideal(a)
        if ideal is None:
            if fallback is not None:
                self._register(a, fallback[0], fallback[1])
                return True
            committed = self._committed(a)
            if committed and self.cfg.allow_expansion:  # re-open already repaired agents together with a
                return self._group_repair([a] + committed, initiator=a)
            self.failure = f"{a}: no feasible route even if every neighbour yields"
            return False
        route, blockers = ideal
        ideal_plan = self._compose(a, route)
        if not blockers:
            self._register(a, "replan", route)
            return True
        # ---- trial: the blockers try to yield to a's ideal route --------------------------------
        trial = self.work.copy()
        trial.release_robot(a, self.td)
        trial.reserve_path(a, ideal_plan, from_time=self.td)
        for j in blockers:
            trial.release_robot(j, self.td)
        tctx = self._ptx(trial)
        yields: dict[str, tuple[str, Positions]] = {}
        failed: list[str] = []
        for j in sorted(blockers, key=lambda x: (-self.robots[x].planning_priority, x)):
            self.bus.send("REPAIR_REQUEST", a, j, route_end=list(route[-1]), reason=self.reason_code)
            cand = self._local(j, tctx)
            if cand is not None:
                trial.reserve_path(j, self._compose(j, cand[1]), from_time=self.td)
                yields[j] = cand
            else:
                failed.append(j)
        bids_j: dict[str, Bid] = {}
        for j in blockers:
            if j in yields:
                pos = yields[j][1]
                bid = compute_bid(cfg, self.robots[j], len(pos) - len(self._suffix(j)),
                                  count_moves(pos) - count_moves(self._suffix(j)), j in self.affected)
            else:
                bid = compute_bid(cfg, self.robots[j], None, None, j in self.affected)
            bids_j[j] = bid
            self.bus.send("BID", j, a, **bid.to_dict())
        if fallback is not None:
            fb = fallback[1]
            base = len(route) if (a in self.full_replan or a in self.base_wps) else len(self._suffix(a))
            bid_a = compute_bid(cfg, robot, max(0, len(fb) - base), count_moves(fb) - count_moves(route), True)
        else:
            bid_a = compute_bid(cfg, robot, None, None, True)
        for j in blockers:
            self.bus.send("BID", a, j, **bid_a.to_dict())
        total_j = sum(b.cost for b in bids_j.values())
        if fallback is not None and bid_a.cost <= total_j:  # the initiator yields: cheaper overall
            for j in blockers:
                self.bus.send("REJECT", a, j, bid_a=bid_a.to_dict()["cost"], bid_j=bids_j[j].to_dict()["cost"])
            self._register(a, fallback[0], fallback[1])
            return True
        if not failed:  # neighbours yield locally (delay / detour)
            for j in blockers:
                self.bus.send("ACCEPT", a, j, yield_method=yields[j][0], bid=bids_j[j].to_dict()["cost"])
                if self.robots[j].planning_priority > robot.planning_priority or is_emergency(robot):
                    self.bus.send("PRIORITY_UPDATE", a, j, note="priority exchange: yields to " + a)
            self.work = trial
            self._register(a, "replan", route, reserve=False)
            for j in blockers:
                self._expand(j, "negotiation", f"INDIRECT: yielded to {a}'s repaired route ({yields[j][0]})", a)
                self._register(j, yields[j][0], yields[j][1], reserve=False)
            return True
        for j in failed:
            self.bus.send("REJECT", a, j, note="cannot yield locally; group repair")
        if not cfg.allow_expansion:
            if fallback is not None:
                self._register(a, fallback[0], fallback[1])
                return True
            self.failure = f"{a}: neighbours {failed} cannot yield locally and expansion is disabled"
            return False
        return self._group_repair([a] + [j for j in blockers], initiator=a)

    # ------------------------------------------------------------------ strategies 4-6: group repair
    def _group_astar(self, group: list[str]) -> Optional[tuple[list[str], dict[str, Positions], ReservationTable]]:
        """Strategy 4/6: prioritized Space-Time A* over the group only.  If a member cannot be planned, the
        priority order is exchanged (failed member bumped to the front; emergency robots stay first)."""
        order = self._sorted(group)
        locked = [r for r in order if is_emergency(self.robots[r])]
        rng = random.Random(self.td)
        seen: set[tuple[str, ...]] = set()
        for _ in range(self.cfg.max_order_retries + 1):
            if tuple(order) in seen:
                rest = [r for r in order if r not in locked]
                rng.shuffle(rest)
                order = locked + rest
                if tuple(order) in seen:
                    break
            seen.add(tuple(order))
            tmp = self.work.copy()
            for m in group:
                tmp.release_robot(m, self.td)
            ptx = self._ptx(tmp)
            plans: dict[str, Positions] = {}
            failed: Optional[str] = None
            for m in order:
                res = space_time_astar(ptx, m, self.robots[m].current_position, self.td, self._all_wps(m),
                                       max_expansions=self.cfg.max_expansions)
                if not res.found or not res.path:
                    failed = m
                    break
                tmp.reserve_path(m, self._compose(m, res.path), from_time=self.td)
                plans[m] = res.path
            if failed is None:
                return order, plans, tmp
            self.conflicts_avoided += 1
            if failed not in locked:
                order = locked + [failed] + [r for r in order if r != failed and r not in locked]
        return None

    def _committed(self, exclude: str) -> list[str]:
        return [r for r in self.affected.ids() if r in self.new_plans and r != exclude and r not in self.forced_plans]

    def _nearest_neighbour(self, group: list[str]) -> Optional[str]:
        best: Optional[tuple[int, str]] = None
        for rid in self._active_ids():
            if rid in group:
                continue
            d = min(abs(self.robots[rid].current_position.x - self.robots[m].current_position.x)
                    + abs(self.robots[rid].current_position.y - self.robots[m].current_position.y) for m in group)
            if best is None or (d, rid) < best:
                best = (d, rid)
        return best[1] if best else None

    def _group_repair(self, group: list[str], initiator: str) -> bool:
        group = list(dict.fromkeys(group))
        for m in group:
            if m != initiator:
                self._expand(m, "group", f"INDIRECT: conflicts with {initiator}'s repaired route; group replan",
                             initiator)
        while True:
            found = self._group_astar(group)
            if found is not None:
                order, plans, tmp = found
                default = self._sorted(group)
                self.work = tmp
                for m in group:
                    self._register(m, "group", plans[m], reserve=False)
                    if m != initiator:
                        self.bus.send("PRIORITY_UPDATE", initiator, m, group_order=order,
                                      priority_exchange=order != default)
                return True
            if not self.cfg.allow_expansion:
                self.failure = f"group repair of {group} failed; expansion disabled"
                return False
            active = self._active_ids()
            if all(r in group for r in active):
                self.failure = f"no solution: affected set covers every active agent ({len(active)})"
                self.deadlock = True
                return False
            counts: Counter[str] = Counter()
            for m in group:
                ideal = self._soft_ideal(m, excluded=group, include_affected=True)
                if ideal is None:
                    self.failure = f"{m}: no feasible route even if every non-group neighbour yields"
                    return False
                counts.update(b for b in ideal[1] if b not in group)
            if not counts:  # conflicts only inside the group: widen by the nearest neighbour
                near = self._nearest_neighbour(group)
                if near is None:
                    self.failure = f"group {group} unsolvable"
                    self.deadlock = True
                    return False
                counts[near] = 0
            cost = lambda j: (self.cfg.w4 + priority_penalty(self.robots[j], self.cfg) - 5.0 * counts[j], j)
            nxt = min(counts, key=cost)
            self.bus.send("REPAIR_REQUEST", initiator, nxt, reason="expand affected set")
            self.bus.send("BID", nxt, initiator, cost=round(cost(nxt)[0], 2), note="cheapest expansion")
            self.bus.send("ACCEPT", initiator, nxt, note="joins group repair")
            self._expand(nxt, "group", f"INDIRECT: blocks the group's routes (expansion cost {round(cost(nxt)[0], 1)})",
                         initiator)
            group.append(nxt)
            self._release(nxt)

    # ------------------------------------------------------------------ result
    def _failure(self, t0: float) -> RepairResult:
        return RepairResult(
            success=False, strategy=self.strategy, failure_reason=self.failure or "unknown",
            direct=list(self.direct_ids), affected=self.affected.ids(), expansions=list(self.affected.history),
            reasons=dict(self.reasons), messages=list(self.bus.messages),
            conflicts_avoided=self.conflicts_avoided, runtime_ms=(_time.perf_counter() - t0) * 1000,
            reassignments=self.reassignments, deadlock=self.deadlock)

    def _finalize(self, t0: float) -> RepairResult:
        td = self.td
        live: dict[str, Plan] = {}
        for rid in self._active_ids():
            live[rid] = self.new_plans.get(rid) or self._old(rid)
        persistent = {rid: r.current_position for rid, r in self.robots.items() if r.status == RobotStatus.BROKEN}
        conflicts = validate_all(live, self.ctx.obstacles, td, persistent)
        old_all = {rid: r.active_plan for rid, r in self.robots.items()}
        if conflicts or not prefixes_preserved(old_all, self.new_plans, td):
            self.failure = f"validation rejected the tentative repair: {conflicts[:2]}"
            return self._failure(t0)
        changed: dict[str, Plan] = {}
        for rid, plan in self.new_plans.items():
            if plan_key(plan) != plan_key(old_all[rid]):
                changed[rid] = plan
        diffs: dict[str, dict[str, Any]] = {}
        delta: dict[str, int] = {}
        for rid, plan in changed.items():
            old = old_all[rid]
            diffs[rid] = {
                "from_time": td,
                "old_suffix": [[tp.position.x, tp.position.y] for tp in old[td:]],
                "new_suffix": [[tp.position.x, tp.position.y] for tp in plan[td:]],
                "method": self.methods.get(rid), "reason": self.reasons.get(rid),
            }
            delta[rid] = plan[-1].time - old[-1].time
        for rid in changed:
            if rid != self.initiator and rid not in self.forced_plans:
                self.bus.send("REPAIR_COMMITTED", self.initiator or "SYSTEM", rid, method=self.methods.get(rid))
        runtime = (_time.perf_counter() - t0) * 1000
        return RepairResult(
            success=True, strategy=self.strategy, new_plans=changed, direct=list(self.direct_ids),
            affected=self.affected.ids(), modified=sorted(changed), expansions=list(self.affected.history),
            reasons=dict(self.reasons), methods=dict(self.methods), messages=list(self.bus.messages),
            diffs=diffs, conflicts_avoided=self.conflicts_avoided,
            runtime_ms=runtime, delta_completion=delta, reassignments=self.reassignments)
