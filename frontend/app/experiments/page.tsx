"use client";

import { useEffect, useRef, useState } from "react";
import ExperimentCharts, { STRATEGY_META } from "@/components/ExperimentCharts";
import { Btn, Field, Panel, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import type { ExperimentJob, ExperimentRequest, Strategy } from "@/lib/types";

const parseList = (s: string): number[] =>
  s.split(/[ ,;]+/).map((x) => x.trim()).filter(Boolean).map(Number).filter((x) => Number.isFinite(x));

export default function ExperimentsPage() {
  const [agents, setAgents] = useState("5, 20, 40");
  const [densities, setDensities] = useState("0, 0.10, 0.20");
  const [type, setType] = useState<ExperimentRequest["disruption_type"]>("cell_blockage");
  const [reps, setReps] = useState(5);
  const [seed, setSeed] = useState(0);
  const [seedList, setSeedList] = useState("");
  const [strategies, setStrategies] = useState<Strategy[]>(["single_agent", "local"]);
  const [job, setJob] = useState<ExperimentJob | null>(null);
  const [error, setError] = useState("");
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  const nAgents = parseList(agents);
  const rhos = parseList(densities);
  const seeds = parseList(seedList);
  const totalRuns = nAgents.length * rhos.length * (seeds.length || reps) * strategies.length;

  const run = async () => {
    setError("");
    setJob(null);
    try {
      const body: ExperimentRequest & { seeds?: number[] } = {
        agent_counts: nAgents, densities: rhos, disruption_type: type, repetitions: reps, seed, strategies,
        ...(seeds.length ? { seeds } : {}),
      };
      const j = await api.runExperiment(body);
      setJob(j);
      if (timer.current) clearInterval(timer.current);
      timer.current = setInterval(async () => {
        try {
          const cur = await api.experiment(j.experiment_id);
          setJob(cur);
          if (cur.status === "done" || cur.status === "failed") {
            if (timer.current) clearInterval(timer.current);
          }
        } catch (e) {
          setError((e as Error).message);
        }
      }, 1000);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const toggle = (s: Strategy) => setStrategies((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));
  const running = job?.status === "queued" || job?.status === "running";
  const res = job?.result;

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
      <aside className="flex flex-col gap-3">
        <Panel title="Experiment configuration">
          <div className="flex flex-col gap-2">
            <Field label="Agent counts N (editable list)">
              <input className={inputCls} value={agents} onChange={(e) => setAgents(e.target.value)} />
            </Field>
            <Field label="Dynamic-obstacle densities ρ = blocked cells / traversable cells">
              <input className={inputCls} value={densities} onChange={(e) => setDensities(e.target.value)} />
            </Field>
            <Field label="Disruption type">
              <select className={inputCls} value={type} onChange={(e) => setType(e.target.value as ExperimentRequest["disruption_type"])}>
                <option value="cell_blockage">Cell blockage</option>
                <option value="robot_breakdown">Robot breakdown (+ρ background blockages)</option>
                <option value="emergency_task">Emergency task (+ρ background blockages)</option>
                <option value="mixed">Mixed</option>
              </select>
            </Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label="Repetitions per config">
                <input type="number" min={1} className={inputCls} value={reps} onChange={(e) => setReps(Number(e.target.value))} />
              </Field>
              <Field label="First seed">
                <input type="number" className={inputCls} value={seed} onChange={(e) => setSeed(Number(e.target.value))} />
              </Field>
            </div>
            <Field label="Explicit seed sequence (optional, overrides the two above)">
              <input className={inputCls} placeholder="e.g. 3, 7, 11" value={seedList} onChange={(e) => setSeedList(e.target.value)} />
            </Field>
            <div className="text-[11px] text-slate-400">
              Strategies:
              <div className="mt-1 flex flex-col gap-1">
                {(Object.keys(STRATEGY_META) as Strategy[]).map((s) => (
                  <label key={s} className="flex items-center gap-2 text-slate-200">
                    <input type="checkbox" checked={strategies.includes(s)} onChange={() => toggle(s)} />
                    {STRATEGY_META[s].label}
                  </label>
                ))}
              </div>
            </div>
            <p className="text-[11px] text-slate-500">{totalRuns} simulation runs (all strategies share identical seeded scenarios and disruptions).</p>
            <Btn variant="primary" disabled={running || !nAgents.length || !rhos.length || !strategies.length} onClick={run}>
              {running ? "Running…" : "Run experiment"}
            </Btn>
            {error && <p className="text-xs text-rose-300">{error}</p>}
          </div>
        </Panel>

        {job && (
          <Panel title="Status">
            <div className="text-xs text-slate-300">
              <div className="mb-1 flex justify-between"><span>{job.status}</span><span className="font-mono">{job.done}/{job.total}</span></div>
              <div className="h-2 overflow-hidden rounded bg-ink-700">
                <div className="h-full bg-accent-dim transition-all" style={{ width: `${job.total ? (100 * job.done) / job.total : 0}%` }} />
              </div>
              {job.error && <p className="mt-2 text-rose-300">{job.error}</p>}
              {res && (
                <>
                  <p className="mt-2 text-slate-400">finished in {res.runtime_s.toFixed(1)} s</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <a className="rounded-md bg-ink-700 px-2.5 py-1.5 text-xs hover:bg-ink-600" href={api.exportUrl(job.experiment_id, "csv", "summary")}>⬇ summary CSV</a>
                    <a className="rounded-md bg-ink-700 px-2.5 py-1.5 text-xs hover:bg-ink-600" href={api.exportUrl(job.experiment_id, "csv", "runs")}>⬇ runs CSV</a>
                    <a className="rounded-md bg-ink-700 px-2.5 py-1.5 text-xs hover:bg-ink-600" href={api.exportUrl(job.experiment_id, "json")}>⬇ JSON</a>
                  </div>
                </>
              )}
            </div>
          </Panel>
        )}

        {res && Object.keys(res.paired_local_vs_single_agent).length > 1 && (
          <Panel title="Paired comparison: B (local) vs A (single-agent)">
            <table className="w-full text-[11px]">
              <tbody className="font-mono">
                {Object.entries(res.paired_local_vs_single_agent).map(([k, v]) => (
                  <tr key={k} className="border-t border-ink-700"><td className="py-1 text-slate-400">{k}</td><td className="text-right">{typeof v === "number" ? v.toFixed(2) : String(v)}</td></tr>
                ))}
              </tbody>
            </table>
            <p className="mt-1 text-[10px] text-slate-500">Only runs where both strategies succeeded on the same seed.</p>
          </Panel>
        )}
      </aside>

      <section className="min-w-0">
        {res ? (
          <ExperimentCharts summary={res.summary} />
        ) : (
          <div className="flex h-96 items-center justify-center rounded-xl border border-dashed border-ink-600 text-slate-400">
            {running ? "Running experiments…" : "Configure and run an experiment to see the charts."}
          </div>
        )}
      </section>
    </div>
  );
}
