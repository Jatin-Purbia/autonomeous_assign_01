"use client";

import { useEffect, useRef, useState } from "react";
import type { SimEvent } from "@/lib/types";

const TONE: Record<string, string> = {
  DISRUPTION_ACTIVATED: "#f43f5e",
  PLAN_INVALIDATED: "#f97316",
  REPAIR_STARTED: "#fb923c",
  REPAIR_REQUEST: "#38bdf8",
  BID_SUBMITTED: "#818cf8",
  BID_ACCEPTED: "#34d399",
  BID_REJECTED: "#94a3b8",
  PRIORITY_UPDATE: "#c084fc",
  AFFECTED_SET_EXPANDED: "#facc15",
  PLAN_SUFFIX_REPAIRED: "#5eead4",
  TASK_REASSIGNED: "#f0abfc",
  REPAIR_COMMITTED: "#4ade80",
  REPAIR_FAILED: "#ef4444",
  SIMULATION_FAILED: "#ef4444",
  SIMULATION_COMPLETED: "#4ade80",
  PICKUP_COMPLETED: "#fde047",
  DELIVERY_COMPLETED: "#a3e635",
  INITIAL_PLAN_CREATED: "#94a3b8",
  ROBOT_FINISHED: "#94a3b8",
};

function summary(e: SimEvent): string {
  const d = e.details as Record<string, unknown>;
  switch (e.event_type) {
    case "BID_SUBMITTED":
      return `${d.sender}→${d.receiver} cost=${d.cost ?? "∞"} (ΔC=${d.delta_c ?? "∞"}, P=${d.P}, M=${d.M})`;
    case "REPAIR_REQUEST":
    case "BID_ACCEPTED":
    case "BID_REJECTED":
    case "PRIORITY_UPDATE":
      return `${d.sender}→${d.receiver}${d.yield_method ? ` yields by ${d.yield_method}` : ""}${d.note ? ` · ${d.note}` : ""}`;
    case "AFFECTED_SET_EXPANDED":
      return `+${d.added} (via ${d.via}, |A|=${d.size})`;
    case "PLAN_SUFFIX_REPAIRED":
      return `${e.robot_ids[0]} ${d.method}: ${e.reason}`;
    case "TASK_REASSIGNED":
      return `${d.task_id}: ${d.from ?? "pool"}→${d.to} (cost ${d.cost})`;
    case "REPAIR_COMMITTED":
      return `impact=${d.impact}, msgs=${d.messages}, ${d.runtime_ms}ms`;
    case "REPAIR_FAILED":
      return String(d.reason ?? "");
    case "DISRUPTION_ACTIVATED":
      return `${e.reason} ${JSON.stringify({ pos: d.position, robot: d.robot_id, dur: d.duration })}`;
    case "PLAN_INVALIDATED":
      return Object.entries(d).map(([k, v]) => `${k}: ${v}`).join(" | ");
    case "INITIAL_PLAN_CREATED":
      return `retries=${d.retries}, ${d.runtime_ms}ms`;
    default:
      return e.robot_ids.join(",") + (d.task_id ? ` ${d.task_id}` : "");
  }
}

export default function EventLog({ events }: { events: SimEvent[] }) {
  const [onlyRepair, setOnlyRepair] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const shown = onlyRepair
    ? events.filter((e) => !["PICKUP_COMPLETED", "DELIVERY_COMPLETED", "ROBOT_FINISHED"].includes(e.event_type))
    : events;
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [shown.length]);
  return (
    <div>
      <label className="mb-1 flex items-center gap-1 text-[11px] text-slate-400">
        <input type="checkbox" checked={onlyRepair} onChange={(e) => setOnlyRepair(e.target.checked)} /> hide task progress
      </label>
      <div ref={ref} className="h-80 overflow-auto rounded-lg bg-ink-950 p-2 font-mono text-[11px] leading-relaxed">
        {shown.length === 0 && <p className="text-slate-500">No events yet.</p>}
        {shown.map((e) => (
          <div key={e.index} className="flex gap-2 border-b border-ink-800 py-0.5">
            <span className="w-8 shrink-0 text-right text-slate-500">t{e.time}</span>
            <span className="w-40 shrink-0 font-semibold" style={{ color: TONE[e.event_type] ?? "#cbd5e1" }}>{e.event_type}</span>
            <span className="break-all text-slate-300">{summary(e)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
