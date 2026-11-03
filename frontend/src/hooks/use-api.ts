import { useCallback, useEffect, useRef, useState } from 'react'

import { errorMessage } from '@/lib/api'

import { useRealtime } from './use-realtime'

export interface ApiState<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
}

/**
 * Fetch data and keep it fresh. `deps` re-run the request; `topics` reload it
 * whenever the backend pushes an event on one of those WebSocket topics.
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[], topics: string[] = []): ApiState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher
  const requestId = useRef(0)

  const reload = useCallback(() => {
    const id = ++requestId.current
    setLoading(true)
    fetcherRef
      .current()
      .then((result) => {
        if (id !== requestId.current) return
        setData(result)
        setError(null)
      })
      .catch((err) => id === requestId.current && setError(errorMessage(err)))
      .finally(() => id === requestId.current && setLoading(false))
  }, [])

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(reload, deps)
  useRealtime(topics, reload)

  return { data, error, loading, reload }
}
