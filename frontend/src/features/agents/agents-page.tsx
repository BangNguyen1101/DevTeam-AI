import { useState } from 'react'
import { Clock, Cpu, ListChecks, Network, ShieldAlert, Users } from 'lucide-react'

import { EmptyState, ErrorNote, LoadingBlock, PageHeader, ProgressBar, Segmented } from '@/components/common/page'
import { Pill, StatusBadge } from '@/components/common/status-badge'
import { useApi } from '@/hooks/use-api'
import { agentMeta } from '@/lib/agents'
import { api } from '@/lib/api'
import { formatCompact, formatInt, formatRelative, formatUsd, percent } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { Agent, AgentStats } from '@/types/api'

import { AgentEditDialog } from './agent-edit-dialog'

type Filter = 'all' | 'busy' | 'idle' | 'disabled'

function stateOf(agent: Agent, stats?: AgentStats): Filter {
  if (!agent.is_enabled) return 'disabled'
  return stats?.current_task_status ? 'busy' : 'idle'
}

export function AgentsPage() {
  const [filter, setFilter] = useState<Filter>('all')
  const data = useApi(() => Promise.all([api.agents.list(), api.agents.stats()]), [], ['agents', 'events'])

  if (data.error) return <ErrorNote message={data.error} />
  if (!data.data) return <LoadingBlock className="h-96" />

  const [agents, stats] = data.data
  const byId = new Map(stats.map((s) => [s.agent_id, s]))
  const manager = agents.find((a) => a.code === 'manager')
  const crew = agents.filter((a) => a.code !== 'manager')
  const count = (f: Filter) => crew.filter((a) => f === 'all' || stateOf(a, byId.get(a.id)) === f).length
  const visible = crew.filter((a) => filter === 'all' || stateOf(a, byId.get(a.id)) === filter)
  const maxTokens = Math.max(...stats.map((s) => s.total_tokens), 1)

  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow={<>Autonomous architecture · {agents.filter((a) => a.is_enabled).length}/{agents.length} tác nhân bật</>}
        title={<>Đội ngũ AI Agents Chuyên trách <span className="text-brand">({agents.length} Tác nhân)</span></>}
        description="AI Manager điều phối 6 kỹ sư AI chuyên môn theo quy trình phát triển phần mềm; mỗi agent chỉ có những quyền được cấp."
      />

      {manager && <ManagerCard agent={manager} stats={byId.get(manager.id)} crew={crew} statsById={byId} />}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-headline-lg font-semibold">
          <Users className="size-5 text-telemetry" /> Kỹ sư AI chuyên môn
        </h2>
        <Segmented
          value={filter}
          onChange={setFilter}
          options={[
            { value: 'all', label: `Tất cả (${count('all')})` },
            { value: 'busy', label: `Đang xử lý (${count('busy')})` },
            { value: 'idle', label: `Rảnh (${count('idle')})` },
            { value: 'disabled', label: `Tắt (${count('disabled')})` },
          ]}
        />
      </div>

      {visible.length === 0 ? (
        <EmptyState icon={Users} title="Không có agent nào ở trạng thái này" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((a) => (
            <AgentCard key={a.id} agent={a} stats={byId.get(a.id)} maxTokens={maxTokens} />
          ))}
        </div>
      )}
    </div>
  )
}

function StatusPill({ agent, stats }: { agent: Agent; stats?: AgentStats }) {
  if (!agent.is_enabled) return <Pill>Tắt</Pill>
  if (stats?.current_task_status) return <StatusBadge status={stats.current_task_status} />
  return <Pill>Rảnh (sẵn sàng)</Pill>
}

