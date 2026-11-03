import { useEffect, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { api, ApiError } from '@/lib/api'
import type { Agent } from '@/types/api'

export function AgentsPage() {
  const [agents, setAgents] = useState<Agent[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.agents
      .list()
      .then(setAgents)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Không thể kết nối backend'))
  }, [])

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">AI Agents</h1>
        <p className="text-sm text-muted-foreground">AI Manager và 6 Agent chuyên môn cùng quyền hạn được cấp.</p>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {agents === null && !error && Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-44" />)}
        {agents?.map((a) => (
          <Card key={a.id} className={a.code === 'manager' ? 'border-primary/50 sm:col-span-2 lg:col-span-3' : ''}>
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle>{a.name}</CardTitle>
                <Badge variant={a.is_enabled ? 'default' : 'secondary'}>{a.is_enabled ? 'Bật' : 'Tắt'}</Badge>
              </div>
              <CardDescription>{a.role_description}</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Model</span>
                <span className="font-mono">{a.model}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Max output tokens</span>
                <span className="font-mono">{a.max_output_tokens.toLocaleString('vi-VN')}</span>
              </div>
              <div className="flex flex-wrap gap-1">
                {a.permissions.map((p) => (
                  <Badge key={p} variant="outline" className="font-mono text-[11px]">
                    {p}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
