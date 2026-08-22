import type { NavMode } from './workspaceLensCookie'
import type { SideNavEntry, TopSectionId } from './navPlacementTypes'
import { FULL_WORKSPACE_UI, getPrimarySectionLabel } from './studioVisibleCopy'
import { getStudioNavMeta } from './studioRouteRegistry'

export type SidebarLinkSemantics =
  | { kind: 'native' }
  | { kind: 'shortcut'; ownerSectionLabel: string }
  | { kind: 'classic'; hint: string }
  | { kind: 'external'; hint: string }

/** Split router `to` (path + optional query) for registry lookup. */
export function parseStudioTo(to: string): { pathname: string; search: string } {
  const q = to.indexOf('?')
  if (q < 0) return { pathname: to || '/', search: '' }
  return { pathname: to.slice(0, q) || '/', search: to.slice(q) }
}

/**
 * Whether a sidebar row is owned by the current primary section or is a cross-area shortcut.
 * Uses the same canonical `groupId` as breadcrumbs for the target URL.
 */
export function getSidebarLinkSemantics(
  entry: SideNavEntry,
  currentSection: TopSectionId,
  mode: NavMode,
): SidebarLinkSemantics {
  if (entry.disabled) return { kind: 'native' }
  if (entry.href) {
    if (entry.external) return { kind: 'external', hint: 'External site' }
    return { kind: 'classic', hint: FULL_WORKSPACE_UI.navHint }
  }
  if (!entry.to) return { kind: 'native' }

  const { pathname, search } = parseStudioTo(entry.to)
  const { groupId } = getStudioNavMeta(pathname, search, mode)
  if (groupId === currentSection) return { kind: 'native' }
  return { kind: 'shortcut', ownerSectionLabel: getPrimarySectionLabel(groupId) }
}

/** Accessible description for the link target (native vs shortcut disclosure). */
export function sidebarLinkAccessibleLabel(
  entry: SideNavEntry,
  semantics: SidebarLinkSemantics,
): string | undefined {
  if (entry.disabled) return undefined
  if (semantics.kind === 'shortcut') {
    return `${entry.label}, shortcut to ${semantics.ownerSectionLabel}`
  }
  if (semantics.kind === 'classic') {
    return `${entry.label}, opens ${semantics.hint} view`
  }
  if (semantics.kind === 'external') {
    return `${entry.label}, ${semantics.hint}`
  }
  return undefined
}
