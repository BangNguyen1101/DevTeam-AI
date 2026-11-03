import { useEffect, useState, type FormEvent } from 'react'
import { Bot, Database, KeyRound, Plus, Receipt, RotateCcw, Save, ShieldCheck, SlidersHorizontal, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { AgentAvatar, ErrorNote, LoadingBlock, PageHeader, Section, StatCard } from '@/components/common/page'
import { Pill } from '@/components/common/status-badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AgentEditDialog } from '@/features/agents/agent-edit-dialog'
import { useApi } from '@/hooks/use-api'
import { useShell } from '@/hooks/use-shell'
import { api, errorMessage } from '@/lib/api'
import { formatInt } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { Limits, ModelPrice, Settings } from '@/types/api'

type Tab = 'models' | 'limits' | 'pricing' | 'system'

const TABS: { value: Tab; label: string; icon: typeof Bot }[] = [
  { value: 'models', label: '1. Cấu hình Model AI', icon: Bot },
  { value: 'limits', label: '2. Giới hạn & Guardrails', icon: ShieldCheck },
  { value: 'pricing', label: '3. Bảng giá model', icon: Receipt },
  { value: 'system', label: '4. Hệ thống', icon: Database },
]

export function SettingsPage() {
  const [tab, setTab] = useState<Tab>('models')
  const settings = useApi(() => api.settings.get(), [], ['settings'])
  const agents = useApi(() => api.agents.list(), [], ['agents'])
  const { health } = useShell()

  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow={<><span className="rounded bg-telemetry/15 px-1.5 text-telemetry">Local</span> / Infrastructure governance</>}
        title="Cài đặt Nền tảng & Cấu hình AI"
        description="Mô hình ngôn ngữ cho từng agent, giới hạn an toàn của Workflow Engine và bảng giá dùng để tính chi phí."
      />

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard label="Agent đang bật" value={agents.data ? `${agents.data.filter((a) => a.is_enabled).length}/${agents.data.length}` : '—'} icon={Bot} />
        <StatCard
          label="OpenAI API key"
          value={settings.data ? (settings.data.openai_key_configured ? 'Đã cấu hình' : 'Chưa có') : '—'}
          icon={KeyRound}
          accent={settings.data?.openai_key_configured ? 'text-success' : 'text-warning'}
          hint="Đọc từ backend/.env, không gửi về trình duyệt"
        />
        <StatCard label="Guardrails" value={settings.data ? `${settings.data.limits.max_task_attempts} lần thử` : '—'} icon={ShieldCheck} hint={settings.data ? `Timeout lệnh ${settings.data.limits.command_timeout_seconds}s` : undefined} />
        <StatCard label="Model có bảng giá" value={settings.data ? Object.keys(settings.data.pricing).length : '—'} icon={Receipt} />
      </div>

      <nav className="panel flex gap-1 overflow-x-auto p-1.5">
        {TABS.map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            type="button"
            onClick={() => setTab(value)}
            className={cn('flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-label-md', tab === value ? 'bg-surface-high text-on-surface' : 'text-on-surface-variant hover:text-on-surface')}
          >
            <Icon className="size-4" /> {label}
          </button>
        ))}
      </nav>

      <ErrorNote message={settings.error ?? agents.error} />
      {!settings.data || !agents.data ? (
        <LoadingBlock className="h-64" />
      ) : tab === 'models' ? (
        <Section title="Model theo từng agent" icon={Bot} description="Tên model phải là model mà API key OpenAI của bạn có quyền dùng.">
          <div className="grid gap-2">
            {agents.data.map((a) => (
              <div key={a.id} className="panel-raised flex flex-wrap items-center gap-3 p-3">
                <AgentAvatar code={a.code} />
                <div className="min-w-48 flex-1">
                  <p className="text-headline-sm font-semibold">{a.name}</p>
                  <p className="font-mono text-label-sm text-outline">{a.code}</p>
                </div>
                <span className="rounded bg-surface-lowest px-2 py-1 font-mono text-label-sm text-telemetry">{a.model}</span>
                <span className="font-mono text-label-sm text-outline">max {formatInt(a.max_output_tokens)} tok</span>
                {a.is_enabled ? <Pill tone="success">Bật</Pill> : <Pill>Tắt</Pill>}
                <AgentEditDialog agent={a} />
              </div>
            ))}
          </div>
        </Section>
      ) : tab === 'limits' ? (
        <LimitsForm settings={settings.data} />
      ) : tab === 'pricing' ? (
        <PricingForm settings={settings.data} models={[...new Set(agents.data.map((a) => a.model))]} />
      ) : (
        <Section title="Trạng thái hệ thống" icon={Database}>
          <div className="grid gap-2 font-mono text-label-md">
            {[
              ['Database', health?.database.ok ? 'SQL Server — online' : 'Không kết nối được'],
              ['Phiên bản SQL Server', health?.database.server_version ?? '—'],
              ['Migration hiện tại', health?.database.migration ?? '—'],
              ['OpenAI API key', settings.data.openai_key_configured ? 'Đã cấu hình trong backend/.env' : 'Chưa cấu hình — thêm OPENAI_API_KEY vào backend/.env'],
              ['Xác thực người dùng', 'Chế độ 1 người dùng (chưa bật đăng nhập)'],
            ].map(([k, v]) => (
              <div key={k} className="flex flex-wrap justify-between gap-2 rounded bg-surface-container px-3 py-2">
                <span className="text-outline">{k}</span>
                <span>{v}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}

function NumberField({ id, label, hint, value, onChange, min, max, step = 1 }: {
  id: string
  label: string
  hint: string
  value: string
  onChange: (v: string) => void
  min: number
  max: number
  step?: number
}) {
  return (
    <div className="grid gap-1.5 rounded-md bg-surface-container p-3">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} type="number" min={min} max={max} step={step} value={value} onChange={(e) => onChange(e.target.value)} className="font-mono" />
      <p className="text-body-sm text-outline">{hint}</p>
    </div>
  )
}

function LimitsForm({ settings }: { settings: Settings }) {
  const toForm = (l: Limits) => ({
    max_task_attempts: String(l.max_task_attempts),
    max_fix_iterations: String(l.max_fix_iterations),
    command_timeout_seconds: String(l.command_timeout_seconds),
    default_run_budget_usd: String(l.default_run_budget_usd),
    monthly_budget_usd: l.monthly_budget_usd?.toString() ?? '',
  })
  const [form, setForm] = useState(toForm(settings.limits))
  const [saving, setSaving] = useState(false)
  useEffect(() => setForm(toForm(settings.limits)), [settings.limits])
  const set = (k: keyof typeof form) => (v: string) => setForm((f) => ({ ...f, [k]: v }))

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.settings.updateLimits({
        max_task_attempts: Number(form.max_task_attempts),
        max_fix_iterations: Number(form.max_fix_iterations),
        command_timeout_seconds: Number(form.command_timeout_seconds),
        default_run_budget_usd: Number(form.default_run_budget_usd),
        monthly_budget_usd: form.monthly_budget_usd.trim() ? Number(form.monthly_budget_usd) : null,
      })
      toast.success('Đã lưu giới hạn')
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title="Rào chắn an toàn & giới hạn thực thi" icon={SlidersHorizontal} description="Workflow Engine kiểm tra các giới hạn này trước mỗi tác vụ và mỗi lệnh.">
      <form onSubmit={submit} className="grid gap-4">
        <div className="grid gap-3 md:grid-cols-2">
          <NumberField id="att" label="Số lần thử tối đa mỗi tác vụ" hint="Tác vụ lỗi quá số lần này sẽ chuyển sang Thất bại." value={form.max_task_attempts} onChange={set('max_task_attempts')} min={1} max={10} />
          <NumberField id="fix" label="Vòng sửa lỗi QA ↔ Reviewer tối đa" hint="Chặn vòng lặp sửa lỗi vô hạn." value={form.max_fix_iterations} onChange={set('max_fix_iterations')} min={0} max={10} />
          <NumberField id="timeout" label="Timeout mỗi lệnh (giây)" hint="Execution Engine dừng lệnh chạy quá thời gian." value={form.command_timeout_seconds} onChange={set('command_timeout_seconds')} min={5} max={1800} />
          <NumberField id="run-budget" label="Ngân sách mặc định mỗi run (USD)" hint="Run dừng lại khi chi phí vượt ngưỡng." value={form.default_run_budget_usd} onChange={set('default_run_budget_usd')} min={0} max={1000} step={0.01} />
          <NumberField id="month-budget" label="Ngân sách tháng (USD, để trống = không giới hạn)" hint="Hiển thị cảnh báo ở trang Phân tích chi phí." value={form.monthly_budget_usd} onChange={set('monthly_budget_usd')} min={0} max={100000} step={0.01} />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={() => setForm(toForm(settings.limits))}><RotateCcw /> Hoàn tác</Button>
          <Button type="submit" disabled={saving}><Save /> Lưu thay đổi</Button>
        </div>
      </form>
    </Section>
  )
}

function PricingForm({ settings, models }: { settings: Settings; models: string[] }) {
  type Row = { model: string; input: string; cached: string; output: string }
  const toRows = (p: Record<string, ModelPrice>): Row[] => {
    const names = [...new Set([...Object.keys(p), ...models])]
    return names.map((m) => ({
      model: m,
      input: p[m]?.input_per_1m.toString() ?? '',
      cached: p[m]?.cached_input_per_1m.toString() ?? '',
      output: p[m]?.output_per_1m.toString() ?? '',
    }))
  }
  const [rows, setRows] = useState<Row[]>(toRows(settings.pricing))
  const [saving, setSaving] = useState(false)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => setRows(toRows(settings.pricing)), [settings.pricing])
  const update = (i: number, k: keyof Row, v: string) => setRows((r) => r.map((row, j) => (j === i ? { ...row, [k]: v } : row)))

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const pricing: Record<string, ModelPrice> = {}
    for (const r of rows) {
      if (!r.model.trim() || (!r.input.trim() && !r.output.trim())) continue
      pricing[r.model.trim()] = { input_per_1m: Number(r.input || 0), cached_input_per_1m: Number(r.cached || 0), output_per_1m: Number(r.output || 0) }
    }
    setSaving(true)
    try {
      await api.settings.updatePricing(pricing)
      toast.success('Đã lưu bảng giá')
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title="Bảng giá model (USD / 1 triệu token)" icon={Receipt} description="Nhập theo bảng giá chính thức của OpenAI. Model chưa có giá sẽ được tính $0 và được cảnh báo ở trang Phân tích.">
      <form onSubmit={submit} className="grid gap-3">
        <div className="hidden grid-cols-[1fr_120px_120px_120px_40px] gap-2 px-1 md:grid">
          {['Model', 'Input', 'Cached input', 'Output', ''].map((h) => <span key={h} className="micro-label">{h}</span>)}
        </div>
        {rows.map((r, i) => (
          <div key={i} className="grid grid-cols-2 gap-2 rounded-md bg-surface-container p-2 md:grid-cols-[1fr_120px_120px_120px_40px]">
            <Input value={r.model} onChange={(e) => update(i, 'model', e.target.value)} placeholder="tên model" className="col-span-2 font-mono md:col-span-1" />
            <Input type="number" min={0} step="0.0001" value={r.input} onChange={(e) => update(i, 'input', e.target.value)} placeholder="input" className="font-mono" />
            <Input type="number" min={0} step="0.0001" value={r.cached} onChange={(e) => update(i, 'cached', e.target.value)} placeholder="cached" className="font-mono" />
            <Input type="number" min={0} step="0.0001" value={r.output} onChange={(e) => update(i, 'output', e.target.value)} placeholder="output" className="font-mono" />
            <Button type="button" size="icon" variant="ghost" onClick={() => setRows((rs) => rs.filter((_, j) => j !== i))} aria-label="Xóa dòng"><Trash2 /></Button>
          </div>
        ))}
        <div className="flex flex-wrap justify-between gap-2">
          <Button type="button" variant="secondary" onClick={() => setRows((rs) => [...rs, { model: '', input: '', cached: '', output: '' }])}><Plus /> Thêm model</Button>
          <Button type="submit" disabled={saving}><Save /> Lưu bảng giá</Button>
        </div>
      </form>
    </Section>
  )
}
