import { agentMeta } from '@/lib/agents'
import { formatRelative, formatTime } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { ExecutionEvent } from '@/types/api'

export function eventTone(type: string) {
  if (/fail|error|reject/.test(type)) return 'text-danger'
  if (/approval|waiting/.test(type)) return 'text-warning'
  if (/complete|approved|success/.test(type)) return 'text-success'
  if (/start|running|plan/.test(type)) return 'text-processing'
  return 'text-telemetry'
}

/** Card-style event used in activity feeds. */
export function EventCard({ event }: { event: ExecutionEvent }) {
  return (
    <div className="panel-raised flex flex-col gap-1.5 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className={cn('rounded px-1.5 py-0.5 font-mono text-label-sm uppercase', agentMeta(event.agent_code).tone)}>
            {event.agent_code ?? 'system'}
          </span>
          <span className={cn('font-mono text-label-sm', eventTone(event.event_type))}>{event.event_type}</span>
        </div>
        <span className="font-mono text-label-sm text-outline">{formatRelative(event.created_at)}</span>
      </div>
      <p className="text-body-md text-on-surface">{event.message}</p>
      <p className="font-mono text-label-sm text-outline">
        {event.project_name} · Run #{event.run_id}
        {event.task_title ? ` · ${event.task_title}` : ''}
      </p>
    </div>
  )
}

/** Terminal-style log line used in trace viewers. */
export function EventLogLine({ event }: { event: ExecutionEvent }) {
  return (
    <div className="font-mono text-code leading-relaxed">
      <span className="text-outline">[{formatTime(event.created_at)}]</span>{' '}
      <span className={eventTone(event.event_type)}>[{event.event_type.toUpperCase()}]</span>{' '}
      {event.agent_code && <span className="text-agent">{event.agent_code}: </span>}
      <span className="text-on-surface-variant">{event.message}</span>
      {event.data && (
        <pre className="mt-1 ml-4 overflow-x-auto rounded bg-surface-lowest p-2 text-label-sm text-outline">
          {JSON.stringify(event.data, null, 2)}
        </pre>
      )}
    </div>
  )
}
