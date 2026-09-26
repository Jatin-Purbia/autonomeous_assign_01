"use client";

import { useState } from "react";
import type { ConflictGraphData } from "@/lib/types";
import { COLORS } from "@/lib/viz";

const EDGE_STYLE: Record<string, { color: string; dash?: string; label: string }> = {
  vertex: { color: "#f43f5e", label: "vertex conflict" },
  edge_swap: { color: "#d946ef", label: "edge-swap conflict" },
  dependency: { color: "#38bdf8", label: "task dependency" },
  shared_resource: { color: "#64748b", dash: "3 3", label: "shared resource" },
};

/** Temporary conflict graph C=(A,E_C): one node per robot, circular layout. */
export default function ConflictGraph({ graphs }: { graphs: ConflictGraphData[] }) {
  const [idx, setIdx] = useState<number | null>(null);
  if (!graphs.length) return <p className="text-xs text-slate-400">No repair has happened yet.</p>;
  const informative = graphs.findIndex((x) => x.edges.some((e) => e.kind !== "shared_resource"));
  const i = Math.min(idx ?? (informative >= 0 ? informative : graphs.length - 1), graphs.length - 1);
  const g = graphs[i];
  // show only robots that participate in an edge or in the affected set to keep it readable
  const active = new Set<string>([...g.affected, ...g.direct]);
  g.edges.forEach((e) => { active.add(e.a); active.add(e.b); });
  const nodes = g.nodes.filter((n) => active.has(n));
  const R = 105, cx = 130, cy = 130;
  const pos = new Map(nodes.map((n, k) => {
    const ang = (2 * Math.PI * k) / Math.max(nodes.length, 1) - Math.PI / 2;
    return [n, [cx + R * Math.cos(ang), cy + R * Math.sin(ang)] as const];
  }));
  const strong = g.edges.filter((e) => e.kind !== "shared_resource");
  const component = new Set<string>(g.direct);
  for (let pass = 0; pass < nodes.length; pass++) strong.forEach((e) => { if (component.has(e.a) || component.has(e.b)) { component.add(e.a); component.add(e.b); } });

  return (
    <div>
      <div className="mb-2 flex items-center gap-2 text-[11px]">
        <select className="w-full rounded border border-ink-600 bg-ink-900 px-1 py-1 text-slate-200" value={i} onChange={(e) => setIdx(Number(e.target.value))}>
          {graphs.map((x, k) => (<option key={k} value={k}>{k + 1}. {x.label}</option>))}
        </select>
      </div>
      <svg viewBox="0 0 260 260" className="w-full rounded-lg bg-ink-950">
        {g.edges.map((e, k) => {
          const a = pos.get(e.a), b = pos.get(e.b);
          if (!a || !b) return null;
          const st = EDGE_STYLE[e.kind];
          return (
            <g key={k}>
              <line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke={st.color} strokeWidth={e.kind === "shared_resource" ? 1 : 2} strokeDasharray={st.dash} opacity={0.9} />
              <title>{`${e.a}–${e.b}: ${st.label}${e.time !== null ? ` at t=${e.time}` : ""}${e.position ? ` @(${e.position[0]},${e.position[1]})` : ""}${e.note ? ` (${e.note})` : ""}`}</title>
            </g>
          );
        })}
        {nodes.map((n) => {
          const [x, y] = pos.get(n)!;
          const role = g.direct.includes(n) ? COLORS.direct : g.affected.includes(n) ? COLORS.indirect : "#475569";
          return (
            <g key={n}>
              <circle cx={x} cy={y} r={14} fill={role} stroke={component.has(n) ? "#f8fafc" : "#0b1020"} strokeWidth={component.has(n) ? 2 : 1} />
              <text x={x} y={y} textAnchor="middle" dy="0.35em" fontSize={10} fontWeight={700} fill="#0b1020">{n}</text>
            </g>
          );
        })}
      </svg>
      <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-slate-400">
        {Object.entries(EDGE_STYLE).map(([k, v]) => (
          <li key={k} className="flex items-center gap-1"><span className="inline-block h-0.5 w-4" style={{ background: v.color }} />{v.label}</li>
        ))}
        <li><span className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: COLORS.direct }} />direct</li>
        <li><span className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: COLORS.indirect }} />indirect</li>
        <li><span className="mr-1 inline-block h-2 w-2 rounded-full border-2 border-white" />local component</li>
      </ul>
    </div>
  );
}
