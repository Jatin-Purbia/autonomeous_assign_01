# Incremental Multi-Agent Path Repair for Dynamic Automated Warehouses

An interactive, **working algorithmic simulation** of robots in an automated warehouse. Robots first receive collision-free
plans from prioritized **Space-Time A\*** (vertex + edge-swap reservations). While they execute, disruptions arrive:

1. a grid cell is suddenly **blocked**,
2. a robot **breaks down**,
3. a high-priority **emergency task** is assigned.

The system repairs **only the necessary parts of the existing plans** (no global replanning): it identifies the directly
affected robots, tries cheap local repairs (wait, shift, detour), lets neighbours **negotiate** with Contract-Net style bids,
expands the affected set only when unavoidable, and preserves every unaffected plan and every executed prefix. Global
replanning exists only as an experimental baseline.

![Simulation](docs/screenshots/simulation_repair.png)

## What is inside

| Part | Where |
|---|---|
| Engine (planning, repair, simulation, metrics) - independent of the UI | `backend/app/{domain,planning,repair,simulation}` |
| REST + WebSocket API (FastAPI, Pydantic) | `backend/app/api` |
| Batch experiments, statistics, CSV/JSON export | `backend/app/experiments` |
| Interactive UI + experiment dashboard (Next.js, TypeScript, Tailwind, Framer Motion, Recharts) | `frontend/` |
| Tests (pytest, 75 tests) | `backend/app/tests` |
| Documentation | `docs/` (`architecture.md`, `algorithm.md`, `experiments.md`, `assignment_report_outline.md`) |

## Installation

Requirements: Python 3.11+ (developed on 3.12), Node.js 20+.

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# frontend
cd ../frontend
npm install
```

## Run

```bash
# terminal 1 - backend (http://localhost:8000, interactive API docs at /docs)
cd backend
python -m uvicorn app.main:app --port 8000

# terminal 2 - frontend (http://localhost:3000)
cd frontend
npm run dev          # or: npm run build && npm start
```

On Windows, `.\start.ps1` (repo root) frees ports 8000/3000 if a stale process holds them and opens both servers in
their own windows. If you see `[Errno 10048] ... 8000` or `EADDRINUSE ... 3000`, a server is already running on that
port: use it, or stop it with `netstat -ano | findstr :8000` then `taskkill /PID <pid> /F`.

The frontend talks to `http://localhost:8000` (override with `NEXT_PUBLIC_API_URL`).

## Tests

```bash
cd backend
python -m pytest            # 75 tests: A*, MAPF, engine, repair, negotiation, breakdown, emergency, metrics, API, experiments
cd ../frontend
npx tsc --noEmit            # type check
```

## Demonstration (5 built-in scenarios)

Open <http://localhost:3000/simulation>, pick a scenario, press **Load scenario**, then **Start** (or **Step**).

| # | Scenario | What to watch | Expected |
|---|---|---|---|
| 1 | Cell blockage | R1 detours around a blocked cell; the other plans stay identical | Impact = 1, 0 messages |
| 2 | Negotiated repair | R1's repaired route collides with R3's reserved route; R1 negotiates, R3 yields | Impact = 2, bids in the Repair tab |
| 3 | Robot breakdown | R2 stops in a 1-wide aisle, its cell is blocked, its task is reassigned, neighbours are repaired | task moves to the best robot |
| 4 | Emergency task | R1 gets a high-priority task; its own yield bid is huge, so R2 yields | R3-R5 untouched |
| 5 | Stress | 30 robots, 12 timed blockages and a breakdown | the affected set grows |

In the UI you can also: click **Block cell** and click the grid; select a robot and press **Break**; use **Emergency task** and
click a pickup then a delivery cell; type a timestep (or leave it blank for "now") and a blockage duration; remove a
temporary obstacle; generate a random scenario from a seed; switch the repair strategy (A/B/C); tune the assignment weights
lambda and mu; scrub the **timeline** to inspect earlier timesteps.

Visual language: thin **dashed** line = original plan, thick **solid bright** line = repaired section, faint line = executed
path. **Red ring** = directly affected robot, **orange ring** = indirectly affected robot. The right-hand panel shows the
affected set, expansion history, negotiation messages, *why* each agent was modified, old-vs-new suffix comparison, the
**conflict graph** and the structured event log.

From the command line (no UI):

```bash
cd backend
python -m app.cli list
python -m app.cli run s2-negotiated-repair --strategy local --events
```

## Experiments

Dashboard: <http://localhost:3000/experiments>. Configure agent counts (default 5,10,20,30,40), obstacle densities
(0, 0.05, 0.10, 0.15, 0.20), disruption type (cell blockage / breakdown / emergency / mixed), repetitions (default 20) and a
first seed or an explicit seed list, then run. The 8 charts (with error bars and a success-rate heatmap) can be exported as CSV/JSON.

From the command line (parallel, deterministic):

```bash
cd backend
python -m app.experiments.batch_runner --type mixed --reps 20 --seed 0 --out experiment_outputs --name my_run
```

Outputs: `<name>.json`, `<name>_runs.csv` (one row per run) and `<name>_summary.csv` (mean / sample std / success rate per
strategy, agent count and density). Results of the runs performed for this project and their analysis: `docs/experiments.md`.

## Algorithm summary

* **Initial planning** - prioritized Space-Time A\* over states `(x, y, t, q)` with `f = g + h`, Manhattan-chain heuristic,
  waiting allowed, reservation of complete paths, a few priority-order retries.
* **Disruption** - `A_d^0` = agents whose *remaining* plan is invalidated; only their future reservations are released.
* **Repair order** - wait, temporal shift, local detour (rejoining the old plan), single-agent replan, then negotiation with
  the neighbours blocking the agent's ideal route (`Bid = w1*dC + w2*dL + w3*P + w4*M`), priority exchange, affected-set expansion
  `A <- A U {a_j}`, group Space-Time A\*. Everything is validated against all fixed reservations and obstacles before an atomic commit.
* **Breakdown** - the robot stops, its cell is blocked, unfinished tasks are reassigned by
  `Cost = d(pos,pickup) + d(pickup,delivery) + lambda*Load + mu*RepairImpact`.
* **Emergency** - the task is inserted into the best robot's sequence and its priority is raised; lower-priority robots yield.
* **Objective** - lexicographic: minimise `|A_d|`, then added completion time, then messages and repair time.

Details and complexity: `docs/algorithm.md`.

## Limitations

* Prioritized planning is incomplete; some solvable instances are reported as failed, and a failed repair ends the run.
* Robots leave the grid after their last delivery (no parked robots); a broken robot stopping on another robot's pickup or
  delivery cell makes that task unreachable.
* Blockage durations are known when the blockage is announced; capacity-1 robots; instantaneous pickup/delivery.
* One interactive simulation per backend process; results are for a synthetic shelf-and-aisle layout.
* The broken robot counts as a modified agent; see `docs/algorithm.md` section 10 for all metric definitions and caveats.

## Future work

Complete repair (e.g. conflict-based search on the affected group), parked robots with re-entry, service times and charging,
multi-item capacity, learned negotiation weights, real warehouse traces.
