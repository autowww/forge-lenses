import { useEffect } from 'react'
import {
  useSetLensesCopilotPageScope,
  type LensesCopilotPageScope,
} from '../context/LensesCopilotPageScopeContext'

function relatedMdRelPathsKey(paths: string[] | undefined): string {
  if (!paths || paths.length === 0) return ''
  return [...paths].map((s) => s.trim()).filter(Boolean).sort().join('\n')
}

/** Register the current page with the global Lenses Copilot rail (route + optional scope + default prompt). */
export function useLensesCopilotPage(scope: LensesCopilotPageScope) {
  const setScope = useSetLensesCopilotPageScope()
  useEffect(() => {
    setScope(scope)
  }, [
    setScope,
    scope.route,
    scope.projectSlug,
    scope.entityId,
    scope.scopeSite,
    scope.defaultQuery,
    scope.pageContextSummary,
    relatedMdRelPathsKey(scope.relatedMdRelPaths),
  ])
}
