import { ListChecks } from 'lucide-react'

import { AgentAvatar, EmptyState, ErrorNote, LoadingBlock } from '@/components/common/page'
import { StatusBadge } from '@/components/common/status-badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useApi } from '@/hooks/use-api'
import { api } from '@/lib/api'
import { formatCompact, formatRelative, formatUsd } from '@/lib/format'
import type { Task } from '@/types/api'

export function TaskTable({ params, tasks }: { params?: Parameters<typeof api.tasks.list>[0]; tasks?: Task[] }) {
  const fetched = useApi(() => (tasks ? Promise.resolve(tasks) : api.tasks.list(params)), [JSON.stringify(params), tasks], tasks ? [] : ['events'])
  const rows = tasks ?? fetched.data

  if (fetched.error) return <ErrorNote message={fetched.error} />
  if (!rows) return <LoadingBlock />
  if (rows.length === 0) return <EmptyState icon={ListChecks} title="Chưa có tác vụ nào" />

  return (
    <div className="panel overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="border-white/[0.06] hover:bg-transparent">
            {['Mã', 'Tác vụ', 'Agent', 'Trạng thái', 'Phụ thuộc', 'Lần thử', 'Tokens', 'Cập nhật'].map((h) => (
              <TableHead key={h} className="micro-label">{h}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((t) => (
            <TableRow key={t.id} className="border-white/[0.06]">
              <TableCell className="font-mono text-label-sm text-outline">#TASK-{t.id}</TableCell>
              <TableCell className="max-w-md">
                <p className="font-semibold whitespace-normal">{t.title}</p>
                <p className="font-mono text-label-sm text-outline">{t.project_name} · Run #{t.run_id} · {t.task_key}</p>
              </TableCell>
              <TableCell>
                <span className="flex items-center gap-2 text-label-md">
                  <AgentAvatar code={t.agent_code} size="sm" /> {t.agent_name}
                </span>
              </TableCell>
              <TableCell><StatusBadge status={t.status} /></TableCell>
              <TableCell className="font-mono text-label-sm text-outline">{t.depends_on.join(', ') || '—'}</TableCell>
              <TableCell className="font-mono text-label-sm">{t.attempt}/{t.max_attempts}</TableCell>
              <TableCell className="font-mono text-label-sm text-telemetry">
                {formatCompact(t.input_tokens + t.output_tokens)} · {formatUsd(t.cost_usd)}
              </TableCell>
              <TableCell className="font-mono text-label-sm text-outline">{formatRelative(t.updated_at)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
