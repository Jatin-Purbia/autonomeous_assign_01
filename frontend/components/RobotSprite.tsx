"use client";

import { motion } from "framer-motion";
import type { RobotState } from "@/lib/types";
import { CELL, COLORS, center, robotColor } from "@/lib/viz";

type Props = {
  robot: RobotState;
  duration: number; // seconds of the move animation (tied to simulation speed)
  role: "direct" | "indirect" | "none";
  selected: boolean;
  onClick?: () => void;
};

export default function RobotSprite({ robot, duration, role, selected, onClick }: Props) {
  if (!robot.position) return null;
  const [cx, cy] = center(robot.position);
  const broken = robot.status === "broken";
  const emergency = robot.status === "emergency";
  const carrying = robot.tasks.some((t) => t.status === "picked");
  const fill = broken ? COLORS.broken : robotColor(robot.index);
  const r = CELL * 0.36;
  const ring = role === "direct" ? COLORS.direct : role === "indirect" ? COLORS.indirect : null;

  return (
    <motion.g
      initial={false}
      animate={{ x: cx, y: cy }}
      transition={{ duration: Math.max(0.05, duration), ease: "linear" }}
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
      style={{ cursor: "pointer" }}
    >
      {ring && (
        <motion.circle
          r={r + 5}
          fill="none"
          stroke={ring}
          strokeWidth={3}
          animate={{ opacity: [1, 0.35, 1] }}
          transition={{ duration: 1.2, repeat: Infinity }}
        />
      )}
      {selected && <circle r={r + 3} fill="none" stroke="#f8fafc" strokeWidth={1.5} strokeDasharray="3 2" />}
      {emergency && <circle r={r + 1.5} fill="none" stroke="#facc15" strokeWidth={2} />}
      <circle r={r} fill={fill} stroke="#0b1020" strokeWidth={1.5} />
      <text textAnchor="middle" dy="0.35em" fontSize={r * 0.95} fontWeight={700} fill="#0b1020" pointerEvents="none">
        {broken ? "✕" : robot.id.replace(/^R/, "")}
      </text>
      {carrying && !broken && <rect x={r * 0.45} y={-r * 1.05} width={7} height={7} fill="#fde047" stroke="#0b1020" strokeWidth={1} />}
      <title>{`${robot.id} · ${robot.status} · priority ${robot.priority}`}</title>
    </motion.g>
  );
}
