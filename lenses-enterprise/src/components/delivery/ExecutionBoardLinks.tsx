import { Link, useLocation } from 'react-router-dom'
import { mergePlanningScopeIntoTo } from '../../lib/planningClusterScope'
import { DELIVERY_LENS, STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

type Props = {
  repoHint: string
}

/**
 * Today tab: boards are native Delivery; timeline is an explicit planning shortcut.
 */
export function ExecutionBoardLinks({ repoHint }: Props) {
  const { search } = useLocation()
  const q = repoHint.trim() ? `?project=${encodeURIComponent(repoHint.trim())}` : ''
  const timelineTo = mergePlanningScopeIntoTo('/timeline', search)

  return (
    <section className="le-delivery-section" aria-labelledby="le-delivery-board-h">
      <h2 id="le-delivery-board-h" className="le-delivery-section__title">
        {DELIVERY_LENS.executionSectionTitle}
      </h2>
      <p className="le-delivery-section__lead">{DELIVERY_LENS.executionSectionLead}</p>
      <div className="le-delivery-cards">
        <Link className="le-delivery-card le-delivery-card--primary" to={`/board${q}`}>
          <span className="le-delivery-card__title">{STUDIO_VOCAB.boards}</span>
          <span className="le-delivery-card__hint">Hub: active, stale, templates, create</span>
        </Link>
        <Link className="le-delivery-card" to={timelineTo}>
          <span className="le-delivery-card__title">
            {STUDIO_VOCAB.timeline}{' '}
            <span className="le-shortcut-pill">Planning shortcut</span>
          </span>
          <span className="le-delivery-card__hint">Schedule view under Plans—scope merged when possible</span>
        </Link>
      </div>
    </section>
  )
}
