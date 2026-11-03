import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Archive, ArchiveRestore, Coins, FolderGit2, LayoutGrid, ListChecks, Plus, Rocket, Search, SquareTerminal, Table2 } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState, ErrorNote, LoadingBlock, PageHeader, ProgressBar, Section, Segmented, StatCard } from '@/components/common/page'
import { Pill, StatusBadge } from '@/components/common/status-badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useApi } from '@/hooks/use-api'
import { useShell } from '@/hooks/use-shell'
import { api, errorMessage } from '@/lib/api'
import { formatCompact, formatRelative, formatUsd, percent } from '@/lib/format'
import type { Project, ProjectStatus } from '@/types/api'

import { CreateProjectDialog } from './create-project-dialog'

type View = 'cards' | 'table'

interface Row {
  project: Project
  runStatus: string | null
  runId: number | null
  done: number
  total: number
  tokens: number
  cost: number
}

export function ProjectsPage() {
  const { summary, setCurrentProjectId } = useShell()
  const [view, setView] = useState<View>('cards')
  const [status, setStatus] = useState<ProjectStatus | undefined>('active')
  const [query, setQuery] = useState('')
  const projects = useApi(() => api.projects.list(status), [status], ['projects'])
  const usage = useApi(() => api.usage.summary(365), [], ['events'])

  const rows: Row[] = useMemo(() => {
    const progress = new Map(summary?.projects.map((p) => [p.project_id, p]))
    const spend = new Map(usage.data?.by_project.map((p) => [p.project_id, p]))
    const q = query.trim().toLowerCase()
    return (projects.data ?? [])
      .filter((p) => !q || p.name.toLowerCase().includes(q) || p.description?.toLowerCase().includes(q) || `prj-${p.id}`.includes(q))
      .map((p) => {
        const pr = progress.get(p.id)
        const sp = spend.get(p.id)
        return {
          project: p,
          runStatus: pr?.latest_run_status ?? null,
          runId: pr?.latest_run_id ?? null,
          done: pr?.tasks_completed ?? 0,
          total: pr?.tasks_total ?? 0,
          tokens: sp?.total_tokens ?? 0,
          cost: sp?.cost_usd ?? 0,
        }
      })
  }, [projects.data, summary, usage.data, query])

  const toggleArchive = async (project: Project) => {
    const next: ProjectStatus = project.status === 'active' ? 'archived' : 'active'
    try {
      await api.projects.update(project.id, { status: next })
      toast.success(next === 'archived' ? 'Đã lưu trữ dự án' : 'Đã khôi phục dự án')
    } catch (err) {
      toast.error(errorMessage(err))
    }
  }

  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow={<><span className="size-1.5 rounded-full bg-telemetry" /> Danh mục dự án phần mềm</>}
        title="Quản lý Dự án Phát triển Phần mềm"
        description="Theo dõi các dự án, tiến độ luồng thực thi mới nhất và chi phí token do đội AI tiêu thụ."
        actions={
          <>
            <Segmented
              value={view}
              onChange={setView}
              options={[
                { value: 'cards', label: <span className="flex items-center gap-1.5"><LayoutGrid className="size-3.5" /> Dạng thẻ</span> },
                { value: 'table', label: <span className="flex items-center gap-1.5"><Table2 className="size-3.5" /> Dạng bảng</span> },
              ]}
            />
            <CreateProjectDialog onCreated={(p) => setCurrentProjectId(p.id)} />
          </>
        }
      />

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard label="Dự án đang hoạt động" value={summary?.projects_active ?? '—'} icon={Rocket} hint={`${summary?.projects_total ?? 0} dự án tổng cộng`} />
        <StatCard label="Luồng thực thi đang chạy" value={summary?.runs_active ?? '—'} icon={SquareTerminal} hint="pending · planning · running · chờ duyệt" />
        <StatCard label="Tác vụ đã hoàn thành" value={summary?.tasks_completed ?? '—'} icon={ListChecks} hint={`${summary?.tasks_failed ?? 0} tác vụ lỗi`} />
        <StatCard label="Chi phí token (12 tháng)" value={usage.data ? formatUsd(usage.data.totals.cost_usd) : '—'} icon={Coins} hint={usage.data ? `${formatCompact(usage.data.totals.total_tokens)} tokens` : undefined} />
      </div>

      <div className="panel flex flex-wrap items-center gap-3 p-3">
        <label className="flex min-w-60 flex-1 items-center gap-2 rounded-md bg-surface-lowest px-3 py-2">
          <Search className="size-4 text-outline" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Lọc theo tên, mô tả hoặc mã PRJ-…"
            className="w-full bg-transparent text-label-md outline-none placeholder:text-outline"
          />
        </label>
        <Segmented
          value={status}
          onChange={setStatus}
          options={[
            { value: 'active', label: 'Đang hoạt động' },
            { value: 'archived', label: 'Lưu trữ' },
            { value: undefined, label: 'Tất cả' },
          ]}
        />
      </div>

      <ErrorNote message={projects.error} />
      {!projects.data ? (
        <LoadingBlock className="h-64" />
      ) : view === 'cards' ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((r) => (
            <ProjectCard key={r.project.id} row={r} onToggleArchive={toggleArchive} onOpen={() => setCurrentProjectId(r.project.id)} />
          ))}
          <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-white/10 p-8 text-center">
            <span className="flex size-12 items-center justify-center rounded-lg bg-surface-high text-on-surface">
              <Plus className="size-6" />
            </span>
            <p className="text-headline-sm font-semibold">Tạo dự án mới</p>
            <p className="max-w-64 text-body-sm text-outline">Mỗi dự án có một workspace riêng, nơi các AI Agent ghi tài liệu, code và test.</p>
            <CreateProjectDialog onCreated={(p) => setCurrentProjectId(p.id)} />
          </div>
        </div>
      ) : rows.length === 0 ? (
        <EmptyState icon={FolderGit2} title="Không có dự án phù hợp bộ lọc" />
      ) : null}

      {projects.data && (
        <Section title="Bảng tóm tắt thực thi" icon={Table2} actions={<span className="font-mono text-label-sm text-outline">Hiển thị {rows.length} dự án</span>}>
          <div className="-mx-4 overflow-x-auto md:-mx-5">
            <Table>
              <TableHeader>
                <TableRow className="border-white/[0.06] hover:bg-transparent">
                  {['Tên dự án', 'Trạng thái', 'Tiến độ', 'Tác vụ xong', 'Chi phí token', 'Cập nhật', ''].map((h) => (
                    <TableHead key={h} className="micro-label">{h}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.project.id} className="border-white/[0.06]">
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-label-sm text-outline">PRJ-{r.project.id}</span>
                        <span className="font-semibold">{r.project.name}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={r.project.status} />
                    </TableCell>
                    <TableCell className="min-w-40">
                      <div className="flex items-center gap-2">
                        <ProgressBar value={percent(r.done, r.total)} />
                        <span className="w-9 font-mono text-label-sm">{percent(r.done, r.total)}%</span>
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-label-sm">{r.done} / {r.total}</TableCell>
                    <TableCell className="font-mono text-label-sm">
                      {formatCompact(r.tokens)} ({formatUsd(r.cost)})
                    </TableCell>
                    <TableCell className="font-mono text-label-sm text-outline">{formatRelative(r.project.updated_at)}</TableCell>
                    <TableCell>
                      <Button size="sm" variant="secondary" asChild onClick={() => setCurrentProjectId(r.project.id)}>
                        <Link to={`/projects/${r.project.id}`}>Workspace</Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Section>
      )}
    </div>
  )
}

