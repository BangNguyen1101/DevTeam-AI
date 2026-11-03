import { useEffect, useRef, useState } from 'react'

import type { RealtimeEvent } from '@/types/api'

export type ConnectionState = 'connecting' | 'open' | 'closed'

const PING_INTERVAL_MS = 25_000
const MAX_BACKOFF_MS = 10_000

/** Subscribe to backend WebSocket topics; reconnects with exponential backoff. */
export function useRealtime(topics: string[], onEvent: (event: RealtimeEvent) => void): ConnectionState {
  const [state, setState] = useState<ConnectionState>('connecting')
  const handler = useRef(onEvent)
  handler.current = onEvent
  const topicKey = topics.join(',')

  useEffect(() => {
    let ws: WebSocket | null = null
    let retry = 0
    let stopped = false
    let pingTimer: number | undefined
    let retryTimer: number | undefined

    const connect = () => {
      setState('connecting')
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${proto}://${window.location.host}/ws?topics=${encodeURIComponent(topicKey)}`)

      ws.onopen = () => {
        retry = 0
        setState('open')
        pingTimer = window.setInterval(() => ws?.send('ping'), PING_INTERVAL_MS)
      }
      ws.onmessage = (msg) => {
        const data = JSON.parse(msg.data)
        if (data.topic) handler.current(data as RealtimeEvent)
      }
      ws.onclose = () => {
        window.clearInterval(pingTimer)
        setState('closed')
        if (stopped) return
        retryTimer = window.setTimeout(connect, Math.min(1000 * 2 ** retry++, MAX_BACKOFF_MS))
      }
    }

    connect()
    return () => {
      stopped = true
      window.clearInterval(pingTimer)
      window.clearTimeout(retryTimer)
      ws?.close()
    }
  }, [topicKey])

  return state
}
