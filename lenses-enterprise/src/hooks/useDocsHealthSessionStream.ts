import { useEffect, useRef, useState } from 'react'
import { docsHealthSessionEventsUrl, type DocsHealthSessionPayload } from '../api/docsHealth'

/**
 * Server-Sent Events stream of merged session payloads (same shape as ``session_get``).
 * Returns whether the EventSource is connected. Use together with polling when disconnected.
 */
export function useDocsHealthSessionStream(
  projectSlug: string,
  sessionId: string,
  enabled: boolean,
  onSession: (s: DocsHealthSessionPayload) => void,
): boolean {
  const [connected, setConnected] = useState(false)
  const cbRef = useRef(onSession)
  cbRef.current = onSession

  useEffect(() => {
    if (!enabled || !projectSlug || !sessionId) {
      setConnected(false)
      return undefined
    }
    if (typeof EventSource === 'undefined') {
      setConnected(false)
      return undefined
    }
    const url = docsHealthSessionEventsUrl(projectSlug, sessionId)
    let es: EventSource
    try {
      es = new EventSource(url)
    } catch {
      setConnected(false)
      return undefined
    }
    es.onopen = () => setConnected(true)
    es.onmessage = (e: MessageEvent<string>) => {
      try {
        const o = JSON.parse(e.data) as { ok?: boolean; session?: DocsHealthSessionPayload }
        if (o.ok && o.session) cbRef.current(o.session)
      } catch {
        /* ignore malformed chunks */
      }
    }
    es.onerror = () => {
      setConnected(false)
      es.close()
    }
    return () => {
      setConnected(false)
      es.close()
    }
  }, [enabled, projectSlug, sessionId])

  return connected
}
