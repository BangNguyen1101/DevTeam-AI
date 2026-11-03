import type { LucideIcon } from 'lucide-react'

import { Skeleton } from '@/components/ui/skeleton'
import { agentMeta } from '@/lib/agents'
import { cn } from '@/lib/utils'

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: React.ReactNode
  title: React.ReactNode
  description?: React.ReactNode
  actions?: React.ReactNode
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0 max-w-3xl">
        {eyebrow && <div className="eyebrow mb-1 flex items-center gap-1.5">{eyebrow}</div>}
        <h1 className="text-headline-xl font-semibold text-on-surface md:text-display">{title}</h1>
        {description && <p className="mt-1 text-body-md text-on-surface-variant">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  accent = 'text-on-surface',
  children,
}: {
  label: string
  value: React.ReactNode
  hint?: React.ReactNode
  icon?: LucideIcon
  accent?: string
  children?: React.ReactNode
}) {
  return (
    <div className="panel flex flex-col gap-2 p-4">
      <div className="flex items-start justify-between gap-2">
        <span className="text-label-md text-on-surface-variant">{label}</span>
        {Icon && <Icon className="size-4 shrink-0 text-telemetry" />}
      </div>
      <div className={cn('tabular text-headline-xl font-semibold', accent)}>{value}</div>
      {hint && <div className="font-mono text-label-sm text-outline">{hint}</div>}
      {children}
    </div>
  )
}

export function Section({
  title,
  icon: Icon,
  actions,
  className,
  children,
  description,
}: {
  title: React.ReactNode
  icon?: LucideIcon
  actions?: React.ReactNode
  className?: string
  description?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <section className={cn('panel flex flex-col gap-4 p-4 md:p-5', className)}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="flex items-center gap-2 text-headline-lg font-semibold text-on-surface">
            {Icon && <Icon className="size-5 text-telemetry" />}
            {title}
          </h2>
          {description && <p className="mt-0.5 text-body-sm text-outline">{description}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  )
}

export function EmptyState({
  icon: Icon,
  title,
  children,
  className,
}: {
  icon?: LucideIcon
  title: string
  children?: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-white/10 px-6 py-10 text-center',
        className,
      )}
    >
      {Icon && <Icon className="size-8 text-outline" />}
      <p className="text-headline-sm font-semibold text-on-surface">{title}</p>
      {children && <div className="max-w-md text-body-sm text-outline">{children}</div>}
    </div>
  )
}

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null
  return <p className="rounded-md border border-danger/30 bg-danger/10 p-3 text-body-sm text-danger">{message}</p>
}

export function LoadingBlock({ className }: { className?: string }) {
  return <Skeleton className={cn('h-32 w-full bg-surface-container', className)} />
}

export function ProgressBar({
  value,
  className,
  tone = 'bg-telemetry',
  color,
}: {
  value: number
  className?: string
  tone?: string
  color?: string
}) {
  return (
    <div className={cn('h-1.5 w-full overflow-hidden rounded-full bg-surface-highest', className)}>
      <div
        className={cn('h-full rounded-full transition-[width]', !color && tone)}
        style={{ width: `${Math.min(100, Math.max(0, value))}%`, background: color }}
      />
    </div>
  )
}

export function AgentAvatar({ code, size = 'md' }: { code: string | null | undefined; size?: 'sm' | 'md' | 'lg' }) {
  const meta = agentMeta(code)
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded font-mono font-semibold',
        meta.tone,
        size === 'sm' && 'size-6 text-[10px]',
        size === 'md' && 'size-8 text-label-sm',
        size === 'lg' && 'size-11 text-label-md',
      )}
    >
      {meta.abbr}
    </span>
  )
}

export function Segmented<T extends string | number | undefined>({
  value,
  options,
  onChange,
}: {
  value: T
  options: { value: T; label: React.ReactNode }[]
  onChange: (value: T) => void
}) {
  return (
    <div className="inline-flex flex-wrap rounded-md border border-white/[0.06] bg-surface-lowest p-0.5">
      {options.map((o) => (
        <button
          key={String(o.value)}
          type="button"
          onClick={() => onChange(o.value)}
          className={cn(
            'rounded px-2.5 py-1 font-mono text-label-sm transition-colors',
            value === o.value ? 'bg-surface-high text-on-surface' : 'text-outline hover:text-on-surface',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
