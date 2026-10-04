"""Command-line front end for the engine (no UI needed).

    python -m app.cli list
    python -m app.cli run s2-negotiated-repair --strategy local [--events]
"""
from __future__ import annotations

import argparse
import json

from .simulation.builtin_scenarios import builtin_scenarios
from .simulation.engine import EngineConfig, SimulationEngine


def main() -> None:
    ap = argparse.ArgumentParser(prog="app.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list built-in scenarios")
    run = sub.add_parser("run", help="run a scenario to completion")
    run.add_argument("scenario")
    run.add_argument("--strategy", default="local", choices=["local", "single_agent"])
    run.add_argument("--events", action="store_true", help="print the structured event log")
    a = ap.parse_args()
    scenarios = builtin_scenarios()
    if a.cmd == "list":
        for sid, s in scenarios.items():
            print(f"{sid:24s} {s['name']}")
        return
    eng = SimulationEngine(scenarios[a.scenario], EngineConfig(strategy=a.strategy, record_movement=False))
    res = eng.run()
    if a.events:
        for e in eng.log.events:
            print(json.dumps(e.to_dict()))
    out = res.to_dict()
    out.pop("per_disruption")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
