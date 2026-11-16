/**
 * Shared query fields for the planning cluster (Plan tabs, matrix, WBS, timeline, roadmap-section).
 * Preserved when navigating sidebar/local nav so scope does not reset silently.
 */
export const PLANNING_SCOPE_PARAM_KEYS = ['repo', 'wbs_p', 'roadmap_p', 'id'] as const

/** Cross-IA hint (`?from=delivery|boards`); merged like scope when absent on the target. */
export type PlanningEntrySource = 'delivery' | 'boards'

export function parsePlanningEntrySource(search: string): PlanningEntrySource | null {
  const qs = search.startsWith('?') ? search.slice(1) : search
  const v = new URLSearchParams(qs).get('from')
  if (v === 'delivery' || v === 'boards') return v
  return null
}

/** Remove `from` so explicit “Plans” top-nav does not keep a stale entry hint. */
export function stripPlanningEntryFromTo(to: string): string {
  const qi = to.indexOf('?')
  if (qi < 0) return to
  const path = to.slice(0, qi)
  const sp = new URLSearchParams(to.slice(qi + 1))
  sp.delete('from')
  const s = sp.toString()
  return s ? `${path}?${s}` : path
}

export type PlanningScopeKey = (typeof PLANNING_SCOPE_PARAM_KEYS)[number]

export function parsePlanningScopeFromSearch(search: string): Record<string, string> {
  const qs = search.startsWith('?') ? search.slice(1) : search
  const sp = new URLSearchParams(qs)
  const out: Record<string, string> = {}
  for (const k of PLANNING_SCOPE_PARAM_KEYS) {
    const v = sp.get(k)
    if (v != null && v !== '') out[k] = v
  }
  return out
}

/** Studio routes that participate in the planning cluster (pathname only). */
export function isPlanningClusterPathname(pathname: string): boolean {
  if (pathname === '/plan' || pathname.startsWith('/plan/')) return true
  if (pathname === '/wbs' || pathname.startsWith('/wbs/')) return true
  if (pathname === '/timeline') return true
  if (pathname === '/roadmap-section') return true
  return false
}

/** Paths where Work scope (`repo`, `wbs_p`, …) should carry from the current URL (includes boards + readiness in Work). */
export function isWorkScopeMergePathname(pathname: string): boolean {
  if (isPlanningClusterPathname(pathname)) return true
  if (pathname === '/knowledge/methodology/readiness') return true
  if (pathname === '/board' || pathname.startsWith('/board/')) return true
  return false
}

function pathnameOfTo(to: string): string {
  const q = to.indexOf('?')
  const path = (q < 0 ? to : to.slice(0, q)) || '/'
  return path.startsWith('/') ? path : `/${path}`
}

/**
 * Merge current planning scope into a sidebar or NavLink `to` string.
 * Query keys already present on the target win (explicit link intent).
 * For `/wbs/view`, copies `wbs_p` into `p` when `p` is absent so the file viewer opens the same backlog.
 */
export function mergePlanningScopeIntoTo(to: string, currentSearch: string): string {
  const scope = parsePlanningScopeFromSearch(currentSearch)
  if (Object.keys(scope).length === 0) return to

  const pathOnly = pathnameOfTo(to)
  if (!isWorkScopeMergePathname(pathOnly)) return to

  const q = to.indexOf('?')
  const target = new URLSearchParams(q >= 0 ? to.slice(q + 1) : '')

  for (const k of PLANNING_SCOPE_PARAM_KEYS) {
    const v = scope[k]
    if (v !== undefined && !target.has(k)) target.set(k, v)
  }

  if (pathOnly === '/wbs/view' && !target.get('p') && scope.wbs_p) {
    target.set('p', scope.wbs_p)
  }

  const fromSrc = parsePlanningEntrySource(currentSearch)
  if (fromSrc && !target.has('from')) target.set('from', fromSrc)

  const s = target.toString()
  return s ? `${pathOnly}?${s}` : pathOnly
}

/** NavLink `end`: `/plan` must not stay active on `/plan/matrix`. */
export function studioNavLinkEnd(to: string): boolean {
  const path = pathnameOfTo(to)
  if (path === '/') return true
  if (path === '/plan') return true
  return false
}
