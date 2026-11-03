import { useState } from 'react'
import { Check, Clock, X } from 'lucide-react'
import { toast } from 'sonner'

import { AgentAvatar } from '@/components/common/page'
import { StatusBadge } from '@/components/common/status-badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { api, errorMessage } from '@/lib/api'
import { formatRelative } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { Approval } from '@/types/api'

export function ApprovalCard({ approval, compact, onDecided }: { approval: Approval; compact?: boolean; onDecided?: () => void }) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const pending = approval.status === 'pending'

  const decide = async (approve: boolean) => {
    setBusy(true)
    try {
      await (approve ? api.approvals.approve : api.approvals.reject)(approval.id, note.trim() || undefined)
      toast.success(approve ? 'Đã phê duyệt' : 'Đã từ chối')
      onDecided?.()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <article
      className={cn(
        'panel-raised flex flex-col gap-3 p-4',
        pending && !compact && 'border-l-2 border-l-warning',
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded bg-surface-high px-1.5 py-0.5 font-mono text-label-sm tracking-wider text-telemetry uppercase">
            {approval.kind}
          </span>
          <span className="font-mono text-label-sm text-outline">APV-{approval.id}</span>
          <span className="flex items-center gap-1 font-mono text-label-sm text-outline">
            <Clock className="size-3" />
            {formatRelative(approval.created_at)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {!pending && <StatusBadge status={approval.status} />}
          {approval.agent_code && <AgentAvatar code={approval.agent_code} size="sm" />}
        </div>
      </div>
      <div>
        <h3 className="text-headline-sm font-semibold text-on-surface">{approval.title}</h3>
        <p className="text-body-sm text-outline">
          {approval.project_name} · Run #{approval.run_id}
        </p>
      </div>
      {!compact && approval.payload && (
        <pre className="max-h-64 overflow-auto rounded-md bg-surface-lowest p-3 font-mono text-code text-on-surface-variant">
          {JSON.stringify(approval.payload, null, 2)}
        </pre>
      )}
      {approval.decision_note && <p className="text-body-sm text-on-surface-variant">Ghi chú: {approval.decision_note}</p>}
      {pending && (
        <div className="flex flex-col gap-2">
          {!compact && (
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Ghi chú cho agent (tùy chọn)"
              rows={2}
              className="bg-surface-lowest"
            />
          )}
          <div className="flex gap-2">
            <Button className="flex-1" disabled={busy} onClick={() => decide(true)}>
              <Check /> Phê duyệt
            </Button>
            <Button variant="secondary" className="flex-1" disabled={busy} onClick={() => decide(false)}>
              <X /> Từ chối
            </Button>
          </div>
        </div>
      )}
    </article>
  )
}
