# Algorithm description

This document explains every algorithmic component of the prototype and points to the code that implements it.
All parameter defaults quoted here live in `backend/app/repair/models.py` (`RepairConfig`).

## 0. Modelling assumptions

| Assumption | Consequence |
|---|---|
| Discrete synchronous time; a move (N/S/E/W) or a wait costs one step. | Plans are lists of positions indexed by absolute time: `plan[t].time == t`. |
| A robot carries at most one parcel; pickup and delivery are instantaneous on arrival. | A task is the ordered waypoint pair (pickup, delivery); several tasks form an ordered waypoint list. |
| **A robot leaves the workspace at its final delivery** (implicit depot off-grid). | Finished robots never block others. Only *broken* robots remain as permanent obstacles. |
| When a blockage is announced its whole interval `[t_s, t_e]` is known (`t_e = None` = permanent). | The planner can wait out finite blockages. |
| A blockage / breakdown at time `t_d` constrains times `> t_d`; a robot already standing on the cell may leave. | Executed positions (times `<= t_d`) are immutable. |
| Every plan is validated before it replaces an active plan. | A failed repair never leaves partially applied plans; the run is declared unsuccessful. |

## 1. Space-Time A* (`planning/space_time_astar.py`)

State `n = (x, y, t, q)`: cell, timestep, and `q` = index of the next waypoint (task progress).

* `g(n) = t - t_start` (each action costs 1, waiting included).
* `h(n) = |x - x_q| + |y - y_q| + sum_{k >= q} |w_k - w_{k+1}|` (Manhattan to the next waypoint plus the remaining ordered legs). It is admissible and consistent, so the first time a goal state is popped the path is time-optimal for the given constraints.
* Successors: 4 moves + wait. A step `u@t -> v@t+1` is legal iff `v` is a traversable cell, not blocked by a dynamic obstacle at `t+1`, `v@t+1` is not reserved by another robot (vertex), and no other robot performs `v -> u` during the same interval (edge swap).
* `q` advances only when the robot stands on `w_q`; visiting a later waypoint's cell early does not count, which enforces *pickup before delivery* and the task order. Consecutive waypoints on the same cell complete together.
* Termination: goal `q == len(waypoints)`; failure reasons `unreachable` (BFS pre-check ignoring finite obstacles), `no_path` (time horizon exhausted), `expansion_limit`.
* *Soft constraints* (used only by negotiation): stepping through a reservation of a yieldable robot costs an extra `penalty`. The search then returns the route that disturbs the fewest neighbours, from which the blockers are read off.

## 2. Reservation table and collision types (`planning/reservation_table.py`, `collision_detection.py`)

* Vertex reservation `R_V(v,t)`: robot occupies `v` at `t`.
* Edge reservation `R_E(u,v,t)`: robot moves `u -> v` in `[t, t+1]`. A move `u -> v` is rejected if `R_E(v,u,t)` exists.
* Following (moving into a cell that is vacated in the same step) is allowed; swaps and shared cells are not.
* Collision kinds checked everywhere: **vertex**, **edge swap**, **obstacle** (static, dynamic, broken-robot cell), plus **adjacency** (every step is a wait or a unit move).
* `release_robot(rid, after_time)` removes only reservations of times `> after_time`: the executed prefix stays reserved.

## 3. Initial planning (`planning/prioritized_mapf.py`)

Robots are planned in descending `planning_priority`. After each robot is planned its complete path is reserved before the next robot is planned. If a robot cannot be planned, up to `max_retries` (5) deterministic priority orders are tried (failed robot bumped to the front, then seeded shuffles). The result is tagged `phase = "INITIAL_PLANNING"`; this planner is **never** used for ordinary disruption repair. Prioritized planning is incomplete (a tight head-on corridor without a bay can fail; see `test_tight_head_on_corridor_is_reported_as_failure_not_collision`), and the engine reports such scenarios as failed instead of producing colliding plans.

## 4. Execution (`simulation/engine.py`)

Each timestep: activate scheduled disruptions (repair happens here) → observe → validate every robot's next planned step (safety net) → detect vertex/edge conflicts → execute all actions simultaneously with collision assertions → update pickup/delivery status → log. After every step (development mode) the engine checks the invariants listed in `docs/architecture.md`.

