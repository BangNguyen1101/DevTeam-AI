import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { api, ApiError } from '@/lib/api'
import { formatDate } from '@/lib/format'
import type { Project } from '@/types/api'

export function ProjectDetailPage() {
  const { projectId } = useParams()
  const [project, setProject] = useState<Project | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.projects
      .get(Number(projectId))
      .then(setProject)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Không thể kết nối backend'))
  }, [projectId])

  return (
    <div className="grid gap-6">
      <Link to="/projects" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Danh sách dự án
      </Link>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {!project && !error && <Skeleton className="h-40 w-full" />}

      {project && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">{project.name}</h1>
            <Badge variant={project.status === 'active' ? 'default' : 'secondary'}>
              {project.status === 'active' ? 'Hoạt động' : 'Lưu trữ'}
            </Badge>
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Thông tin dự án</CardTitle>
              <CardDescription>{project.description || 'Chưa có mô tả.'}</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-2 text-sm sm:grid-cols-[160px_1fr]">
              <span className="text-muted-foreground">Workspace</span>
              <span className="font-mono">workspaces/{project.workspace_dir}</span>
              <span className="text-muted-foreground">Tạo lúc</span>
              <span>{formatDate(project.created_at)}</span>
              <span className="text-muted-foreground">Cập nhật</span>
              <span>{formatDate(project.updated_at)}</span>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Workflow runs</CardTitle>
              <CardDescription>
                Gửi yêu cầu cho AI Manager và theo dõi các Agent sẽ có ở tuần 2.
              </CardDescription>
            </CardHeader>
          </Card>
        </>
      )}
    </div>
  )
}
