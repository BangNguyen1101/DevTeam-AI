import { cn } from '@/lib/utils'
import type { ApprovalStatus, ProjectStatus, RunStatus, TaskStatus } from '@/types/api'

type Tone = 'processing' | 'warning' | 'success' | 'danger' | 'idle' | 'info'

const TONE: Record<Tone, string> = {
  processing: 'bg-processing/15 text-processing',
  warning: 'bg-warning/15 text-warning',
  success: 'bg-success/15 text-success',
  danger: 'bg-danger/15 text-danger',
  idle: 'bg-surface-high text-outline',
  info: 'bg-telemetry/15 text-telemetry',
}

type AnyStatus = RunStatus | TaskStatus | ApprovalStatus | ProjectStatus

const STATUS: Record<AnyStatus, [string, Tone]> = {
  pending: ['Chờ xử lý', 'idle'],
  ready: ['Sẵn sàng', 'info'],
  planning: ['Lập kế hoạch', 'processing'],
  running: ['Đang xử lý', 'processing'],
  waiting_approval: ['Chờ duyệt', 'warning'],
  completed: ['Hoàn thành', 'success'],
  failed: ['Lỗi', 'danger'],
  cancelled: ['Đã hủy', 'idle'],
  skipped: ['Bỏ qua', 'idle'],
  approved: ['Đã duyệt', 'success'],
  rejected: ['Từ chối', 'danger'],
  active: ['Đang hoạt động', 'info'],
  archived: ['Lưu trữ', 'idle'],
}

export function statusLabel(status: AnyStatus) {
  return STATUS[status]?.[0] ?? status
}

export function StatusBadge({ status, className }: { status: AnyStatus; className?: string }) {
  const [label, tone] = STATUS[status] ?? [status, 'idle']
  return <Pill tone={tone} pulse={tone === 'processing'} className={className}>{label}</Pill>
}

export function Pill({
  tone = 'idle',
  pulse,
  dot = true,
  className,
  children,
}: {
  tone?: Tone
  pulse?: boolean
  dot?: boolean
  className?: string
  children: React.ReactNode
}) {
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1.5 rounded px-1.5 py-0.5 font-mono text-label-sm font-medium whitespace-nowrap',
        TONE[tone],
        className,
      )}
    >
      {dot && (
        <span className="relative flex size-1.5">
          {pulse && <span className="absolute inline-flex size-full animate-ping rounded-full bg-current opacity-60" />}
          <span className="relative inline-flex size-1.5 rounded-full bg-current" />
        </span>
      )}
      {children}
    </span>
  )
}
