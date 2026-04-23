import { NavLink, useLocation } from 'react-router-dom'
import { useNavigationMode } from '../nav/useNavigationMode'
import { getBreadcrumbSegments } from '../nav/routeMeta'

export function BreadcrumbBar() {
  const { mode } = useNavigationMode()
  const location = useLocation()
  const segments = getBreadcrumbSegments(location.pathname, location.search, mode)

  if (
    segments.length <= 1 ||
    (location.pathname === '/' &&
      segments[0]?.label === 'Workspace' &&
      segments[1]?.label === 'Overview')
  ) {
    return null
  }

  return (
    <div className="le-breadcrumb" aria-label="Breadcrumb">
      {segments.map((seg, i) => {
        const isLast = i === segments.length - 1
        return (
          <span key={`${seg.label}-${i}`} className="le-breadcrumb__segment">
            {i > 0 && (
              <span className="le-breadcrumb__sep" aria-hidden="true">
                {'\u00a0/\u00a0'}
              </span>
            )}
            {isLast ? (
              <span className="le-breadcrumb__current">{seg.label}</span>
            ) : seg.href ? (
              <NavLink className="le-breadcrumb__link" to={seg.href} end={seg.href === '/'}>
                {seg.label}
              </NavLink>
            ) : (
              <span className="le-breadcrumb__plain">{seg.label}</span>
            )}
          </span>
        )
      })}
    </div>
  )
}
