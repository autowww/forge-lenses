import { Link } from 'react-router-dom'
import type { RepoPortfolioRow } from '../../lib/workspacePortfolio'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

type Props = {
  rows: RepoPortfolioRow[]
}

/**
 * Monday checklist band — attention → blockers → readiness for the week ahead.
 */
export function MondayChecklist({ rows }: Props) {
  const attention = rows.filter((r) => r.health === 'at_risk' || r.health === 'watch')
  const blockers = rows.filter((r) => r.dirty || r.riskScore >= 4)
  const readiness = rows.filter((r) => r.health === 'healthy')

  return (
    <section className="le-card le-monday-checklist" aria-labelledby="le-monday-checklist-h">
      <h2 id="le-monday-checklist-h" className="le-cc-section__title">
        Monday checklist
      </h2>
      <p className="le-cc-section__lead">
        Start the week with attention items, clear blockers, then confirm release readiness.
      </p>
      <ol className="le-monday-checklist__list">
        <li>
          <strong>Attention</strong> — {attention.length} repo{attention.length === 1 ? '' : 's'} need a look.{' '}
          {attention.length > 0 ? (
            <Link to="/projects?filter=attention">Review attention</Link>
          ) : (
            <span className="le-muted">None flagged</span>
          )}
        </li>
        <li>
          <strong>Blockers</strong> — {blockers.length} repo{blockers.length === 1 ? '' : 's'} with dirty trees or open PRs.{' '}
          {blockers.length > 0 ? (
            <Link to="/plan?tab=today">Open {STUDIO_VOCAB.today}</Link>
          ) : (
            <span className="le-muted">No blockers in scan</span>
          )}
        </li>
        <li>
          <strong>Readiness</strong> — {readiness.length} repo{readiness.length === 1 ? '' : 's'} look ready.{' '}
          <Link to="/knowledge/methodology/readiness">Release readiness gaps</Link>
        </li>
      </ol>
    </section>
  )
}
