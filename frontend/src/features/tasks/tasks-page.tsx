import { useMemo, useState } from 'react'
import { Coins, Columns3, List, ListChecks, Search, TriangleAlert, Zap } from 'lucide-react'

import { AgentAvatar, EmptyState, ErrorNote, LoadingBlock, PageHeader, Segmented } from '@/components/common/page'
import { Pill } from '@/components/common/status-badge'
import { useApi } from '@/hooks/use-api'
import { useShell } from '@/hooks/use-shell'
import { AGENT_ORDER, agentMeta } from '@/lib/agents'
import { api } from '@/lib/api'
import { formatCompact, formatInt, formatRelative, formatUsd } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { Task, TaskStatus } from '@/types/api'

import { TaskTable } from './task-table'

const COLUMNS: { title: string; statuses: TaskStatus[]; dot: string }[] = [
  { title: 'Cần làm', statuses: ['pending', 'ready'], dot: 'bg-outline' },
  { title: 'Đang thực hiện', statuses: ['running'], dot: 'bg-telemetry' },
  { title: 'Chờ phê duyệt', statuses: ['waiting_approval'], dot: 'bg-warning' },
  { title: 'Đã hoàn thành', statuses: ['completed'], dot: 'bg-success' },
  { title: 'Thất bại / Bỏ qua', statuses: ['failed', 'skipped'], dot: 'bg-danger' },
]

export function TasksPage() {
  const { projects } = useShell()
  const [view, setView] = useState<'kanban' | 'list'>('kanban')
  const [projectId, setProjectId] = useState<number | undefined>()
  const [agent, setAgent] = useState<string | undefined>()
  const [query, setQuery] = useState('')
  const tasks = useApi(() => api.tasks.list({ project_id: projectId, agent_code: agent }), [projectId, agent], ['events'])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (tasks.data ?? []).filter(
      (t) => !q || t.title.toLowerCase().includes(q) || t.description?.toLowerCase().includes(q) || `task-${t.id}`.includes(q),
    )
  }, [tasks.data, query])

  const running = filtered.filter((t) => t.status === 'running').length
  const waiting = filtered.filter((t) => t.status === 'waiting_approval').length
  const tokens = filtered.reduce((s, t) => s + t.input_tokens + t.output_tokens, 0)
  const cost = filtered.reduce((s, t) => s + t.cost_usd, 0)

  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow={<><span className="size-1.5 rounded-full bg-telemetry" /> Autonomous swarm orchestration</>}
        title={<>Quản lý Tác vụ Đa Tác nhân <span className="text-on-surface-variant">— Task Kanban</span></>}
        actions={
          <Segmented
            value={view}
            onChange={setView}
            options={[
              { value: 'kanban', label: <span className="flex items-center gap-1.5"><Columns3 className="size-3.5" /> Bảng Kanban</span> },
              { value: 'list', label: <span className="flex items-center gap-1.5"><List className="size-3.5" /> Danh sách</span> },
            ]}
          />
        }
      />

      <div className="panel grid gap-3 p-3">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex min-w-60 flex-1 items-center gap-2 rounded-md bg-surface-lowest px-3 py-2">
            <Search className="size-4 text-outline" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Tìm theo mã TASK-…, tiêu đề, mô tả"
              className="w-full bg-transparent text-label-md outline-none placeholder:text-outline"
            />
          </label>
          <select
            value={projectId ?? ''}
            onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : undefined)}
            className="rounded-md bg-surface-lowest px-3 py-2 text-label-md outline-none"
          >
            <option value="">Mọi dự án</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        <div className="flex flex-wrap gap-1">
          {[undefined, ...AGENT_ORDER].map((code) => (
            <button
              key={code ?? 'all'}
              type="button"
              onClick={() => setAgent(code)}
              className={cn(
                'rounded px-2.5 py-1 font-mono text-label-sm',
                agent === code ? 'bg-surface-high text-telemetry' : 'text-outline hover:text-on-surface',
              )}
            >
              {code ? agentMeta(code).abbr + ' · ' + code : 'Tất cả agent'}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 border-t border-white/[0.06] pt-3 font-mono text-label-sm text-on-surface-variant">
          <span className="flex items-center gap-1.5"><Zap className="size-3.5 text-telemetry" /> Đang chạy: <b className="text-telemetry">{running}</b></span>
          <span className="flex items-center gap-1.5"><TriangleAlert className="size-3.5 text-warning" /> Chờ human-gate: <b className="text-warning">{waiting}</b></span>
          <span className="flex items-center gap-1.5"><Coins className="size-3.5 text-agent" /> Tokens: <b>{formatInt(tokens)}</b> (~{formatUsd(cost)})</span>
        </div>
      </div>

      <ErrorNote message={tasks.error} />
      {!tasks.data ? (
        <LoadingBlock className="h-96" />
      ) : view === 'list' ? (
        <TaskTable tasks={filtered} />
      ) : filtered.length === 0 && !query ? (
        <EmptyState icon={ListChecks} title="Chưa có tác vụ nào">
          Tác vụ được AI Manager tạo ra khi một luồng thực thi bắt đầu.
        </EmptyState>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-2">
          {COLUMNS.map((col) => {
            const items = filtered.filter((t) => col.statuses.includes(t.status))
            return (
              <div key={col.title} className="flex w-72 shrink-0 flex-col gap-3">
                <div className="flex items-center gap-2 px-1">
                  <span className={cn('size-2 rounded-full', col.dot)} />
                  <span className="text-headline-sm font-semibold">{col.title}</span>
                  <span className="rounded bg-surface-high px-1.5 font-mono text-label-sm">{items.length}</span>
                </div>
                {items.map((t) => <TaskCard key={t.id} task={t} />)}
                {items.length === 0 && <div className="rounded-lg border border-dashed border-white/10 p-4 text-center text-body-sm text-outline">Trống</div>}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function TaskCard({ task }: { task: Task }) {
  return (
    <article className={cn('panel-raised flex flex-col gap-2 p-3', task.status === 'running' && 'border-brand-strong/60 shadow-[0_0_16px_-4px_rgb(59_130_246/0.3)]')}>
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="font-mono text-label-sm text-telemetry">#TASK-{task.id}</span>
        <span className="rounded bg-surface-high px-1.5 font-mono text-label-sm text-outline">{task.task_key}</span>
        {task.attempt > 1 && <Pill tone="warning" dot={false}>Lần {task.attempt}/{task.max_attempts}</Pill>}
      </div>
      <h3 className="text-headline-sm font-semibold">{task.title}</h3>
      {task.description && <p className="line-clamp-3 text-body-sm text-on-surface-variant">{task.description}</p>}
      {task.error && <p className="line-clamp-3 rounded bg-danger/10 p-2 font-mono text-label-sm text-danger">{task.error}</p>}
      {task.depends_on.length > 0 && <p className="font-mono text-label-sm text-outline">Phụ thuộc: {task.depends_on.join(', ')}</p>}
      <div className="flex items-center justify-between border-t border-white/[0.06] pt-2 font-mono text-label-sm">
        <span className="flex items-center gap-1.5 text-on-surface-variant">
          <AgentAvatar code={task.agent_code} size="sm" /> {task.agent_name}
        </span>
        <span className="text-telemetry">{formatCompact(task.input_tokens + task.output_tokens)} tkn</span>
      </div>
      <p className="font-mono text-label-sm text-outline">{task.project_name} · {formatRelative(task.updated_at)}</p>
    </article>
  )
}
