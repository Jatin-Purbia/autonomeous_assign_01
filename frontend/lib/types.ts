export type XY = [number, number];

export type TaskState = {
  id: string;
  pickup: XY;
  delivery: XY;
  priority: number;
  emergency: boolean;
  status: "pending" | "picked" | "delivered" | "reassigned";
  completed_at: number | null;
};

export type RobotState = {
  id: string;
  index: number;
  position: XY | null;
  status: "active" | "waiting" | "broken" | "emergency" | "done";
  on_grid: boolean;
  priority: number;
  completion_time: number | null;
  broken_at: number | null;
  tasks: TaskState[];
  waypoints: { task_id: string; kind: "pickup" | "delivery"; position: XY }[];
  original_plan: XY[]; // index == time
  active_plan: XY[];
  executed: XY[];
};

export type ObstacleState = {
  id: string;
  position: XY;
  start: number;
  end: number | null;
  owner: string | null;
  active: boolean;
};

export type DisruptionImpact = {
  disruption_id: string;
  type: string;
  time: number;
  direct_agents: string[];
  affected_agents: string[];
  modified_agents: string[];
  impact: number;
  messages: number;
  runtime_ms: number;
  success: boolean;
  strategy: string;
};

export type Metrics = {
  success: boolean;
  status: string;
  failure_reason: string | null;
  time: number;
  completion_times: Record<string, number>;
  flowtime: number;
  makespan: number;
  original_flowtime: number;
  original_makespan: number;
  delta_flowtime: number;
  n_agents: number;
  num_modified: number;
  modified_ids: string[];
  modified_ratio: number;
  total_path_length: number;
  original_path_length: number;
  additional_path_length: number;
  total_waits: number;
  repair_time_ms: number;
  messages: number;
  collisions: number;
  deadlocks: number;
  conflicts_avoided: number;
  remaining_tasks: number;
  n_disruptions: number;
  n_repairs_failed: number;
  per_disruption: DisruptionImpact[];
};

export type RepairMessage = {
  time: number;
  kind: string;
  sender: string;
  receiver: string;
  details: Record<string, unknown>;
};

export type ConflictEdge = {
  a: string;
  b: string;
  kind: "vertex" | "edge_swap" | "shared_resource" | "dependency";
  time: number | null;
  position: XY | null;
  note: string;
};

export type ConflictGraphData = {
  label: string;
  time: number;
  nodes: string[];
  edges: ConflictEdge[];
  affected: string[];
  direct: string[];
};

export type RepairSummary = {
  success: boolean;
  strategy: string;
  failure_reason: string | null;
  direct: string[];
  affected: string[];
  modified: string[];
  expansions: { time: number; robot: string; added_by: string | null; via: string; reason: string; size: number }[];
  reasons: Record<string, string>;
  methods: Record<string, string>;
  messages: RepairMessage[];
  conflict_graphs: ConflictGraphData[];
  diffs: Record<string, { from_time: number; old_suffix: XY[]; new_suffix: XY[]; method: string; reason: string }>;
  conflicts_avoided: number;
  runtime_ms: number;
  delta_completion: Record<string, number>;
  reassignments: Record<string, unknown>[];
  objective: number;
};

export type SimState = {
  time: number;
  status: "ready" | "running" | "completed" | "failed";
  failure_reason: string | null;
  grid: { width: number; height: number; static: XY[] };
  robots: RobotState[];
  obstacles: ObstacleState[];
  scheduled: { id: string; type: string; time: number; position?: XY; robot_id?: string; duration?: number; task?: unknown }[];
  metrics: Metrics;
  last_repair: RepairSummary | null;
  repairs: { time: number; disruption_id: string; modified: string[]; affected: string[]; success: boolean }[];
  initial_plan: Record<string, unknown>;
  events_total: number;
  scenario: { id: string; name: string; description: string };
};

export type SimEvent = {
  index: number;
  time: number;
  event_type: string;
  robot_ids: string[];
  reason: string | null;
  details: Record<string, unknown>;
};

export type ScenarioSummary = {
  id: string;
  name: string;
  description: string;
  n_robots: number;
  width: number;
  height: number;
  builtin: boolean;
  expected_impact: number | null;
};

export type ServerMessage =
  | { type: "state"; running: boolean; speed: number; strategy: string; state: SimState; events?: SimEvent[] }
  | { type: "error"; message: string };

export type Strategy = "local" | "single_agent" | "global";

// ---- experiments
export type ExperimentRequest = {
  agent_counts: number[];
  densities: number[];
  disruption_type: "cell_blockage" | "robot_breakdown" | "emergency_task" | "mixed";
  repetitions: number;
  seed: number;
  strategies: Strategy[];
};

export type SummaryRow = {
  strategy: Strategy;
  n_agents: number;
  density: number;
  n: number;
  n_success: number;
  success_rate: number;
  collisions: number;
  deadlocks: number;
  [k: string]: number | string | null;
};

export type ExperimentJob = {
  experiment_id: string;
  status: "queued" | "running" | "done" | "failed";
  done: number;
  total: number;
  error: string | null;
  config: Record<string, unknown>;
  result: {
    summary: SummaryRow[];
    rows: Record<string, unknown>[];
    paired_local_vs_global: Record<string, number>;
    paired_local_vs_single_agent: Record<string, number>;
    runtime_s: number;
  } | null;
};
