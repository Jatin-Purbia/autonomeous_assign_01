import type { ExperimentJob, ExperimentRequest, ScenarioSummary, SimState, Strategy } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

const post = <T>(p: string, body?: unknown) => req<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined });

export const api = {
  scenarios: () => req<ScenarioSummary[]>("/api/scenarios"),
  initialize: (body: {
    scenario_id?: string;
    random?: { n_agents: number; seed: number; width?: number; height?: number; tasks_per_robot?: number };
    strategy: Strategy;
    seed: number;
    repair_config?: Record<string, number>;
  }) => post<{ state: SimState }>("/api/simulation/initialize", body),
  start: () => post("/api/simulation/start"),
  pause: () => post("/api/simulation/pause"),
  step: () => post("/api/simulation/step"),
  reset: () => post("/api/simulation/reset"),
  speed: (steps_per_second: number) => post("/api/simulation/speed", { steps_per_second }),
  repairDefaults: () => req<Record<string, number>>("/api/config/defaults"),
  blockCell: (x: number, y: number, duration: number | null, activation_time: number | null) =>
    post<{ ok: boolean; scheduled: boolean; message: string }>("/api/disruptions/block-cell", { x, y, duration, activation_time }),
  breakRobot: (robot_id: string, activation_time: number | null) =>
    post<{ ok: boolean; scheduled: boolean; message: string }>("/api/disruptions/break-robot", { robot_id, activation_time }),
  emergency: (pickup: [number, number], delivery: [number, number], robot_id: string | null, activation_time: number | null) =>
    post<{ ok: boolean; scheduled: boolean; message: string }>("/api/disruptions/emergency-task", {
      pickup: { x: pickup[0], y: pickup[1] },
      delivery: { x: delivery[0], y: delivery[1] },
      robot_id,
      activation_time,
    }),
  removeObstacle: (id: string) => req(`/api/disruptions/obstacle/${id}`, { method: "DELETE" }),
  cancelScheduled: (id: string) => req(`/api/disruptions/scheduled/${id}`, { method: "DELETE" }),
  runExperiment: (body: ExperimentRequest) => post<ExperimentJob>("/api/experiments/run", body),
  experiment: (id: string) => req<ExperimentJob>(`/api/experiments/${id}`),
  exportUrl: (id: string, format: "csv" | "json", table: "summary" | "runs" = "summary") =>
    `${API_URL}/api/experiments/${id}/export?format=${format}&table=${table}`,
};
