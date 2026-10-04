import Link from "next/link";

const steps = [
  ["1", "Plan", "Prioritized Space-Time A* gives every robot a collision-free plan (vertex + edge reservations)."],
  ["2", "Disrupt", "Block a cell, break a robot, or inject an emergency task while the robots are moving."],
  ["3", "Repair locally", "Only invalidated plans are released. Wait → shift → detour → negotiate → expand the affected set."],
  ["4", "Compare", "See old vs. repaired paths, bids, and metrics, or run batch experiments."],
];

export default function Home() {
  return (
    <div className="mx-auto max-w-4xl py-10">
      <h1 className="text-3xl font-bold tracking-tight text-slate-50">Incremental Multi-Agent Path Repair</h1>
      <p className="mt-2 text-slate-400">
        A working algorithmic simulation of a dynamic automated warehouse: robots plan with Space-Time A*, and when the
        world changes only the necessary parts of the plans are repaired.
      </p>
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {steps.map(([n, t, d]) => (
          <div key={n} className="rounded-xl border border-ink-600 bg-ink-800/60 p-4">
            <div className="text-xs font-mono text-accent">step {n}</div>
            <div className="text-lg font-semibold">{t}</div>
            <p className="text-sm text-slate-400">{d}</p>
          </div>
        ))}
      </div>
      <div className="mt-8 flex gap-3">
        <Link href="/simulation" className="rounded-lg bg-accent-dim px-5 py-2.5 font-medium text-ink-950 hover:bg-accent">
          Open the simulation
        </Link>
        <Link href="/experiments" className="rounded-lg bg-ink-700 px-5 py-2.5 font-medium hover:bg-ink-600">
          Run experiments
        </Link>
      </div>
      <p className="mt-6 text-xs text-slate-500">
        Requires the backend at <code className="font-mono">http://localhost:8000</code> (see README).
      </p>
    </div>
  );
}