## 5. Disruption handling (`repair/dispatcher.py`)

**Cell blockage.** Adds `DynamicObstacle(v, t_d, t_d + duration)`. Directly affected agents are those whose *unexecuted* plan enters `v` while blocked (`affected_set.find_directly_invalidated`).

**Robot breakdown.** The robot stops on its cell, which becomes a permanent obstacle (owner = robot). Its executed prefix is kept and its future is dropped. Every unfinished task returns to the pool and is assigned to
`a* = argmin_j d(pos_j, pickup) + d(pickup, delivery) + lambda*Load(a_j) + mu*RepairImpact(a_j)`
(`lambda = 4`, `mu = 2`, both configurable in the UI). `RepairImpact` counts the *other* robots whose remaining plan passes through the bounding box of `{pos_j, pickup, delivery}`. A parcel already on the broken robot is handed over from the free neighbouring cell nearest to its delivery (the pickup of the reassigned task moves there). Recipients keep their old plan and only the extension for the new waypoints is planned (`extension` method), unless that is impossible and a full replan is needed. The initial affected set is the recipients plus every robot whose plan enters the broken cell.

**Emergency task.** The robot with minimum `d(pos, pickup) + lambda*Load + mu*RepairImpact` (or the one chosen in the UI) receives the task; it is inserted after the parcel currently on board (capacity 1) or before the first pending task. Its `planning_priority` is raised by 1000 and it is marked `emergency`. Its plan is fully recomputed (insertion changes the waypoint order).

## 6. Incremental local plan repair (`repair/local_repair.py`)

```
LOCAL_PLAN_REPAIR(d, t_d):
    update dynamic map; A <- directly affected agents; keep executed prefixes
    release future reservations of A only            (everything else stays reserved)
    for each pending agent a in A (emergency first, then by priority):
        candidate <- first valid of:  1 wait   2 temporal shift   3 local detour / single-agent replan
        if candidate exists and a is not an emergency robot and its delay <= 12:  commit candidate
        else: NEGOTIATE(a)
    validate all plans against each other and against every obstacle; commit atomically or fail
```

Strategies (each candidate is validated against obstacles and all fixed reservations before use):

1. **Wait** - insert `1..max_wait (12)` waits just before the first illegal step.
2. **Temporal shift** - delay the whole remaining plan by `1..max_shift (12)` steps.
3. **Local detour** - replace a window of the plan by a Space-Time A* leg that rejoins the old plan up to `detour_window (14)` steps later (waypoints inside the window are still visited). If no window works, a single-agent replan over all remaining waypoints is tried. All other plans stay fixed.
4. **Priority exchange** - during negotiation/group repair the cheaper-to-move robot yields even if its planning priority is higher (logged as `PRIORITY_UPDATE`); in group replanning a robot that cannot be planned is bumped to the front of the order.
5. **Expansion** - `A <- A U {a_j}`; only `a_j`'s future reservations are released.
6. **Group replan** - prioritized Space-Time A* over the affected group only, everything else fixed.

### Negotiation (`repair/negotiation.py`, `_negotiate`)

When agent `a` cannot be repaired locally (or `a` is an emergency robot, or its own yield is expensive):

1. `a` computes its *ideal* route with soft constraints. The robots whose reservations it crosses are the **blockers** (ordered by first conflict time).
2. For each blocker `j`: `REPAIR_REQUEST a -> j`. Each blocker tries to yield to the ideal route with strategies 1-3 against the table that already contains `a`'s ideal route.
3. Bids: `Bid_i = w1*dC_i + w2*dL_i + w3*P_i + w4*M_i` with `w1=1, w2=0.5, w3=1, w4=30`. `P_i = planning_priority + 1000` for emergency robots (a huge penalty for delaying them). `M_i = 1` if the robot's plan has not been modified yet, so touching a new agent costs `w4`. A robot that cannot yield locally bids infinity. `BID` messages go both ways.
4. If `a` has a fallback (its own yield) and `Bid_a <= sum_j Bid_j`, `a` yields and blockers receive `REJECT`. Otherwise blockers receive `ACCEPT`, their new plans are adopted, they join `A` (`AFFECTED_SET_EXPANDED`, via `negotiation`), and a `PRIORITY_UPDATE` records priority inversions and emergency yielding.
5. If a blocker cannot yield locally, `a` and the blockers form a group (strategy 6). If the group replan fails, the group expands by the neighbour with the cheapest expansion cost `w4 + P_j - 5*(#conflicts with the group's ideal routes)` (or the nearest robot if no conflicts are visible), until the group covers every active robot; then the repair fails and is flagged as a deadlock.
6. `REPAIR_COMMITTED` is sent to every modified robot other than the initiator. Message-only participants are **not** counted as modified: the impact set is computed from plan differences.