function ProjectCard({ row, onToggleArchive, onOpen }: { row: Row; onToggleArchive: (p: Project) => void; onOpen: () => void }) {
  const { project } = row
  const pct = percent(row.done, row.total)
  return (
    <article className="panel flex flex-col gap-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="rounded bg-brand-strong/15 px-1.5 py-0.5 font-mono text-label-sm text-brand">PRJ-{project.id}</span>
        {row.runStatus ? <StatusBadge status={row.runStatus as Parameters<typeof StatusBadge>[0]['status']} /> : <StatusBadge status={project.status} />}
      </div>
      <Link to={`/projects/${project.id}`} onClick={onOpen} className="text-headline-lg font-semibold hover:text-brand">
        {project.name}
      </Link>
      <p className="line-clamp-2 min-h-11 text-body-md text-on-surface-variant">{project.description || 'Chưa có mô tả.'}</p>
      <span className="w-fit rounded border border-white/[0.08] bg-surface-lowest px-1.5 py-0.5 font-mono text-label-sm text-outline">
        workspaces/{project.workspace_dir}
      </span>
      <div className="grid gap-1.5">
        <div className="flex justify-between font-mono text-label-sm">
          <span className="text-outline">{row.runId ? `Run #${row.runId}` : 'Chưa có luồng thực thi'}</span>
          <span>{pct}%</span>
        </div>
        <ProgressBar value={pct} tone="bg-brand" />
      </div>
      <div className="flex justify-between font-mono text-label-sm text-outline">
        <span>{row.done}/{row.total} tác vụ</span>
        <span>{formatCompact(row.tokens)} tokens · {formatUsd(row.cost)}</span>
      </div>
      <div className="mt-auto flex items-center justify-between border-t border-white/[0.06] pt-3">
        <span className="font-mono text-label-sm text-outline">{formatRelative(project.updated_at)}</span>
        <div className="flex gap-1">
          <Button size="sm" variant="secondary" asChild onClick={onOpen}>
            <Link to={`/projects/${project.id}`}>
              <SquareTerminal /> Workspace
            </Link>
          </Button>
          <Button size="icon-sm" variant="ghost" onClick={() => onToggleArchive(project)} title={project.status === 'active' ? 'Lưu trữ' : 'Khôi phục'}>
            {project.status === 'active' ? <Archive /> : <ArchiveRestore />}
          </Button>
        </div>
      </div>
      {project.status === 'archived' && <Pill>Đã lưu trữ</Pill>}
    </article>
  )
}
