import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import {
  fetchOverviewChartPayload,
  pollOverviewJob,
  requestOverviewChart,
  type OverviewChartPayload,
  type OverviewJobHint,
} from '../api/chartOverview'
import { useShellChrome, type TimeHorizonId } from './ShellChromeContext'
import { useWorkspace } from './WorkspaceContext'

type OverviewTelemetryCtx = {
  payload: OverviewChartPayload | null
  loading: boolean
  error: boolean
  jobHint: OverviewJobHint | null
  progress: number | null
  refreshOverview: (opts?: { force?: boolean }) => Promise<void>
}

const OverviewTelemetryContext = createContext<OverviewTelemetryCtx | null>(null)

function progressFromHint(hint: OverviewJobHint | null): number | null {
  if (!hint) return null
  if (hint.status === 'done' || hint.status === 'ready') return 1
  if (hint.repoTotal <= 0) return hint.status === 'running' || hint.status === 'pending' ? 0.05 : null
  return Math.min(1, Math.max(0, hint.repoDone / hint.repoTotal))
}

export function OverviewTelemetryProvider({ children }: { children: ReactNode }) {
  const { state } = useWorkspace()
  const { timeHorizon, beginOverviewDataLoad, endOverviewDataLoad } = useShellChrome()
  const [payload, setPayload] = useState<OverviewChartPayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const [jobHint, setJobHint] = useState<OverviewJobHint | null>(null)
  const flightRef = useRef(0)

  const runFetch = useCallback(
    async (horizon: TimeHorizonId, force = false) => {
      const ticket = ++flightRef.current
      setLoading(true)
      setError(false)
      beginOverviewDataLoad()
      try {
        const outcome = await requestOverviewChart(horizon, { force })
        if (ticket !== flightRef.current) return
        if (outcome.kind === 'ready') {
          setPayload(outcome.payload)
          setJobHint(null)
          return
        }
        if (outcome.payload) setPayload(outcome.payload)
        setJobHint(outcome.hint)
        const fresh = await pollOverviewJob(outcome.jobId, (hint) => {
          if (ticket !== flightRef.current) return
          setJobHint(hint)
        })
        if (ticket !== flightRef.current) return
        setPayload(fresh)
        setJobHint(null)
      } catch {
        if (ticket !== flightRef.current) return
        setError(true)
        try {
          const fallback = await fetchOverviewChartPayload(horizon, { force })
          if (ticket !== flightRef.current) return
          setPayload(fallback)
          setError(false)
        } catch {
          if (ticket !== flightRef.current) return
          setPayload(null)
        }
      } finally {
        if (ticket === flightRef.current) {
          setLoading(false)
          endOverviewDataLoad()
        }
      }
    },
    [beginOverviewDataLoad, endOverviewDataLoad],
  )

  useEffect(() => {
    void runFetch(timeHorizon, false)
  }, [state?.resolved_at, timeHorizon, runFetch])

  const refreshOverview = useCallback(
    async (opts?: { force?: boolean }) => {
      await runFetch(timeHorizon, Boolean(opts?.force))
    },
    [runFetch, timeHorizon],
  )

  const progress = useMemo(() => progressFromHint(jobHint), [jobHint])

  const value = useMemo(
    () => ({
      payload,
      loading,
      error,
      jobHint,
      progress,
      refreshOverview,
    }),
    [payload, loading, error, jobHint, progress, refreshOverview],
  )

  return (
    <OverviewTelemetryContext.Provider value={value}>
      {children}
    </OverviewTelemetryContext.Provider>
  )
}

export function useOverviewTelemetry() {
  const ctx = useContext(OverviewTelemetryContext)
  if (!ctx) throw new Error('useOverviewTelemetry outside OverviewTelemetryProvider')
  return ctx
}
