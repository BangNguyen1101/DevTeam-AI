// Mirrors backend/app/schemas. Keep in sync with docs/API_DOCUMENTATION.md.

export type ProjectStatus = 'active' | 'archived'

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
  permissions: string[]
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
