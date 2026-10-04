"""Turn an experiment JSON into markdown tables (used for docs/experiments.md; nothing is typed by hand).

    python -m app.experiments.make_tables experiment_outputs/default_cell_blockage.json
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from typing import Any

LABEL = {"single_agent": "A single-agent", "local": "B local negotiated"}


def _f(v: Any, d: int = 1) -> str:
    return "-" if v is None else f"{v:.{d}f}"


def table(summary: list[dict], metric: str, rows_key: str, cols_key: str, fixed: dict, d: int = 1,
          with_std: bool = True) -> str:
    rows = sorted({r[rows_key] for r in summary if all(r[k] == v for k, v in fixed.items())})
    cols = sorted({r[cols_key] for r in summary})
    out = [f"| {rows_key} \\ {cols_key} | " + " | ".join(f"{c}" for c in cols) + " |",
           "|---|" + "---|" * len(cols)]
    for x in rows:
        cells = []
        for c in cols:
            parts = []
            for s in ("single_agent", "local"):
                rec = next((r for r in summary if r["strategy"] == s and r[rows_key] == x and r[cols_key] == c
                            and all(r[k] == v for k, v in fixed.items())), None)
                if rec is None:
                    continue
                m, sd = rec.get(f"{metric}_mean"), rec.get(f"{metric}_std")
                parts.append(f"{ {'single_agent': 'A', 'local': 'B'}[s] }:{_f(m, d)}" + (f"±{_f(sd, d)}" if with_std and sd is not None else ""))
            cells.append("<br>".join(parts))
        out.append(f"| {x} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def success_table(summary: list[dict]) -> str:
    ns = sorted({r["n_agents"] for r in summary})
    rhos = sorted({r["density"] for r in summary})
    out = ["| N \\ rho | " + " | ".join(str(r) for r in rhos) + " |", "|---|" + "---|" * len(rhos)]
    for n in ns:
        cells = []
        for rho in rhos:
            parts = []
            for s, tag in (("single_agent", "A"), ("local", "B")):
                rec = next((r for r in summary if r["strategy"] == s and r["n_agents"] == n and r["density"] == rho), None)
                if rec:
                    parts.append(f"{tag}:{rec['success_rate'] * 100:.0f}%")
            cells.append(" ".join(parts))
        out.append(f"| {n} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def failure_reasons(rows: list[dict]) -> str:
    cnt: dict[tuple[str, str], int] = defaultdict(int)
    for r in rows:
        if r["success"] or r.get("skipped"):
            continue
        reason = r.get("failure_reason") or r.get("error") or "unknown"
        if "negotiation disabled" in reason:
            key = "conflict with an unchanged plan (negotiation disabled)"
        elif "no feasible route" in reason or "unsolvable" in reason or "no solution" in reason:
            key = "no feasible route even if neighbours yield / group unsolvable"
        elif "no active robot" in reason or "cannot be recovered" in reason:
            key = "task cannot be reassigned"
        else:
            key = reason[:70]
        cnt[(r["strategy"], key)] += 1
    out = ["| strategy | failure reason | runs |", "|---|---|---|"]
    for (s, k), v in sorted(cnt.items()):
        out.append(f"| {LABEL[s]} | {k} | {v} |")
    return "\n".join(out)


def main(path: str) -> None:
    d = json.load(open(path, encoding="utf-8"))
    summary, rows = d["summary"], d["rows"]
    print(f"Config: {json.dumps({k: v for k, v in d['config'].items() if k not in ('seeds',)})}\n")
    print(f"Total runs: {d['total_runs']}, wall time {d['runtime_s']:.0f} s\n")
    print("### Success rate (share of runs completing all tasks)\n" + success_table(summary) + "\n")
    for metric, title, dd in (("flowtime", "Flowtime", 0), ("num_modified", "Modified agents", 1),
                              ("repair_time_ms", "Repair time (ms)", 0), ("messages", "Messages", 1),
                              ("affected_expansions", "Affected-set expansions per run", 2),
                              ("max_affected_size", "Largest |A_d| of any repair", 1),
                              ("modified_ratio", "Modified ratio", 2)):
        print(f"### {title} vs agent count (rows) and density (columns); mean±std over successful runs\n"
              + table(summary, metric, "n_agents", "density", {}, dd) + "\n")
    print("### Failure reasons\n" + failure_reasons(rows) + "\n")
    print("\n### Paired comparison, B (local) vs A (single-agent)")
    for k, v in d["paired_local_vs_single_agent"].items():
        print(f"- {k}: {v:.3f}" if isinstance(v, float) else f"- {k}: {v}")


if __name__ == "__main__":
    main(sys.argv[1])
