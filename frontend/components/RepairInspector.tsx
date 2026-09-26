"use client";

import { useState } from "react";
import type { RepairSummary, SimState, XY } from "@/lib/types";
import { CELL, COLORS, pointsAttr, robotColor } from "@/lib/viz";
import { Chip } from "./ui";

const MSG_TONE: Record<string, string> = {
  REPAIR_REQUEST: "#38bdf8", BID: "#818cf8", ACCEPT: "#34d399", REJECT: "#94a3b8",
  PRIORITY_UPDATE: "#c084fc", REPAIR_COMMITTED: "#4ade80",
};

function Compare({ state, rid, oldS, newS }: { state: SimState; rid: string; oldS: XY[]; newS: XY[] }) {
  const { width, height, static: shelves } = state.grid;
  const c = robotColor(state.robots.find((r) => r.id === rid)?.index ?? 0);
  return (
    <svg viewBox={`0 0 ${width * CELL} ${height * CELL}`} className="w-full rounded-lg bg-ink-950">
      {shelves.map((s, i) => <rect key={i} x={s[0] * CELL} y={s[1] * CELL} width={CELL} height={CELL} fill={COLORS.shelf} />)}
      {oldS.length > 1 && <polyline points={pointsAttr(oldS)} fill="none" stroke="#94a3b8" strokeWidth={3} strokeDasharray="6 5" />}
      {newS.length > 1 && <polyline points={pointsAttr(newS)} fill="none" stroke={c} strokeWidth={4.5} strokeLinecap="round" strokeLinejoin="round" />}
    </svg>
  );
}

/** Explains the last repair: who was affected and why, negotiation messages, expansion, old vs new suffix. */
export default function RepairInspector({ state }: { state: SimState }) {
  const rep: RepairSummary | null = state.last_repair;
  const [sel, setSel] = useState<string | null>(null);
  if (!rep) return <p className="text-xs text-slate-400">No disruption yet. Inject one from the Disruptions panel, or load a built-in scenario and press Start.</p>;
  const modified = rep.modified;
  const pick = sel && rep.diffs[sel] ? sel : modified[0] ?? null;
  const ind = rep.affected.filter((a) => !rep.direct.includes(a));

  return (
    <div className="space-y-3 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <Chip color={rep.success ? "#4ade80" : "#ef4444"}>{rep.success ? "REPAIRED" : "FAILED"}</Chip>
        <span className="text-slate-400">strategy <b className="text-slate-200">{rep.strategy}</b> · {rep.runtime_ms.toFixed(1)} ms · {rep.messages.length} msgs · J={rep.objective.toFixed(0)}</span>
      </div>
      {rep.failure_reason && <p className="rounded bg-rose-950/60 p-2 text-rose-200">{rep.failure_reason}</p>}
      <div>
        <div className="mb-1 text-[11px] uppercase text-slate-400">Affected set A<sub>d</sub> (|A|={rep.affected.length}, modified {modified.length})</div>
        <div className="flex flex-wrap gap-1">
          {rep.direct.map((r) => <Chip key={r} color={COLORS.direct}>{r} direct</Chip>)}
          {ind.map((r) => <Chip key={r} color={COLORS.indirect}>{r} indirect</Chip>)}
          {rep.affected.length === 0 && <span className="text-slate-500">no plan was invalidated</span>}
        </div>
      </div>
      {rep.expansions.length > 0 && (
        <div>
          <div className="mb-1 text-[11px] uppercase text-slate-400">Affected-set expansion</div>
          <ol className="space-y-1">
            {rep.expansions.map((e, i) => (
              <li key={i} className="rounded bg-ink-900 px-2 py-1"><b>{e.robot}</b> joined via <i>{e.via}</i>{e.added_by ? ` (asked by ${e.added_by})` : ""} → |A|={e.size}<div className="text-slate-400">{e.reason}</div></li>
            ))}
          </ol>
        </div>
      )}
      {rep.reassignments.length > 0 && (
        <div>
          <div className="mb-1 text-[11px] uppercase text-slate-400">Task reassignment</div>
          {rep.reassignments.map((r, i) => (
            <div key={i} className="rounded bg-ink-900 px-2 py-1">{String(r.task_id)}: {String(r.from ?? "pool")} → <b>{String(r.to)}</b> · cost {String(r.cost)}</div>
          ))}
        </div>
      )}
      {rep.messages.length > 0 && (
        <div>
          <div className="mb-1 text-[11px] uppercase text-slate-400">Negotiation messages ({rep.messages.length})</div>
          <div className="max-h-40 overflow-auto rounded bg-ink-950 p-2 font-mono text-[11px]">
            {rep.messages.map((m, i) => (
              <div key={i}><span style={{ color: MSG_TONE[m.kind] ?? "#e2e8f0" }}>{m.kind}</span> {m.sender}→{m.receiver}{m.details.cost !== undefined ? ` cost=${String(m.details.cost ?? "∞")}` : ""}{m.details.yield_method ? ` (${String(m.details.yield_method)})` : ""}</div>
            ))}
          </div>
        </div>
      )}
      {modified.length > 0 && (
        <div>
          <div className="mb-1 text-[11px] uppercase text-slate-400">Why each agent was modified</div>
          <ul className="space-y-1">
            {modified.map((r) => (
              <li key={r}>
                <button onClick={() => setSel(r)} className={`w-full rounded px-2 py-1 text-left ${pick === r ? "bg-ink-600" : "bg-ink-900 hover:bg-ink-700"}`}>
                  <b>{r}</b> <span className="text-accent">{rep.methods[r]}</span> · ΔC {rep.delta_completion[r] ?? 0}
                  <div className="text-slate-400">{rep.reasons[r]}</div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {pick && rep.diffs[pick] && (
        <div>
          <div className="mb-1 text-[11px] uppercase text-slate-400">{pick}: old (dashed) vs new (solid) suffix from t={rep.diffs[pick].from_time}</div>
          <Compare state={state} rid={pick} oldS={rep.diffs[pick].old_suffix} newS={rep.diffs[pick].new_suffix} />
          <div className="mt-1 text-[11px] text-slate-400">old length {rep.diffs[pick].old_suffix.length - 1} → new length {rep.diffs[pick].new_suffix.length - 1}</div>
        </div>
      )}
    </div>
  );
}
