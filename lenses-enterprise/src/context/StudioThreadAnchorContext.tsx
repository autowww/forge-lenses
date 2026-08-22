import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useLocation } from 'react-router-dom'

export type StudioThreadAnchor = {
  /** `pathname` + `search` for the last Studio screen that was not Chat. */
  threadKey: string
  pathname: string
  search: string
}

const StudioThreadAnchorContext = createContext<StudioThreadAnchor | null>(null)

const DEFAULT_ANCHOR: StudioThreadAnchor = {
  threadKey: '/',
  pathname: '/',
  search: '',
}

export function StudioThreadAnchorProvider({ children }: { children: ReactNode }) {
  const { pathname, search } = useLocation()
  const [anchor, setAnchor] = useState<StudioThreadAnchor>(DEFAULT_ANCHOR)

  useEffect(() => {
    if (pathname === '/chat' || pathname.startsWith('/chat/')) return
    const s = search || ''
    setAnchor({
      threadKey: pathname + s,
      pathname,
      search: s,
    })
  }, [pathname, search])

  const value = useMemo(() => anchor, [anchor])
  return (
    <StudioThreadAnchorContext.Provider value={value}>{children}</StudioThreadAnchorContext.Provider>
  )
}

export function useStudioThreadAnchor(): StudioThreadAnchor {
  const c = useContext(StudioThreadAnchorContext)
  if (!c) throw new Error('useStudioThreadAnchor must be used within StudioThreadAnchorProvider')
  return c
}
