import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import {
  Bot,
  CircleCheck,
  FileCode2,
  FileText,
  Folder,
  FolderTree,
  GitBranch,
  History,
  LayoutDashboard,
  ListChecks,
  Loader2,
  Radio,
  Sparkles,
  TriangleAlert,
  X,
} from 'lucide-react'
import { toast } from 'sonner'

import { Ring } from '@/components/common/charts'
import { Markdown } from '@/components/common/markdown'
import { AgentAvatar, EmptyState, ErrorNote, LoadingBlock, ProgressBar, Section } from '@/components/common/page'
import { Pill, StatusBadge } from '@/components/common/status-badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { EventLogLine } from '@/features/history/event-item'
import { TaskTable } from '@/features/tasks/task-table'
import { useApi } from '@/hooks/use-api'
import { useShell } from '@/hooks/use-shell'
import { api, errorMessage } from '@/lib/api'
import { formatBytes, formatCompact, formatRelative, formatUsd, percent } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { FileContent, Project, RunDetail, Task } from '@/types/api'

type Tab = 'overview' | 'tasks' | 'files' | 'history'

const TABS: { value: Tab; label: string; icon: typeof Bot }[] = [
  { value: 'overview', label: 'Tổng quan', icon: LayoutDashboard },
  { value: 'tasks', label: 'Tác vụ', icon: ListChecks },
  { value: 'files', label: 'Tệp tin & Mã nguồn', icon: FolderTree },
  { value: 'history', label: 'Lịch sử & Logs', icon: History },
]

/** /workspace → workspace of the project picked in the top bar. */
export function CurrentWorkspaceRedirect() {
  const { currentProject, projects } = useShell()
  if (currentProject) return <Navigate to={`/projects/${currentProject.id}`} replace />
  return (
    <EmptyState icon={FolderTree} title={projects.length ? 'Chọn một dự án' : 'Chưa có dự án nào'}>
      <Link to="/projects" className="text-brand hover:underline">Đi tới trang Dự án</Link> để tạo hoặc chọn dự án.
    </EmptyState>
  )
}

export function WorkspacePage() {
  const projectId = Number(useParams().projectId)
  const { setCurrentProjectId } = useShell()
  const [tab, setTab] = useState<Tab>('overview')
  const project = useApi(() => api.projects.get(projectId), [projectId], ['projects'])
  const runs = useApi(() => api.runs.list({ project_id: projectId, limit: 20 }), [projectId], ['events'])
  const latestRunId = runs.data?.[0]?.id
  const run = useApi<RunDetail | null>(
    () => (latestRunId ? api.runs.get(latestRunId) : Promise.resolve(null)),
    [latestRunId],
    latestRunId ? [`runs:${latestRunId}`] : [],
  )

  useEffect(() => {
    if (project.data) setCurrentProjectId(project.data.id)
  }, [project.data, setCurrentProjectId])

  if (project.error) return <ErrorNote message={project.error} />
  if (!project.data) return <LoadingBlock className="h-96" />
  const p = project.data

  return (
    <div className="grid gap-6">
      <div className="panel grid gap-4 p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="font-mono text-label-sm text-outline">
              <Link to="/projects" className="hover:text-on-surface">Dự án</Link> / {p.name} / <span className="text-telemetry">Workspace</span>
            </p>
            <h1 className="mt-1 text-headline-xl font-semibold md:text-display">{p.name}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="flex items-center gap-1.5 rounded bg-surface-lowest px-2 py-1 font-mono text-label-sm text-telemetry">
                <GitBranch className="size-3.5" /> workspaces/{p.workspace_dir}
              </span>
              <StatusBadge status={p.status} />
              {run.data && <Pill tone="info">Run #{run.data.id} · {percent(run.data.tasks_completed, run.data.tasks_total)}%</Pill>}
            </div>
            {p.description && <p className="mt-2 max-w-3xl text-body-md text-on-surface-variant">{p.description}</p>}
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto border-t border-white/[0.06] pt-3">
          {TABS.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              type="button"
              onClick={() => setTab(value)}
              className={cn(
                'flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-label-md',
                tab === value ? 'bg-surface-high text-on-surface' : 'text-on-surface-variant hover:text-on-surface',
              )}
            >
              <Icon className="size-4" /> {label}
            </button>
          ))}
        </nav>
      </div>

      {tab === 'overview' && <Overview project={p} run={run.data} />}
      {tab === 'tasks' && <TaskTable params={{ project_id: p.id }} />}
      {tab === 'files' && <FileBrowser project={p} />}
      {tab === 'history' && <ProjectLog projectId={p.id} />}
    </div>
  )
}

