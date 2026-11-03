import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Activity, Copy, ListTree, RefreshCw, Search, TriangleAlert, X } from 'lucide-react'
import { toast } from 'sonner'

import { AgentAvatar, EmptyState, ErrorNote, LoadingBlock, PageHeader, StatCard } from '@/components/common/page'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useApi } from '@/hooks/use-api'
import { useShell } from '@/hooks/use-shell'
import { AGENT_ORDER } from '@/lib/agents'
import { api, errorMessage } from '@/lib/api'
import { formatDate, formatInt } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { ExecutionEvent } from '@/types/api'

import { EventLogLine, eventTone } from './event-item'

const PAGE = 50

export function HistoryPage() {
  const { projects } = useShell()
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const [search, setSearch] = useState(q)
  const [projectId, setProjectId] = useState<number | undefined>()
  const [agent, setAgent] = useState<string | undefined>()
  const [extra, setExtra] = useState<ExecutionEvent[]>([])
  const [nextBefore, setNextBefore] = useState<number | null>(null)
  const [selectedRun, setSelectedRun] = useState<number | null>(null)

  const page = useApi(() => api.events.list({ q, project_id: projectId, agent_code: agent, limit: PAGE }), [q, projectId, agent], ['events'])
  const runs = useApi(() => api.runs.list({ limit: 500 }), [], ['events'])

  useEffect(() => {
    setExtra([])
    setNextBefore(page.data?.next_before_id ?? null)
  }, [page.data])
  useEffect(() => setSearch(q), [q])

  const items = [...(page.data?.items ?? []), ...extra]
  const traceRun = selectedRun ?? items[0]?.run_id ?? null

  const loadMore = async () => {
    if (!nextBefore) return
    try {
      const more = await api.events.list({ q, project_id: projectId, agent_code: agent, limit: PAGE, before_id: nextBefore })
      setExtra((e) => [...e, ...more.items])
      setNextBefore(more.next_before_id)
    } catch (err) {
      toast.error(errorMessage(err))
    }
  }

  const finished = runs.data?.filter((r) => r.status === 'completed' || r.status === 'failed') ?? []
  const succeeded = finished.filter((r) => r.status === 'completed').length
  const failedRuns = finished.length - succeeded
  const tokens = runs.data?.reduce((s, r) => s + r.total_input_tokens + r.total_output_tokens, 0) ?? 0

  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow={<><span className="rounded bg-brand-strong/20 px-1.5 text-brand">Telemetry</span> execution_events · SQL Server</>}
        title="Lịch sử Thực thi & Nhật ký Hệ thống"
        description="Mọi sự kiện của các luồng thực thi: agent bắt đầu/kết thúc tác vụ, lệnh gọi công cụ, lỗi, phê duyệt."
        actions={
          <Button variant="secondary" onClick={page.reload}>
            <RefreshCw /> Làm mới
          </Button>
        }
      />

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard label="Tỉ lệ run thành công" value={finished.length ? `${((succeeded / finished.length) * 100).toFixed(1)}%` : '—'} icon={Activity} hint={`${succeeded}/${finished.length} run đã kết thúc`} />
        <StatCard label="Tổng sự kiện" value={formatInt(page.data?.total ?? 0)} icon={ListTree} hint="Khớp bộ lọc hiện tại" />
        <StatCard label="Run thất bại" value={failedRuns} icon={TriangleAlert} accent={failedRuns ? 'text-danger' : 'text-success'} hint="Toàn bộ thời gian" />
        <StatCard label="Token tiêu thụ" value={formatInt(tokens)} icon={Activity} hint={`${runs.data?.length ?? 0} run`} />
      </div>

      <div className="panel flex flex-wrap items-center gap-3 p-3">
        <form
          className="flex min-w-60 flex-1 items-center gap-2 rounded-md bg-surface-lowest px-3 py-2"
          onSubmit={(e) => {
            e.preventDefault()
            setParams(search.trim() ? { q: search.trim() } : {})
          }}
        >
          <Search className="size-4 text-outline" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm trong nội dung sự kiện… (Enter)" className="w-full bg-transparent text-label-md outline-none placeholder:text-outline" />
          {q && (
            <button type="button" onClick={() => setParams({})} aria-label="Xóa tìm kiếm"><X className="size-4 text-outline" /></button>
          )}
        </form>
        <select value={projectId ?? ''} onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : undefined)} className="rounded-md bg-surface-lowest px-3 py-2 text-label-md outline-none">
          <option value="">Mọi dự án</option>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select value={agent ?? ''} onChange={(e) => setAgent(e.target.value || undefined)} className="rounded-md bg-surface-lowest px-3 py-2 text-label-md outline-none">
          <option value="">Mọi AI Agent</option>
          {AGENT_ORDER.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
      </div>

      <ErrorNote message={page.error} />
      {!page.data ? (
        <LoadingBlock className="h-96" />
      ) : items.length === 0 ? (
        <EmptyState icon={ListTree} title={q ? `Không có sự kiện nào khớp “${q}”` : 'Chưa có sự kiện thực thi nào'}>
          Nhật ký được ghi tự động khi các agent làm việc.
        </EmptyState>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[1fr_440px]">
          <div className="panel overflow-hidden">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-white/[0.06] hover:bg-transparent">
                    {['Mã', 'Dự án', 'Agent', 'Sự kiện', 'Thời gian'].map((h) => <TableHead key={h} className="micro-label">{h}</TableHead>)}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((e) => (
                    <TableRow key={e.id} onClick={() => setSelectedRun(e.run_id)} className={cn('cursor-pointer border-white/[0.06]', traceRun === e.run_id && 'bg-surface-container')}>
                      <TableCell className="font-mono text-label-sm text-telemetry">#EVT-{e.id}<br /><span className="text-outline">Run #{e.run_id}</span></TableCell>
                      <TableCell className="text-label-md">{e.project_name}</TableCell>
                      <TableCell>{e.agent_code ? <span className="flex items-center gap-2"><AgentAvatar code={e.agent_code} size="sm" /><span className="text-label-md">{e.agent_code}</span></span> : <span className="text-outline">system</span>}</TableCell>
                      <TableCell className="max-w-md whitespace-normal">
                        <span className={cn('font-mono text-label-sm', eventTone(e.event_type))}>{e.event_type}</span>
                        <p className="text-body-sm">{e.message}</p>
                      </TableCell>
                      <TableCell className="font-mono text-label-sm whitespace-nowrap text-outline">{formatDate(e.created_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <div className="flex items-center justify-between border-t border-white/[0.06] p-3 font-mono text-label-sm text-outline">
              <span>Hiển thị {items.length} / {formatInt(page.data.total)} bản ghi</span>
              {nextBefore && <Button size="sm" variant="secondary" onClick={loadMore}>Tải thêm</Button>}
            </div>
          </div>
          {traceRun && <TraceViewer runId={traceRun} />}
        </div>
      )}
    </div>
  )
}

function TraceViewer({ runId }: { runId: number }) {
  const trace = useApi(() => api.events.list({ run_id: runId, limit: 200 }), [runId], ['events', `runs:${runId}`])
  const lines = [...(trace.data?.items ?? [])].reverse()
  const copy = () => {
    navigator.clipboard
      .writeText(lines.map((e) => `[${e.created_at}] [${e.event_type}] ${e.agent_code ?? 'system'}: ${e.message}`).join('\n'))
      .then(() => toast.success('Đã sao chép log'))
      .catch(() => toast.error('Không sao chép được'))
  }
  return (
    <div className="panel flex max-h-[720px] flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/[0.06] p-3">
        <div className="flex items-center gap-2">
          <span className="flex gap-1"><span className="size-2.5 rounded-full bg-danger/70" /><span className="size-2.5 rounded-full bg-warning/70" /><span className="size-2.5 rounded-full bg-success/70" /></span>
          <span className="font-mono text-label-md">Trace viewer · Run #{runId}</span>
        </div>
        <Button size="sm" variant="ghost" onClick={copy}><Copy /> Sao chép</Button>
      </div>
      <div className="grid flex-1 content-start gap-2 overflow-auto bg-surface-lowest p-3">
        <ErrorNote message={trace.error} />
        {lines.map((e) => <EventLogLine key={e.id} event={e} />)}
      </div>
    </div>
  )
}
