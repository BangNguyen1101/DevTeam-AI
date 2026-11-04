import { useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  Bell,
  Bot,
  ChartNoAxesCombined,
  Coins,
  FolderGit2,
  LayoutDashboard,
  ListChecks,
  ListTree,
  LogOut,
  Menu,
  Network,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  SquareTerminal,
  X,
} from 'lucide-react'

import { useAuth } from '@/features/auth/auth-gate'
import { useShell } from '@/hooks/use-shell'
import { formatCompact, formatUsd } from '@/lib/format'
import { cn } from '@/lib/utils'

interface NavItem {
  to: string
  label: string
  icon: typeof Bot
  badge?: (s: ReturnType<typeof useShell>) => React.ReactNode
}

const NAV: NavItem[] = [
  { to: '/dashboard', label: 'Tổng quan', icon: LayoutDashboard },
  { to: '/projects', label: 'Dự án', icon: FolderGit2 },
  { to: '/workspace', label: 'Không gian Dự án', icon: SquareTerminal },
  {
    to: '/agents',
    label: 'Quản lý AI Agent',
    icon: Bot,
    badge: (s) => s.summary && <Badge className="text-telemetry">{s.summary.agents_enabled}</Badge>,
  },
  {
    to: '/workflow',
    label: 'Quy trình Phối hợp',
    icon: Network,
    badge: (s) =>
      !!s.summary?.runs_active && (
        <Badge className="text-telemetry">
          <span className="size-1.5 animate-pulse rounded-full bg-telemetry" />
          Live
        </Badge>
      ),
  },
  {
    to: '/tasks',
    label: 'Quản lý Tác vụ',
    icon: ListChecks,
    badge: (s) => !!s.summary?.tasks_running && <Badge>{s.summary.tasks_running}</Badge>,
  },
  {
    to: '/approvals',
    label: 'Trung tâm Phê duyệt',
    icon: ShieldCheck,
    badge: (s) =>
      !!s.summary?.approvals_pending && (
        <Badge className="bg-surface-highest text-brand">{s.summary.approvals_pending} chờ</Badge>
      ),
  },
  { to: '/history', label: 'Lịch sử Thực thi', icon: ListTree },
  { to: '/analytics', label: 'Phân tích & Chi phí', icon: ChartNoAxesCombined },
  { to: '/settings', label: 'Cài đặt Hệ thống', icon: SlidersHorizontal },
]

function Badge({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <span
      className={cn(
        'flex items-center gap-1 rounded bg-surface-container px-1.5 py-0.5 font-mono text-label-sm whitespace-nowrap text-on-surface-variant',
        className,
      )}
    >
      {children}
    </span>
  )
}

