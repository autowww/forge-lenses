import type { NavMode } from './workspaceLensCookie'
import type { TopSectionId } from './navPlacementTypes'
import { getStudioNavMeta } from './studioRouteRegistry'

export type NavMeta = {
  groupId: TopSectionId
  breadcrumbs: string[]
  /** Parallel to `breadcrumbs`: link target for each segment, or `null` for the current page / non-link. */
  hrefs: (string | null)[]
}

export function getNavMeta(pathname: string, search: string, mode: NavMode): NavMeta {
  return getStudioNavMeta(pathname, search, mode)
}

/** Parent route for the back control: second-to-last segment’s href when present. */
export function getBackTarget(pathname: string, search: string, mode: NavMode): string | null {
  const { hrefs } = getNavMeta(pathname, search, mode)
  if (hrefs.length < 2) return null
  return hrefs[hrefs.length - 2]
}

export type BreadcrumbSegment = { label: string; href: string | null }

export function getBreadcrumbSegments(
  pathname: string,
  search: string,
  mode: NavMode,
): BreadcrumbSegment[] {
  const { breadcrumbs, hrefs } = getNavMeta(pathname, search, mode)
  return breadcrumbs.map((label, i) => ({
    label,
    href: hrefs[i] ?? null,
  }))
}

/**
 * Pathname-only lens hint (UI nudge). Not used for auto-switching — shared routes
 * (`/plan`, `/timeline`, `/board`, …) map differently per lens; lens follows the
 * workspace toggle and primary nav clicks instead.
 */
export function suggestNavModeFromPath(pathname: string): NavMode | null {
  void pathname
  return null
}

const HINT_DISMISS_KEY = 'lenses_lens_hint_dismissed'

export function isLensHintDismissed(): boolean {
  try {
    return sessionStorage.getItem(HINT_DISMISS_KEY) === '1'
  } catch {
    return false
  }
}

export function dismissLensHint(): void {
  try {
    sessionStorage.setItem(HINT_DISMISS_KEY, '1')
  } catch {
    /* ignore */
  }
}
