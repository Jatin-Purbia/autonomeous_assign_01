"""Batch experiments.  Deterministic: every (N, rho, seed) scenario and disruption sequence depends only
on the seed, and all strategies are run on identical scenarios/disruptions (paired comparison).

CLI:  python -m app.experiments.batch_runner --agents 5 10 --density 0 0.1 --type mixed --reps 5 --out out
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Optional

from ..domain.metrics import obstacle_density
from ..simulation.engine import EngineConfig, SimulationEngine
from ..simulation.scenario_generator import generate_random_scenario
from .configurations import STRATEGIES, ExperimentConfig
from .statistics import paired_comparison, summarize


def make_disruptions(probe: SimulationEngine, cfg: ExperimentConfig, n_blocks: int, rng: random.Random) -> list[dict]:
    """Seeded disruption list, targeted at cells that robots' original plans actually use."""
    robots = [r for r in probe.robots.values() if len(r.original_plan) >= 6]
    out: list[dict] = []
    used_cells: set[tuple[int, int]] = set()
    kind = cfg.disruption_type

    cells = probe.grid.traversable_cells()
    horizon = max((len(r.original_plan) for r in probe.robots.values()), default=10)

    def add_blockage(i: int) -> None:
        for _ in range(20):
            if robots and rng.random() < cfg.targeted_fraction:  # cell on a planned path (guaranteed to matter)
                r = rng.choice(robots)
                tp = r.original_plan[rng.randint(2, len(r.original_plan) - 2)]
                cell = (tp.position.x, tp.position.y)
                td = max(1, tp.time - rng.randint(1, 4))
                dur = max(rng.randint(cfg.block_duration_min, cfg.block_duration_max), tp.time - td)
            else:  # uniformly random cell and time
                c = rng.choice(cells)
                cell = (c.x, c.y)
                td = rng.randint(1, max(1, int(0.8 * horizon)))
                dur = rng.randint(cfg.block_duration_min, cfg.block_duration_max)
            if cell in used_cells:
                continue
            used_cells.add(cell)
            out.append({"id": f"B{i + 1}", "type": "cell_blockage", "time": td, "position": list(cell),
                        "duration": dur})
            return

    for i in range(n_blocks):
        add_blockage(i)
    if kind in ("robot_breakdown", "mixed") and robots:
        for i in range(cfg.n_breakdowns):
            r = rng.choice(robots)
            out.append({"id": f"X{i + 1}", "type": "robot_breakdown",
                        "time": rng.randint(2, max(2, len(r.original_plan) - 3)), "robot_id": r.robot_id})
    if kind in ("emergency_task", "mixed"):
        for i in range(cfg.n_emergencies):
            pu, de = rng.sample(cells, 2)
            out.append({"id": f"E{i + 1}", "type": "emergency_task", "time": rng.randint(1, max(1, horizon // 3)),
                        "task": {"id": f"EM{i + 1}", "pickup": [pu.x, pu.y], "delivery": [de.x, de.y],
                                 "priority": 10}})
    return out


def build_run_spec(cfg: ExperimentConfig, n_agents: int, rho: float, seed: int) -> Optional[dict[str, Any]]:
    """Scenario + disruptions for one (N, rho, seed); retries neighbouring seeds if initial planning is infeasible."""
    for attempt in range(6):
        s = seed + 100_000 * attempt
        spec = generate_random_scenario(n_agents, s, cfg.width, cfg.height, cfg.tasks_per_robot)
        probe = SimulationEngine(spec, EngineConfig(record_movement=False, dev_checks=False, seed=s))
        if probe.status == "failed":
            continue
        rng = random.Random(f"{s}-{float(rho)}-{cfg.disruption_type}")
        n_blocks = 0
        if cfg.disruption_type in ("cell_blockage", "mixed") or rho > 0:
            n_blocks = round(rho * probe.grid.traversable_count)
        spec["disruptions"] = make_disruptions(probe, cfg, n_blocks, rng)
        spec["_meta"] = {"seed_used": s, "attempt": attempt, "n_blocks": n_blocks,
                         "realised_density": obstacle_density(
                             sum(1 for d in spec["disruptions"] if d["type"] == "cell_blockage"),
                             probe.grid.traversable_count)}
        return spec
    return None


def run_one(args: tuple[dict[str, Any], int, float, int, str]) -> dict[str, Any]:
    cfg_d, n_agents, rho, seed, strategy = args
    cfg = ExperimentConfig.from_dict(cfg_d)
    row: dict[str, Any] = {"strategy": strategy, "n_agents": n_agents, "density": rho, "seed": seed,
                           "disruption_type": cfg.disruption_type, "success": False, "collisions": 0,
                           "deadlocks": 0, "error": None}
    spec = build_run_spec(cfg, n_agents, rho, seed)
    if spec is None:
        row.update(error="initial planning infeasible for all retried seeds", skipped=True)
        return row
    meta = spec.pop("_meta")
    t0 = time.perf_counter()
    try:
        eng = SimulationEngine(spec, EngineConfig(strategy=strategy, max_time=cfg.max_time, dev_checks=False,
                                                  record_movement=False, seed=meta["seed_used"]))
        res = eng.run()
    except AssertionError as exc:  # collision / invariant violation would be a bug: record it loudly
        row.update(error=f"{type(exc).__name__}: {exc}", collisions=1)
        return row
    impacts = [d.impact for d in res.per_disruption if d.success]
    row.update(
        success=res.success, failure_reason=res.failure_reason, n_disruptions=res.n_disruptions,
        realised_density=meta["realised_density"], seed_attempt=meta["attempt"],
        flowtime=res.flowtime, makespan=res.makespan, original_flowtime=res.original_flowtime,
        delta_flowtime=res.delta_flowtime, num_modified=res.num_modified, modified_ratio=res.modified_ratio,
        mean_impact_per_disruption=(sum(impacts) / len(impacts)) if impacts else 0.0,
        repair_time_ms=res.repair_time_ms, messages=res.messages, additional_path_length=res.additional_path_length,
        total_path_length=res.total_path_length, total_waits=res.total_waits, collisions=res.collisions,
        deadlocks=res.deadlocks, conflicts_avoided=res.conflicts_avoided, n_repairs_failed=res.n_repairs_failed,
        affected_expansions=res.affected_expansions, max_affected_size=res.max_affected_size,
        wall_ms=(time.perf_counter() - t0) * 1000)
    return row


def run_experiment(cfg: ExperimentConfig, progress: Optional[Callable[[int, int], None]] = None,
                   workers: Optional[int] = None) -> dict[str, Any]:
    cfg.validate()
    jobs = [(cfg.to_dict(), n, rho, seed, strat)
            for n in cfg.agent_counts for rho in cfg.densities for seed in cfg.seed_list()
            for strat in cfg.strategies]
    rows: list[dict[str, Any]] = []
    total = len(jobs)
    workers = workers if workers is not None else min(os.cpu_count() or 1, 8)
    t0 = time.perf_counter()
    if workers <= 1 or total < 4:
        for i, j in enumerate(jobs):
            rows.append(run_one(j))
            if progress:
                progress(i + 1, total)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(run_one, j) for j in jobs]
            for i, f in enumerate(as_completed(futs)):
                rows.append(f.result())
                if progress:
                    progress(i + 1, total)
    rows.sort(key=lambda r: (r["strategy"], r["n_agents"], r["density"], r["seed"]))
    valid = [r for r in rows if not r.get("skipped")]
    return {"config": cfg.to_dict(), "rows": rows, "summary": summarize(valid),
            "paired_local_vs_single_agent": paired_comparison(valid, "local", "single_agent"),
            "runtime_s": time.perf_counter() - t0, "total_runs": total}


def export_results(result: dict[str, Any], out_dir: str | Path, name: str) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {"json": out / f"{name}.json", "runs_csv": out / f"{name}_runs.csv", "summary_csv": out / f"{name}_summary.csv"}
    paths["json"].write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    for key, data in (("runs_csv", result["rows"]), ("summary_csv", result["summary"])):
        if not data:
            continue
        cols: list[str] = []
        for r in data:
            for k in r:
                if k not in cols:
                    cols.append(k)
        with open(paths[key], "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(data)
    return {k: str(v) for k, v in paths.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description="Run multi-agent repair experiments")
    ap.add_argument("--agents", type=int, nargs="+", default=[5, 20, 40])
    ap.add_argument("--density", type=float, nargs="+", default=[0, 0.10, 0.20])
    ap.add_argument("--type", default="cell_blockage", choices=["cell_blockage", "robot_breakdown",
                                                                "emergency_task", "mixed"])
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--tasks", type=int, default=1, help="tasks (pickup+delivery) per robot")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--strategies", nargs="+", default=list(STRATEGIES))
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--out", default="experiment_outputs")
    ap.add_argument("--name", default=None)
    a = ap.parse_args()
    cfg = ExperimentConfig(agent_counts=a.agents, densities=a.density, disruption_type=a.type, repetitions=a.reps,
                           seed=a.seed, strategies=a.strategies, tasks_per_robot=a.tasks)

    def prog(done: int, total: int) -> None:
        print(f"\r{done}/{total} runs", end="", flush=True)

    res = run_experiment(cfg, prog, a.workers)
    print()
    name = a.name or f"{a.type}_{uuid.uuid4().hex[:6]}"
    print(json.dumps(export_results(res, a.out, name), indent=2))
    print(f"runtime {res['runtime_s']:.1f}s")


if __name__ == "__main__":
    main()
