import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { getDocsHealthLiveSessions, type DocsHealthLiveSessionRow } from '../api/docsHealth'

export type DocsHealthPulse = {
  projectSlug: string
  sessionId: string
  status: string
  totalTokens: number
  promptTokens: number
  completionTokens: number
  lastModel?: string | null
  href: string
  clusterLabel?: string | null
  /** Non-null while a session step request is in flight (header chip progress). */
  activeStep?: string | null
}

export type DocsHealthLiveContextValue = {
  /** Prefer detail pulse when on a session page; else first live workspace session */
  pulse: DocsHealthPulse | null
  setDetailPulse: (p: DocsHealthPulse | null) => void
  globalSessions: DocsHealthLiveSessionRow[]
  refreshGlobal: () => void
}

const DocsHealthLiveContext = createContext<DocsHealthLiveContextValue | null>(null)

function rowToPulse(r: DocsHealthLiveSessionRow): DocsHealthPulse | null {
  const proj = String(r.project || '').trim()
  const sid = String(r.session_id || '').trim()
  if (!proj || !sid) return null
  const tt = Number(r.total_tokens) || 0
  const pt = Number(r.prompt_tokens) || 0
  const ct = Number(r.completion_tokens) || 0
  return {
    projectSlug: proj,
    sessionId: sid,
    status: String(r.status || ''),
    totalTokens: tt,
    promptTokens: pt,
    completionTokens: ct,
    lastModel: r.last_model,
    clusterLabel: r.cluster_label,
    href: `/projects/${encodeURIComponent(proj)}/docs-health/session/${encodeURIComponent(sid)}`,
  }
}

export function DocsHealthLiveProvider({ children }: { children: ReactNode }) {
  const [detail, setDetail] = useState<DocsHealthPulse | null>(null)
  const [globalSessions, setGlobalSessions] = useState<DocsHealthLiveSessionRow[]>([])

  const refreshGlobal = useCallback(() => {
    void getDocsHealthLiveSessions()
      .then((d) => {
        if (d.ok && Array.isArray(d.sessions)) setGlobalSessions(d.sessions)
        else setGlobalSessions([])
      })
      .catch(() => setGlobalSessions([]))
  }, [])

  useEffect(() => {
    refreshGlobal()
    const id = window.setInterval(refreshGlobal, 4500)
    return () => window.clearInterval(id)
  }, [refreshGlobal])

  const pulse = useMemo(() => {
    if (detail) return detail
    for (const row of globalSessions) {
      const p = rowToPulse(row)
      if (p) return p
    }
    return null
  }, [detail, globalSessions])

  const value = useMemo(
    () => ({
      pulse,
      setDetailPulse: setDetail,
      globalSessions,
      refreshGlobal,
    }),
    [pulse, globalSessions, refreshGlobal],
  )

  return <DocsHealthLiveContext.Provider value={value}>{children}</DocsHealthLiveContext.Provider>
}

export function useDocsHealthLive(): DocsHealthLiveContextValue | null {
  return useContext(DocsHealthLiveContext)
}
