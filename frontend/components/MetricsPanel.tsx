"use client";

import type { Metrics } from "@/lib/types";
import { fmt } from "@/lib/viz";
import { Panel } from "./ui";

function Stat({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "warn" | "bad" | "good" }) {
  const color = tone === "bad" ? "text-rose-300" : tone === "warn" ? "text-amber-300" : tone === "good" ? "text-emerald-300" : "text-slate-50";
  return (
    <div className="rounded-lg bg-ink-900 px-2.5 py-2">
      <div className="text-[10px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className={`font-mono text-lg font-semibold leading-tight ${color}`}>{value}</div>
      {sub && <div className="text-[10px] text-slate-500">{sub}</div>}
    </div>
  );
}

export default function MetricsPanel({ m }: { m: Metrics | null }) {
  if (!m) return null;
  return (
    <Panel title="Live metrics">
      <div className="grid grid-cols-3 gap-2 md:grid-cols-4 xl:grid-cols-6">
        <Stat label="Flowtime" value={fmt(m.flowtime)} sub={`planned ${m.original_flowtime}`} />
        <Stat label="Makespan" value={fmt(m.makespan)} sub={`planned ${m.original_makespan}`} />
        <Stat label="Δ Flowtime" value={`${m.delta_flowtime >= 0 ? "+" : ""}${m.delta_flowtime}`} tone={m.delta_flowtime > 0 ? "warn" : "good"} sub="vs original plans" />
        <Stat label="Path length" value={fmt(m.total_path_length)} sub={`${m.additional_path_length >= 0 ? "+" : ""}${m.additional_path_length} vs plan`} />
        <Stat label="Modified robots" value={`${m.num_modified}/${m.n_agents}`} sub={`ratio ${(m.modified_ratio * 100).toFixed(0)}%`} tone={m.num_modified ? "warn" : undefined} />
        <Stat label="Repair time" value={`${fmt(m.repair_time_ms)} ms`} />
        <Stat label="Messages" value={fmt(m.messages)} sub="negotiation" />
        <Stat label="Waits" value={fmt(m.total_waits)} />
        <Stat label="Conflicts avoided" value={fmt(m.conflicts_avoided)} sub="rejected candidates" />
        <Stat label="Remaining tasks" value={fmt(m.remaining_tasks)} />
        <Stat label="Collisions" value={fmt(m.collisions)} tone={m.collisions ? "bad" : "good"} />
        <Stat label="Disruptions" value={fmt(m.n_disruptions)} sub={m.n_repairs_failed ? `${m.n_repairs_failed} failed` : "all repaired"} tone={m.n_repairs_failed ? "bad" : undefined} />
      </div>
      {m.per_disruption.length > 0 && (
        <table className="mt-3 w-full text-left text-[11px]">
          <thead className="text-slate-400">
            <tr>
              <th className="py-1">Disruption</th><th>t</th><th>Direct</th><th>Affected</th><th>Impact</th><th>Msgs</th><th>ms</th>
            </tr>
          </thead>
          <tbody className="font-mono text-slate-200">
            {m.per_disruption.map((d, i) => (
              <tr key={i} className="border-t border-ink-700">
                <td className="py-1">{d.disruption_id}{!d.success && " ✗"}</td>
                <td>{d.time}</td>
                <td>{d.direct_agents.join(",") || "–"}</td>
                <td>{d.affected_agents.join(",") || "–"}</td>
                <td>{d.impact}</td>
                <td>{d.messages}</td>
                <td>{fmt(d.runtime_ms)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
