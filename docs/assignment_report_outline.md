# Assignment report outline

*Incremental Multi-Agent Path Repair for Dynamic Automated Warehouses.*
Each section lists what to write and where the material comes from. **Do not type result numbers from memory:**
take every number from the files in `backend/experiment_outputs/` (see `docs/experiments.md`) or from a fresh run.

## 1. Abstract
Problem (dynamic warehouse, disruptions), approach (Space-Time A* + reservation table + incremental, negotiated repair that touches as few robots as possible), evaluation (5 agent counts x 5 obstacle densities x 20 seeds x 3 strategies), and 2-3 headline findings. Write it last, quoting numbers from `default_*_summary.csv`.

## 2. Introduction
Motivation (automated warehouses, changing environments), why replanning everything is disruptive, the research question: *can plans be repaired locally while keeping the number of modified robots minimal?* Contributions (bullets). Roadmap of the report.

## 3. Problem formulation
Grid `G=(V,E)`, robots, tasks, timesteps, actions. Plans `pi_i = pi_i^executed (+) pi_i^remaining`. Disruptions (blockage, breakdown, emergency). Collision constraints (vertex, edge swap). Objective: flowtime, makespan, and the lexicographic repair objective `min |A_d|`, then `min sum dC`, then messages and runtime. Source: `docs/algorithm.md` sections 0 and 6.

## 4. Related concepts
Multi-agent path finding (MAPF), prioritized planning, Space-Time A*, reservation tables, plan repair vs replanning, Contract-Net protocol, lifelong/online MAPF. (Cite the literature you read; this prototype implements the concepts, not a specific paper.)

## 5. Warehouse environment
Shelf/aisle layout (`scenario_generator.warehouse_map`), cell states, capacity-1 robots, exit-at-goal assumption, known blockage intervals. Figure: `docs/screenshots/`.

## 6. Initial Space-Time A* planning
State `(x, y, t, q)`, `f = g + h`, Manhattan-chain heuristic and its admissibility, waiting, waypoint semantics (pickup before delivery), reservation table, priority-order retries. Include the pseudocode from `algorithm.md` section 1 and 3. Mention the incompleteness of prioritized planning (tight-corridor test).

## 7. Dynamic disruption model
Definitions and handling of the three disruption types, direct affected set `A_d^0`, task reassignment cost `Cost(a_j, tau)`, emergency insertion. Source: `algorithm.md` section 5.

## 8. Proposed incremental repair algorithm
`LOCAL_PLAN_REPAIR` pseudocode, the repair strategies in order (delay, detour, negotiation, expansion, group replan), atomic commit, validation. Include a worked example: scenario 1 (Impact = 1) and scenario 2 (Impact = 2) with the event log excerpt (`python -m app.cli run s2-negotiated-repair --events`).

## 9. Neighbour negotiation protocol
Message types, bid function `Bid_i = w1 dC + w2 dL + w3 P + w4 M`, chosen weights, emergency priority penalty, priority exchange. Include a message sequence diagram taken from the UI (Repair tab) or the event log.

## 10. Experimental methodology
Configuration space (N, rho, disruption type, seeds), how blockages are generated (targeted fraction, durations), that all strategies see identical scenarios and disruptions (paired design), statistics (mean, sample std over successful runs; success rate over all runs), hardware, software versions. Source: `docs/experiments.md`.

## 11. Metrics
Flowtime, makespan, Impact and ImpactRatio, Delta flowtime, repair runtime, messages, additional path length, success rate, collisions, deadlocks, conflicts avoided; definitions of "modified agent" (plan differs; message-only agents excluded) and of the completion time of a broken robot.

## 12. Results
Tables and the 8 charts produced by the dashboard (export CSV/JSON). One subsection per hypothesis in `docs/experiments.md` section "Hypotheses": state the observation with numbers and whether it is supported, not supported, or only partly supported. Do not assume the expected direction.

## 13. Discussion
Interpretation, local negotiated repair vs single-agent repair (success rate, modified robots, runtime), when the affected set grows, sensitivity to `w4`, failure analysis (failure reasons in `*_runs.csv`).

## 14. Limitations
Copy and adapt `algorithm.md` section 10; add threats to validity (synthetic layout, single grid size, generated disruptions, short task lists, parameter choices).

## 15. Conclusion
What was built, what was found, future work: complete MAPF repair (CBS-style), parked robots and re-entry, dwell times, larger task lists, learned negotiation weights, real warehouse traces.

## Appendices
A. Repository layout (`docs/architecture.md`). B. Test summary (`pytest`). C. Parameter table (`RepairConfig`). D. Full result tables (CSV).
