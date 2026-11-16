import { Link } from 'react-router-dom'
import type { RepoPortfolioRow } from '../../lib/workspacePortfolio'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

type Props = {
  rows: RepoPortfolioRow[]
  sitesCount: number
  hasChargeArtifact: boolean
  scanLabel: string
}

function countAttention(rows: RepoPortfolioRow[]) {
  return rows.filter((r) => r.health === 'at_risk' || r.health === 'watch').length
}

function countDirty(rows: RepoPortfolioRow[]) {
  return rows.filter((r) => r.dirty).length
}

function countEvidence(rows: RepoPortfolioRow[]) {
  return rows.filter((r) => r.evidenceFlags > 0).length
}

/**
 * Workspace home: management questions → counts → 1-click drilldowns (not a dead-end dashboard).
 */
export function WorkspaceOperationalSnapshot({
  rows,
  sitesCount,
  hasChargeArtifact,
  scanLabel,
}: Props) {
  const attention = countAttention(rows)
  const dirty = countDirty(rows)
  const evidenceRepos = countEvidence(rows)
  const watchOnly = rows.filter((r) => r.health === 'watch').length

  return (
    <section className="le-cc-section" aria-labelledby="le-cc-tower-h">
      <h2 id="le-cc-tower-h" className="le-cc-section__title">
        Operational control tower
      </h2>
      <p className="le-cc-section__lead">
        Decision center for this workspace — urgency, freshness, and ownership. Scan: {scanLabel}. This is not the
        same as {STUDIO_VOCAB.plan} detail; use the cards below to jump into execution surfaces.
      </p>
      <div className="le-cc-tower-grid" role="list">
        <Link className="le-cc-tower-card le-cc-tower-card--primary" to="/plan?tab=today" role="listitem">
          <span className="le-cc-tower-card__kicker">Now</span>
          <span className="le-cc-tower-card__title">{STUDIO_VOCAB.today}</span>
          <span className="le-cc-tower-card__hint">Commitments, blockers, boards — operational queue</span>
        </Link>
        <Link className="le-cc-tower-card" to="/search" role="listitem">
          <span className="le-cc-tower-card__kicker">Find</span>
          <span className="le-cc-tower-card__title">{STUDIO_VOCAB.search}</span>
          <span className="le-cc-tower-card__hint">Grounded lookup — portfolio charts stay under Settings (gear)</span>
        </Link>
        <Link className="le-cc-tower-card" to="/board" role="listitem">
          <span className="le-cc-tower-card__kicker">Execute</span>
          <span className="le-cc-tower-card__title">{STUDIO_VOCAB.boards}</span>
          <span className="le-cc-tower-card__hint">Sticker boards and execution view</span>
        </Link>
        <Link
          className="le-cc-tower-card"
          to={attention > 0 ? '/projects?filter=attention' : '/projects'}
          role="listitem"
        >
          <span className="le-cc-tower-card__kicker">Attention</span>
          <span className="le-cc-tower-card__title">{STUDIO_VOCAB.projects}</span>
          <span className="le-cc-tower-card__metric" aria-live="polite">
            {attention > 0 ? `${attention} need attention` : 'All clear'}
          </span>
          <span className="le-cc-tower-card__hint">At risk or watch — sorted portfolio</span>
        </Link>
        <Link className="le-cc-tower-card" to={dirty > 0 ? '/projects?filter=dirty' : '/projects'} role="listitem">
          <span className="le-cc-tower-card__kicker">Working tree</span>
          <span className="le-cc-tower-card__title">Uncommitted / dirty</span>
          <span className="le-cc-tower-card__metric" aria-live="polite">
            {dirty > 0 ? `${dirty} dirty repos` : 'No dirty trees'}
          </span>
          <span className="le-cc-tower-card__hint">Repos with local changes pending</span>
        </Link>
        <Link
          className="le-cc-tower-card"
          to={watchOnly > 0 ? '/projects?filter=attention' : '/projects'}
          role="listitem"
        >
          <span className="le-cc-tower-card__kicker">Coverage gaps</span>
          <span className="le-cc-tower-card__title">Missing roadmap or WBS</span>
          <span className="le-cc-tower-card__metric" aria-live="polite">
            {watchOnly > 0 ? `${watchOnly} on watch` : 'No watch items'}
          </span>
          <span className="le-cc-tower-card__hint">Repos flagged until roadmap/WBS lines up</span>
        </Link>
        <Link
          className="le-cc-tower-card"
          to={evidenceRepos > 0 ? '/projects?filter=evidence' : '/workspace-md'}
          role="listitem"
        >
          <span className="le-cc-tower-card__kicker">Evidence</span>
          <span className="le-cc-tower-card__title">{STUDIO_VOCAB.workspaceNotes}</span>
          <span className="le-cc-tower-card__metric" aria-live="polite">
            {evidenceRepos > 0
              ? `${evidenceRepos} repos with forge signals`
              : hasChargeArtifact
                ? 'Charge detected'
                : 'Open notes'}
          </span>
          <span className="le-cc-tower-card__hint">Markdown + forge artifacts — drill to repos or notes</span>
        </Link>
        {sitesCount > 0 ? (
          <Link className="le-cc-tower-card" to="/websites" role="listitem">
            <span className="le-cc-tower-card__kicker">Sites</span>
            <span className="le-cc-tower-card__title">{STUDIO_VOCAB.websites}</span>
            <span className="le-cc-tower-card__metric">{sitesCount} published</span>
            <span className="le-cc-tower-card__hint">Browse previews and deploy context</span>
          </Link>
        ) : null}
      </div>
    </section>
  )
}
