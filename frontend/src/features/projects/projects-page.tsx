import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useRealtime } from '@/hooks/use-realtime'
import { api, ApiError } from '@/lib/api'
import { formatDate } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { Project, ProjectStatus, RealtimeEvent } from '@/types/api'

import { CreateProjectDialog } from './create-project-dialog'

const FILTERS: { value: ProjectStatus | undefined; label: string }[] = [
  { value: 'active', label: 'Đang hoạt động' },
  { value: 'archived', label: 'Đã lưu trữ' },
  { value: undefined, label: 'Tất cả' },
]

export function ProjectsPage() {
  const [filter, setFilter] = useState<ProjectStatus | undefined>('active')
  const [projects, setProjects] = useState<Project[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api.projects
      .list(filter)
      .then((data) => {
        setProjects(data)
        setError(null)
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Không thể kết nối backend'))
  }, [filter])

  useEffect(load, [load])

  // Other tabs/clients creating or updating projects show up without reload
  const connection = useRealtime(['projects'], (event: RealtimeEvent) => {
    if (event.type.startsWith('project.')) load()
  })

  const toggleArchive = async (project: Project) => {
    const status: ProjectStatus = project.status === 'active' ? 'archived' : 'active'
    try {
      await api.projects.update(project.id, { status })
      toast.success(status === 'archived' ? 'Đã lưu trữ dự án' : 'Đã khôi phục dự án')
      load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Cập nhật thất bại')
    }
  }

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dự án</h1>
          <p className="text-sm text-muted-foreground">
            Quản lý các dự án phần mềm do đội AI thực hiện.{' '}
            <span className={cn(connection === 'open' ? 'text-emerald-600' : 'text-amber-600')}>
              ● Realtime {connection === 'open' ? 'đã kết nối' : 'đang kết nối…'}
            </span>
          </p>
        </div>
        <CreateProjectDialog onCreated={load} />
      </div>

      <div className="flex gap-2">
        {FILTERS.map((f) => (
          <Button
            key={f.label}
            size="sm"
            variant={filter === f.value ? 'secondary' : 'ghost'}
            onClick={() => setFilter(f.value)}
          >
            {f.label}
          </Button>
        ))}
      </div>

      {error && <p className="rounded-md border border-destructive/40 p-3 text-sm text-destructive">{error}</p>}

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tên</TableHead>
              <TableHead className="hidden md:table-cell">Workspace</TableHead>
              <TableHead>Trạng thái</TableHead>
              <TableHead className="hidden sm:table-cell">Tạo lúc</TableHead>
              <TableHead className="w-0" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {projects === null && !error
              ? Array.from({ length: 3 }, (_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={5}>
                      <Skeleton className="h-5 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              : projects?.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell>
                      <Link to={`/projects/${p.id}`} className="font-medium hover:underline">
                        {p.name}
                      </Link>
                      {p.description && (
                        <p className="line-clamp-1 max-w-md text-xs text-muted-foreground">{p.description}</p>
                      )}
                    </TableCell>
                    <TableCell className="hidden font-mono text-xs md:table-cell">{p.workspace_dir}</TableCell>
                    <TableCell>
                      <Badge variant={p.status === 'active' ? 'default' : 'secondary'}>
                        {p.status === 'active' ? 'Hoạt động' : 'Lưu trữ'}
                      </Badge>
                    </TableCell>
                    <TableCell className="hidden text-sm text-muted-foreground sm:table-cell">
                      {formatDate(p.created_at)}
                    </TableCell>
                    <TableCell>
                      <Button size="sm" variant="ghost" onClick={() => toggleArchive(p)}>
                        {p.status === 'active' ? 'Lưu trữ' : 'Khôi phục'}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
            {projects?.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                  Chưa có dự án nào. Bấm “Dự án mới” để bắt đầu.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
