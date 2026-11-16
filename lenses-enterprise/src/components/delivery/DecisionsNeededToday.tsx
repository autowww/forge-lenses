import { Link } from 'react-router-dom'
import { parseTodayCharge, commitmentsAtRiskCounts } from '../../lib/todayCharge'

type Props = {
  payload: Record<string, unknown> | null
  wbsSelected: boolean
}

export function DecisionsNeededToday({ payload, wbsSelected }: Props) {
  const { charge, sections } = parseTodayCharge(payload)
  const counts = commitmentsAtRiskCounts(sections)

  return (
    <section className="le-delivery-section" aria-labelledby="le-delivery-dec-h">
      <h2 id="le-delivery-dec-h" className="le-delivery-section__title">
        Decisions needed today
      </h2>
      <p className="le-delivery-section__lead">
        Charge file, blocked work, and pending Versona reviews usually need explicit decisions or owners.
      </p>
      {!wbsSelected ? (
        <p className="le-delivery-section__empty">Select a WBS in scope to load charge signals.</p>
      ) : !payload ? (
        <p className="le-delivery-section__empty">Loading…</p>
      ) : (
        <ul className="le-delivery-decisions">
          {charge?.view_href ? (
            <li>
              <a href={charge.view_href}>Review charge.md</a> ({charge.hat ?? 'charge'} {charge.date ?? ''})
            </li>
          ) : (
            <li>No charge link in payload.</li>
          )}
          <li>
            <strong>{counts.blocked}</strong> blocked item(s) need unblock decisions.
          </li>
          <li>
            <strong>{counts.pendingVersona}</strong> pending Versona session(s).
          </li>
          <li>
            <Link to="/workspace-md">Workspace notes</Link>
          </li>
        </ul>
      )}
    </section>
  )
}
