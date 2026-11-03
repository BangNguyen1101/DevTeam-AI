import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { api } from '@/lib/api'
import type { DashboardSummary, Health, Project } from '@/types/api'

import { useApi } from './use-api'

const STORAGE_KEY = 'devteam.currentProjectId'

interface ShellState {
  projects: Project[]
  currentProject: Project | null
  setCurrentProjectId: (id: number) => void
  summary: DashboardSummary | null
  health: Health | null
  healthFailed: boolean
  reloadProjects: () => void
}

const ShellContext = createContext<ShellState | null>(null)

function readStoredId(): number | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return raw ? Number(raw) : null
  } catch {
    return null
  }
}

/** App-wide data used by the sidebar/top bar: projects, current project, counters, health. */
export function ShellProvider({ children }: { children: React.ReactNode }) {
  const projects = useApi(() => api.projects.list('active'), [], ['projects'])
  const summary = useApi(() => api.dashboard(), [], ['projects', 'approvals', 'agents', 'events'])
  const [health, setHealth] = useState<Health | null>(null)
  const [healthFailed, setHealthFailed] = useState(false)
  const [currentId, setCurrentId] = useState<number | null>(readStoredId)

  useEffect(() => {
    const check = () =>
      api
        .health()
        .then((h) => {
          setHealth(h)
          setHealthFailed(false)
        })
        .catch(() => setHealthFailed(true))
    check()
    const timer = window.setInterval(check, 30_000)
    return () => window.clearInterval(timer)
  }, [])

  const setCurrentProjectId = useCallback((id: number) => {
    setCurrentId(id)
    try {
      window.localStorage.setItem(STORAGE_KEY, String(id))
    } catch {
      /* storage unavailable: selection lasts for this session only */
    }
  }, [])

  const list = projects.data ?? []
  const currentProject = list.find((p) => p.id === currentId) ?? list[0] ?? null

  const value = useMemo(
    () => ({
      projects: list,
      currentProject,
      setCurrentProjectId,
      summary: summary.data,
      health,
      healthFailed,
      reloadProjects: projects.reload,
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [projects.data, currentProject, summary.data, health, healthFailed],
  )
  return <ShellContext.Provider value={value}>{children}</ShellContext.Provider>
}

export function useShell(): ShellState {
  const ctx = useContext(ShellContext)
  if (!ctx) throw new Error('useShell must be used inside ShellProvider')
  return ctx
}
