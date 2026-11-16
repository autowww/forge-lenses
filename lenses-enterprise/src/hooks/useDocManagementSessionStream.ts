import { useEffect, useRef, useState } from 'react'
import type { DocManagementSession } from '../api/docManagement'
import { docManagementSessionEventsUrl } from '../api/docManagement'

export function useDocManagementSessionStream(sessionId: string | undefined, enabled: boolean) {
  const [session, setSession] = useState<DocManagementSession | null>(null)
  const [error, setError] = useState<string | null>(null)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!sessionId || !enabled) return undefined
    setError(null)
    const url = docManagementSessionEventsUrl(sessionId)
    const es = new EventSource(url, { withCredentials: true })
    esRef.current = es
    es.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data) as { ok?: boolean; session?: DocManagementSession; error?: string }
        if (payload.session) setSession(payload.session)
        if (!payload.ok && payload.error) setError(payload.error)
      } catch {
        setError('invalid_sse_payload')
      }
    }
    es.onerror = () => setError('stream_disconnected')
    return () => {
      es.close()
      esRef.current = null
    }
  }, [sessionId, enabled])

  return { session, error }
}
