"use client";

import { useMemo, useState } from "react";
import type { SimState, XY } from "@/lib/types";
import { CELL, COLORS, center, isRepaired, pointsAttr, repairedSegments, robotColor } from "@/lib/viz";
import RobotSprite from "./RobotSprite";

export type PathMode = "focus" | "affected" | "all" | "none";
export type InteractionMode = "none" | "block" | "unblock" | "emergency-pickup" | "emergency-delivery" | "break";

type Props = {
  state: SimState;
  stepSeconds: number;
  mode: InteractionMode;
  pathMode: PathMode;
  selectedRobot: string | null;
  pendingPickup: XY | null;
  highlightDirect: string[];
  highlightIndirect: string[];
  interactive: boolean;
  onCell: (x: number, y: number) => void;
  onRobot: (id: string) => void;
};

export default function GridView(p: Props) {
  const { state, stepSeconds } = p;
  const { width, height } = state.grid;
  const [hover, setHover] = useState<XY | null>(null);
  const shelves = useMemo(() => new Set(state.grid.static.map((s) => `${s[0]},${s[1]}`)), [state.grid.static]);
  const t = state.time;
  const direct = new Set(p.highlightDirect);
  const indirect = new Set(p.highlightIndirect);

  const shown = state.robots.filter((r) => {
    if (!r.on_grid && r.status !== "broken") return false;
    if (p.pathMode === "all") return true;
    if (p.pathMode === "none") return false;
    if (p.pathMode === "affected") return direct.has(r.id) || indirect.has(r.id) || r.id === p.selectedRobot;
    return r.id === p.selectedRobot;
  });

  const cursor =
    !p.interactive || p.mode === "none" ? "default" : p.mode === "break" ? "pointer" : "crosshair";

  return (
    <div className="relative w-full overflow-hidden rounded-xl border border-ink-600 bg-ink-950 shadow-lg">
      <svg
        viewBox={`0 0 ${width * CELL} ${height * CELL}`}
        className="block w-full select-none"
        style={{ cursor }}
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="6" height="6" fill="#3b0d1a" />
            <line x1="0" y1="0" x2="0" y2="6" stroke={COLORS.obstacle} strokeWidth="3" />
          </pattern>
        </defs>
        <rect width={width * CELL} height={height * CELL} fill={COLORS.floor} />
        {/* cells */}
        {Array.from({ length: height }).flatMap((_, y) =>
          Array.from({ length: width }).map((__, x) => {
            const shelf = shelves.has(`${x},${y}`);
            return (
              <rect
                key={`${x},${y}`}
                x={x * CELL}
                y={y * CELL}
                width={CELL}
                height={CELL}
                fill={shelf ? COLORS.shelf : "transparent"}
                stroke={COLORS.grid}
                strokeWidth={0.6}
                rx={shelf ? 3 : 0}
                onMouseEnter={() => setHover([x, y])}
                onClick={() => p.interactive && p.onCell(x, y)}
              />
            );
          }),
        )}
        {/* dynamic obstacles */}
        {state.obstacles
          .filter((o) => o.end === null || o.end >= t)
          .map((o) => (
            <g key={o.id} pointerEvents="none">
              <rect
                x={o.position[0] * CELL + 2}
                y={o.position[1] * CELL + 2}
                width={CELL - 4}
                height={CELL - 4}
                fill={o.owner ? "#1f2937" : "url(#hatch)"}
                stroke={o.owner ? "#94a3b8" : COLORS.obstacle}
                strokeWidth={1.5}
                opacity={o.start > t ? 0.5 : 1}
              />
              <title>{`${o.id} · from t=${o.start}${o.end !== null ? ` to t=${o.end}` : " (permanent)"}${o.owner ? ` · broken ${o.owner}` : ""}`}</title>
            </g>
          ))}
        {/* pickups / deliveries of remaining tasks */}
        {state.robots.flatMap((r) =>
          r.waypoints.map((w, i) => {
            const [cx, cy] = center(w.position);
            const c = robotColor(r.index);
            return (
              <g key={`${r.id}-${w.task_id}-${w.kind}-${i}`} pointerEvents="none" opacity={i === 0 ? 1 : 0.55}>
                {w.kind === "pickup" ? (
                  <path d={`M${cx},${cy - 9} L${cx + 9},${cy} L${cx},${cy + 9} L${cx - 9},${cy} Z`} fill={c} fillOpacity={0.25} stroke={c} strokeWidth={1.8} />
                ) : (
                  <rect x={cx - 8} y={cy - 8} width={16} height={16} fill="none" stroke={c} strokeWidth={2} strokeDasharray="3 2" />
                )}
              </g>
            );
          }),
        )}
        {/* paths */}
        {shown.map((r) => {
          const c = robotColor(r.index);
          const orig = r.original_plan.slice(t);
          const segs = repairedSegments(r, t);
          const repaired = isRepaired(r);
          return (
            <g key={`path-${r.id}`} pointerEvents="none">
              {r.executed.length > 1 && (
                <polyline points={pointsAttr(r.executed)} fill="none" stroke={c} strokeOpacity={0.35} strokeWidth={3} strokeLinejoin="round" />
              )}
              {orig.length > 1 && (
                <polyline points={pointsAttr(orig)} fill="none" stroke={c} strokeOpacity={repaired ? 0.55 : 0.8} strokeWidth={1.3} strokeDasharray="4 4" />
              )}
              {segs.map((s, i) => (
                <g key={i}>
                  <polyline points={pointsAttr(s)} fill="none" stroke="#fff" strokeOpacity={0.35} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" />
                  <polyline points={pointsAttr(s)} fill="none" stroke={c} strokeWidth={3.5} strokeLinecap="round" strokeLinejoin="round" />
                </g>
              ))}
            </g>
          );
        })}
        {/* pending emergency pickup */}
        {p.pendingPickup && (
          <circle cx={center(p.pendingPickup)[0]} cy={center(p.pendingPickup)[1]} r={11} fill="none" stroke="#facc15" strokeWidth={2.5} pointerEvents="none" />
        )}
        {/* hover */}
        {hover && p.interactive && p.mode !== "none" && (
          <rect x={hover[0] * CELL} y={hover[1] * CELL} width={CELL} height={CELL} fill="#5eead4" fillOpacity={0.18} stroke="#5eead4" pointerEvents="none" />
        )}
        {/* robots */}
        {state.robots.map((r) => (
          <RobotSprite
            key={r.id}
            robot={r}
            duration={stepSeconds}
            role={direct.has(r.id) ? "direct" : indirect.has(r.id) ? "indirect" : "none"}
            selected={r.id === p.selectedRobot}
            onClick={() => p.onRobot(r.id)}
          />
        ))}
      </svg>
      <div className="pointer-events-none absolute left-2 top-2 rounded-md bg-ink-900/85 px-2 py-1 font-mono text-xs text-slate-200">
        t = {state.time}
        {hover ? `  ·  (${hover[0]},${hover[1]})` : ""}
      </div>
      <Legend />
    </div>
  );
}

function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-ink-700 bg-ink-900 px-3 py-1.5 text-[10px] text-slate-300">
      <span className="flex items-center gap-1"><svg width="22" height="6"><line x1="0" y1="3" x2="22" y2="3" stroke="#cbd5e1" strokeDasharray="4 3" /></svg>original</span>
      <span className="flex items-center gap-1"><svg width="22" height="6"><line x1="0" y1="3" x2="22" y2="3" stroke="#cbd5e1" strokeWidth="3.5" /></svg>repaired</span>
      <span className="flex items-center gap-1"><svg width="22" height="6"><line x1="0" y1="3" x2="22" y2="3" stroke="#cbd5e1" strokeOpacity="0.4" strokeWidth="3" /></svg>executed</span>
      <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rotate-45 border border-slate-300" />pickup</span>
      <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 border border-dashed border-slate-300" />delivery</span>
      <span className="flex items-center gap-1"><span className="inline-block h-2.5 w-2.5 rounded-full border-2" style={{ borderColor: COLORS.direct }} />direct</span>
      <span className="flex items-center gap-1"><span className="inline-block h-2.5 w-2.5 rounded-full border-2" style={{ borderColor: COLORS.indirect }} />indirect</span>
    </div>
  );
}
