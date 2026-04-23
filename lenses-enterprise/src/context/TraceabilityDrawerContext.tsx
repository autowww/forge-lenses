import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

export type TraceabilityOpenOpts = {
  /** Optional headline when root is not human-friendly */
  title?: string
}

type TraceabilityDrawerContextValue = {
  isOpen: boolean
  rootId: string | null
  headline: string | null
  openTrace: (rootId: string, opts?: TraceabilityOpenOpts) => void
  close: () => void
}

const TraceabilityDrawerContext = createContext<TraceabilityDrawerContextValue | null>(null)

export function TraceabilityDrawerProvider({ children }: { children: ReactNode }) {
  const [isOpen, setOpen] = useState(false)
  const [rootId, setRootId] = useState<string | null>(null)
  const [headline, setHeadline] = useState<string | null>(null)

  const close = useCallback(() => {
    setOpen(false)
    setRootId(null)
    setHeadline(null)
  }, [])

  const openTrace = useCallback((id: string, opts?: TraceabilityOpenOpts) => {
    const t = id.trim()
    if (!t) return
    setRootId(t)
    setHeadline(opts?.title?.trim() || null)
    setOpen(true)
  }, [])

  const value = useMemo(
    () => ({ isOpen, rootId, headline, openTrace, close }),
    [isOpen, rootId, headline, openTrace, close],
  )

  return (
    <TraceabilityDrawerContext.Provider value={value}>{children}</TraceabilityDrawerContext.Provider>
  )
}

export function useTraceabilityDrawer(): TraceabilityDrawerContextValue {
  const ctx = useContext(TraceabilityDrawerContext)
  if (!ctx) {
    throw new Error('useTraceabilityDrawer must be used within TraceabilityDrawerProvider')
  }
  return ctx
}
