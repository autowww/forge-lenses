import { useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { PublishHealthPopover } from './PublishHealthPopover'
import { useForgesdlcBlog } from '../context/ForgesdlcBlogContext'
import { useWorkspace } from '../context/WorkspaceContext'
import { publishHealthSummary } from '../lib/publishHealthSummary'
import { mergePlanningScopeIntoTo, stripPlanningEntryFromTo } from '../lib/planningClusterScope'
import { useNavigationMode } from '../nav/useNavigationMode'
import { getTopNav, type TopNavItem } from '../nav/navigationConfig'
import { resolveTopSection } from '../nav/resolveNavSection'

function topNavDestination(item: TopNavItem, search: string): string {
  if (item.id === 'work' && item.to.startsWith('/plan')) {
    return stripPlanningEntryFromTo(mergePlanningScopeIntoTo(item.to, search))
  }
  return item.to
}

export function TopNavigation() {
  const { mode } = useNavigationMode()
  const location = useLocation()
  const activeId = resolveTopSection(location.pathname, location.search, mode)
  const items = getTopNav(mode)
  const { unreadCount } = useForgesdlcBlog()
  const { state } = useWorkspace()
  const publishHealth = publishHealthSummary(state?.websites)
  const [publishOpen, setPublishOpen] = useState(false)
  const publishBadgeRef = useRef<HTMLButtonElement | null>(null)

  return (
    <nav className="le-top-nav" aria-label="Primary areas">
      <ul className="le-top-nav__list">
        {items.map((item) => (
          <li key={item.id}>
            <NavLink
              className={() =>
                `le-top-nav__link${activeId === item.id ? ' le-top-nav__link--active' : ''}`
              }
              to={topNavDestination(item, location.search)}
              end={item.id === 'home'}
            >
              {item.label}
              {item.id === 'publish' ? (
                <>
                  <button
                    ref={publishBadgeRef}
                    type="button"
                    className={`le-badge le-top-nav__badge le-top-nav__publish-health le-top-nav__publish-health--${publishHealth.tone}`}
                    title={`Publish health: ${publishHealth.label}`}
                    aria-label={`Publish health: ${publishHealth.label}`}
                    aria-expanded={publishOpen}
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      setPublishOpen((open) => !open)
                    }}
                  >
                    {publishHealth.label}
                  </button>
                  {unreadCount > 0 ? (
                    <span
                      className="le-badge le-badge--dirty le-top-nav__badge le-top-nav__badge--dot"
                      title={`${unreadCount} unread blog post${unreadCount === 1 ? '' : 's'} in the Studio feed`}
                      aria-label={`${unreadCount} unread blog posts`}
                    >
                      {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                  ) : null}
                </>
              ) : null}
            </NavLink>
          </li>
        ))}
      </ul>
      <PublishHealthPopover
        open={publishOpen}
        onClose={() => setPublishOpen(false)}
        websites={state?.websites}
        summary={publishHealth}
        anchorRef={publishBadgeRef}
      />
    </nav>
  )
}
