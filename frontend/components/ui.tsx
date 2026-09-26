"use client";

import type { ReactNode } from "react";

export function Panel({ title, children, right }: { title: string; children: ReactNode; right?: ReactNode }) {
  return (
    <section className="rounded-xl border border-ink-600 bg-ink-800/70 p-3 shadow">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">{title}</h3>
        {right}
      </div>
      {children}
    </section>
  );
}

export function Btn({
  children,
  onClick,
  variant = "default",
  disabled,
  active,
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "default" | "primary" | "danger";
  disabled?: boolean;
  active?: boolean;
  title?: string;
}) {
  const base = "rounded-md px-2.5 py-1.5 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-40";
  const styles = {
    default: "bg-ink-700 text-slate-100 hover:bg-ink-600",
    primary: "bg-accent-dim text-ink-950 hover:bg-accent",
    danger: "bg-rose-600 text-white hover:bg-rose-500",
  }[variant];
  return (
    <button title={title} disabled={disabled} onClick={onClick} className={`${base} ${styles} ${active ? "ring-2 ring-accent" : ""}`}>
      {children}
    </button>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-[11px] text-slate-400">
      {label}
      {children}
    </label>
  );
}

export const inputCls =
  "w-full rounded-md border border-ink-600 bg-ink-900 px-2 py-1 text-xs text-slate-100 outline-none focus:border-accent";

export function Chip({ children, color }: { children: ReactNode; color?: string }) {
  return (
    <span className="rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold text-ink-950" style={{ background: color ?? "#94a3b8" }}>
      {children}
    </span>
  );
}
