import { NavLink, useLocation } from 'react-router-dom'
import { useForgesdlcBlog } from '../context/ForgesdlcBlogContext'
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
              {item.id === 'publish' && unreadCount > 0 ? (
                <span
                  className="le-badge le-badge--dirty le-top-nav__badge"
                  title={`${unreadCount} unread blog post${unreadCount === 1 ? '' : 's'} in the Studio feed (not a deploy count)`}
                  aria-label={`${unreadCount} unread blog posts in Studio`}
                >
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              ) : null}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
