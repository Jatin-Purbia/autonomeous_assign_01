import pytest

from app.domain.metrics import mean, sample_std
from app.experiments.batch_runner import build_run_spec, run_experiment, run_one
from app.experiments.configurations import ExperimentConfig
from app.experiments.statistics import paired_comparison, summarize


def small_cfg(**kw):
    base = dict(agent_counts=[4], densities=[0.0, 0.1], repetitions=3, disruption_type="cell_blockage")
    base.update(kw)
    return ExperimentConfig(**base)


def test_same_seed_gives_identical_scenarios_and_disruptions():
    cfg = small_cfg()
    a = build_run_spec(cfg, 6, 0.1, 5)
    b = build_run_spec(cfg, 6, 0.1, 5)
    assert a == b
    assert a != build_run_spec(cfg, 6, 0.1, 6)


def test_density_defines_number_of_blocked_cells():
    cfg = small_cfg()
    spec = build_run_spec(cfg, 8, 0.1, 1)
    from app.domain.grid import Grid
    n_free = Grid.from_ascii(spec["map"]).traversable_count
    n_blocks = sum(1 for d in spec["disruptions"] if d["type"] == "cell_blockage")
    assert n_blocks <= round(0.1 * n_free) and n_blocks >= 0.8 * round(0.1 * n_free)
    assert not build_run_spec(cfg, 8, 0.0, 1)["disruptions"]


def test_run_one_is_deterministic():
    args = (small_cfg().to_dict(), 5, 0.1, 2, "local")
    r1, r2 = run_one(args), run_one(args)
    for k in ("flowtime", "makespan", "num_modified", "messages", "success"):
        assert r1[k] == r2[k]


def test_experiment_summary_matches_manual_statistics():
    res = run_experiment(small_cfg(strategies=["local"]), workers=1)
    rows = [r for r in res["rows"] if r["density"] == 0.1 and r["success"]]
    rec = next(s for s in res["summary"] if s["density"] == 0.1)
    assert rec["flowtime_mean"] == pytest.approx(mean([r["flowtime"] for r in rows]))
    assert rec["flowtime_std"] == pytest.approx(sample_std([r["flowtime"] for r in rows]))
    assert rec["success_rate"] == rec["n_success"] / rec["n"]
    zero = next(s for s in res["summary"] if s["density"] == 0.0)
    assert zero["num_modified_mean"] == 0 and zero["success_rate"] == 1.0   # no disruption -> no repair


def test_all_strategies_run_on_identical_scenarios_and_local_never_collides():
    res = run_experiment(small_cfg(disruption_type="mixed"), workers=1)
    assert {r["strategy"] for r in res["rows"]} == {"single_agent", "local"}
    assert all(r["collisions"] == 0 and not r["error"] for r in res["rows"])
    seeds = {(r["n_agents"], r["density"], r["seed"]) for r in res["rows"]}
    assert len(res["rows"]) == 2 * len(seeds)


def test_paired_comparison_only_uses_pairs_where_both_succeed():
    rows = [
        {"strategy": "local", "n_agents": 5, "density": .1, "seed": 0, "success": True, "num_modified": 2, "flowtime": 10, "repair_time_ms": 1},
        {"strategy": "single_agent", "n_agents": 5, "density": .1, "seed": 0, "success": True, "num_modified": 5, "flowtime": 9, "repair_time_ms": 9},
        {"strategy": "local", "n_agents": 5, "density": .1, "seed": 1, "success": True, "num_modified": 1, "flowtime": 8, "repair_time_ms": 1},
        {"strategy": "single_agent", "n_agents": 5, "density": .1, "seed": 1, "success": False, "num_modified": 0, "flowtime": 0, "repair_time_ms": 0},
    ]
    p = paired_comparison(rows)
    assert p["pairs"] == 1 and p["mean_modified_local"] == 2 and p["mean_modified_single_agent"] == 5


def test_invalid_config_rejected():
    with pytest.raises(ValueError):
        ExperimentConfig.from_dict({"disruption_type": "nope"})
    with pytest.raises(ValueError):
        ExperimentConfig.from_dict({"densities": [1.5]})


def test_integer_and_float_zero_density_are_identical():
    """Regression: rho=0 (int, e.g. an argparse default) and rho=0.0 must generate the same run."""
    cfg = small_cfg(disruption_type="robot_breakdown", densities=[0, 0.1])
    assert cfg.densities == [0.0, 0.1] and all(isinstance(d, float) for d in cfg.densities)
    assert build_run_spec(cfg, 5, 0, 1) == build_run_spec(cfg, 5, 0.0, 1)
    assert run_one((cfg.to_dict(), 5, 0, 1, "local"))["flowtime"] == run_one((cfg.to_dict(), 5, 0.0, 1, "local"))["flowtime"]