function Overview({ project, run }: { project: Project; run: RunDetail | null }) {
  const tasks = run?.tasks ?? []
  const count = (s: Task['status']) => tasks.filter((t) => t.status === s).length
  const pct = run ? percent(run.tasks_completed, run.tasks_total) : 0
  const tokens = tasks.reduce((s, t) => s + t.input_tokens + t.output_tokens, 0)
  const cost = tasks.reduce((s, t) => s + t.cost_usd, 0)

  return (
    <div className="grid gap-6">
      <RequestBox project={project} run={run} />
      {run?.summary && (
        <Section title="Kết quả từ AI Manager" icon={Sparkles}>
          <Markdown>{run.summary}</Markdown>
        </Section>
      )}
      {run?.error && <ErrorNote message={`Run #${run.id}: ${run.error}`} />}
      <div className="grid gap-6 xl:grid-cols-[300px_1fr_380px]">
        <Section title="Tiến độ run mới nhất" className="content-start">
          {!run ? (
            <EmptyState icon={Sparkles} title="Chưa có luồng thực thi">Gửi yêu cầu cho AI Manager để bắt đầu.</EmptyState>
          ) : (
            <>
              <div className="flex justify-center rounded-md bg-surface-lowest p-4">
                <Ring value={pct}>
                  <span className="text-headline-xl font-semibold">{pct}%</span>
                  <span className="font-mono text-label-sm text-outline">hoàn thành</span>
                </Ring>
              </div>
              <div className="grid gap-2 text-label-md">
                {[
                  ['Hoàn thành', count('completed'), 'text-success'],
                  ['Đang xử lý', count('running'), 'text-processing'],
                  ['Chờ duyệt', count('waiting_approval'), 'text-warning'],
                  ['Lỗi', count('failed'), 'text-danger'],
                ].map(([label, n, tone]) => (
                  <div key={label as string} className="flex justify-between rounded-md bg-surface-container px-3 py-2">
                    <span>{label}</span>
                    <span className={cn('font-mono', tone as string)}>{n}</span>
                  </div>
                ))}
              </div>
              <div className="rounded-md bg-surface-container p-3">
                <div className="flex justify-between text-label-md">
                  <span>Tokens tiêu thụ</span>
                  <span className="font-mono text-telemetry">{formatUsd(cost, 4)}</span>
                </div>
                <p className="mt-1 font-mono text-label-sm text-outline">
                  {formatCompact(tokens)} tokens
                  {run.budget_usd ? ` · ngân sách ${formatUsd(run.budget_usd)}` : ''}
                </p>
                {run.budget_usd ? <ProgressBar className="mt-2" value={percent(cost, run.budget_usd)} /> : null}
              </div>
            </>
          )}
        </Section>

        <Section title="Trục thời gian phát triển" icon={Radio} actions={run && <StatusBadge status={run.status} />}>
          {!run || tasks.length === 0 ? (
            <EmptyState icon={ListChecks} title="Chưa có tác vụ">AI Manager sẽ phân rã yêu cầu thành các tác vụ hiển thị tại đây.</EmptyState>
          ) : (
            <ol className="relative grid gap-3 border-l border-white/10 pl-6">
              {tasks.map((t, i) => (
                <li key={t.id} className="relative">
                  <span
                    className={cn(
                      'absolute top-3 -left-[33px] flex size-5 items-center justify-center rounded-full border-2 border-surface',
                      t.status === 'completed' ? 'bg-telemetry' : t.status === 'running' ? 'bg-processing' : t.status === 'failed' ? 'bg-danger' : 'bg-surface-highest',
                    )}
                  >
                    {t.status === 'completed' && <CircleCheck className="size-3 text-surface" />}
                    {t.status === 'running' && <Loader2 className="size-3 animate-spin text-surface" />}
                  </span>
                  <div className={cn('panel-raised p-3', t.status === 'running' && 'border-brand-strong/60', t.status === 'pending' && 'opacity-60')}>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <h3 className="text-headline-sm font-semibold">{i + 1}. {t.title}</h3>
                      <StatusBadge status={t.status} />
                    </div>
                    {t.description && <p className="mt-1 line-clamp-2 text-body-sm text-on-surface-variant">{t.description}</p>}
                    <p className="mt-2 flex items-center gap-2 font-mono text-label-sm text-outline">
                      <AgentAvatar code={t.agent_code} size="sm" /> {t.agent_name} · {formatRelative(t.updated_at)}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Section>

        <FileBrowser project={project} compact />
      </div>
      <ProjectLog projectId={project.id} />
    </div>
  )
}

const ACTIVE_RUN: RunDetail['status'][] = ['pending', 'planning', 'running', 'waiting_approval']

function RequestBox({ project, run }: { project: Project; run: RunDetail | null }) {
  const settings = useApi(() => api.settings.get(), [], ['settings'])
  const [text, setText] = useState('')
  const [budget, setBudget] = useState('')
  const [busy, setBusy] = useState(false)
  const active = run && ACTIVE_RUN.includes(run.status)
  const configured = settings.data?.llm_configured

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      const created = await api.runs.create(project.id, {
        request_text: text.trim(),
        budget_usd: budget.trim() ? Number(budget) : null,
      })
      toast.success(`Đã gửi yêu cầu — Run #${created.id}`)
      setText('')
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const cancel = async () => {
    if (!run) return
    try {
      await api.runs.cancel(run.id)
      toast.success('Đã gửi yêu cầu hủy run')
    } catch (err) {
      toast.error(errorMessage(err))
    }
  }

  return (
    <form onSubmit={submit} className="panel flex flex-col gap-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-headline-sm font-semibold">
          <Sparkles className="size-4 text-brand" /> Gửi yêu cầu cho AI Manager
        </h2>
        {active ? (
          <Pill tone="processing" pulse>Run #{run.id} đang chạy</Pill>
        ) : configured === false ? (
          <Pill tone="warning">Chưa cấu hình LLM_API_KEY</Pill>
        ) : configured ? (
          <Pill tone="success">{settings.data?.llm_endpoint}</Pill>
        ) : null}
      </div>
      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        minLength={10}
        maxLength={10000}
        disabled={!!active}
        placeholder="Mô tả phần mềm bạn muốn đội AI xây dựng, ví dụ: API quản lý thư viện cho phép thêm sách, mượn và trả sách, kèm trang web đơn giản…"
        className="bg-surface-lowest"
      />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-body-sm text-outline">
          <TriangleAlert className="size-4 text-warning" />
          {configured === false
            ? 'Thêm LLM_API_KEY vào backend/.env rồi khởi động lại backend.'
            : 'AI Manager lập kế hoạch → BA → Architect → Backend ∥ Frontend → QA ↔ Reviewer. Chạy test cần bạn phê duyệt.'}
        </p>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            step="0.01"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            placeholder={`Ngân sách $ (mặc định ${settings.data?.limits.default_run_budget_usd ?? '—'})`}
            className="w-52 rounded-md bg-surface-lowest px-3 py-1.5 font-mono text-label-sm outline-none placeholder:text-outline"
          />
          {active ? (
            <Button type="button" variant="destructive" onClick={cancel}>
              <X /> Hủy run
            </Button>
          ) : (
            <Button type="submit" disabled={busy || !configured || text.trim().length < 10}>
              <Sparkles /> {busy ? 'Đang gửi…' : 'Bắt đầu phát triển bằng AI'}
            </Button>
          )}
        </div>
      </div>
    </form>
  )
}

function FileBrowser({ project, compact }: { project: Project; compact?: boolean }) {
  const files = useApi(() => api.projects.files(project.id), [project.id], ['events'])
  const [selected, setSelected] = useState<string | null>(null)
  const [content, setContent] = useState<FileContent | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileCount = useMemo(() => files.data?.filter((f) => !f.is_dir).length ?? 0, [files.data])

  useEffect(() => {
    if (!selected) return
    setContent(null)
    setError(null)
    api.projects.file(project.id, selected).then(setContent).catch((err) => setError(errorMessage(err)))
  }, [project.id, selected])

  return (
    <Section title="Tài liệu & Tệp sinh bởi AI" icon={FileCode2} actions={<span className="font-mono text-label-sm text-outline">{fileCount} tệp</span>} className="content-start">
      <ErrorNote message={files.error} />
      {files.data?.length === 0 ? (
        <EmptyState icon={Folder} title="Workspace đang trống">Các agent sẽ ghi tài liệu, code và test vào workspaces/{project.workspace_dir}.</EmptyState>
      ) : (
        <div className={cn('grid gap-3', !compact && 'lg:grid-cols-[320px_1fr]')}>
          <ul className="grid max-h-96 content-start gap-0.5 overflow-auto">
            {files.data?.map((f) => (
              <li key={f.path}>
                <button
                  type="button"
                  disabled={f.is_dir}
                  onClick={() => setSelected(f.path)}
                  style={{ paddingLeft: `${f.path.split('/').length * 10}px` }}
                  className={cn(
                    'flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-label-md',
                    f.is_dir ? 'text-outline' : 'hover:bg-surface-high',
                    selected === f.path && 'bg-surface-high text-brand',
                  )}
                >
                  {f.is_dir ? <Folder className="size-4 shrink-0" /> : <FileText className="size-4 shrink-0" />}
                  <span className="truncate">{f.path.split('/').pop()}</span>
                  {!f.is_dir && <span className="ml-auto font-mono text-label-sm text-outline">{formatBytes(f.size)}</span>}
                </button>
              </li>
            ))}
          </ul>
          {selected && (
            <div className="min-w-0 rounded-md bg-surface-lowest">
              <div className="flex justify-between border-b border-white/[0.06] px-3 py-2 font-mono text-label-sm">
                <span className="truncate text-on-surface">{selected}</span>
                {content && <span className="text-outline">{formatBytes(content.size)}{content.truncated && ' (cắt bớt)'}</span>}
              </div>
              <ErrorNote message={error} />
              <pre className="max-h-96 overflow-auto p-3 font-mono text-code text-on-surface-variant">{content?.content ?? ''}</pre>
            </div>
          )}
        </div>
      )}
    </Section>
  )
}

function ProjectLog({ projectId }: { projectId: number }) {
  const events = useApi(() => api.events.list({ project_id: projectId, limit: 100 }), [projectId], ['events'])
  return (
    <Section
      title={<span className="flex items-center gap-2"><span className="eyebrow">Live agent stream</span></span>}
      actions={<span className="font-mono text-label-sm text-outline">{events.data?.total ?? 0} sự kiện</span>}
    >
      <ErrorNote message={events.error} />
      <div className="max-h-[420px] overflow-auto rounded-md bg-surface-lowest p-3">
        {events.data?.items.length ? (
          <div className="grid gap-1.5">
            {[...events.data.items].reverse().map((e) => (
              <EventLogLine key={e.id} event={e} />
            ))}
          </div>
        ) : (
          <p className="font-mono text-code text-outline">$ chưa có sự kiện nào cho dự án này…</p>
        )}
      </div>
    </Section>
  )
}
