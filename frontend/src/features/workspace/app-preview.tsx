import { useState } from 'react'
import { ExternalLink, MonitorPlay, Play, RotateCw, ShieldCheck, Square, TriangleAlert } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState, ErrorNote, Section } from '@/components/common/page'
import { Pill } from '@/components/common/status-badge'
import { Button } from '@/components/ui/button'
import { useApi } from '@/hooks/use-api'
import { api, errorMessage } from '@/lib/api'
import type { Project } from '@/types/api'

/**
 * Live view of the app the agents generated. The page is loaded in a sandboxed
 * iframe WITHOUT allow-same-origin: it gets an opaque origin, so AI-written
 * JavaScript can neither read DevTeam's DOM nor call its API with the admin cookie.
 */
export function AppPreview({ project }: { project: Project }) {
  const status = useApi(() => api.projects.preview(project.id), [project.id])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [frameKey, setFrameKey] = useState(0)
  const preview = status.data

  const start = async () => {
    setBusy(true)
    setError(null)
    try {
      await api.projects.startPreview(project.id)
      status.reload()
      setFrameKey((k) => k + 1)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const stop = async () => {
    setBusy(true)
    try {
      await api.projects.stopPreview(project.id)
      toast.success('Đã dừng bản xem trước')
      status.reload()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section
      title="Xem trước ứng dụng do đội AI tạo"
      icon={MonitorPlay}
      description="Chạy backend FastAPI trong workspace và mở trang frontend/index.html ngay tại đây."
      actions={
        preview?.running ? (
          <div className="flex flex-wrap gap-2">
            <Pill tone={preview.api_running ? 'success' : 'warning'}>
              {preview.api_running ? 'API đang chạy' : 'Chỉ có frontend'}
            </Pill>
            <Button size="sm" variant="secondary" onClick={() => setFrameKey((k) => k + 1)}><RotateCw /> Tải lại</Button>
            <Button size="sm" variant="secondary" asChild>
              <a href={preview.url ?? '#'} target="_blank" rel="noopener noreferrer"><ExternalLink /> Tab mới</a>
            </Button>
            <Button size="sm" variant="destructive" onClick={stop} disabled={busy}><Square /> Dừng</Button>
          </div>
        ) : null
      }
    >
      <ErrorNote message={status.error} />
      {error && <pre className="overflow-auto rounded-md border border-danger/30 bg-danger/10 p-3 font-mono text-label-sm whitespace-pre-wrap text-danger">{error}</pre>}

      {preview?.running && preview.url ? (
        <>
          <div className="overflow-hidden rounded-lg border border-white/10 bg-white">
            <div className="flex items-center gap-2 border-b bg-surface-container px-3 py-1.5 font-mono text-label-sm text-outline">
              <span className="flex gap-1"><span className="size-2.5 rounded-full bg-danger/70" /><span className="size-2.5 rounded-full bg-warning/70" /><span className="size-2.5 rounded-full bg-success/70" /></span>
              <span className="truncate">{project.name} — preview</span>
            </div>
            <iframe
              key={frameKey}
              src={preview.url}
              title={`Xem trước ${project.name}`}
              sandbox="allow-scripts allow-forms allow-modals"
              referrerPolicy="no-referrer"
              className="h-[640px] w-full bg-white"
            />
          </div>
          <p className="flex items-center gap-1.5 text-body-sm text-outline">
            <ShieldCheck className="size-4 text-success" />
            Chạy trong sandbox: trang không truy cập được phiên đăng nhập DevTeam. Tự dừng sau 15 phút không dùng.
          </p>
          {preview.log_tail && (
            <details className="rounded-md bg-surface-lowest p-3">
              <summary className="cursor-pointer font-mono text-label-sm text-outline">Log backend của ứng dụng</summary>
              <pre className="mt-2 max-h-48 overflow-auto font-mono text-label-sm text-on-surface-variant">{preview.log_tail}</pre>
            </details>
          )}
        </>
      ) : (
        <EmptyState icon={MonitorPlay} title="Chưa chạy bản xem trước">
          <span className="flex items-start gap-1.5 text-left">
            <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warning" />
            Bấm nút sẽ chạy code backend do AI viết trên máy này (không có khóa bí mật, chỉ nghe nội bộ). Chỉ chạy khi test đã đạt và bạn đã xem qua code.
          </span>
          <Button className="mt-3" onClick={start} disabled={busy}>
            <Play /> {busy ? 'Đang khởi động…' : 'Chạy xem trước'}
          </Button>
        </EmptyState>
      )}
    </Section>
  )
}
