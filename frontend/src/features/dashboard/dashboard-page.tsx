import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  Bot,
  CircleCheck,
  Coins,
  DollarSign,
  FolderOpen,
  Radio,
  Rocket,
  ShieldCheck,
  Sparkles,
  Users,
  Zap,
} from 'lucide-react'

import { AgentAvatar, EmptyState, ErrorNote, LoadingBlock, PageHeader, ProgressBar, Section, Segmented, StatCard } from '@/components/common/page'
import { Pill, StatusBadge } from '@/components/common/status-badge'
import { Button } from '@/components/ui/button'
import { ApprovalCard } from '@/features/approvals/approval-card'
import { EventCard } from '@/features/history/event-item'
import { useApi } from '@/hooks/use-api'
import { useShell } from '@/hooks/use-shell'
import { agentMeta } from '@/lib/agents'
import { api } from '@/lib/api'
import { formatInt, formatUsd, percent } from '@/lib/format'

export function DashboardPage() {
  const { summary } = useShell()
  const [days, setDays] = useState(1)
  const usage = useApi(() => api.usage.summary(days), [days], ['events'])
  const agents = useApi(() => Promise.all([api.agents.list(), api.agents.stats()]), [], ['agents', 'events'])
  const approvals = useApi(() => api.approvals.list('pending'), [], ['approvals'])
  const events = useApi(() => api.events.list({ limit: 6 }), [], ['events'])

  if (!summary) return <LoadingBlock className="h-96" />

  const rate = summary.task_success_rate
  const statsById = new Map((agents.data?.[1] ?? []).map((s) => [s.agent_id, s]))
  const usageTotal = usage.data?.totals.total_tokens ?? 0

  return (
    <div className="grid gap-6">
      <div className="panel flex flex-wrap items-center justify-between gap-4 p-5 md:p-6">
        <PageHeader
          eyebrow={
            <>
              <span className="size-1.5 rounded-full bg-telemetry" />
              {summary.runs_active ? 'Multi-agent đang vận hành' : 'Hệ thống sẵn sàng'}
            </>
          }
          title="Trung tâm điều phối DevTeam AI"
          description={
            summary.runs_active
              ? `AI Manager đang điều phối ${summary.tasks_running} tác vụ trên ${summary.runs_active} luồng thực thi. ${summary.agents_enabled}/${summary.agents_total} agent đang bật.`
              : `Chưa có luồng thực thi nào đang chạy. ${summary.agents_enabled}/${summary.agents_total} agent đang bật và sẵn sàng nhận việc.`
          }
        />
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" asChild>
            <Link to="/analytics">
              <BarChart3 /> Xem báo cáo chi phí
            </Link>
          </Button>
          <Button asChild>
            <Link to="/workspace">
              <Sparkles /> Khởi tạo yêu cầu AI mới
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <StatCard label="Tổng số dự án" value={`${summary.projects_total} dự án`} icon={FolderOpen} hint={`${summary.projects_active} đang hoạt động`} />
        <StatCard label="Tác vụ đang chạy" value={`${summary.tasks_running} tác vụ`} icon={Zap} hint={`${summary.runs_active} luồng song song`} />
        <StatCard
          label="Tác vụ hoàn thành"
          value={`${summary.tasks_completed} tác vụ`}
          icon={CircleCheck}
          hint={rate === null ? 'Chưa có dữ liệu' : `Tỉ lệ thành công ${(rate * 100).toFixed(1)}%`}
        />
        <StatCard label="AI Agents sẵn sàng" value={`${summary.agents_enabled}/${summary.agents_total}`} icon={Bot} hint="Agent đang bật" accent="text-telemetry" />
        <StatCard label="Tokens tiêu thụ" value={formatInt(summary.total_tokens)} icon={Coins} hint="Toàn bộ thời gian" />
        <StatCard
          label="Chi phí ước tính"
          value={formatUsd(summary.cost_usd)}
          icon={DollarSign}
          hint={summary.monthly_budget_usd ? `Ngân sách tháng: ${formatUsd(summary.monthly_budget_usd)}` : 'Chưa đặt ngân sách'}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <div className="grid content-start gap-6">
          <Section
            title="Tiến độ dự án"
            icon={Rocket}
            actions={
              <Link to="/projects" className="flex items-center gap-1 text-label-md text-brand hover:underline">
                Toàn bộ dự án <ArrowRight className="size-4" />
              </Link>
            }
          >
            {summary.projects.length === 0 ? (
              <EmptyState icon={FolderOpen} title="Chưa có dự án đang hoạt động">
                Tạo dự án ở trang Dự án để đội AI bắt đầu làm việc.
              </EmptyState>
            ) : (
              <div className="grid gap-3">
                {summary.projects.slice(0, 5).map((p) => {
                  const pct = percent(p.tasks_completed, p.tasks_total)
                  return (
                    <Link key={p.project_id} to={`/projects/${p.project_id}`} className="panel-raised flex flex-col gap-2 p-4 hover:border-white/20">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="rounded bg-surface-high px-1.5 py-0.5 font-mono text-label-sm text-outline">PRJ-{p.project_id}</span>
                          <span className="text-headline-sm font-semibold">{p.project_name}</span>
                        </div>
                        {p.latest_run_status ? <StatusBadge status={p.latest_run_status} /> : <Pill>Chưa có run</Pill>}
                      </div>
                      <div className="flex justify-between font-mono text-label-sm text-outline">
                        <span>{p.latest_run_id ? `Run #${p.latest_run_id} · ${p.tasks_completed}/${p.tasks_total} tác vụ` : 'Chưa gửi yêu cầu cho AI Manager'}</span>
                        <span className="text-telemetry">{pct}%</span>
                      </div>
                      <ProgressBar value={pct} />
                    </Link>
                  )
                })}
              </div>
            )}
          </Section>

          <Section
            title="Phân bổ tiêu thụ token theo Agent"
            icon={BarChart3}
            description="Tính từ bảng llm_usage"
            actions={
              <Segmented
                value={days}
                onChange={setDays}
                options={[
                  { value: 1, label: '24H' },
                  { value: 7, label: '7D' },
                  { value: 30, label: '30D' },
                ]}
              />
            }
          >
            {usage.data && usage.data.by_agent.length > 0 ? (
              <div className="grid gap-3 rounded-md bg-surface-lowest p-4">
                <div className="flex justify-between font-mono text-label-sm text-outline uppercase">
                  <span>Phân bổ tokens theo vai trò</span>
                  <span className="text-telemetry">Tổng: {formatInt(usageTotal)} tokens</span>
                </div>
                {usage.data.by_agent.map((a) => (
                  <div key={a.agent_code} className="grid gap-1">
                    <div className="flex flex-wrap justify-between gap-2 font-mono text-label-sm">
                      <span className="flex items-center gap-2 text-on-surface">
                        <span className="size-2 rounded-sm" style={{ background: agentMeta(a.agent_code).color }} />
                        {a.agent_name}
                      </span>
                      <span className="text-telemetry">
                        {formatInt(a.total_tokens)} ({percent(a.total_tokens, usageTotal)}%)
                        {a.avg_latency_ms !== null && ` · ${Math.round(a.avg_latency_ms)} ms avg`}
                      </span>
                    </div>
                    <ProgressBar value={percent(a.total_tokens, usageTotal)} color={agentMeta(a.agent_code).color} />
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState icon={Coins} title="Chưa có lượt gọi model nào trong khoảng này" />
            )}
          </Section>

          <Section
            title="Hoạt động gần đây của các Agent"
            icon={Radio}
            actions={
              <Link to="/history" className="flex items-center gap-1 text-label-md text-brand hover:underline">
                Lịch sử thực thi <ArrowRight className="size-4" />
              </Link>
            }
          >
            <ErrorNote message={events.error} />
            {events.data?.items.length ? (
              <div className="grid gap-2">
                {events.data.items.map((e) => (
                  <EventCard key={e.id} event={e} />
                ))}
              </div>
            ) : (
              <EmptyState icon={Radio} title="Chưa có hoạt động nào">
                Các sự kiện của Agent sẽ hiện ở đây theo thời gian thực.
              </EmptyState>
            )}
          </Section>
        </div>

        <div className="grid content-start gap-6">
          <Section
            title={`Trạng thái ${agents.data?.[0].length ?? 7} AI Agents`}
            icon={Users}
            actions={<Pill tone="info">{summary.agents_enabled}/{summary.agents_total} bật</Pill>}
          >
            {!agents.data ? (
              <LoadingBlock />
            ) : (
              <div className="grid gap-2">
                {agents.data[0].map((a) => {
                  const s = statsById.get(a.id)
                  return (
                    <div key={a.id} className="flex items-center gap-3 rounded-md bg-surface-container p-2.5">
                      <AgentAvatar code={a.code} />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-label-md font-semibold">{a.name}</p>
                        <p className="truncate font-mono text-label-sm text-outline">{s?.current_task_title ?? a.model}</p>
                      </div>
                      {!a.is_enabled ? (
                        <Pill>Tắt</Pill>
                      ) : s?.current_task_status ? (
                        <StatusBadge status={s.current_task_status} />
                      ) : (
                        <Pill>Rảnh</Pill>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </Section>

          <Section
            title="Yêu cầu phê duyệt"
            icon={ShieldCheck}
            description="Human-in-the-loop"
            actions={!!approvals.data?.length && <Pill tone="warning">{approvals.data.length} chờ</Pill>}
          >
            {approvals.data?.length ? (
              <div className="grid gap-3">
                {approvals.data.slice(0, 3).map((a) => (
                  <ApprovalCard key={a.id} approval={a} compact onDecided={approvals.reload} />
                ))}
                <Link to="/approvals" className="flex items-center justify-center gap-1 text-label-md text-brand hover:underline">
                  Xem tất cả yêu cầu <ArrowRight className="size-4" />
                </Link>
              </div>
            ) : (
              <EmptyState icon={ShieldCheck} title="Không có yêu cầu nào đang chờ" />
            )}
          </Section>
        </div>
      </div>
    </div>
  )
}
