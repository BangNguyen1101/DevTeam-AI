import type {
  Agent,
  AgentStats,
  AgentUpdate,
  Approval,
  ApprovalStatus,
  Artifact,
  DashboardSummary,
  EventPage,
  FileContent,
  FileEntry,
  Health,
  Limits,
  ModelPrice,
  PreviewStatus,
  Project,
  ProjectCreate,
  ProjectStatus,
  ProjectUpdate,
  Run,
  RunDetail,
  RunStatus,
  Settings,
  Task,
  TaskStatus,
  UsageSummary,
} from '@/types/api'

const BASE = '/api/v1'

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

type Query = Record<string, string | number | boolean | null | undefined>

function qs(params: Query = {}): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : ''
}

/** Fired when the backend answers 401 so the app can show the login screen. */
export const UNAUTHORIZED_EVENT = 'devteam:unauthorized'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const body = res.status === 204 ? null : await res.json().catch(() => null)
  if (res.status === 401 && !path.startsWith('/auth/login')) {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
  }
  if (!res.ok) {
    // AppError -> {error: {code, message}}; validation -> {detail: [...]}
    const message =
      body?.error?.message ??
      (Array.isArray(body?.detail) ? body.detail.map((d: { msg: string }) => d.msg).join('; ') : null) ??
      res.statusText
    throw new ApiError(res.status, body?.error?.code ?? 'http_error', message)
  }
  return body as T
}

const send = <T>(method: string, path: string, data?: unknown) =>
  request<T>(path, { method, body: data === undefined ? undefined : JSON.stringify(data) })

export function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : 'Không thể kết nối backend'
}

export const api = {
  auth: {
    me: () => request<{ username: string }>('/auth/me'),
    login: (username: string, password: string) =>
      send<{ username: string }>('POST', '/auth/login', { username, password }),
    logout: () => send<null>('POST', '/auth/logout'),
    changePassword: (current_password: string, new_password: string) =>
      send<null>('POST', '/auth/password', { current_password, new_password }),
  },
  health: () => request<Health>('/health'),
  dashboard: () => request<DashboardSummary>('/dashboard'),
  projects: {
    list: (status?: ProjectStatus) => request<Project[]>(`/projects${qs({ status })}`),
    get: (id: number) => request<Project>(`/projects/${id}`),
    create: (data: ProjectCreate) => send<Project>('POST', '/projects', data),
    update: (id: number, data: ProjectUpdate) => send<Project>('PATCH', `/projects/${id}`, data),
    files: (id: number) => request<FileEntry[]>(`/projects/${id}/files`),
    file: (id: number, path: string) => request<FileContent>(`/projects/${id}/files/content${qs({ path })}`),
    preview: (id: number) => request<PreviewStatus>(`/projects/${id}/preview`),
    startPreview: (id: number) => send<PreviewStatus>('POST', `/projects/${id}/preview`),
    stopPreview: (id: number) => send<null>('DELETE', `/projects/${id}/preview`),
  },
  agents: {
    list: () => request<Agent[]>('/agents'),
    stats: () => request<AgentStats[]>('/agents/stats'),
    update: (id: number, data: AgentUpdate) => send<Agent>('PATCH', `/agents/${id}`, data),
  },
  llm: {
    models: () => request<string[]>('/llm/models'),
  },
  runs: {
    create: (projectId: number, data: { request_text: string; budget_usd?: number | null }) =>
      send<Run>('POST', `/projects/${projectId}/runs`, data),
    cancel: (id: number) => send<null>('POST', `/runs/${id}/cancel`),
    list: (params: { project_id?: number; status?: RunStatus; limit?: number } = {}) => request<Run[]>(`/runs${qs(params)}`),
    get: (id: number) => request<RunDetail>(`/runs/${id}`),
    artifacts: (id: number) => request<Artifact[]>(`/runs/${id}/artifacts`),
  },
  tasks: {
    list: (params: { project_id?: number; run_id?: number; agent_code?: string; status?: TaskStatus } = {}) =>
      request<Task[]>(`/tasks${qs(params)}`),
  },
  events: {
    list: (params: {
      project_id?: number
      run_id?: number
      agent_code?: string
      event_type?: string
      q?: string
      before_id?: number
      limit?: number
    } = {}) => request<EventPage>(`/events${qs(params)}`),
  },
  approvals: {
    list: (status?: ApprovalStatus) => request<Approval[]>(`/approvals${qs({ status })}`),
    approve: (id: number, note?: string) => send<Approval>('POST', `/approvals/${id}/approve`, { note }),
    reject: (id: number, note?: string) => send<Approval>('POST', `/approvals/${id}/reject`, { note }),
  },
  usage: {
    summary: (days: number, project_id?: number) => request<UsageSummary>(`/usage/summary${qs({ days, project_id })}`),
  },
  settings: {
    get: () => request<Settings>('/settings'),
    updateLimits: (data: Limits) => send<Settings>('PUT', '/settings/limits', data),
    updatePricing: (data: Record<string, ModelPrice>) => send<Settings>('PUT', '/settings/pricing', data),
  },
}
