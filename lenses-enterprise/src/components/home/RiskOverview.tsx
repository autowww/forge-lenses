import { Link } from 'react-router-dom'
import type { RepoPortfolioRow } from '../../lib/workspacePortfolio'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

type Props = {
  rows: RepoPortfolioRow[]
}

export function RiskOverview({ rows }: Props) {
  return (
    <section className="le-cc-section" aria-labelledby="le-cc-risk">
      <h2 id="le-cc-risk" className="le-cc-section__title">
        Risk and blockers
      </h2>
      <p className="le-cc-section__lead">
        Quick scan of factors per repository. Open a row for git and strategy detail, or{' '}
        <Link className="le-cc-link" to="/projects?filter=attention">
          filter {STUDIO_VOCAB.projects.toLowerCase()} to attention
        </Link>{' '}
        /{' '}
        <Link className="le-cc-link" to="/projects?filter=dirty">
          dirty trees
        </Link>
        .
      </p>
      {rows.length === 0 ? (
        <p className="le-cc-section__empty">Nothing to show.</p>
      ) : (
        <ul className="le-cc-risk-list">
          {rows.map((r) => (
            <li key={r.name} className="le-cc-risk-row">
              <Link className="le-cc-risk-name" to={`/projects/${encodeURIComponent(r.name)}`}>
                {r.name}
              </Link>
              <span className="le-cc-risk-chips">
                {r.dirty ? (
                  <span className="le-badge le-badge--dirty">Dirty</span>
                ) : (
                  <span className="le-cc-chip le-cc-chip--ok">Clean</span>
                )}
                {r.standardsTier === 'minimal' || (r.standardsScore != null && r.standardsScore < 70) ? (
                  <span className="le-cc-chip le-cc-chip--warn">Standards gap</span>
                ) : (
                  <span className="le-cc-chip le-cc-chip--ok">Standards OK</span>
                )}
                {r.roadmapCount === 0 ? (
                  <span className="le-cc-chip le-cc-chip--warn">No roadmap indexed</span>
                ) : (
                  <span className="le-cc-chip le-cc-chip--ok">Roadmap</span>
                )}
                {r.wbsCount === 0 ? (
                  <span className="le-cc-chip le-cc-chip--warn">No WBS</span>
                ) : (
                  <span className="le-cc-chip le-cc-chip--ok">WBS</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
