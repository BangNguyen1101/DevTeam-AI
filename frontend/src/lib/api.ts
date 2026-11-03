import type { Agent, Health, Project, ProjectCreate, ProjectStatus, ProjectUpdate } from '@/types/api'

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const body = res.status === 204 ? null : await res.json().catch(() => null)
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

export const api = {
  health: () => request<Health>('/health'),
  projects: {
    list: (status?: ProjectStatus) => request<Project[]>(`/projects${status ? `?status=${status}` : ''}`),
    get: (id: number) => request<Project>(`/projects/${id}`),
    create: (data: ProjectCreate) => request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: number, data: ProjectUpdate) =>
      request<Project>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },
  agents: {
    list: () => request<Agent[]>('/agents'),
  },
}
