import { useMemo, useState } from 'react'
import { CheckCircle2, History, Hourglass, ShieldCheck, ShieldQuestion, XCircle } from 'lucide-react'

import { AgentAvatar, EmptyState, ErrorNote, LoadingBlock, PageHeader, Section, Segmented, StatCard } from '@/components/common/page'
import { Pill, StatusBadge } from '@/components/common/status-badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useApi } from '@/hooks/use-api'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/format'

import { ApprovalCard } from './approval-card'

export function ApprovalsPage() {
  const approvals = useApi(() => api.approvals.list(), [], ['approvals'])
  const [kind, setKind] = useState<string | undefined>()

  const all = useMemo(() => approvals.data ?? [], [approvals.data])
  const kinds = useMemo(() => [...new Set(all.map((a) => a.kind))].sort(), [all])
  const pending = all.filter((a) => a.status === 'pending' && (!kind || a.kind === kind))
  const decided = all.filter((a) => a.status !== 'pending')
  const approved = decided.filter((a) => a.status === 'approved').length

  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow={<><ShieldCheck className="size-3.5" /> Security gate · HITL controller <Pill tone="info" dot={false}>Real-time</Pill></>}
        title="Trung tâm Phê duyệt An toàn (Human-in-the-Loop)"
        description="Các hành động nhạy cảm do AI Agent đề xuất (lệnh ngoài allowlist, vượt ngân sách, thao tác nguy hiểm) phải được bạn chấp thuận trước khi thực hiện."
      />

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard label="Chờ phê duyệt" value={String(pending.length).padStart(2, '0')} icon={Hourglass} accent={pending.length ? 'text-warning' : undefined} hint="Yêu cầu cần xử lý" />
        <StatCard label="Đã duyệt" value={String(approved).padStart(2, '0')} icon={CheckCircle2} accent="text-success" hint="Toàn bộ thời gian" />
        <StatCard label="Đã từ chối" value={String(decided.length - approved).padStart(2, '0')} icon={XCircle} accent="text-danger" hint="Agent phải đổi phương án" />
        <StatCard label="Tỉ lệ chấp thuận" value={decided.length ? `${Math.round((approved / decided.length) * 100)}%` : '—'} icon={ShieldQuestion} hint={`${decided.length} quyết định`} />
      </div>

      {kinds.length > 1 && (
        <div className="panel flex flex-wrap items-center gap-3 p-3">
          <span className="micro-label">Loại hành động:</span>
          <Segmented value={kind} onChange={setKind} options={[{ value: undefined, label: 'Tất cả' }, ...kinds.map((k) => ({ value: k, label: k }))]} />
        </div>
      )}

      <ErrorNote message={approvals.error} />
      {!approvals.data ? (
        <LoadingBlock className="h-64" />
      ) : pending.length === 0 ? (
        <EmptyState icon={ShieldCheck} title="Không có yêu cầu nào đang chờ">
          Khi một agent cần thực hiện thao tác vượt quyền, yêu cầu sẽ xuất hiện tại đây theo thời gian thực.
        </EmptyState>
      ) : (
        <div className="grid gap-4">
          {pending.map((a) => <ApprovalCard key={a.id} approval={a} />)}
        </div>
      )}

      <Section title="Lịch sử phê duyệt (Audit log)" icon={History} description="Nhật ký quyết định bất biến">
        {decided.length === 0 ? (
          <p className="text-body-sm text-outline">Chưa có quyết định nào.</p>
        ) : (
          <div className="-mx-4 overflow-x-auto md:-mx-5">
            <Table>
              <TableHeader>
                <TableRow className="border-white/[0.06] hover:bg-transparent">
                  {['Mã', 'Hành động', 'Agent đề xuất', 'Dự án', 'Người duyệt', 'Thời gian', 'Kết quả'].map((h) => (
                    <TableHead key={h} className="micro-label">{h}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {decided.map((a) => (
                  <TableRow key={a.id} className="border-white/[0.06]">
                    <TableCell className="font-mono text-label-sm text-telemetry">APV-{a.id}</TableCell>
                    <TableCell className="max-w-sm whitespace-normal">
                      {a.title}
                      {a.decision_note && <p className="text-body-sm text-outline">“{a.decision_note}”</p>}
                    </TableCell>
                    <TableCell>{a.agent_code ? <span className="flex items-center gap-2"><AgentAvatar code={a.agent_code} size="sm" />{a.agent_code}</span> : '—'}</TableCell>
                    <TableCell className="text-label-md">{a.project_name}</TableCell>
                    <TableCell className="font-mono text-label-sm">{a.decided_by ?? 'hệ thống'}</TableCell>
                    <TableCell className="font-mono text-label-sm text-outline">{a.decided_at ? formatDate(a.decided_at) : '—'}</TableCell>
                    <TableCell><StatusBadge status={a.status} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Section>
    </div>
  )
}
