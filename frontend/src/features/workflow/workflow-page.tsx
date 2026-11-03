import { useEffect, useMemo, useState } from 'react'
import { Cpu, Network, ShieldCheck, Timer, Workflow } from 'lucide-react'

import { AgentAvatar, EmptyState, ErrorNote, LoadingBlock, PageHeader, Section, StatCard } from '@/components/common/page'
import { Pill, StatusBadge } from '@/components/common/status-badge'
import { EventLogLine } from '@/features/history/event-item'
import { useApi } from '@/hooks/use-api'
import { useShell } from '@/hooks/use-shell'
import { api } from '@/lib/api'
import { formatCompact, formatDuration, formatInt, formatRelative, formatUsd } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { RunDetail, Task } from '@/types/api'

/** Group tasks into DAG layers: a task sits one layer below its deepest dependency. */
function layers(tasks: Task[]): Task[][] {
  const byKey = new Map(tasks.map((t) => [t.task_key, t]))
  const depth = new Map<string, number>()
  const visit = (t: Task, seen: Set<string>): number => {
    if (depth.has(t.task_key)) return depth.get(t.task_key)!
    if (seen.has(t.task_key)) return 0 // cycle guard; the backend validates DAGs
    seen.add(t.task_key)
    const d = Math.max(-1, ...t.depends_on.map((k) => (byKey.has(k) ? visit(byKey.get(k)!, seen) : -1))) + 1
    depth.set(t.task_key, d)
    return d
  }
  tasks.forEach((t) => visit(t, new Set()))
  const result: Task[][] = []
  tasks.forEach((t) => (result[depth.get(t.task_key)!] ??= []).push(t))
  return result
}

