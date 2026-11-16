import { Link } from 'react-router-dom'

type Props = {
  today: Record<string, unknown> | null
  wbsSelected: boolean
  onOpenTodayTab: () => void
}

export function DecisionsWaiting({ today, wbsSelected, onOpenTodayTab }: Props) {
  const charge = today?.charge as { view_href?: string; hat?: string; date?: string } | undefined
  const sections = today?.sections as Record<string, Record<string, unknown>[]> | undefined
  const blocked = sections?.blocked?.length ?? 0
  const active = sections?.active?.length ?? 0
  const pendingVers = sections?.pending_versona?.length ?? 0

  return (
    <section className="le-plan-section" aria-labelledby="le-plan-decisions-h">
      <h2 id="le-plan-decisions-h" className="le-plan-section__title">
        Decisions waiting
      </h2>
      <p className="le-plan-section__lead">
        Signals from today-charge when loaded: charge file, blockers, and pending Versona items.
      </p>
      {!wbsSelected ? (
        <p className="le-plan-section__empty">Select a WBS to load Today data.</p>
      ) : !today ? (
        <p className="le-plan-section__empty">Loading today-charge… or none returned.</p>
      ) : (
        <ul className="le-plan-decisions">
          {charge && (
            <li>
              Charge: {charge.hat ?? '—'} {charge.date ?? ''}
              {charge.view_href ? (
                <>
                  {' '}
                  <a href={charge.view_href}>Open charge.md</a>
                </>
              ) : null}
            </li>
          )}
          <li>
            Active items: <strong>{active}</strong> · Blocked: <strong>{blocked}</strong> · Pending Versona:{' '}
            <strong>{pendingVers}</strong>
          </li>
          <li>
            <button type="button" className="le-btn" onClick={onOpenTodayTab}>
              Open Today tab
            </button>
          </li>
          <li>
            <Link to="/workspace-md">Workspace notes</Link>
          </li>
        </ul>
      )}
    </section>
  )
}
