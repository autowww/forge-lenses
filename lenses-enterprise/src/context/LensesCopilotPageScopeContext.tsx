import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

/** Studio route label for audit + grounding (matches former CopilotPanel `route`). */
export type LensesCopilotPageScope = {
  route: string
  projectSlug?: string
  /** True when the slug matches a child from `/api/workspace-state` (same folder as Projects). */
  projectScopeConfirmed?: boolean
  entityId?: string
  scopeSite?: string
  defaultQuery?: string
  /** Short description of what the user is looking at (prepended as a grounding citation). */
  pageContextSummary?: string
  /**
   * Workspace-relative allowlisted markdown paths (e.g. forge/charge.md, repo/forge/journal/x.md)
   * to load as early copilot grounding context. Invalid paths are ignored server-side.
   */
  relatedMdRelPaths?: string[]
}

type Ctx = {
  scope: LensesCopilotPageScope
  setScope: (s: LensesCopilotPageScope) => void
}

const LensesCopilotPageScopeContext = createContext<Ctx | null>(null)

const DEFAULT_SCOPE: LensesCopilotPageScope = { route: 'overview' }

export function LensesCopilotPageScopeProvider({ children }: { children: ReactNode }) {
  const [scope, setScopeState] = useState<LensesCopilotPageScope>(DEFAULT_SCOPE)
  const setScope = useCallback((s: LensesCopilotPageScope) => {
    setScopeState(s)
  }, [])
  const value = useMemo(() => ({ scope, setScope }), [scope, setScope])
  return (
    <LensesCopilotPageScopeContext.Provider value={value}>{children}</LensesCopilotPageScopeContext.Provider>
  )
}

export function useLensesCopilotPageScope(): LensesCopilotPageScope {
  const ctx = useContext(LensesCopilotPageScopeContext)
  if (!ctx) {
    throw new Error('useLensesCopilotPageScope must be used under LensesCopilotPageScopeProvider')
  }
  return ctx.scope
}

export function useSetLensesCopilotPageScope(): (s: LensesCopilotPageScope) => void {
  const ctx = useContext(LensesCopilotPageScopeContext)
  if (!ctx) {
    throw new Error('useSetLensesCopilotPageScope must be used under LensesCopilotPageScopeProvider')
  }
  return ctx.setScope
}