function ManagerCard({ agent, stats, crew, statsById }: { agent: Agent; stats?: AgentStats; crew: Agent[]; statsById: Map<number, AgentStats> }) {
  const Icon = agentMeta(agent.code).icon
  return (
    <div className="panel grid gap-6 p-5 lg:grid-cols-[1fr_420px]">
      <div className="grid content-start gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded bg-telemetry/15 px-1.5 py-0.5 font-mono text-label-sm text-telemetry">CORE-TIER 00</span>
          <span className="font-mono text-label-sm text-outline">ID: {agent.code}</span>
          <StatusPill agent={agent} stats={stats} />
        </div>
        <div className="flex gap-4">
          <span className="flex size-16 shrink-0 items-center justify-center rounded-lg bg-brand-strong/20 text-brand">
            <Icon className="size-8" />
          </span>
          <div>
            <h2 className="text-headline-xl font-semibold">{agent.name}</h2>
            <p className="text-label-md text-brand">Trưởng nhóm điều phối & giám sát toàn pipeline</p>
            <p className="mt-1 text-body-md text-on-surface-variant">{agent.role_description}</p>
          </div>
        </div>
        <div className="rounded-md bg-surface-lowest p-3">
          <p className="micro-label">Lệnh điều phối hiện tại</p>
          <p className="mt-1 font-mono text-code text-on-surface">{stats?.current_task_title ?? 'Không có — đang chờ yêu cầu mới.'}</p>
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {[
            ['Tác vụ điều phối', formatInt(stats?.tasks_total ?? 0), `${stats?.tasks_completed ?? 0} hoàn thành`],
            ['Lỗi', formatInt(stats?.tasks_failed ?? 0), 'tác vụ thất bại'],
            ['Tokens đã dùng', formatCompact(stats?.total_tokens ?? 0), formatUsd(stats?.cost_usd ?? 0)],
            ['Hoạt động cuối', stats?.last_active_at ? formatRelative(stats.last_active_at) : '—', 'lượt gọi model'],
          ].map(([label, value, hint]) => (
            <div key={label} className="rounded-md bg-surface-container p-3">
              <p className="font-mono text-label-sm text-outline">{label}</p>
              <p className="tabular text-headline-lg font-semibold">{value}</p>
              <p className="font-mono text-label-sm text-telemetry">{hint}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="grid content-start gap-3 rounded-lg bg-surface-container p-4">
        <div className="flex justify-between">
          <span className="flex items-center gap-2 micro-label"><Network className="size-4 text-telemetry" /> Graph truyền dữ liệu agents</span>
        </div>
        <AgentGraph crew={crew} statsById={statsById} />
        <div className="grid gap-2 text-label-md">
          <div className="flex justify-between"><span className="text-on-surface-variant">Động cơ suy luận</span><span className="rounded bg-surface-lowest px-2 font-mono text-label-sm">{agent.model}</span></div>
          <div className="flex justify-between"><span className="text-on-surface-variant">Max output tokens</span><span className="font-mono text-label-sm">{formatInt(agent.max_output_tokens)}</span></div>
          <div className="flex justify-between"><span className="text-on-surface-variant">Quyền thực thi</span><span className="font-mono text-label-sm text-telemetry">{agent.permissions.join(' · ')}</span></div>
        </div>
        <AgentEditDialog agent={agent} />
      </div>
    </div>
  )
}

function AgentGraph({ crew, statsById }: { crew: Agent[]; statsById: Map<number, AgentStats> }) {
  const w = 380
  const h = 170
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="dot-grid h-auto w-full rounded-md bg-surface-lowest">
      {crew.map((a, i) => {
        const x = 30 + (i * (w - 60)) / Math.max(crew.length - 1, 1)
        const busy = !!statsById.get(a.id)?.current_task_status
        return (
          <g key={a.id}>
            <line x1={w / 2} y1={40} x2={x} y2={125} stroke={busy ? '#4cd7f6' : '#424754'} strokeWidth={busy ? 2 : 1} strokeDasharray={a.is_enabled ? undefined : '3 3'} />
            <circle cx={x} cy={125} r={7} fill={busy ? '#4cd7f6' : a.is_enabled ? '#31353e' : '#1c2028'} stroke="#8c909f" />
            <text x={x} y={152} textAnchor="middle" className="fill-on-surface-variant font-mono text-[10px]">{agentMeta(a.code).abbr}</text>
          </g>
        )
      })}
      <circle cx={w / 2} cy={40} r={12} fill="#4d8eff" stroke="#adc6ff" strokeWidth={2} />
      <text x={w / 2} y={18} textAnchor="middle" className="fill-on-surface-variant font-mono text-[10px]">MANAGER</text>
    </svg>
  )
}

function AgentCard({ agent, stats, maxTokens }: { agent: Agent; stats?: AgentStats; maxTokens: number }) {
  const meta = agentMeta(agent.code)
  const Icon = meta.icon
  return (
    <article className={cn('panel flex flex-col gap-3 p-4', !agent.is_enabled && 'opacity-60', stats?.current_task_status === 'running' && 'border-brand-strong/50')}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex gap-3">
          <span className={cn('flex size-11 shrink-0 items-center justify-center rounded-lg', meta.tone)}>
            <Icon className="size-5" />
          </span>
          <div>
            <h3 className="text-headline-sm font-semibold">{agent.name}</h3>
            <p className="font-mono text-label-sm text-outline uppercase">Agent: {agent.code}</p>
          </div>
        </div>
        <StatusPill agent={agent} stats={stats} />
      </div>
      <p className="line-clamp-2 min-h-11 text-body-md text-on-surface-variant">{agent.role_description}</p>
      <div className="rounded-md bg-surface-lowest p-3">
        <p className="micro-label">Tác vụ hiện tại</p>
        <p className="mt-1 line-clamp-2 font-mono text-label-sm text-on-surface">{stats?.current_task_title ?? 'Không có tác vụ đang chạy'}</p>
      </div>
      <div className="grid gap-1">
        <div className="flex justify-between font-mono text-label-sm">
          <span className="text-on-surface-variant">Tiêu thụ token</span>
          <span>{formatCompact(stats?.total_tokens ?? 0)} · {formatUsd(stats?.cost_usd ?? 0)}</span>
        </div>
        <ProgressBar value={percent(stats?.total_tokens ?? 0, maxTokens)} color={meta.color} />
      </div>
      <div className="flex justify-between font-mono text-label-sm text-outline">
        <span className="flex items-center gap-1"><ListChecks className="size-3.5" /> {stats?.tasks_completed ?? 0}/{stats?.tasks_total ?? 0} xong</span>
        {!!stats?.tasks_failed && <span className="flex items-center gap-1 text-danger"><ShieldAlert className="size-3.5" /> {stats.tasks_failed} lỗi</span>}
        <span className="flex items-center gap-1"><Clock className="size-3.5" /> {stats?.last_active_at ? formatRelative(stats.last_active_at) : 'chưa chạy'}</span>
      </div>
      <div className="mt-auto flex items-center justify-between gap-2 border-t border-white/[0.06] pt-3">
        <span className="flex items-center gap-1.5 font-mono text-label-sm"><Cpu className="size-3.5 text-telemetry" /> {agent.model}</span>
        <AgentEditDialog agent={agent} />
      </div>
      <div className="flex flex-wrap gap-1">
        {agent.permissions.map((p) => (
          <span key={p} className="rounded border border-white/10 px-1.5 font-mono text-label-sm text-outline">{p}</span>
        ))}
      </div>
    </article>
  )
}
