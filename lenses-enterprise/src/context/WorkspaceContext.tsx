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
import { getWorkspaceState, type WorkspaceState } from '../api/workspace'
import { resolveUxFailure, workspaceInvalidEnvelopeUx } from '../lib/uxPageState'

type Ctx = {
  state: WorkspaceState | null
  loading: boolean
  /** Background rescan while UI stays mounted */
  softRefreshing: boolean
  /** Short headline when workspace bootstrap failed */
  error: string | null
  /** Plain-language detail shown under the headline (splash / fallbacks) */
  errorDescription: string | null
  /** Diagnostics for “Show technical details” */
  errorDetail: string | null
  refresh: (opts?: { soft?: boolean }) => Promise<void>
}

const WorkspaceContext = createContext<Ctx | null>(null)

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<WorkspaceState | null>(null)
  const [loading, setLoading] = useState(true)
  const [softRefreshing, setSoftRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [errorDescription, setErrorDescription] = useState<string | null>(null)
  const [errorDetail, setErrorDetail] = useState<string | null>(null)
  const stateRef = useRef<WorkspaceState | null>(null)
  stateRef.current = state

  const refresh = useCallback(async (opts?: { soft?: boolean }) => {
    const soft = Boolean(opts?.soft) && stateRef.current != null
    if (soft) {
      setSoftRefreshing(true)
    } else {
      setLoading(true)
    }
    setError(null)
    setErrorDescription(null)
    setErrorDetail(null)
    try {
      const s = await getWorkspaceState(true)
      if (s == null || typeof s !== 'object' || Array.isArray(s)) {
        const inv = workspaceInvalidEnvelopeUx()
        setError(inv.title)
        setErrorDescription(inv.description)
        setErrorDetail(inv.technical)
        if (!soft) setState(null)
      } else {
        setState(s)
      }
    } catch (e) {
      const ux = resolveUxFailure(e)
      setError(ux.title)
      setErrorDescription(ux.description)
      setErrorDetail(ux.technical)
      if (!soft) setState(null)
    } finally {
      setLoading(false)
      setSoftRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const value = useMemo(
    () => ({
      state,
      loading,
      softRefreshing,
      error,
      errorDescription,
      errorDetail,
      refresh,
    }),
    [state, loading, softRefreshing, error, errorDescription, errorDetail, refresh],
  )

  return (
    <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
  )
}

export function useWorkspace() {
  const c = useContext(WorkspaceContext)
  if (!c) throw new Error('useWorkspace outside WorkspaceProvider')
  return c
}

/** Same context as ``useWorkspace`` but ``null`` outside ``WorkspaceProvider`` (optional embeds). */
export function useWorkspaceOptional(): Ctx | null {
  return useContext(WorkspaceContext)
}
