import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { getDocsHealthWorkspaceSummary, type DocsHealthWorkspaceSummary } from '../api/docsHealth'

type DocsHealthSummaryCtx = {
  data: DocsHealthWorkspaceSummary | null
  loading: boolean
  refresh: () => void
}

const DocsHealthSummaryContext = createContext<DocsHealthSummaryCtx | null>(null)

export function DocsHealthSummaryProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<DocsHealthWorkspaceSummary | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(() => {
    setLoading(true)
    void getDocsHealthWorkspaceSummary()
      .then((d) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const value = useMemo(
    () => ({
      data,
      loading,
      refresh,
    }),
    [data, loading, refresh],
  )

  return (
    <DocsHealthSummaryContext.Provider value={value}>
      {children}
    </DocsHealthSummaryContext.Provider>
  )
}

export function useDocsHealthSummary() {
  const ctx = useContext(DocsHealthSummaryContext)
  if (!ctx) throw new Error('useDocsHealthSummary outside DocsHealthSummaryProvider')
  return ctx
}
