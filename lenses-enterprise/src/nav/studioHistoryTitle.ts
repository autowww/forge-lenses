import type { NavMode } from './workspaceLensCookie'
import { getStudioTitleTrail } from './studioRouteRegistry'

/** Short label for session history / recent pages menu (aligned with `document.title` trail, no product suffix). */
export function buildStudioHistoryTitle(pathname: string, search: string, mode: NavMode): string {
  return getStudioTitleTrail(pathname, search, mode)
}
