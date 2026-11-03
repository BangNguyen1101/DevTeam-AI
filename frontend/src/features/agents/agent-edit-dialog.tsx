import { useState, type FormEvent } from 'react'
import { Settings2 } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, errorMessage } from '@/lib/api'
import type { Agent } from '@/types/api'

export function AgentEditDialog({ agent, trigger }: { agent: Agent; trigger?: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const [model, setModel] = useState(agent.model)
  const [maxTokens, setMaxTokens] = useState(String(agent.max_output_tokens))
  const [enabled, setEnabled] = useState(agent.is_enabled)
  const [instructions, setInstructions] = useState(agent.instructions ?? '')
  const [saving, setSaving] = useState(false)

  const reset = () => {
    setModel(agent.model)
    setMaxTokens(String(agent.max_output_tokens))
    setEnabled(agent.is_enabled)
    setInstructions(agent.instructions ?? '')
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.agents.update(agent.id, {
        model: model.trim(),
        max_output_tokens: Number(maxTokens),
        is_enabled: enabled,
        instructions: instructions.trim() || null,
      })
      toast.success(`Đã lưu cấu hình ${agent.name}`)
      setOpen(false)
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) reset() }}>
      <DialogTrigger asChild>
        {trigger ?? (
          <Button size="sm" variant="secondary">
            <Settings2 /> Cấu hình
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={submit} className="grid gap-4">
          <DialogHeader>
            <DialogTitle>Cấu hình {agent.name}</DialogTitle>
            <DialogDescription>Thay đổi có hiệu lực từ lần gọi model tiếp theo của agent này.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="agent-model">Model OpenAI</Label>
            <Input id="agent-model" list="llm-models" value={model} onChange={(e) => setModel(e.target.value)} required maxLength={100} className="font-mono" />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="agent-tokens">Max output tokens</Label>
            <Input id="agent-tokens" type="number" min={256} max={128000} value={maxTokens} onChange={(e) => setMaxTokens(e.target.value)} required />
          </div>
          <label className="flex items-center gap-2 text-label-md">
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} className="size-4 accent-brand-strong" />
            Bật agent (agent tắt sẽ không được AI Manager phân công)
          </label>
          <div className="grid gap-2">
            <Label htmlFor="agent-instructions">Chỉ dẫn bổ sung (system prompt)</Label>
            <Textarea id="agent-instructions" rows={5} value={instructions} onChange={(e) => setInstructions(e.target.value)} placeholder="Để trống để dùng chỉ dẫn mặc định của hệ thống" />
          </div>
          <div className="flex flex-wrap gap-1">
            <span className="text-label-sm text-outline">Quyền:</span>
            {agent.permissions.map((p) => (
              <span key={p} className="rounded border border-white/10 px-1.5 font-mono text-label-sm text-on-surface-variant">{p}</span>
            ))}
          </div>
          <DialogFooter>
            <Button type="submit" disabled={saving}>{saving ? 'Đang lưu…' : 'Lưu thay đổi'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
