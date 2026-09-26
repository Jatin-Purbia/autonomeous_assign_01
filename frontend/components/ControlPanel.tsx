"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ScenarioSummary, SimState, Strategy } from "@/lib/types";
import { Btn, Field, Panel, inputCls } from "./ui";

type Props = {
  state: SimState | null;
  running: boolean;
  connected: boolean;
  speed: number;
  send: (cmd: string, value?: number) => void;
  onInitialised: (state: SimState) => void;
  onError: (msg: string) => void;
};

export default function ControlPanel({ state, running, connected, speed, send, onInitialised, onError }: Props) {
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [scenarioId, setScenarioId] = useState("s1-cell-blockage");
  const [strategy, setStrategy] = useState<Strategy>("local");
  const [seed, setSeed] = useState(0);
  const [nAgents, setNAgents] = useState(12);
  const [busy, setBusy] = useState(false);
  const [lambda, setLambda] = useState(4);
  const [mu, setMu] = useState(2);

  useEffect(() => {
    api.scenarios().then(setScenarios).catch((e) => onError(String(e.message ?? e)));
  }, [onError]);

  const init = async (body: Parameters<typeof api.initialize>[0]) => {
    setBusy(true);
    try {
      const res = await api.initialize({ ...body, repair_config: { lambda_load: lambda, mu_impact: mu } });
      onInitialised(res.state);
      if (body.random) api.scenarios().then(setScenarios);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const finished = state?.status === "completed" || state?.status === "failed";
  const selected = scenarios.find((s) => s.id === scenarioId);

  return (
    <div className="flex flex-col gap-3">
      <Panel
        title="Scenario"
        right={<span className={`text-[10px] ${connected ? "text-emerald-400" : "text-rose-400"}`}>{connected ? "● live" : "● offline"}</span>}
      >
        <div className="flex flex-col gap-2">
          <Field label="Scenario">
            <select className={inputCls} value={scenarioId} onChange={(e) => setScenarioId(e.target.value)}>
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.n_robots}R)
                </option>
              ))}
            </select>
          </Field>
          {selected && <p className="text-[11px] leading-snug text-slate-400">{selected.description}</p>}
          <Field label="Repair strategy">
            <select className={inputCls} value={strategy} onChange={(e) => setStrategy(e.target.value as Strategy)}>
              <option value="local">B · local negotiated repair (proposed)</option>
              <option value="single_agent">A · single-agent repair</option>
              <option value="global">C · global replanning (baseline)</option>
            </select>
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="λ (load)">
              <input type="number" step="0.5" className={inputCls} value={lambda} onChange={(e) => setLambda(Number(e.target.value))} />
            </Field>
            <Field label="μ (repair impact)">
              <input type="number" step="0.5" className={inputCls} value={mu} onChange={(e) => setMu(Number(e.target.value))} />
            </Field>
          </div>
          <Btn variant="primary" disabled={busy || !connected} onClick={() => init({ scenario_id: scenarioId, strategy, seed })}>
            Load scenario
          </Btn>
        </div>
      </Panel>

      <Panel title="Random generator">
        <div className="grid grid-cols-2 gap-2">
          <Field label="Robots">
            <input type="number" min={1} max={60} className={inputCls} value={nAgents} onChange={(e) => setNAgents(Number(e.target.value))} />
          </Field>
          <Field label="Seed">
            <input type="number" className={inputCls} value={seed} onChange={(e) => setSeed(Number(e.target.value))} />
          </Field>
        </div>
        <div className="mt-2 flex gap-2">
          <Btn disabled={busy || !connected} onClick={() => init({ random: { n_agents: nAgents, seed }, strategy, seed })}>
            Generate & load
          </Btn>
          <Btn disabled={busy} onClick={() => setSeed(Math.floor(Math.random() * 100000))} title="pick a new random seed">
            🎲 seed
          </Btn>
        </div>
      </Panel>

      <Panel title="Run">
        <div className="flex flex-wrap gap-2">
          {running ? (
            <Btn onClick={() => send("pause")}>⏸ Pause</Btn>
          ) : (
            <Btn variant="primary" disabled={!state || finished} onClick={() => send("start")}>
              ▶ Start
            </Btn>
          )}
          <Btn disabled={!state || running || finished} onClick={() => send("step")}>
            ⏭ Step
          </Btn>
          <Btn disabled={!state} onClick={() => send("reset")}>
            ↺ Reset
          </Btn>
        </div>
        <div className="mt-3">
          <Field label={`Speed · ${speed.toFixed(1)} steps/s`}>
            <input
              type="range"
              min={0.5}
              max={20}
              step={0.5}
              value={speed}
              onChange={(e) => send("speed", Number(e.target.value))}
              className="accent-teal-300"
            />
          </Field>
        </div>
        {state && (
          <p className="mt-2 text-[11px] text-slate-400">
            status: <b className="text-slate-200">{state.status}</b>
            {state.failure_reason ? ` · ${state.failure_reason}` : ""}
          </p>
        )}
      </Panel>
    </div>
  );
}
