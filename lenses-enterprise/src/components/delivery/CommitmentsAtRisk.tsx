import { Link } from 'react-router-dom'
import { parseTodayCharge, commitmentsAtRiskCounts } from '../../lib/todayCharge'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'
import { SparkTable } from './TodayChargeView'

type Props = {
  payload: Record<string, unknown> | null
}

export function CommitmentsAtRisk({ payload }: Props) {
  const { sections } = parseTodayCharge(payload)
  const counts = commitmentsAtRiskCounts(sections)
  const activeRows = sections.active ?? []
  const preview = activeRows.slice(0, 8)

  return (
    <section className="le-delivery-section" aria-labelledby="le-delivery-risk-h">
      <h2 id="le-delivery-risk-h" className="le-delivery-section__title">
        Commitments at risk
      </h2>
      <p className="le-delivery-section__lead">
        Active sparks are in flight; blocked items need unblock work. Counts come from today-charge sections.
      </p>
      {!payload ? (
        <p className="le-delivery-section__empty">Load a WBS scope to see today-charge.</p>
      ) : (
        <>
          <ul className="le-delivery-kpis">
            <li>
              <strong>{counts.active}</strong> active
            </li>
            <li>
              <strong>{counts.blocked}</strong> blocked
            </li>
            <li>
              <strong>{counts.pendingVersona}</strong> pending Versona
            </li>
          </ul>
          {preview.length > 0 ? (
            <>
              <h3 className="le-delivery-subtitle">Active queue (preview)</h3>
              <SparkTable rows={preview} />
            </>
          ) : (
            <p className="le-delivery-section__empty">No active rows in this payload.</p>
          )}
          <p className="le-delivery-section__actions forge-support">
            <Link className="le-delivery-link" to="/board">
              Open {STUDIO_VOCAB.boards}
            </Link>
            {' · '}
            <Link className="le-delivery-link" to="/projects?filter=attention">
              {STUDIO_VOCAB.projects} (attention)
            </Link>
          </p>
        </>
      )}
    </section>
  )
}
