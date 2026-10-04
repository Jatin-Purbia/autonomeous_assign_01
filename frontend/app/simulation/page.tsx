"use client";

import { useCallback, useMemo, useState } from "react";
import ControlPanel from "@/components/ControlPanel";
import DisruptionPanel from "@/components/DisruptionPanel";
import EventLog from "@/components/EventLog";
import GridView, { type InteractionMode, type PathMode } from "@/components/GridView";
import MetricsPanel from "@/components/MetricsPanel";
import RepairInspector from "@/components/RepairInspector";
import Timeline from "@/components/Timeline";
import { Btn, Panel } from "@/components/ui";
import { api } from "@/lib/api";
import type { SimState, XY } from "@/lib/types";
import { useSimulationStream } from "@/lib/websocket";

const HIGHLIGHT_STEPS = 8;

export default function SimulationPage() {
  const stream = useSimulationStream();
  const [viewTime, setViewTime] = useState<number | null>(null);
  const [mode, setMode] = useState<InteractionMode>("none");
  const [pathMode, setPathMode] = useState<PathMode>("affected");
  const [selected, setSelected] = useState<string | null>(null);
  const [pendingPickup, setPendingPickup] = useState<XY | null>(null);
  const [activation, setActivation] = useState("");
  const [duration, setDuration] = useState("");
  const [message, setMessage] = useState("");
  const [tab, setTab] = useState<"repair" | "events">("repair");

  const live = stream.state;
  const view: SimState | null = useMemo(
    () => (viewTime !== null && stream.history[viewTime] ? stream.history[viewTime] : live),
    [viewTime, stream.history, live],
  );
  const historical = viewTime !== null && view !== live;
  const onError = useCallback((m: string) => setMessage(m), []);

  const lastRepairTime = view && view.repairs.length ? view.repairs[view.repairs.length - 1].time : null;
  const highlighting = !!view?.last_repair && lastRepairTime !== null && view.time - lastRepairTime <= HIGHLIGHT_STEPS;
  const direct = highlighting ? view!.last_repair!.direct : [];
  const indirect = highlighting ? view!.last_repair!.affected.filter((a) => !view!.last_repair!.direct.includes(a)) : [];

  const nowOrLater = () => (activation === "" ? null : Number(activation));
  const durationVal = () => (duration === "" ? null : Number(duration));
  const report = (r: { ok: boolean; scheduled: boolean; message: string }) => setMessage(r.message + (r.ok ? "" : " ⚠"));

  const onCell = async (x: number, y: number) => {
    if (!view) return;
    const isShelf = view.grid.static.some((s) => s[0] === x && s[1] === y);
    try {
      if (mode === "block") {
        if (isShelf) return setMessage("That cell is a static shelf.");
        report(await api.blockCell(x, y, durationVal(), nowOrLater()));
      } else if (mode === "unblock") {
        const o = view.obstacles.find((o) => !o.owner && o.position[0] === x && o.position[1] === y && (o.end === null || o.end >= view.time));
        if (!o) return setMessage("No removable obstacle on that cell.");
        await api.removeObstacle(o.id);
        setMessage(`Removed ${o.id}`);
      } else if (mode === "emergency-pickup") {
        if (isShelf) return setMessage("Pickup must be on a free cell.");
        setPendingPickup([x, y]);
        setMode("emergency-delivery");
      } else if (mode === "emergency-delivery" && pendingPickup) {
        if (isShelf) return setMessage("Delivery must be on a free cell.");
        report(await api.emergency(pendingPickup, [x, y], null, nowOrLater()));
        setPendingPickup(null);
        setMode("none");
      }
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  const onBreak = async () => {
    if (!selected) return;
    try {
      report(await api.breakRobot(selected, nowOrLater()));
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  const stepSeconds = stream.running ? Math.min(0.9 / stream.speed, 1) : 0.3;
  const canInteract = !!live && !historical && live.status !== "completed" && live.status !== "failed";

  return (
    <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)_360px]">
      <aside className="flex flex-col gap-3">
        <ControlPanel
          state={live}
          running={stream.running}
          connected={stream.connected}
          speed={stream.speed}
          send={stream.send}
          onError={onError}
          onInitialised={(s) => {
            setViewTime(null);
            setSelected(null);
            setMessage("");
            stream.push({ type: "state", running: false, speed: stream.speed, strategy: stream.strategy, state: s });
          }}
        />
        <DisruptionPanel
          state={live}
          mode={mode}
          setMode={setMode}
          selectedRobot={selected}
          setSelectedRobot={setSelected}
          pendingPickup={pendingPickup}
          setPendingPickup={setPendingPickup}
          activation={activation}
          setActivation={setActivation}
          duration={duration}
          setDuration={setDuration}
          message={message}
          disabled={!canInteract}
          onBreak={onBreak}
        />
      </aside>

      <section className="flex min-w-0 flex-col gap-3">
        {!view ? (
          <div className="flex h-96 items-center justify-center rounded-xl border border-dashed border-ink-600 text-slate-400">
            {stream.connected ? "Load a scenario to begin." : "Connecting to the backend at localhost:8000…"}
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-slate-400">{view.scenario.name}</span>
              <span className="ml-auto text-[11px] text-slate-400">paths:</span>
              {(["focus", "affected", "all", "none"] as PathMode[]).map((m) => (
                <Btn key={m} active={pathMode === m} onClick={() => setPathMode(m)}>{m}</Btn>
              ))}
            </div>
            <GridView
              state={view}
              stepSeconds={stepSeconds}
              mode={mode}
              pathMode={pathMode}
              selectedRobot={selected}
              pendingPickup={pendingPickup}
              highlightDirect={direct}
              highlightIndirect={indirect}
              interactive={canInteract}
              onCell={onCell}
              onRobot={(id) => setSelected(id)}
            />
            {view.status === "failed" && (
              <div className="rounded-lg border border-rose-500/50 bg-rose-950/50 p-2 text-sm text-rose-200">
                Simulation failed: {view.failure_reason}
              </div>
            )}
            {view.status === "completed" && (
              <div className="rounded-lg border border-emerald-500/40 bg-emerald-950/40 p-2 text-sm text-emerald-200">
                All tasks completed · flowtime {view.metrics.flowtime} · makespan {view.metrics.makespan}
              </div>
            )}
            {live && <Timeline state={live} history={stream.history} viewTime={viewTime} setViewTime={setViewTime} />}
            <MetricsPanel m={view.metrics} />
            <RobotTable view={view} selected={selected} setSelected={setSelected} />
          </>
        )}
      </section>

      <aside className="flex min-w-0 flex-col gap-3">
        <Panel
          title="Repair visualisation"
          right={
            <div className="flex gap-1">
              {(["repair", "events"] as const).map((t) => (
                <Btn key={t} active={tab === t} onClick={() => setTab(t)}>{t}</Btn>
              ))}
            </div>
          }
        >
          {view && tab === "repair" && <RepairInspector state={view} />}
          {tab === "events" && <EventLog events={stream.events} />}
          {!view && <p className="text-xs text-slate-400">Nothing loaded.</p>}
        </Panel>
        {stream.error && (
          <p className="rounded-lg bg-rose-950/60 p-2 text-xs text-rose-200" onClick={stream.clearError}>{stream.error}</p>
        )}
      </aside>
    </div>
  );
}

function RobotTable({ view, selected, setSelected }: { view: SimState; selected: string | null; setSelected: (id: string) => void }) {
  return (
    <Panel title="Robots">
      <div className="max-h-56 overflow-auto">
        <table className="w-full text-left text-[11px]">
          <thead className="sticky top-0 bg-ink-800 text-slate-400">
            <tr><th className="py-1">Robot</th><th>Status</th><th>Pos</th><th>Prio</th><th>Next waypoint</th><th>Tasks (done/total)</th><th>C<sub>i</sub></th></tr>
          </thead>
          <tbody className="font-mono text-slate-200">
            {view.robots.map((r) => {
              const w = r.waypoints[0];
              const done = r.tasks.filter((t) => t.status === "delivered").length;
              return (
                <tr key={r.id} onClick={() => setSelected(r.id)} className={`cursor-pointer border-t border-ink-700 hover:bg-ink-700/60 ${selected === r.id ? "bg-ink-700" : ""}`}>
                  <td className="py-1 font-semibold">{r.id}</td>
                  <td>{r.status}</td>
                  <td>{r.position ? `(${r.position[0]},${r.position[1]})` : "–"}</td>
                  <td>{r.priority}</td>
                  <td>{w ? `${w.kind} (${w.position[0]},${w.position[1]})` : "–"}</td>
                  <td>{done}/{r.tasks.filter((t) => t.status !== "reassigned").length}</td>
                  <td>{r.completion_time ?? r.broken_at ?? "–"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