export function WorkflowPage() {
  const { currentProject } = useShell()
  const runs = useApi(() => api.runs.list({ limit: 100 }), [], ['events'])
  const [runId, setRunId] = useState<number | null>(null)
  // Default: latest run of the project picked in the top bar, else the latest run overall
  const selectedId =
    runId ?? runs.data?.find((r) => r.project_id === currentProject?.id)?.id ?? runs.data?.[0]?.id ?? null
  const selectedRun = runs.data?.find((r) => r.id === selectedId)
  const run = useApi<RunDetail | null>(
    () => (selectedId ? api.runs.get(selectedId) : Promise.resolve(null)),
    [selectedId],
    selectedId ? [`runs:${selectedId}`, 'events'] : [],
  )
  const [taskId, setTaskId] = useState<number | null>(null)

  useEffect(() => setTaskId(null), [selectedId])

  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow={<>Quy trình phối hợp / {selectedRun?.project_name ?? 'Tất cả dự án'}{selectedId && <span className="text-brand"> / Run #{selectedId}</span>}</>}
        title="Quy trình Phối hợp Multi-Agent"
        description="Đồ thị phụ thuộc (DAG) giữa các tác vụ của một luồng thực thi, cập nhật theo thời gian thực."
        actions={
          runs.data && runs.data.length > 0 && (
            <select
              value={selectedId ?? ''}
              onChange={(e) => setRunId(Number(e.target.value))}
              className="rounded-md bg-surface-low px-3 py-2 text-label-md outline-none"
            >
              {runs.data.map((r) => (
                <option key={r.id} value={r.id}>
                  Run #{r.id} · {r.project_name} · {r.request_text.slice(0, 40)}
                </option>
              ))}
            </select>
          )
        }
      />
      <ErrorNote message={runs.error ?? run.error} />
      {!runs.data ? (
        <LoadingBlock className="h-96" />
      ) : runs.data.length === 0 ? (
        <EmptyState icon={Workflow} title="Chưa có luồng thực thi nào">
          Khi bạn gửi yêu cầu cho AI Manager trong Không gian Dự án, đồ thị phối hợp giữa các agent sẽ xuất hiện tại đây.
        </EmptyState>
      ) : !run.data ? (
        <LoadingBlock className="h-96" />
      ) : (
        <RunView run={run.data} taskId={taskId} onSelect={setTaskId} />
      )}
    </div>
  )
}

function RunView({ run, taskId, onSelect }: { run: RunDetail; taskId: number | null; onSelect: (id: number) => void }) {
  const dag = useMemo(() => layers(run.tasks), [run.tasks])
  const selected = run.tasks.find((t) => t.id === taskId) ?? run.tasks.find((t) => t.status === 'running') ?? run.tasks[0]
  const activeAgents = new Set(run.tasks.filter((t) => t.status === 'running').map((t) => t.agent_code)).size
  const waiting = run.tasks.filter((t) => t.status === 'waiting_approval').length
  // Summed from per-task llm_usage so it is correct even before the run totals are rolled up
  const tokens = run.tasks.reduce((s, t) => s + t.input_tokens + t.output_tokens, 0)
  const cost = run.tasks.reduce((s, t) => s + t.cost_usd, 0)

  return (
    <>
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard label="Tổng thời gian run" value={formatDuration(run.started_at, run.finished_at)} icon={Timer} hint={<StatusBadge status={run.status} />} />
        <StatCard label="Agent đang hoạt động" value={`${activeAgents} / ${run.tasks.length} nodes`} icon={Network} accent="text-telemetry" />
        <StatCard label="Tổng token đã dùng" value={`${formatInt(tokens)} tok`} icon={Cpu} hint={formatUsd(cost, 4)} />
        <StatCard label="Điểm an toàn / gates" value={waiting ? `${waiting} chờ duyệt` : 'Không có chặn'} icon={ShieldCheck} accent={waiting ? 'text-warning' : 'text-success'} />
      </div>

      <div className="panel p-4">
        <p className="micro-label">Yêu cầu gốc</p>
        <p className="mt-1 text-body-md">{run.request_text}</p>
        {run.error && <p className="mt-2 font-mono text-label-sm text-danger">{run.error}</p>}
        {run.summary && <p className="mt-2 text-body-md text-success">{run.summary}</p>}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_400px]">
        <div className="panel dot-grid grid content-start gap-2 bg-surface-lowest p-4 md:p-6">
          <div className="mb-2 flex flex-wrap gap-2">
            <span className="rounded bg-surface-high px-2 py-1 font-mono text-label-sm">DAG: {dag.length} tầng · {run.tasks.length} node</span>
          </div>
          {run.tasks.length === 0 ? (
            <EmptyState icon={Workflow} title="AI Manager đang lập kế hoạch…" />
          ) : (
            dag.map((layer, i) => (
              <div key={i} className="grid gap-2">
                {i > 0 && <div className="mx-auto h-6 w-px bg-white/15" />}
                <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${Math.min(layer.length, 3)}, minmax(0, 1fr))` }}>
                  {layer.map((t) => (
                    <NodeCard key={t.id} task={t} active={selected?.id === t.id} onClick={() => onSelect(t.id)} />
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
        {selected && <NodeDetail task={selected} />}
      </div>
    </>
  )
}

function NodeCard({ task, active, onClick }: { task: Task; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex flex-col gap-2 rounded-lg border bg-[#1a2234] p-3 text-left transition-colors',
        active ? 'border-brand-strong shadow-[0_0_16px_-4px_rgb(59_130_246/0.4)]' : 'border-white/10 hover:border-white/25',
        task.status === 'running' && 'border-t-2 border-t-telemetry',
        task.status === 'pending' && 'opacity-70',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="flex items-center gap-2">
          <AgentAvatar code={task.agent_code} size="sm" />
          <span className="text-label-md font-semibold">{task.agent_name}</span>
        </span>
        <StatusBadge status={task.status} />
      </div>
      <p className="line-clamp-2 text-body-sm text-on-surface-variant">{task.title}</p>
      <div className="flex justify-between font-mono text-label-sm text-outline">
        <span>{formatDuration(task.started_at, task.finished_at)}</span>
        <span>Tokens: {formatCompact(task.input_tokens + task.output_tokens)}</span>
      </div>
    </button>
  )
}

function NodeDetail({ task }: { task: Task }) {
  const events = useApi(() => api.events.list({ run_id: task.run_id, limit: 200 }), [task.run_id], ['events', `runs:${task.run_id}`])
  const own = (events.data?.items ?? []).filter((e) => e.task_id === task.id).reverse()
  return (
    <Section title="Chi tiết node" actions={<span className="rounded bg-surface-high px-1.5 font-mono text-label-sm text-telemetry">#TASK-{task.id}</span>} className="content-start">
      <div className="flex gap-3 rounded-md bg-surface-container p-3">
        <AgentAvatar code={task.agent_code} size="lg" />
        <div className="min-w-0">
          <p className="flex flex-wrap items-center gap-2 text-headline-sm font-semibold">
            {task.agent_name} <StatusBadge status={task.status} />
          </p>
          <p className="text-body-sm text-on-surface-variant">{task.title}</p>
          <p className="font-mono text-label-sm text-outline">key: {task.task_key} · lần thử {task.attempt}/{task.max_attempts}</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-md bg-surface-container p-3">
          <p className="micro-label">Prompt / completion</p>
          <p className="font-mono text-label-md">{formatCompact(task.input_tokens)} / {formatCompact(task.output_tokens)}</p>
        </div>
        <div className="rounded-md bg-surface-container p-3">
          <p className="micro-label">Chi phí</p>
          <p className="font-mono text-label-md text-telemetry">{formatUsd(task.cost_usd, 4)}</p>
        </div>
      </div>
      {task.depends_on.length > 0 && <p className="font-mono text-label-sm text-outline">Phụ thuộc: {task.depends_on.join(', ')}</p>}
      {task.error && <p className="rounded bg-danger/10 p-2 font-mono text-label-sm text-danger">{task.error}</p>}
      <div>
        <div className="mb-1 flex justify-between font-mono text-label-sm">
          <span>Nhật ký node</span>
          {task.status === 'running' && <Pill tone="info">Live</Pill>}
        </div>
        <div className="grid max-h-80 gap-1.5 overflow-auto rounded-md bg-surface-lowest p-3">
          {own.length ? own.map((e) => <EventLogLine key={e.id} event={e} />) : <p className="font-mono text-code text-outline">Chưa có sự kiện.</p>}
        </div>
      </div>
      <p className="font-mono text-label-sm text-outline">Cập nhật {formatRelative(task.updated_at)}</p>
    </Section>
  )
}
