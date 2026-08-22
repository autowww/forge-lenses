import { Link, useLocation } from 'react-router-dom'
import {
  mergePlanningScopeIntoTo,
  parsePlanningScopeFromSearch,
} from '../../lib/planningClusterScope'
import { FULL_WORKSPACE_UI, PLANNING_CLUSTER_NAV_HINT, WORK_JOURNEY } from '../../nav/studioVisibleCopy'

type NavItem = {
  id: string
  label: string
  /** In-app route (Studio router). */
  to?: string
  /** Same-origin classic page outside SPA merge rules. */
  href?: string
  disabled?: boolean
}

function roadmapsSummaryHref(search: string): string {
  const { roadmap_p } = parsePlanningScopeFromSearch(search)
  if (!roadmap_p?.trim()) return '/roadmaps/summary'
  return `/roadmaps/summary?${new URLSearchParams({ p: roadmap_p.trim() }).toString()}`
}

function planningClusterItemActive(
  itemId: string,
  loc: { pathname: string; search: string },
): boolean {
  const q = loc.search.startsWith('?') ? loc.search.slice(1) : loc.search
  const tab = new URLSearchParams(q).get('tab') || 'plan'
  switch (itemId) {
    case 'plan':
      return loc.pathname === '/plan' && tab === 'plan'
    case 'today':
      return loc.pathname === '/plan' && tab === 'today'
    case 'story':
      return loc.pathname === '/plan' && tab === 'story'
    case 'matrix':
      return loc.pathname === '/plan/matrix'
    case 'wbs':
      return loc.pathname === '/wbs'
    case 'wbsDoc':
      return loc.pathname === '/wbs/view'
    case 'timeline':
      return loc.pathname === '/timeline'
    case 'sources':
      return loc.pathname === '/plan' && tab === 'source'
    case 'boards':
      return loc.pathname === '/board' || loc.pathname.startsWith('/board/')
    case 'readiness':
      return loc.pathname === '/knowledge/methodology/readiness'
    case 'roadmapSection':
      return loc.pathname === '/roadmap-section'
    case 'roadmapSummary':
      return false
    default:
      return false
  }
}

function disabledHint(item: NavItem, hasWbs: boolean): string | undefined {
  if (!item.disabled) return undefined
  if (item.id === 'wbsDoc' || item.id === 'story') {
    if (!hasWbs) return 'Select a work backlog on Plan first'
  }
  return undefined
}

function NavRow({
  items,
  pathname,
  search,
  ariaLabelledBy,
}: {
  items: NavItem[]
  pathname: string
  search: string
  ariaLabelledBy: string
}) {
  const scope = parsePlanningScopeFromSearch(search)
  const hasWbs = Boolean(scope.wbs_p)

  return (
    <ul className="le-planning-cluster-nav__list" aria-labelledby={ariaLabelledBy}>
      {items.map((item, i) => {
        const resolvedTo = item.to != null ? mergePlanningScopeIntoTo(item.to, search) : undefined
        const active = planningClusterItemActive(item.id, { pathname, search })
        const linkClass = `le-planning-cluster-nav__link${active ? ' le-planning-cluster-nav__link--active' : ''}`

        return (
          <li key={item.id} className="le-planning-cluster-nav__item">
            {i > 0 ? (
              <span className="le-planning-cluster-nav__sep" aria-hidden>
                ·
              </span>
            ) : null}
            {item.disabled ? (
              <span
                className={`${linkClass} le-planning-cluster-nav__link--disabled`}
                title={disabledHint(item, hasWbs)}
              >
                {item.label}
              </span>
            ) : item.href ? (
              <a
                href={item.href}
                className={`${linkClass} le-planning-cluster-nav__link--classic`}
                title={FULL_WORKSPACE_UI.navHint}
              >
                {item.label}
              </a>
            ) : resolvedTo ? (
              <Link to={resolvedTo} className={linkClass} aria-current={active ? 'page' : undefined}>
                {item.label}
              </Link>
            ) : null}
          </li>
        )
      })}
    </ul>
  )
}

/**
 * In-page Work journey (Sprint UX4): one primary strip; matrix / WBS / classic roadmaps in “Advanced & more”.
 * Preserves `repo`, `wbs_p`, `roadmap_p`, and `id` from the current URL where merge rules allow.
 */
export function PlanningClusterLocalNav() {
  const { pathname, search } = useLocation()
  const scope = parsePlanningScopeFromSearch(search)
  const hasWbs = Boolean(scope.wbs_p)

  const primary: NavItem[] = [
    { id: 'today', label: WORK_JOURNEY.today, to: '/plan?tab=today' },
    { id: 'plan', label: WORK_JOURNEY.plan, to: '/plan' },
    { id: 'boards', label: WORK_JOURNEY.boards, to: '/board' },
    { id: 'timeline', label: WORK_JOURNEY.timeline, to: '/timeline' },
    { id: 'story', label: WORK_JOURNEY.story, to: '/plan?tab=story' },
    { id: 'sources', label: WORK_JOURNEY.sources, to: '/plan?tab=source' },
    { id: 'readiness', label: WORK_JOURNEY.readiness, to: '/knowledge/methodology/readiness' },
  ]

  const advanced: NavItem[] = [
    { id: 'matrix', label: WORK_JOURNEY.matrix, to: '/plan/matrix' },
    { id: 'wbs', label: WORK_JOURNEY.wbs, to: '/wbs' },
    {
      id: 'wbsDoc',
      label: WORK_JOURNEY.wbsFile,
      to: '/wbs/view',
      disabled: !hasWbs,
    },
    { id: 'roadmapSection', label: 'Roadmap section', to: '/roadmap-section' },
    { id: 'roadmapSummary', label: 'Roadmaps summary', href: roadmapsSummaryHref(search) },
  ]

  return (
    <nav className="le-planning-cluster-nav" aria-label="Work journey for this scope">
      <div className="le-planning-cluster-nav__row">
        <span id="le-work-journey-primary-label" className="le-glossary-sr-only">
          Primary Work steps: today, plan summary, boards, timeline, story, sources, readiness
        </span>
        <NavRow
          items={primary}
          pathname={pathname}
          search={search}
          ariaLabelledBy="le-work-journey-primary-label"
        />
      </div>
      <details className="le-planning-cluster-nav__more">
        <summary className="le-planning-cluster-nav__more-summary">Advanced & more</summary>
        <div className="le-planning-cluster-nav__more-body">
          <span id="le-work-journey-advanced-label" className="le-glossary-sr-only">
            Advanced and legacy workspace tools
          </span>
          <NavRow
            items={advanced}
            pathname={pathname}
            search={search}
            ariaLabelledBy="le-work-journey-advanced-label"
          />
          <p className="le-planning-cluster-nav__more-note forge-support">
            Matrix, file-level WBS, roadmap HTML previews, and the classic roadmaps summary — optional paths that keep
            the same scope when possible.
          </p>
        </div>
      </details>
      <p className="le-planning-cluster-nav__hint">{PLANNING_CLUSTER_NAV_HINT}</p>
    </nav>
  )
}
