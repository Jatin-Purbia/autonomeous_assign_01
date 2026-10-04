"""Aggregation of experiment rows: mean, sample standard deviation, success rate."""
from __future__ import annotations

from typing import Any, Sequence

from ..domain.metrics import mean, sample_std, success_rate

METRICS = ["flowtime", "makespan", "delta_flowtime", "num_modified", "modified_ratio", "repair_time_ms",
           "messages", "additional_path_length", "total_waits", "mean_impact_per_disruption",
           "conflicts_avoided", "total_path_length", "affected_expansions", "max_affected_size"]


def summarize(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """One record per (strategy, n_agents, density).

    Means / standard deviations are computed over *successful* runs (a failed run has no completion
    times); ``success_rate`` is computed over all runs.  ``n`` and ``n_success`` are reported.
    """
    groups: dict[tuple, list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault((r["strategy"], r["n_agents"], r["density"]), []).append(r)
    out = []
    for (strategy, n, rho), rs in sorted(groups.items()):
        ok = [r for r in rs if r["success"]]
        rec: dict[str, Any] = {"strategy": strategy, "n_agents": n, "density": rho, "n": len(rs),
                               "n_success": len(ok), "success_rate": success_rate(r["success"] for r in rs),
                               "collisions": sum(r["collisions"] for r in rs),
                               "deadlocks": sum(r["deadlocks"] for r in rs),
                               "errors": sum(1 for r in rs if r.get("error"))}
        for m in METRICS:
            vals = [float(r[m]) for r in ok if r.get(m) is not None]
            rec[f"{m}_mean"] = mean(vals) if vals else None
            rec[f"{m}_std"] = sample_std(vals) if vals else None
        out.append(rec)
    return out


def paired_comparison(rows: Sequence[dict[str, Any]], a: str = "local", b: str = "single_agent") -> dict[str, Any]:
    """Compare two strategies on runs where *both* succeeded (same seed, same scenario)."""
    by = {}
    for r in rows:
        by.setdefault((r["n_agents"], r["density"], r["seed"]), {})[r["strategy"]] = r
    pairs = [(v[a], v[b]) for v in by.values() if a in v and b in v and v[a]["success"] and v[b]["success"]]
    if not pairs:
        return {"pairs": 0}
    return {
        "pairs": len(pairs),
        f"mean_modified_{a}": mean([p[0]["num_modified"] for p in pairs]),
        f"mean_modified_{b}": mean([p[1]["num_modified"] for p in pairs]),
        f"mean_flowtime_{a}": mean([p[0]["flowtime"] for p in pairs]),
        f"mean_flowtime_{b}": mean([p[1]["flowtime"] for p in pairs]),
        f"mean_repair_ms_{a}": mean([p[0]["repair_time_ms"] for p in pairs]),
        f"mean_repair_ms_{b}": mean([p[1]["repair_time_ms"] for p in pairs]),
        f"{a}_modifies_fewer_or_equal": sum(1 for p in pairs if p[0]["num_modified"] <= p[1]["num_modified"]) / len(pairs),
        f"{b}_lower_flowtime": sum(1 for p in pairs if p[1]["flowtime"] < p[0]["flowtime"]) / len(pairs),
    }
