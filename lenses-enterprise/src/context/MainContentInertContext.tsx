import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

type MainContentInertCtx = {
  /** When true, the main studio chrome (header + shell) is inert — use with a portaled modal. */
  mainContentInert: boolean
  setMainContentInert: (v: boolean) => void
}

const MainContentInertContext = createContext<MainContentInertCtx | null>(null)

export function MainContentInertProvider({ children }: { children: ReactNode }) {
  const [mainContentInert, setMainContentInertState] = useState(false)
  const setMainContentInert = useCallback((v: boolean) => {
    setMainContentInertState(v)
  }, [])

  const value = useMemo(
    () => ({ mainContentInert, setMainContentInert }),
    [mainContentInert, setMainContentInert],
  )

  return (
    <MainContentInertContext.Provider value={value}>{children}</MainContentInertContext.Provider>
  )
}

export function useMainContentInert() {
  const c = useContext(MainContentInertContext)
  if (!c) throw new Error('useMainContentInert must be used within MainContentInertProvider')
  return c
}
