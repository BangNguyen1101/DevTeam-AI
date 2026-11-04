// Mirrors backend/app/schemas. Keep in sync with docs/API_DOCUMENTATION.md.

export type ProjectStatus = 'active' | 'archived'
export type RunStatus = 'pending' | 'planning' | 'running' | 'waiting_approval' | 'completed' | 'failed' | 'cancelled'
export type TaskStatus = 'pending' | 'ready' | 'running' | 'waiting_approval' | 'completed' | 'failed' | 'skipped'
export type ApprovalStatus = 'pending' | 'approved' | 'rejected'

export interface Project {
  id: number
  name: string
  description: string | null
  status: ProjectStatus
  workspace_dir: string
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  name: string
  description?: string | null
}

export interface ProjectUpdate {
  name?: string
  description?: string | null
  status?: ProjectStatus
}

export interface Agent {
  id: number
  code: string
  name: string
  role_description: string
  model: string
  max_output_tokens: number
  is_enabled: boolean
  instructions: string | null
  permissions: string[]
}

export interface AgentUpdate {
  model?: string
  max_output_tokens?: number
  is_enabled?: boolean
  instructions?: string | null
}

export interface AgentStats {
  agent_id: number
  agent_code: string
  tasks_total: number
  tasks_completed: number
  tasks_failed: number
  current_task_title: string | null
  current_task_status: TaskStatus | null
  total_tokens: number
  cost_usd: number
  last_active_at: string | null
}

export interface Task {
  id: number
  run_id: number
  project_id: number
  project_name: string
  agent_code: string
  agent_name: string
  task_key: string
  title: string
  description: string | null
  status: TaskStatus
  attempt: number
  max_attempts: number
  error: string | null
  depends_on: string[]
  input_tokens: number
  output_tokens: number
  cost_usd: number
  started_at: string | null
  finished_at: string | null
  created_at: string
  updated_at: string
}

export interface Run {
  id: number
  project_id: number
  project_name: string
  request_text: string
  status: RunStatus
  budget_usd: number | null
  total_input_tokens: number
  total_output_tokens: number
  total_cost_usd: number
  summary: string | null
  error: string | null
  tasks_total: number
  tasks_completed: number
  started_at: string | null
  finished_at: string | null
  created_at: string
}

export interface RunDetail extends Run {
  tasks: Task[]
}

export interface Artifact {
  id: number
  run_id: number
  task_id: number | null
  kind: string
  name: string
  file_path: string | null
  created_at: string
}

export interface ExecutionEvent {
  id: number
  run_id: number
  project_id: number
  project_name: string
  task_id: number | null
  task_title: string | null
  agent_code: string | null
  event_type: string
  message: string
  data: Record<string, unknown> | unknown[] | null
  created_at: string
}

export interface EventPage {
  items: ExecutionEvent[]
  total: number
  next_before_id: number | null
}

export interface Approval {
  id: number
  run_id: number
  project_id: number
  project_name: string
  task_id: number | null
  agent_code: string | null
  kind: string
  title: string
  payload: Record<string, unknown> | unknown[] | null
  status: ApprovalStatus
  decision_note: string | null
  decided_by: string | null
  decided_at: string | null
  created_at: string
}

export interface UsageSummary {
  days: number
  totals: {
    calls: number
    requests: number
    input_tokens: number
    cached_input_tokens: number
    output_tokens: number
    total_tokens: number
    cost_usd: number
  }
  by_agent: { agent_code: string; agent_name: string; calls: number; total_tokens: number; cost_usd: number; avg_latency_ms: number | null }[]
  by_day: { day: string; total_tokens: number; cost_usd: number; calls: number }[]
  by_model: { model: string; calls: number; total_tokens: number; cost_usd: number; avg_latency_ms: number | null }[]
  by_project: { project_id: number; project_name: string; tasks_completed: number; total_tokens: number; cost_usd: number }[]
  monthly_budget_usd: number | null
  month_cost_usd: number
}

export interface DashboardSummary {
  projects_total: number
  projects_active: number
  runs_active: number
  tasks_running: number
  tasks_completed: number
  tasks_failed: number
  task_success_rate: number | null
  agents_enabled: number
  agents_total: number
  total_tokens: number
  cost_usd: number
  monthly_budget_usd: number | null
  approvals_pending: number
  projects: {
    project_id: number
    project_name: string
    latest_run_id: number | null
    latest_run_status: RunStatus | null
    tasks_total: number
    tasks_completed: number
  }[]
}

export interface Limits {
  max_task_attempts: number
  max_fix_iterations: number
  command_timeout_seconds: number
  default_run_budget_usd: number
  monthly_budget_usd: number | null
  require_command_approval: boolean
  mandatory_review: boolean
}

export interface ModelPrice {
  input_per_1m: number
  cached_input_per_1m: number
  output_per_1m: number
}

export interface Settings {
  limits: Limits
  pricing: Record<string, ModelPrice>
  llm_configured: boolean
  llm_endpoint: string
}

export interface FileEntry {
  path: string
  is_dir: boolean
  size: number | null
}

export interface FileContent {
  path: string
  size: number
  content: string
  truncated: boolean
}

export interface PreviewStatus {
  running: boolean
  url: string | null
  api_running: boolean
  started_at: number | null
  log_tail: string | null
}

export interface Health {
  status: 'ok' | 'error'
  database: { ok: boolean; server_version?: string; migration?: string; error?: string }
}

export interface RealtimeEvent<T = unknown> {
  topic: string
  type: string
  data: T
  timestamp: string
}
