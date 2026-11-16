import { Link, useLocation } from 'react-router-dom'
import { mergePlanningScopeIntoTo } from '../../lib/planningClusterScope'
import { DELIVERY_LENS, STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

function ShortcutPill() {
  return (
    <span className="le-shortcut-pill" title={DELIVERY_LENS.shortcutsSectionLead}>
      Shortcut
    </span>
  )
}

/**
 * On the boards hub: quick links across the unified Work journey and workspace utilities.
 */
export function BoardPlanningShortcutStrip() {
  const { search } = useLocation()

  const items: { to: string; label: string; note?: string }[] = [
    { to: mergePlanningScopeIntoTo('/plan?tab=today', search), label: STUDIO_VOCAB.today },
    { to: mergePlanningScopeIntoTo('/plan', search), label: STUDIO_VOCAB.planSummary },
    { to: mergePlanningScopeIntoTo('/timeline', search), label: STUDIO_VOCAB.timeline },
    { to: '/search', label: STUDIO_VOCAB.search },
    { to: '/workspace-md', label: STUDIO_VOCAB.workspaceNotes },
    { to: '/projects', label: STUDIO_VOCAB.projects },
  ]

  return (
    <section className="le-board-shortcuts" aria-labelledby="le-board-shortcuts-h">
      <h2 id="le-board-shortcuts-h" className="le-board-shortcuts__title">
        {DELIVERY_LENS.shortcutsSectionTitle}
      </h2>
      <p className="le-board-shortcuts__lead forge-support">{DELIVERY_LENS.shortcutsSectionLead}</p>
      <ul className="le-board-shortcuts__list">
        {items.map((it) => (
          <li key={it.to + it.label} className="le-board-shortcuts__item">
            <Link className="le-board-shortcuts__link" to={it.to}>
              {it.label}
            </Link>
            <ShortcutPill />
            {it.note ? <span className="le-board-shortcuts__note forge-support">{it.note}</span> : null}
          </li>
        ))}
      </ul>
    </section>
  )
}
