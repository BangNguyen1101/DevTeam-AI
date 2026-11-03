import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { BarChart3, Coins, Cpu, DollarSign, Gauge, Receipt, ShieldCheck, Users } from 'lucide-react'
import { toast } from 'sonner'

import { Donut, LineChart } from '@/components/common/charts'
import { EmptyState, ErrorNote, LoadingBlock, PageHeader, ProgressBar, Section, Segmented, StatCard } from '@/components/common/page'
import { Pill } from '@/components/common/status-badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useApi } from '@/hooks/use-api'
import { agentMeta } from '@/lib/agents'
import { api, errorMessage } from '@/lib/api'
import { formatCompact, formatInt, formatUsd, percent } from '@/lib/format'
import type { Settings, UsageSummary } from '@/types/api'

export function AnalyticsPage() {
  const [days, setDays] = useState(7)
  const usage = useApi(() => api.usage.summary(days), [days], ['events', 'settings'])
  const settings = useApi(() => api.settings.get(), [], ['settings'])

  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow="Telemetry engine // cost matrix"
        title="Phân tích Tiêu thụ & Quản lý Chi phí API"
        description="Số liệu tổng hợp từ từng lượt gọi model (bảng llm_usage). Chi phí tính theo bảng giá bạn khai báo trong Cài đặt."
        actions={
          <Segmented
            value={days}
            onChange={setDays}
            options={[
              { value: 1, label: 'Hôm nay' },
              { value: 7, label: '7 ngày qua' },
              { value: 30, label: '30 ngày qua' },
              { value: 90, label: '90 ngày' },
            ]}
          />
        }
      />
      <ErrorNote message={usage.error} />
      {!usage.data ? <LoadingBlock className="h-96" /> : <Content usage={usage.data} settings={settings.data} />}
    </div>
  )
}

