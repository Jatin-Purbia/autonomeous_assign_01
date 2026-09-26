import type { RobotState, XY } from "./types";

/** Distinct, colour-blind-friendly-ish hues via golden-angle spacing; alternating lightness. */
export function robotColor(index: number): string {
  const hue = (index * 137.508 + 20) % 360;
  const light = index % 2 === 0 ? 58 : 66;
  return `hsl(${hue.toFixed(0)} 72% ${light}%)`;
}

export const COLORS = {
  direct: "#ef4444",
  indirect: "#fb923c",
  obstacle: "#f43f5e",
  shelf: "#334155",
  floor: "#0f172a",
  grid: "#1e293b",
  broken: "#64748b",
};

export const CELL = 32;

export function center(p: XY): [number, number] {
  return [(p[0] + 0.5) * CELL, (p[1] + 0.5) * CELL];
}

export function pointsAttr(pts: XY[]): string {
  return pts.map((p) => center(p).join(",")).join(" ");
}

const same = (a: XY | undefined, b: XY | undefined) => !!a && !!b && a[0] === b[0] && a[1] === b[1];

/** Contiguous stretches (from `fromTime`) where the active plan deviates from the original plan. */
export function repairedSegments(r: RobotState, fromTime: number): XY[][] {
  const out: XY[][] = [];
  let cur: XY[] = [];
  for (let t = fromTime; t < r.active_plan.length; t++) {
    const differs = !same(r.original_plan[t], r.active_plan[t]);
    if (differs) {
      if (cur.length === 0 && t > 0) cur.push(r.active_plan[t - 1]);
      cur.push(r.active_plan[t]);
    } else if (cur.length) {
      cur.push(r.active_plan[t]);
      out.push(cur);
      cur = [];
    }
  }
  if (cur.length) out.push(cur);
  return out;
}

export function isRepaired(r: RobotState): boolean {
  if (r.original_plan.length !== r.active_plan.length) return true;
  return r.active_plan.some((p, i) => !same(p, r.original_plan[i]));
}

export function fmt(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  return Number.isInteger(n) ? String(n) : n.toFixed(digits);
}