If `a` is *already committed* and a later agent finds no route, already repaired agents are re-opened into the group (this was needed for completeness: without it, local repair failed on cases global replanning solved).

### Optimisation objective

Lexicographic, implemented as a weighted sum with `W1 >> W2 >> W3, W4`:
`J = W1*|A_d| + W2*sum(dC_i) + W3*N_msg + W4*T_repair`, with `W1 = 10000, W2 = 100, W3 = 1, W4 = 0.1` (`RepairResult.objective`). Primary minimisation of `|A_d|` is achieved structurally: cheaper strategies that touch no neighbour are always tried first, and a neighbour is only involved when the bid (`w4 = 30` per newly modified robot) or infeasibility demands it.

## 7. Baselines

* **A - single-agent repair** (`strategy = "single_agent"`): same strategies 1-3 for the directly affected robots only; negotiation and expansion are disabled, so any conflict with an unchanged plan is a failure.
* **B - local negotiated repair** (`"local"`): the proposed method above.
* **C - global replanning** (`"global"`, experimental only): every active robot's remaining path is recomputed with prioritized Space-Time A* from the current positions at `t_d` (with order retries). It uses the same task reassignment/insertion as A and B. Its message count is 1 request per active robot plus 1 commit per modified robot (central coordinator).

## 8. Conflict graph (`repair/conflict_graph.py`)

Nodes are robots. Edges: `vertex`, `edge_swap`, `shared_resource` (same cell used within 2 timesteps), `dependency` (breakdown -> task recipient). Strong edges (all but shared-resource) define the local connected component of the disrupted agent. Snapshots are recorded before the repair, after each ideal route, at each group step and after the repair; the UI shows them.

## 9. Complexity

* One Space-Time A* call explores at most `|V| * T * |Q|` states (`T` = horizon, `|Q|` = number of waypoints + 1) with a heap: `O(|V| T |Q| log(|V| T |Q|))` worst case. In practice the admissible heuristic keeps it far smaller. Calls are bounded by `max_expansions = 250000`.
* Strategies 1-2 cost `O(max_wait + max_shift)` validations of `O(L)` each (`L` = plan length). Strategy 3 performs at most `4 * detour_window` bounded A* calls.
* Negotiation: one soft A* + one local repair per blocker. Group replan: `|G|` A* calls per order, `<= max_order_retries + 1` orders. Expansion grows `|G|` at most `N` times, so the worst case degrades to global prioritized replanning, `O(N)` A* calls per attempt.
* Conflict graph: `O(sum L)` with a cell-time index.

## 10. Limitations

* Prioritized planning (initial and group) is incomplete: solvable instances can be reported as failures. Repair failure ends the run (no partial recovery).
* Exit-at-goal is an assumption; parked robots (that could later be blocked in place) are not modelled.
* A broken robot that stops on somebody's pickup/delivery cell makes that task unreachable (repair fails). Blockage intervals must be known at announcement.
* The broken robot is counted as a *modified* agent (its plan is truncated) and its completion time is its breakdown time.
* `Delta Flowtime` compares against the originally planned flowtime; for breakdown runs this mixes the lost tasks' effect with the repair effect. Live (mid-run) values project unfinished robots to the end of their active plan.
* "Conflicts avoided" counts tentative repair candidates rejected by validation (per strategy attempt), not physical near-misses.
* One interactive simulation session per backend process; experiments run in a separate worker pool.
