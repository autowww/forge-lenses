import type { NavMode } from './workspaceLensCookie'
import type { TopSectionId } from './navPlacementTypes'
import { getNavMeta } from './routeMeta'

const VALID_IDS = new Set<TopSectionId>(['home', 'work', 'projects', 'knowledge', 'publish'])

/** Active top-level section for top + left nav (aligned with `getNavMeta().groupId`). */
export function resolveTopSection(
  pathname: string,
  search: string,
  mode: NavMode,
): TopSectionId {
  const { groupId } = getNavMeta(pathname, search, mode)
  return VALID_IDS.has(groupId as TopSectionId) ? (groupId as TopSectionId) : 'home'
}
