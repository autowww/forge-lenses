import { NavLink, useLocation } from 'react-router-dom'
import { useMemo } from 'react'
import { useNavigationMode } from '../nav/useNavigationMode'
import { getBreadcrumbSegments } from '../nav/routeMeta'
import { useWorkspace } from '../context/WorkspaceContext'

function workspaceLabelFromRoot(root: string | undefined): string {
  const trimmed = root?.trim()
  if (!trimmed) return 'Workspace'
  const parts = trimmed.replace(/[/\\]+$/, '').split(/[/\\]/)
  return parts[parts.length - 1] || 'Workspace'
}

export function BreadcrumbBar() {
  const { mode } = useNavigationMode()
  const location = useLocation()
  const { state } = useWorkspace()
  const workspaceLabel = useMemo(
    () => workspaceLabelFromRoot(state?.workspace_root),
    [state?.workspace_root],
  )
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
      <span className="le-breadcrumb__workspaceLabel le-muted" title={state?.workspace_root ?? undefined}>
        {workspaceLabel}
      </span>
      <span className="le-breadcrumb__sep" aria-hidden="true">
        {'\u00a0/\u00a0'}
      </span>
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
