import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useLocation, useNavigate, useNavigationType } from 'react-router-dom'
import { useNavigationMode } from '../nav/useNavigationMode'
import { buildStudioHistoryTitle } from '../nav/studioHistoryTitle'

const MAX_ENTRIES = 28

export type StudioTrailEntry = {
  key: string
  pathname: string
  search: string
  title: string
}

type Ctx = {
  /** Chronological visit order (oldest → newest). */
  recent: StudioTrailEntry[]
  goBack: () => void
  goForward: () => void
  goToEntry: (e: StudioTrailEntry) => void
  currentKey: string
}

const StudioNavigationTrailContext = createContext<Ctx | null>(null)

export function StudioNavigationTrailProvider({ children }: { children: ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const navType = useNavigationType()
  const { mode } = useNavigationMode()
  const [recent, setRecent] = useState<StudioTrailEntry[]>([])

  const currentKey = location.pathname + location.search

  useEffect(() => {
    const key = currentKey
    const title = buildStudioHistoryTitle(location.pathname, location.search, mode)
    const entry: StudioTrailEntry = {
      key,
      pathname: location.pathname,
      search: location.search,
      title,
    }

    setRecent((prev) => {
      if (navType === 'POP') {
        const i = prev.findIndex((e) => e.key === key)
        if (i >= 0) return prev.slice(0, i + 1)
        return [...prev, entry]
      }
      if (navType === 'REPLACE') {
        if (prev.length === 0) return [entry]
        const copy = prev.slice(0, -1)
        copy.push(entry)
        return copy
      }
      // PUSH
      const last = prev[prev.length - 1]
      if (last?.key === key) {
        const c = [...prev]
        c[c.length - 1] = entry
        return c
      }
      const next = [...prev, entry]
      return next.length > MAX_ENTRIES ? next.slice(-MAX_ENTRIES) : next
    })
  }, [currentKey, location.pathname, location.search, mode, navType])

  const goBack = useCallback(() => navigate(-1), [navigate])
  const goForward = useCallback(() => navigate(1), [navigate])
  const goToEntry = useCallback(
    (e: StudioTrailEntry) => {
      navigate(e.pathname + (e.search || ''))
    },
    [navigate],
  )

  const value = useMemo(
    () => ({ recent, goBack, goForward, goToEntry, currentKey }),
    [recent, goBack, goForward, goToEntry, currentKey],
  )

  return (
    <StudioNavigationTrailContext.Provider value={value}>
      {children}
    </StudioNavigationTrailContext.Provider>
  )
}

export function useStudioNavigationTrail() {
  const c = useContext(StudioNavigationTrailContext)
  if (!c) throw new Error('useStudioNavigationTrail outside StudioNavigationTrailProvider')
  return c
}
