import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  Activity,
  BarChart3,
  Bot,
  CheckSquare,
  FolderKanban,
  History,
  LayoutDashboard,
  ListTodo,
  Settings,
  ShieldCheck,
  Workflow,
} from 'lucide-react'

import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { Health } from '@/types/api'

interface NavItem {
  to: string
  label: string
  icon: typeof Activity
  // Week of the implementation plan in which the module becomes functional
  availableInWeek?: number
}

const NAV: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, availableInWeek: 4 },
  { to: '/projects', label: 'Dự án', icon: FolderKanban },
  { to: '/agents', label: 'AI Agents', icon: Bot },
  { to: '/workflows', label: 'Workflow', icon: Workflow, availableInWeek: 2 },
  { to: '/tasks', label: 'Nhiệm vụ', icon: ListTodo, availableInWeek: 2 },
  { to: '/approvals', label: 'Phê duyệt', icon: CheckSquare, availableInWeek: 3 },
  { to: '/history', label: 'Lịch sử', icon: History, availableInWeek: 4 },
  { to: '/usage', label: 'Chi phí & Token', icon: BarChart3, availableInWeek: 2 },
  { to: '/settings', label: 'Cài đặt', icon: Settings, availableInWeek: 4 },
]

function HealthIndicator() {
  const [health, setHealth] = useState<Health | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    const check = () =>
      api
        .health()
        .then((h) => {
          setHealth(h)
          setFailed(false)
        })
        .catch(() => setFailed(true))
    check()
    const timer = window.setInterval(check, 30_000)
    return () => window.clearInterval(timer)
  }, [])

  const ok = !failed && health?.database.ok
  const label = failed ? 'Mất kết nối backend' : !health ? 'Đang kiểm tra…' : ok ? 'SQL Server OK' : 'Lỗi database'
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground" title={health?.database.server_version}>
      <span className={cn('size-2 rounded-full', !health && !failed ? 'bg-muted-foreground' : ok ? 'bg-emerald-500' : 'bg-red-500')} />
      {label}
    </div>
  )
}

export function AppLayout() {
  return (
    <div className="flex min-h-svh bg-background text-foreground">
      <aside className="hidden w-60 shrink-0 flex-col border-r bg-sidebar md:flex">
        <div className="flex h-14 items-center gap-2 border-b px-4 font-semibold">
          <ShieldCheck className="size-5 text-primary" />
          DevTeam AI
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 p-2">
          {NAV.map(({ to, label, icon: Icon, availableInWeek }) =>
            availableInWeek ? (
              <span
                key={to}
                className="flex cursor-not-allowed items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground/60"
                title={`Triển khai ở tuần ${availableInWeek}`}
              >
                <Icon className="size-4" />
                {label}
                <span className="ml-auto text-[10px]">T{availableInWeek}</span>
              </span>
            ) : (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors hover:bg-sidebar-accent',
                    isActive && 'bg-sidebar-accent font-medium text-sidebar-accent-foreground',
                  )
                }
              >
                <Icon className="size-4" />
                {label}
              </NavLink>
            ),
          )}
        </nav>
        <div className="border-t p-4">
          <HealthIndicator />
        </div>
      </aside>
      <main className="flex-1 overflow-x-hidden">
        {/* Compact top navigation for small screens (sidebar is hidden below md) */}
        <div className="flex items-center gap-1 overflow-x-auto border-b px-4 py-2 md:hidden">
          <ShieldCheck className="mr-2 size-5 shrink-0 text-primary" />
          {NAV.filter((n) => !n.availableInWeek).map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn('shrink-0 rounded-md px-3 py-1.5 text-sm', isActive ? 'bg-muted font-medium' : 'text-muted-foreground')
              }
            >
              {label}
            </NavLink>
          ))}
          <div className="ml-auto shrink-0">
            <HealthIndicator />
          </div>
        </div>
        <div className="mx-auto max-w-6xl p-4 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
