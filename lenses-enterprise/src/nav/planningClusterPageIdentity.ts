import type { NavMode } from './workspaceLensCookie'
import { parsePlanningEntrySource, type PlanningEntrySource } from '../lib/planningClusterScope'
import { PLANNING_CLUSTER_ENTRY } from './studioVisibleCopy'
import { getStudioRouteDefinition } from './studioRouteRegistry'

export { parsePlanningEntrySource, type PlanningEntrySource }

export function planningEntryHint(source: PlanningEntrySource | null): string | null {
  if (source === 'delivery') return PLANNING_CLUSTER_ENTRY.delivery
  if (source === 'boards') return PLANNING_CLUSTER_ENTRY.boards
  return null
}

export type PlanningClusterPageIdentity = {
  routeId: string
  title: string
  subtitle: string | undefined
  storyWorkItemLine: string | null
  entryHint: string | null
}

/**
 * Page chrome for the planning cluster: H1 + subtitle align with `studioRouteRegistry` (same source as breadcrumbs
 * and `document.title`, modulo Story id suffix in title).
 */
export function getPlanningClusterPageIdentity(
  pathname: string,
  search: string,
  _mode: NavMode,
): PlanningClusterPageIdentity {
  void _mode
  const def = getStudioRouteDefinition(pathname, search)
  const q = search.startsWith('?') ? search.slice(1) : search
  const sp = new URLSearchParams(q)

  let title = def.canonicalTitle
  let storyWorkItemLine: string | null = null
  if (pathname === '/plan' && sp.get('tab') === 'story') {
    const id = sp.get('id')?.trim()
    if (id) storyWorkItemLine = `Work item: ${id}`
  }

  return {
    routeId: def.id,
    title,
    subtitle: def.subtitle,
    storyWorkItemLine,
    entryHint: planningEntryHint(parsePlanningEntrySource(search)),
  }
}
