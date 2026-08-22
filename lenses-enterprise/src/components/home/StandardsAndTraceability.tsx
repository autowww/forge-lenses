import { Link } from 'react-router-dom'
import type { WorkspaceChild } from '../../api/workspace'
import type { RepoPortfolioRow } from '../../lib/workspacePortfolio'

type Props = {
  childrenList: WorkspaceChild[]
  portfolioRows: RepoPortfolioRow[]
}

export function StandardsAndTraceability({ childrenList, portfolioRows }: Props) {
  const git = childrenList.filter((c) => c.is_git)
  const withScore = git.filter(
    (c) => c.standards_compliance && typeof c.standards_compliance.score === 'number',
  )
  const pctWithScore =
    git.length === 0 ? null : Math.round((withScore.length / git.length) * 100)
  const avg =
    withScore.length === 0
      ? null
      : Math.round(
          withScore.reduce(
            (acc, c) => acc + (c.standards_compliance?.score ?? 0),
            0,
          ) / withScore.length,
        )

  const weakest = [...portfolioRows]
    .sort((a, b) => {
      const as = a.standardsScore ?? 999
      const bs = b.standardsScore ?? 999
      return as - bs
    })
    .slice(0, 5)

  const totalEvidence = portfolioRows.reduce((acc, r) => acc + r.evidenceFlags, 0)
  const reposWithEvidence = portfolioRows.filter((r) => r.evidenceFlags > 0).length

  return (
    <section className="le-cc-section" aria-labelledby="le-cc-standards">
      <h2 id="le-cc-standards" className="le-cc-section__title">
        Standards and traceability
      </h2>
      <p className="le-cc-section__lead">
        Layout compliance scores from the workspace scan; traceability counts forge charge, journal,
        Versona, and Ember log artifacts when present under each repo.
      </p>
      <div className="le-cc-stats-row">
        <div className="le-cc-stat">
          <span className="le-cc-stat__value">{pctWithScore != null ? `${pctWithScore}%` : '—'}</span>
          <span className="le-cc-stat__label">Repos with a standards score</span>
        </div>
        <div className="le-cc-stat">
          <span className="le-cc-stat__value">{avg != null ? `${avg}` : '—'}</span>
          <span className="le-cc-stat__label">Average score (where measured)</span>
        </div>
        <div className="le-cc-stat">
          <span className="le-cc-stat__value">{reposWithEvidence}</span>
          <span className="le-cc-stat__label">Repos with traceability artifacts</span>
        </div>
        <div className="le-cc-stat">
          <span className="le-cc-stat__value">{totalEvidence}</span>
          <span className="le-cc-stat__label">Artifact flags (charge, journal, Versona, Ember)</span>
        </div>
      </div>
      {weakest.length > 0 && (
        <>
          <h3 className="le-cc-subtitle">Weakest standards (by score)</h3>
          <ul className="le-cc-list">
            {weakest.map((r) => (
              <li key={r.name}>
                <Link to={`/projects/${encodeURIComponent(r.name)}`}>{r.name}</Link>
                {' — '}
                {r.standardsScore != null ? (
                  <span className="le-mono">{r.standardsScore}</span>
                ) : (
                  'no score'
                )}
                {r.standardsTier ? <span className="le-muted"> · {r.standardsTier}</span> : null}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
