import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { NavModeContext } from '../nav/navModeContext'
import {
  readWorkspaceLens,
  writeWorkspaceLens,
  type NavMode,
} from '../nav/workspaceLensCookie'
import { recordLensChange } from '../telemetry/studioTelemetry'

/**
 * Default is **flow** when no cookie: cross-functional / lifecycle-first entry (Unified IA v2).
 */
const DEFAULT_MODE: NavMode = 'flow'

export function NavModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<NavMode>(() => readWorkspaceLens() ?? DEFAULT_MODE)

  const setMode = useCallback((m: NavMode) => {
    setModeState((prev) => {
      if (prev === m) return prev
      recordLensChange(prev, m)
      writeWorkspaceLens(m)
      return m
    })
  }, [])

  useEffect(() => {
    document.documentElement.dataset.workspaceLens = mode
    document.documentElement.dataset.navMode = mode
  }, [mode])

  const value = useMemo(() => ({ mode, setMode }), [mode, setMode])

  return <NavModeContext.Provider value={value}>{children}</NavModeContext.Provider>
}
