"use client";

import type { SimState } from "@/lib/types";

type Props = {
  state: SimState;
  history: Record<number, SimState>;
  viewTime: number | null; // null = live
  setViewTime: (t: number | null) => void;
};

/** Scrubber over the recorded timesteps; markers show repairs (red) and scheduled disruptions (amber). */
export default function Timeline({ state, history, viewTime, setViewTime }: Props) {
  const times = Object.keys(history).map(Number).sort((a, b) => a - b);
  const max = Math.max(state.time, state.metrics.original_makespan + 10, 20);
  const shown = viewTime ?? state.time;
  const pct = (t: number) => `${((t - 0) / max) * 100}%`;

  return (
    <div className="rounded-xl border border-ink-600 bg-ink-800/70 p-3">
      <div className="mb-1 flex items-center justify-between text-[11px] text-slate-300">
        <span>
          Timeline · viewing <b className="font-mono">t={shown}</b> {viewTime === null ? "(live)" : "(history)"}
        </span>
        {viewTime !== null && (
          <button className="rounded bg-accent-dim px-2 py-0.5 text-[11px] font-medium text-ink-950" onClick={() => setViewTime(null)}>
            back to live
          </button>
        )}
      </div>
      <div className="relative h-8">
        <div className="absolute left-0 right-0 top-3 h-1.5 rounded bg-ink-700" />
        <div className="absolute left-0 top-3 h-1.5 rounded bg-accent-dim/60" style={{ width: pct(state.time) }} />
        {state.repairs.map((r, i) => (
          <div key={i} className={`absolute top-1 h-5 w-1 rounded ${r.success ? "bg-rose-400" : "bg-fuchsia-500"}`} style={{ left: pct(r.time) }} title={`t=${r.time}: ${r.disruption_id} → modified ${r.modified.join(", ") || "none"}`} />
        ))}
        {state.scheduled.map((d) => (
          <div key={d.id} className="absolute top-1 h-5 w-1 rounded bg-amber-300/80" style={{ left: pct(d.time) }} title={`scheduled t=${d.time}: ${d.type}`} />
        ))}
        <input
          type="range"
          min={0}
          max={max}
          value={shown}
          onChange={(e) => {
            const t = Number(e.target.value);
            if (t >= state.time) return setViewTime(null);
            // snap to the nearest recorded timestep
            const snap = times.reduce((best, x) => (Math.abs(x - t) < Math.abs(best - t) ? x : best), times[0] ?? 0);
            setViewTime(snap);
          }}
          className="absolute left-0 right-0 top-0 h-8 w-full cursor-pointer opacity-0"
        />
        <div className="pointer-events-none absolute top-1.5 h-4 w-1.5 rounded bg-white shadow" style={{ left: pct(shown) }} />
      </div>
      <div className="mt-1 flex gap-3 text-[10px] text-slate-400">
        <span><i className="mr-1 inline-block h-2 w-2 rounded-sm bg-rose-400" />repair committed</span>
        <span><i className="mr-1 inline-block h-2 w-2 rounded-sm bg-amber-300/80" />scheduled disruption</span>
      </div>
    </div>
  );
}
