import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

export type TimeHorizonId = 'day' | 'week' | 'month' | 'quarter'
export type CompareModeId = 'none' | 'previous_period'

type ShellChromeCtx = {
  timeHorizon: TimeHorizonId
  setTimeHorizon: (v: TimeHorizonId) => void
  compareMode: CompareModeId
  setCompareMode: (v: CompareModeId) => void
  railCollapsed: boolean
  setRailCollapsed: (v: boolean) => void
  overviewDataLoading: boolean
  beginOverviewDataLoad: () => void
  endOverviewDataLoad: () => void
}

const ShellChromeContext = createContext<ShellChromeCtx | null>(null)

const LS_HORIZON = 'lenses.studio.horizon'
const LS_COMPARE = 'lenses.studio.compare'
const LS_RAIL = 'lenses.studio.railCollapsed'

function readHorizon(): TimeHorizonId {
  try {
    const v = localStorage.getItem(LS_HORIZON)
    if (v === 'day' || v === 'month' || v === 'quarter' || v === 'week') return v
  } catch {
    /* ignore */
  }
  return 'week'
}

function readCompare(): CompareModeId {
  try {
    const v = localStorage.getItem(LS_COMPARE)
    if (v === 'previous_period') return 'previous_period'
  } catch {
    /* ignore */
  }
  return 'none'
}

function readRailCollapsed(): boolean {
  try {
    return localStorage.getItem(LS_RAIL) === '1'
  } catch {
    return false
  }
}

export function ShellChromeProvider({ children }: { children: ReactNode }) {
  const [timeHorizon, setTimeHorizonState] = useState<TimeHorizonId>(readHorizon)
  const [compareMode, setCompareModeState] = useState<CompareModeId>(readCompare)
  const [railCollapsed, setRailCollapsedState] = useState<boolean>(readRailCollapsed)
  const [overviewDataLoading, setOverviewDataLoading] = useState(false)
  const overviewLoadCountRef = useRef(0)

  const beginOverviewDataLoad = useCallback(() => {
    overviewLoadCountRef.current += 1
    setOverviewDataLoading(true)
  }, [])

  const endOverviewDataLoad = useCallback(() => {
    overviewLoadCountRef.current = Math.max(0, overviewLoadCountRef.current - 1)
    if (overviewLoadCountRef.current === 0) {
      setOverviewDataLoading(false)
    }
  }, [])

  const setTimeHorizon = useCallback((v: TimeHorizonId) => {
    setTimeHorizonState(v)
    try {
      localStorage.setItem(LS_HORIZON, v)
    } catch {
      /* ignore */
    }
  }, [])

  const setCompareMode = useCallback((v: CompareModeId) => {
    setCompareModeState(v)
    try {
      localStorage.setItem(LS_COMPARE, v)
    } catch {
      /* ignore */
    }
  }, [])

  const setRailCollapsed = useCallback((v: boolean) => {
    setRailCollapsedState(v)
    try {
      localStorage.setItem(LS_RAIL, v ? '1' : '0')
    } catch {
      /* ignore */
    }
  }, [])

  const value = useMemo(
    () => ({
      timeHorizon,
      setTimeHorizon,
      compareMode,
      setCompareMode,
      railCollapsed,
      setRailCollapsed,
      overviewDataLoading,
      beginOverviewDataLoad,
      endOverviewDataLoad,
    }),
    [
      timeHorizon,
      setTimeHorizon,
      compareMode,
      setCompareMode,
      railCollapsed,
      setRailCollapsed,
      overviewDataLoading,
      beginOverviewDataLoad,
      endOverviewDataLoad,
    ],
  )

  return (
    <ShellChromeContext.Provider value={value}>{children}</ShellChromeContext.Provider>
  )
}

export function useShellChrome() {
  const c = useContext(ShellChromeContext)
  if (!c) throw new Error('useShellChrome outside ShellChromeProvider')
  return c
}
