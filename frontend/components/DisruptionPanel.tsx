"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { SimState, XY } from "@/lib/types";
import type { InteractionMode } from "./GridView";
import { Btn, Field, Panel, inputCls } from "./ui";

type Props = {
  state: SimState | null;
  mode: InteractionMode;
  setMode: (m: InteractionMode) => void;
  selectedRobot: string | null;
  setSelectedRobot: (id: string | null) => void;
  pendingPickup: XY | null;
  setPendingPickup: (p: XY | null) => void;
  activation: string;
  setActivation: (s: string) => void;
  duration: string;
  setDuration: (s: string) => void;
  message: string;
  disabled: boolean;
  onBreak: () => void;
};

export default function DisruptionPanel(p: Props) {
  const { state } = p;
  const [busyId, setBusyId] = useState<string | null>(null);
  const robots = state?.robots.filter((r) => r.on_grid && r.status !== "broken" && r.status !== "done") ?? [];
  const obstacles = state?.obstacles.filter((o) => !o.owner && (o.end === null || o.end >= state.time)) ?? [];
  const modeBtn = (m: InteractionMode, label: string, title: string) => (
    <Btn active={p.mode === m} disabled={p.disabled} title={title} onClick={() => { p.setPendingPickup(null); p.setMode(p.mode === m ? "none" : m); }}>
      {label}
    </Btn>
  );

  return (
    <Panel title="Disruptions">
      <div className="grid grid-cols-2 gap-2">
        <Field label="At timestep (blank = now)">
          <input className={inputCls} inputMode="numeric" placeholder="now" value={p.activation} onChange={(e) => p.setActivation(e.target.value.replace(/\D/g, ""))} />
        </Field>
        <Field label="Blockage duration (blank = ∞)">
          <input className={inputCls} inputMode="numeric" placeholder="permanent" value={p.duration} onChange={(e) => p.setDuration(e.target.value.replace(/\D/g, ""))} />
        </Field>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {modeBtn("block", "▦ Block cell", "then click a cell on the grid")}
        {modeBtn("unblock", "✕ Remove obstacle", "then click an obstacle")}
        {modeBtn("emergency-pickup", "🚨 Emergency task", "click a pickup cell, then a delivery cell")}
      </div>
      {p.mode !== "none" && (
        <p className="mt-2 rounded bg-ink-900 px-2 py-1 text-[11px] text-accent">
          {p.mode === "block" && "Click a grid cell to block it."}
          {p.mode === "unblock" && "Click a dynamic obstacle to remove it."}
          {p.mode === "emergency-pickup" && "Click the PICKUP cell."}
          {p.mode === "emergency-delivery" && `Pickup ${p.pendingPickup ? `(${p.pendingPickup[0]},${p.pendingPickup[1]})` : ""} set. Click the DELIVERY cell.`}
        </p>
      )}
      <div className="mt-3 flex items-end gap-2">
        <Field label="Robot breakdown">
          <select className={inputCls} value={p.selectedRobot ?? ""} onChange={(e) => p.setSelectedRobot(e.target.value || null)}>
            <option value="">select robot…</option>
            {robots.map((r) => (
              <option key={r.id} value={r.id}>{r.id}</option>
            ))}
          </select>
        </Field>
        <Btn variant="danger" disabled={p.disabled || !p.selectedRobot} onClick={p.onBreak}>
          Break
        </Btn>
      </div>
      {p.message && <p className="mt-2 text-[11px] text-amber-300">{p.message}</p>}

      {obstacles.length > 0 && (
        <div className="mt-3">
          <h4 className="mb-1 text-[11px] uppercase text-slate-400">Active dynamic obstacles</h4>
          <ul className="max-h-24 space-y-1 overflow-auto text-[11px]">
            {obstacles.map((o) => (
              <li key={o.id} className="flex items-center justify-between rounded bg-ink-900 px-2 py-1">
                <span className="font-mono">({o.position[0]},{o.position[1]}) t{o.start}–{o.end ?? "∞"}</span>
                <button
                  className="text-rose-300 hover:text-rose-200 disabled:opacity-40"
                  disabled={busyId === o.id}
                  onClick={async () => {
                    setBusyId(o.id);
                    try { await api.removeObstacle(o.id); } catch { /* shown through state */ }
                    setBusyId(null);
                  }}
                >
                  remove
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {state && state.scheduled.length > 0 && (
        <div className="mt-3">
          <h4 className="mb-1 text-[11px] uppercase text-slate-400">Scheduled</h4>
          <ul className="max-h-24 space-y-1 overflow-auto text-[11px]">
            {state.scheduled.map((d) => (
              <li key={d.id} className="flex items-center justify-between rounded bg-ink-900 px-2 py-1">
                <span className="font-mono">t={d.time} · {d.type}{d.position ? ` (${d.position[0]},${d.position[1]})` : ""}{d.robot_id ? ` ${d.robot_id}` : ""}</span>
                <button className="text-rose-300 hover:text-rose-200" onClick={() => api.cancelScheduled(d.id)}>cancel</button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}
