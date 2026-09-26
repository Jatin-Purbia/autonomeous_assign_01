"use client";

import { useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, ErrorBar, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { Strategy, SummaryRow } from "@/lib/types";
import { Panel, inputCls } from "./ui";

export const STRATEGY_META: Record<Strategy, { label: string; color: string }> = {
  single_agent: { label: "A · single-agent", color: "#f59e0b" },
  local: { label: "B · local negotiated", color: "#2dd4bf" },
  global: { label: "C · global replanning", color: "#a78bfa" },
};

const AXIS = { stroke: "#94a3b8", fontSize: 11 };
const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);

type Series = Record<string, number | null>;

/** rows for a chart: one record per x value, with `<strategy>` (mean) and `<strategy>_err` (std). */
function shape(rows: SummaryRow[], xKey: "n_agents" | "density", metric: string, fixed: { key: "n_agents" | "density"; value: number }, strategies: Strategy[]) {
  const xs = Array.from(new Set(rows.map((r) => r[xKey] as number))).sort((a, b) => a - b);
  return xs.map((x) => {
    const rec: Series = { x };
    for (const s of strategies) {
      const r = rows.find((q) => q.strategy === s && q[xKey] === x && q[fixed.key] === fixed.value);
      rec[s] = r ? num(r[`${metric}_mean`]) : null;
      rec[`${s}_err`] = r ? num(r[`${metric}_std`]) : null;
    }
    return rec;
  });
}