function Content({ usage, settings }: { usage: UsageSummary; settings: Settings | null }) {
  const t = usage.totals
  const budget = usage.monthly_budget_usd
  const tasksDone = usage.by_project.reduce((s, p) => s + p.tasks_completed, 0)
  const latencies = usage.by_model.filter((m) => m.avg_latency_ms !== null)
  const avgLatency = latencies.length ? latencies.reduce((s, m) => s + (m.avg_latency_ms ?? 0) * m.calls, 0) / latencies.reduce((s, m) => s + m.calls, 0) : null
  const unpriced = usage.by_model.filter((m) => settings && !settings.pricing[m.model]).map((m) => m.model)

  return (
    <>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Tổng chi phí API (thực tế)" value={formatUsd(t.cost_usd)} icon={DollarSign} hint={budget ? `Tháng này ${formatUsd(usage.month_cost_usd)} / ${formatUsd(budget)}` : 'Chưa đặt ngân sách tháng'}>
          {budget ? <ProgressBar value={percent(usage.month_cost_usd, budget)} tone={usage.month_cost_usd > budget * 0.8 ? 'bg-warning' : 'bg-telemetry'} /> : null}
        </StatCard>
        <StatCard label="Tổng token tiêu thụ" value={formatInt(t.total_tokens)} icon={Coins}>
          <div className="grid grid-cols-2 gap-2 rounded-md bg-surface-lowest p-2 font-mono text-label-sm">
            <span>Input <b className="block text-on-surface">{formatInt(t.input_tokens)}</b></span>
            <span>Output <b className="block text-telemetry">{formatInt(t.output_tokens)}</b></span>
          </div>
        </StatCard>
        <StatCard label="Chi phí bình quân / tác vụ" value={tasksDone ? formatUsd(t.cost_usd / tasksDone, 3) : '—'} icon={Receipt} accent="text-telemetry" hint={`${tasksDone} tác vụ hoàn thành trong kỳ`} />
        <StatCard label="Độ trễ trung bình" value={avgLatency !== null ? `${(avgLatency / 1000).toFixed(2)}s` : '—'} icon={Gauge} hint={`${formatInt(t.calls)} lượt gọi · ${formatInt(t.requests)} request`} />
      </div>

      {unpriced.length > 0 && (
        <p className="rounded-md border border-warning/30 bg-warning/10 p-3 text-body-sm text-warning">
          Chưa có bảng giá cho model: <span className="font-mono">{unpriced.join(', ')}</span>. Chi phí của các model này được ghi là $0 —{' '}
          <Link to="/settings" className="underline">khai báo giá trong Cài đặt</Link>.
        </p>
      )}

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <Section
          title="Xu hướng tiêu thụ token & chi phí theo ngày"
          icon={BarChart3}
          actions={
            <div className="flex gap-3 font-mono text-label-sm">
              <span className="flex items-center gap-1"><span className="size-2 rounded-full bg-brand" /> Token</span>
              <span className="flex items-center gap-1"><span className="size-2 rounded-full bg-telemetry" /> Chi phí</span>
            </div>
          }
        >
          {usage.by_day.length === 0 ? (
            <EmptyState icon={BarChart3} title="Chưa có lượt gọi model trong khoảng thời gian này" />
          ) : (
            <>
              <LineChart
                points={usage.by_day.map((d) => ({ label: d.day.slice(5), values: [d.total_tokens, d.cost_usd] }))}
                series={[
                  { name: 'Tokens', color: '#adc6ff' },
                  { name: 'Chi phí', color: '#4cd7f6', format: (n) => formatUsd(n, 4) },
                ]}
              />
              <div className="grid grid-cols-3 gap-2 rounded-md bg-surface-lowest p-3 text-center font-mono text-label-sm">
                <span>Đỉnh tiêu thụ<b className="block text-on-surface">{formatInt(Math.max(...usage.by_day.map((d) => d.total_tokens)))}</b></span>
                <span>Chi phí ngày cao nhất<b className="block text-telemetry">{formatUsd(Math.max(...usage.by_day.map((d) => d.cost_usd)), 4)}</b></span>
                <span>Lượt gọi<b className="block text-agent">{formatInt(t.calls)}</b></span>
              </div>
            </>
          )}
        </Section>

        <Section title="Phân bổ theo AI Agent" icon={Users} actions={<span className="font-mono text-label-sm text-telemetry">{formatUsd(t.cost_usd)} tổng</span>}>
          {usage.by_agent.length === 0 ? (
            <EmptyState title="Chưa có dữ liệu" />
          ) : (
            <>
              <div className="flex items-center gap-4 rounded-md bg-surface-lowest p-3">
                <Donut
                  parts={usage.by_agent.map((a) => ({ value: a.total_tokens, color: agentMeta(a.agent_code).color }))}
                  label={<><span className="font-mono text-label-sm">{usage.by_agent.length} agents</span><span className="text-label-sm text-outline">active</span></>}
                />
                <div className="font-mono text-label-sm">
                  <p className="text-outline">Tỉ trọng lớn nhất:</p>
                  <p className="text-brand">{usage.by_agent[0].agent_name} ({percent(usage.by_agent[0].total_tokens, t.total_tokens)}%)</p>
                </div>
              </div>
              <div className="grid gap-2">
                {usage.by_agent.map((a) => (
                  <div key={a.agent_code} className="grid gap-1">
                    <div className="flex justify-between font-mono text-label-sm">
                      <span className="flex items-center gap-2"><span className="size-2 rounded-sm" style={{ background: agentMeta(a.agent_code).color }} />{a.agent_name}</span>
                      <span>{percent(a.total_tokens, t.total_tokens)}% ({formatUsd(a.cost_usd)})</span>
                    </div>
                    <ProgressBar value={percent(a.total_tokens, t.total_tokens)} color={agentMeta(a.agent_code).color} />
                  </div>
                ))}
              </div>
            </>
          )}
        </Section>
      </div>

      <Section title="So sánh hiệu quả theo model" icon={Cpu} description="Tính trên dữ liệu thực tế của kỳ đang xem">
        {usage.by_model.length === 0 ? (
          <EmptyState title="Chưa có model nào được gọi" />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {usage.by_model.map((m) => (
              <div key={m.model} className="panel-raised grid gap-2 p-4 font-mono text-label-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-headline-sm font-semibold text-telemetry">{m.model}</span>
                  {settings?.pricing[m.model] ? <Pill tone="success" dot={false}>Có giá</Pill> : <Pill tone="warning" dot={false}>Chưa có giá</Pill>}
                </div>
                {[
                  ['Lượt gọi', formatInt(m.calls)],
                  ['Tokens', formatInt(m.total_tokens)],
                  ['Chi phí', formatUsd(m.cost_usd, 4)],
                  ['Tokens / $', m.cost_usd > 0 ? formatInt(Math.round(m.total_tokens / m.cost_usd)) : '—'],
                  ['Độ trễ TB', m.avg_latency_ms !== null ? `${(m.avg_latency_ms / 1000).toFixed(2)}s` : '—'],
                  ['Tỉ trọng chi phí', `${percent(m.cost_usd, t.cost_usd)}%`],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between rounded bg-surface-lowest px-2 py-1.5"><span className="text-outline">{k}</span><span>{v}</span></div>
                ))}
              </div>
            ))}
          </div>
        )}
      </Section>

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <Section title="Chi tiết theo dự án" icon={Receipt}>
          {usage.by_project.length === 0 ? (
            <EmptyState title="Chưa có dự án nào phát sinh chi phí" />
          ) : (
            <div className="-mx-4 overflow-x-auto md:-mx-5">
              <Table>
                <TableHeader>
                  <TableRow className="border-white/[0.06] hover:bg-transparent">
                    {['Dự án', 'Tác vụ xong', 'Tổng token', 'Chi phí', 'Tỉ trọng'].map((h) => <TableHead key={h} className="micro-label">{h}</TableHead>)}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {usage.by_project.map((p) => (
                    <TableRow key={p.project_id} className="border-white/[0.06]">
                      <TableCell><Link to={`/projects/${p.project_id}`} className="text-telemetry hover:underline">{p.project_name}</Link></TableCell>
                      <TableCell className="font-mono text-label-sm">{p.tasks_completed}</TableCell>
                      <TableCell className="font-mono text-label-sm">{formatCompact(p.total_tokens)}</TableCell>
                      <TableCell className="font-mono text-label-sm text-telemetry">{formatUsd(p.cost_usd)}</TableCell>
                      <TableCell className="min-w-28"><ProgressBar value={percent(p.cost_usd, t.cost_usd)} /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </Section>
        {settings && <BudgetPanel settings={settings} monthCost={usage.month_cost_usd} />}
      </div>
    </>
  )
}

function BudgetPanel({ settings, monthCost }: { settings: Settings; monthCost: number }) {
  const [value, setValue] = useState(settings.limits.monthly_budget_usd?.toString() ?? '')
  const [saving, setSaving] = useState(false)
  const budget = settings.limits.monthly_budget_usd

  const save = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.settings.updateLimits({ ...settings.limits, monthly_budget_usd: value.trim() ? Number(value) : null })
      toast.success('Đã lưu ngân sách tháng')
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title="Ngân sách & cảnh báo" icon={ShieldCheck} description="Workflow Engine dùng các giới hạn này khi điều phối agent">
      <div className="rounded-md bg-surface-lowest p-3">
        <div className="flex justify-between text-label-md">
          <span>Hạn mức tháng</span>
          <span className="font-mono text-headline-sm">{budget ? formatUsd(budget) : 'Chưa đặt'}</span>
        </div>
        {budget ? (
          <>
            <ProgressBar className="mt-2" value={percent(monthCost, budget)} tone={monthCost > budget * 0.8 ? 'bg-warning' : 'bg-brand'} />
            <p className="mt-1 text-body-sm text-outline">Đã dùng {formatUsd(monthCost)} — còn {formatUsd(Math.max(0, budget - monthCost))}</p>
          </>
        ) : null}
      </div>
      <div className="grid gap-1 text-body-sm text-on-surface-variant">
        <p>• Ngân sách mỗi run: <b className="font-mono text-on-surface">{formatUsd(settings.limits.default_run_budget_usd)}</b></p>
        <p>• Số lần thử lại mỗi tác vụ: <b className="font-mono text-on-surface">{settings.limits.max_task_attempts}</b></p>
        <p>• Vòng sửa lỗi QA ↔ Reviewer tối đa: <b className="font-mono text-on-surface">{settings.limits.max_fix_iterations}</b></p>
      </div>
      <form onSubmit={save} className="flex gap-2">
        <Input type="number" min={0} step="0.01" value={value} onChange={(e) => setValue(e.target.value)} placeholder="USD / tháng" className="font-mono" />
        <Button type="submit" disabled={saving}>Lưu</Button>
      </form>
    </Section>
  )
}