function Logo() {
  return (
    <Link to="/dashboard" className="flex items-center gap-2">
      <span className="flex size-8 items-center justify-center rounded-md bg-brand-strong/20 text-brand">
        <Network className="size-4" />
      </span>
      <span className="flex flex-col leading-none">
        <span className="text-headline-sm font-semibold text-on-surface">DevTeam AI</span>
        <span className="mt-1 font-mono text-label-sm text-brand">v0.2 · MVP</span>
      </span>
    </Link>
  )
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const shell = useShell()
  const { username, logout } = useAuth()
  const dbOk = !shell.healthFailed && shell.health?.database.ok
  return (
    <div className="flex h-full flex-col justify-between">
      <div>
        <div className="flex h-16 items-center px-4">
          <Logo />
        </div>
        <nav className="flex flex-col gap-0.5 px-2 py-2">
          {NAV.map(({ to, label, icon: Icon, badge }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  'flex items-center justify-between gap-2 rounded-md px-2.5 py-2 text-label-md transition-colors',
                  isActive
                    ? 'bg-surface-high font-semibold text-on-surface'
                    : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface',
                )
              }
            >
              <span className="flex min-w-0 items-center gap-2.5">
                <Icon className="size-[18px] shrink-0" />
                <span className="leading-tight">{label}</span>
              </span>
              {badge?.(shell)}
            </NavLink>
          ))}
        </nav>
      </div>
      <div className="flex flex-col gap-2 p-2">
        <div
          className={cn(
            'flex items-center gap-2 rounded-md bg-surface-low px-2.5 py-1.5 font-mono text-label-sm',
            dbOk ? 'text-telemetry' : 'text-danger',
          )}
          title={shell.health?.database.server_version}
        >
          <span className={cn('size-2 shrink-0 rounded-full', dbOk ? 'bg-telemetry' : 'bg-danger')} />
          <span className="truncate">{shell.healthFailed ? 'Backend mất kết nối' : dbOk ? 'SQL Server online' : 'Database lỗi'}</span>
          {shell.summary && (
            <span className="ml-auto shrink-0 text-outline">
              {shell.summary.agents_enabled}/{shell.summary.agents_total} AI
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 rounded-md bg-surface-low p-2">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-surface-highest font-mono text-label-sm uppercase text-on-surface">
            {username.slice(0, 2)}
          </span>
          <span className="flex min-w-0 flex-1 flex-col leading-tight">
            <span className="truncate text-label-md text-on-surface">{username}</span>
            <span className="font-mono text-label-sm text-outline">Quản trị viên</span>
          </span>
          <button
            type="button"
            onClick={logout}
            className="rounded p-1.5 text-outline hover:bg-surface-high hover:text-on-surface"
            title="Đăng xuất"
            aria-label="Đăng xuất"
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

function ProjectSelector() {
  const { projects, currentProject, setCurrentProjectId } = useShell()
  if (!projects.length) {
    return (
      <Link to="/projects" className="truncate rounded-md bg-surface-low px-3 py-2 text-label-md text-outline hover:text-on-surface">
        Chưa có dự án
      </Link>
    )
  }
  return (
    <label className="flex min-w-0 items-center gap-2 rounded-md bg-surface-low px-3 py-1.5">
      <FolderGit2 className="size-4 shrink-0 text-outline" />
      <span className="sr-only">Dự án hiện tại</span>
      <select
        value={currentProject?.id}
        onChange={(e) => setCurrentProjectId(Number(e.target.value))}
        className="min-w-0 max-w-56 truncate bg-transparent text-label-md text-on-surface outline-none"
      >
        {projects.map((p) => (
          <option key={p.id} value={p.id} className="bg-surface-container">
            {p.name}
          </option>
        ))}
      </select>
    </label>
  )
}

function TopBar({ onMenu }: { onMenu: () => void }) {
  const { summary } = useShell()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const budget = summary?.monthly_budget_usd

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-white/[0.06] bg-surface/95 px-4 backdrop-blur md:px-6">
      <button type="button" onClick={onMenu} className="rounded-md p-1.5 text-on-surface-variant hover:bg-surface-high lg:hidden" aria-label="Mở menu">
        <Menu className="size-5" />
      </button>
      <div className="hidden items-center gap-1.5 text-label-md text-on-surface-variant sm:flex">
        <LayoutDashboard className="size-4" />
        <span>/</span>
        <span className="font-semibold text-on-surface">Workspace</span>
      </div>
      <ProjectSelector />
      <form
        className="hidden flex-1 items-center gap-2 rounded-md bg-surface-low px-3 py-2 md:flex"
        onSubmit={(e) => {
          e.preventDefault()
          if (query.trim()) navigate(`/history?q=${encodeURIComponent(query.trim())}`)
        }}
      >
        <Search className="size-4 text-outline" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Tìm trong nhật ký thực thi…"
          className="w-full bg-transparent text-label-md text-on-surface outline-none placeholder:text-outline"
        />
      </form>
      <div className="ml-auto flex items-center gap-2">
        {summary && (
          <Link
            to="/analytics"
            className="hidden items-center gap-2 rounded-md bg-surface-low px-3 py-1.5 font-mono text-label-sm text-telemetry lg:flex"
            title="Tổng token và chi phí đã ghi nhận"
          >
            <Coins className="size-4" />
            <span className="leading-tight">
              {formatCompact(summary.total_tokens)} tokens
              <br />
              {formatUsd(summary.cost_usd)}
              {budget ? ` / ${formatUsd(budget, 0)}` : ''}
            </span>
          </Link>
        )}
        <Link to="/approvals" className="relative rounded-md p-2 text-on-surface-variant hover:bg-surface-high" aria-label="Yêu cầu phê duyệt">
          <Bell className="size-5" />
          {!!summary?.approvals_pending && <span className="absolute top-1.5 right-1.5 size-2 rounded-full bg-brand-strong" />}
        </Link>
      </div>
    </header>
  )
}

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  return (
    <div className="min-h-svh bg-surface text-on-surface">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[260px] border-r border-white/[0.04] bg-surface-lowest lg:block">
        <SidebarContent />
      </aside>
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button type="button" className="absolute inset-0 bg-black/60" aria-label="Đóng menu" onClick={() => setMobileOpen(false)} />
          <aside className="relative h-full w-[260px] bg-surface-lowest">
            <button type="button" className="absolute top-4 right-3 text-outline" onClick={() => setMobileOpen(false)} aria-label="Đóng menu">
              <X className="size-5" />
            </button>
            <SidebarContent onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}
      <div className="lg:pl-[260px]">
        <TopBar onMenu={() => setMobileOpen(true)} />
        <main className="mx-auto max-w-[1440px] p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
