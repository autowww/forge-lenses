import { Link } from 'react-router-dom'
import type { RepoPortfolioRow } from '../../lib/workspacePortfolio'

type Props = {
  rows: RepoPortfolioRow[]
}

function healthLabel(health: RepoPortfolioRow['health']): string {
  if (health === 'at_risk') return 'At risk'
  if (health === 'watch') return 'Watch'
  return 'Ready'
}

/**
 * Portfolio attention strip — surfaces repos that need a look before the KPI wall.
 */
export function PortfolioAttentionStrip({ rows }: Props) {
  const attention = rows.filter((r) => r.health !== 'healthy')
  if (attention.length === 0) return null

  return (
    <section className="le-attention-strip le-panel" aria-label="Portfolio attention strip">
      <h2 className="le-panel__title" style={{ marginTop: 0 }}>
        Needs attention
      </h2>
      <p className="forge-support" style={{ marginTop: 0 }}>
        {attention.length} project(s) flagged from workspace health signals — open the dashboard for the suggested next
        step.
      </p>
      <ul className="le-attention-strip__list" style={{ margin: 0, paddingLeft: '1.25rem' }}>
        {attention.slice(0, 8).map((row) => (
          <li key={row.name} style={{ marginBottom: '0.35rem' }}>
            <Link to={`/projects/${encodeURIComponent(row.name)}`}>
              <strong>{row.name}</strong>
            </Link>
            <span className="le-attention-strip__tier le-muted" style={{ marginLeft: '0.5rem' }}>
              {healthLabel(row.health)}
            </span>
            {row.dirty ? <span className="le-muted"> · uncommitted changes</span> : null}
            {row.standardsScore != null && row.standardsScore < 70 ? (
              <span className="le-muted"> · standards {row.standardsScore}</span>
            ) : null}
          </li>
        ))}
      </ul>
      <p className="forge-support" style={{ marginBottom: 0, marginTop: '0.5rem' }}>
        <Link to="/projects?filter=attention">View all in Projects</Link>
      </p>
    </section>
  )
}
