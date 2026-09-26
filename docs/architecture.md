# Architecture

The algorithmic engine is a plain Python package with **no dependency on FastAPI or the frontend**. The same code is driven by the REST/WebSocket API, the CLI (`python -m app.cli`), the batch runner (`python -m app.experiments.batch_runner`) and pytest.

```
backend/app
  domain/        grid.py (Position, Grid, DynamicObstacle, ObstacleMap)  task.py  robot.py
                 disruption.py  metrics.py (flowtime, makespan, impact, mean, sample std, ...)
  planning/      space_time_astar.py  heuristics.py  reservation_table.py
                 collision_detection.py  prioritized_mapf.py           <- initial planning only
  repair/        dispatcher.py        disruption -> repair problem, strategy selection (A / B / C)
                 local_repair.py      RepairSession (strategies 1-6, negotiation, expansion) + global baseline
                 affected_set.py      A_d^0 detection and A_d tracking
                 conflict_graph.py    temporary conflict graph C = (A, E_C)
                 negotiation.py       bid function, message bus (message count metric)
                 task_reassignment.py breakdown task pool, emergency insertion, assignment cost
                 repair_validation.py validation of tentative repairs
                 models.py            RepairConfig, RepairContext, RepairResult, Message
  simulation/    engine.py            discrete-time execution, invariants, metrics, snapshot
                 event_log.py  event_scheduler.py  scenario_loader.py
                 builtin_scenarios.py scenario_generator.py
  experiments/   configurations.py  batch_runner.py  statistics.py
  api/           schemas.py (Pydantic)  simulation_routes.py  experiment_routes.py  websocket.py  state.py
  cli.py  main.py
  tests/

frontend (Next.js / TypeScript / Tailwind / Framer Motion / Recharts)
  app/            page.tsx  simulation/page.tsx  experiments/page.tsx
  components/     GridView  RobotSprite  ControlPanel  DisruptionPanel  MetricsPanel  Timeline
                  EventLog  ConflictGraph  RepairInspector  ExperimentCharts  ui
  lib/            api.ts  websocket.ts  types.ts  viz.ts
```

## Data flow

```
UI / CLI / test / batch  ->  SimulationEngine.step()
                               1. scheduler.pop_due(t)  -> Disruption
                               2. repair.dispatcher.apply_disruption(ctx, d, strategy)
                                     updates obstacles / tasks, builds RepairSession, returns RepairResult
                               3. engine._finish_repair: validate, commit atomically, rebuild reservations
                               4. execute t -> t+1 (collision assertions), update tasks, invariants
                             -> EventLog (structured events)  -> snapshot() -> WebSocket / REST
```

`RepairSession` works on a **copy** of the reservation table; robots' `active_plan`s are only replaced by the engine after the whole repair validated. On failure nothing is replaced.

## Invariants (checked after every timestep in development mode)

1. No two robots occupy the same cell at the same timestep.
2. No two robots swap cells in one timestep.
3. No robot is inside an active obstacle (other than the timestep an obstacle appears under it).
4. A pickup precedes its delivery.
5. Executed prefixes never change (`active_plan[:t+1] == executed_prefix`).
6. Unaffected plans are identical after a repair (asserted at commit).
7. Every committed repair is validated against all remaining plans and all obstacles.
8. A broken robot never moves.
9. Every unfinished task is owned by exactly one robot.
10. Metrics are computed from executed trajectories (`executed_prefix`), not from plans.

Violations raise `CollisionError` / `InvariantError`; the fuzz tests in `test_milestone6_8_repair.py` and the batch runner's stress runs exercise them on random scenarios.

## REST / WebSocket API

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/api/scenarios`, `/api/scenarios/{id}`, `/api/scenarios/random` | list / save / fetch / generate scenarios |
| POST | `/api/simulation/initialize` | load a scenario (`scenario_id`, inline `scenario` or `random`), choose strategy, repair parameters |
| POST | `/api/simulation/start` `pause` `step` `reset` `speed` | control |
| GET | `/api/simulation/state` `metrics` `events` | inspection |
| POST | `/api/disruptions/block-cell` `break-robot` `emergency-task` | inject now or at `activation_time` |
| DELETE | `/api/disruptions/obstacle/{id}`, `/api/disruptions/scheduled/{id}` | remove a temporary obstacle / cancel a scheduled disruption |
| POST/GET | `/api/experiments/run`, `/api/experiments/{id}`, `/api/experiments/{id}/export?format=csv|json&table=summary|runs` | batch experiments |
| WS | `/ws/simulation` | pushes `{type:"state", state, events, running}`; accepts `{cmd: start|pause|step|reset|speed}` |

Interactive docs: <http://localhost:8000/docs>.