function LineCard({ title, data, xLabel, yLabel, strategies }: { title: string; data: Series[]; xLabel: string; yLabel: string; strategies: Strategy[] }) {
  return (
    <Panel title={title}>
      <div className="h-64">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 16 }}>
            <CartesianGrid stroke="#1e293b" />
            <XAxis dataKey="x" {...AXIS} label={{ value: xLabel, position: "insideBottom", offset: -8, fill: "#94a3b8", fontSize: 11 }} />
            <YAxis {...AXIS} label={{ value: yLabel, angle: -90, position: "insideLeft", fill: "#94a3b8", fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#111831", border: "1px solid #33406f", fontSize: 12 }} formatter={(v: unknown) => (typeof v === "number" ? v.toFixed(2) : String(v))} />
            <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 11 }} />
            {strategies.map((s) => (
              <Line key={s} type="monotone" dataKey={s} name={STRATEGY_META[s].label} stroke={STRATEGY_META[s].color} strokeWidth={2} dot={{ r: 3 }} connectNulls isAnimationActive={false}>
                <ErrorBar dataKey={`${s}_err`} width={4} strokeWidth={1.2} stroke={STRATEGY_META[s].color} />
              </Line>
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}

const METRIC_OPTIONS: [string, string][] = [
  ["flowtime", "Flowtime"], ["makespan", "Makespan"], ["num_modified", "Modified agents"],
  ["repair_time_ms", "Repair time (ms)"], ["messages", "Messages"], ["delta_flowtime", "Δ Flowtime"],
];

export default function ExperimentCharts({ summary }: { summary: SummaryRow[] }) {
  const strategies = useMemo(() => (Object.keys(STRATEGY_META) as Strategy[]).filter((s) => summary.some((r) => r.strategy === s)), [summary]);
  const ns = useMemo(() => Array.from(new Set(summary.map((r) => r.n_agents))).sort((a, b) => a - b), [summary]);
  const rhos = useMemo(() => Array.from(new Set(summary.map((r) => r.density))).sort((a, b) => a - b), [summary]);
  const [rho, setRho] = useState<number | null>(null);
  const [n, setN] = useState<number | null>(null);
  const [cmpMetric, setCmpMetric] = useState("flowtime");
  const [heatStrategy, setHeatStrategy] = useState<Strategy | null>(null);
  const fixedRho = rho ?? rhos[Math.floor(rhos.length / 2)] ?? 0;
  const fixedN = n ?? ns[Math.floor(ns.length / 2)] ?? 0;
  const hs = heatStrategy ?? strategies[0];

  const byN = (metric: string) => shape(summary, "n_agents", metric, { key: "density", value: fixedRho }, strategies);
  const byRho = (metric: string) => shape(summary, "density", metric, { key: "n_agents", value: fixedN }, strategies);
  const cmp = shape(summary, "n_agents", cmpMetric, { key: "density", value: fixedRho }, strategies);

  return (
    <div className="space-y-4">
      <Panel title="Chart parameters">
        <div className="flex flex-wrap gap-4 text-xs">
          <label className="flex items-center gap-2">Fixed obstacle density ρ (agent-count charts)
            <select className={`${inputCls} w-24`} value={fixedRho} onChange={(e) => setRho(Number(e.target.value))}>
              {rhos.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2">Fixed agent count N (density charts)
            <select className={`${inputCls} w-24`} value={fixedN} onChange={(e) => setN(Number(e.target.value))}>
              {ns.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </label>
        </div>
        <p className="mt-2 text-[11px] text-slate-500">Points are means over successful runs; error bars are ±1 sample standard deviation.</p>
      </Panel>
      <div className="grid gap-4 xl:grid-cols-3 md:grid-cols-2">
        <LineCard title={`1 · Agent count vs mean flowtime (ρ=${fixedRho})`} data={byN("flowtime")} xLabel="agents N" yLabel="flowtime" strategies={strategies} />
        <LineCard title={`2 · Agent count vs mean makespan (ρ=${fixedRho})`} data={byN("makespan")} xLabel="agents N" yLabel="makespan" strategies={strategies} />
        <LineCard title={`3 · Agent count vs modified agents (ρ=${fixedRho})`} data={byN("num_modified")} xLabel="agents N" yLabel="modified agents" strategies={strategies} />
        <LineCard title={`4 · Obstacle density vs flowtime (N=${fixedN})`} data={byRho("flowtime")} xLabel="density ρ" yLabel="flowtime" strategies={strategies} />
        <LineCard title={`5 · Obstacle density vs repair time (N=${fixedN})`} data={byRho("repair_time_ms")} xLabel="density ρ" yLabel="repair time (ms)" strategies={strategies} />
        <LineCard title={`6 · Obstacle density vs modified-agent ratio (N=${fixedN})`} data={byRho("modified_ratio")} xLabel="density ρ" yLabel="modified ratio" strategies={strategies} />
      </div>

      <Panel
        title={`7 · Repair strategy comparison (ρ=${fixedRho})`}
        right={
          <select className={`${inputCls} w-44`} value={cmpMetric} onChange={(e) => setCmpMetric(e.target.value)}>
            {METRIC_OPTIONS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        }
      >
        <div className="h-72">
          <ResponsiveContainer>
            <BarChart data={cmp} margin={{ top: 8, right: 12, left: 0, bottom: 16 }}>
              <CartesianGrid stroke="#1e293b" />
              <XAxis dataKey="x" {...AXIS} label={{ value: "agents N", position: "insideBottom", offset: -8, fill: "#94a3b8", fontSize: 11 }} />
              <YAxis {...AXIS} />
              <Tooltip contentStyle={{ background: "#111831", border: "1px solid #33406f", fontSize: 12 }} formatter={(v: unknown) => (typeof v === "number" ? v.toFixed(2) : String(v))} />
              <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 11 }} />
              {strategies.map((s) => (
                <Bar key={s} dataKey={s} name={STRATEGY_META[s].label} fill={STRATEGY_META[s].color} isAnimationActive={false}>
                  <ErrorBar dataKey={`${s}_err`} width={4} strokeWidth={1.2} stroke="#e2e8f0" />
                </Bar>
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <Panel
        title="8 · Success-rate heatmap (agent count × obstacle density)"
        right={
          <select className={`${inputCls} w-48`} value={hs} onChange={(e) => setHeatStrategy(e.target.value as Strategy)}>
            {strategies.map((s) => <option key={s} value={s}>{STRATEGY_META[s].label}</option>)}
          </select>
        }
      >
        <Heatmap summary={summary} ns={ns} rhos={rhos} strategy={hs} />
      </Panel>
    </div>
  );
}

function Heatmap({ summary, ns, rhos, strategy }: { summary: SummaryRow[]; ns: number[]; rhos: number[]; strategy: Strategy }) {
  // sequential single-hue scale: dark (0%) -> teal (100%)
  const color = (v: number) => `hsl(174 ${30 + 55 * v}% ${14 + 38 * v}%)`;
  return (
    <div className="overflow-auto">
      <table className="border-separate border-spacing-1 text-xs">
        <thead>
          <tr>
            <th className="px-2 text-slate-400">N \ ρ</th>
            {rhos.map((r) => <th key={r} className="px-2 font-mono text-slate-300">{r}</th>)}
          </tr>
        </thead>
        <tbody>
          {ns.map((n) => (
            <tr key={n}>
              <th className="px-2 text-right font-mono text-slate-300">{n}</th>
              {rhos.map((r) => {
                const row = summary.find((q) => q.strategy === strategy && q.n_agents === n && q.density === r);
                const v = row ? row.success_rate : null;
                return (
                  <td key={r} className="h-12 w-20 rounded text-center font-mono font-semibold" style={{ background: v === null ? "#1e293b" : color(v), color: v !== null && v > 0.55 ? "#04211d" : "#e2e8f0" }} title={row ? `${row.n_success}/${row.n} successful` : "no data"}>
                    {v === null ? "–" : `${Math.round(v * 100)}%`}
                    {row && <div className="text-[9px] font-normal opacity-70">{row.n_success}/{row.n}</div>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
