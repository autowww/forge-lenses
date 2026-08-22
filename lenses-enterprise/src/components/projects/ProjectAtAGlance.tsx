import { Link } from 'react-router-dom'
import { EVIDENCE_IA, PROJECT_OBJECT_HOME, STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

/** concreteNext — map a risk line to the best Studio destination. */
function riskDestination(risk: string): string {
  const lower = risk.toLowerCase()
  if (lower.includes('evidence') || lower.includes('charge')) {
    return '/knowledge/methodology/evidence'
  }
  if (lower.includes('decision') || lower.includes('adr')) {
    return '/knowledge/methodology/decisions'
  }
  if (lower.includes('release') || lower.includes('readiness')) {
    return '/knowledge/methodology/readiness'
  }
  return '/plan?tab=today'
}

function resolveRiskLabel(risk: string): string {
  const dest = riskDestination(risk)
  if (dest.includes('evidence')) return 'Review evidence'
  if (dest.includes('decisions')) return 'Open decisions'
  if (dest.includes('readiness')) return 'Check readiness'
  return 'Open Today'
}

export type WorkItemLinkRow = {
  story_id?: string
  pr_url?: string
  branch_url?: string
  pull_request_number?: number
}

type Props = {
  encodedProject: string
  projectName: string
  evidenceHref: string
  riskLines: string[]
  nextAction: { title: string; description: string; to: string }
  metricCommits: string | number
  metricFiles: string | number
  metricOpenPrs: string | number
  workItemLinks: WorkItemLinkRow[]
  thisWeekNarrative?: string
}

/**
 * Action-first summary: snapshot, risks, next step, activity, linked work, evidence, methodology pointers.
 */
export function ProjectAtAGlance({
  encodedProject,
  projectName,
  evidenceHref,
  riskLines,
  nextAction,
  metricCommits,
  metricFiles,
  metricOpenPrs,
  workItemLinks,
  thisWeekNarrative,
}: Props) {
  const base = `/projects/${encodedProject}`
  const planHref = `/plan?repo=${encodeURIComponent(projectName)}`

  return (
    <section className="le-project-at-a-glance" aria-labelledby="le-project-at-a-glance-h">
      <h2 id="le-project-at-a-glance-h" className="le-project-at-a-glance__title">
        {PROJECT_OBJECT_HOME.atAGlanceTitle}
      </h2>
      <div className="le-project-at-a-glance__grid">
        <div className="le-project-at-a-glance__card">
          <h3 className="le-project-at-a-glance__card-title">{PROJECT_OBJECT_HOME.atAGlanceMetricsTitle}</h3>
          <div className="le-stats le-stats--compact">
            <div className="le-stat">
              <span className="le-stat__value">{metricCommits}</span>
              <span className="le-stat__label">Commits (HEAD)</span>
            </div>
            <div className="le-stat">
              <span className="le-stat__value">{metricFiles}</span>
              <span className="le-stat__label">Tracked files</span>
            </div>
            <div className="le-stat">
              <span className="le-stat__value">{metricOpenPrs}</span>
              <span className="le-stat__label">Open PRs</span>
            </div>
          </div>
        </div>

        <div className="le-project-at-a-glance__card">
          <h3 className="le-project-at-a-glance__card-title">{PROJECT_OBJECT_HOME.atAGlanceRisksTitle}</h3>
          {riskLines.length > 0 ? (
            <ul className="le-project-at-a-glance__list">
              {riskLines.map((t) => (
                <li key={t}>
                  {t}{' '}
                  <Link className="le-project-at-a-glance__concreteNext" to={riskDestination(t)}>
                    {resolveRiskLabel(t)} →
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="forge-support" style={{ margin: 0 }}>
              {PROJECT_OBJECT_HOME.atAGlanceRisksEmpty}
            </p>
          )}
        </div>

        <div className="le-project-at-a-glance__card le-project-at-a-glance__card--wide">
          <h3 className="le-project-at-a-glance__card-title">This week</h3>
          <p className="forge-support" style={{ margin: 0 }}>
            {thisWeekNarrative ??
              (riskLines.length > 0
                ? `Focus on ${riskLines[0]?.toLowerCase() ?? 'open risks'} before expanding scope — charts and strategy stay one click away when you need depth.`
                : `No urgent flags in the latest scan for ${projectName}. Keep charge and evidence current, then use ${STUDIO_VOCAB.today} for delivery execution.`)}
          </p>
        </div>

        <div className="le-project-at-a-glance__card le-project-at-a-glance__card--cta">
          <h3 className="le-project-at-a-glance__card-title">{PROJECT_OBJECT_HOME.atAGlanceNextTitle}</h3>
          <p className="le-project-at-a-glance__lead">{nextAction.description}</p>
          <Link className="le-btn le-btn--primary" to={nextAction.to}>
            {nextAction.title}
          </Link>
        </div>

        <div className="le-project-at-a-glance__card le-project-at-a-glance__card--wide">
          <h3 className="le-project-at-a-glance__card-title">{PROJECT_OBJECT_HOME.atAGlanceRecentTitle}</h3>
          <p className="forge-support" style={{ margin: '0 0 0.5rem' }}>
            {PROJECT_OBJECT_HOME.atAGlanceRecentLead}
          </p>
          <p className="forge-support" style={{ margin: 0, fontSize: '0.88rem' }}>
            <Link to={`${base}/charts`}>{STUDIO_VOCAB.repositoryCharts}</Link>
            {' · '}
            <Link to={`${base}/strategy`}>{STUDIO_VOCAB.architectureStrategy}</Link>
            {' · '}
            <Link to="/plan?tab=today">{STUDIO_VOCAB.today}</Link>
            {' · '}
            <Link to={planHref}>{STUDIO_VOCAB.planSummary}</Link>
          </p>
        </div>

        <div className="le-project-at-a-glance__card le-project-at-a-glance__card--wide">
          <h3 className="le-project-at-a-glance__card-title">{PROJECT_OBJECT_HOME.atAGlanceLinkedWorkTitle}</h3>
          {workItemLinks.length > 0 ? (
            <ul className="le-project-at-a-glance__list le-project-at-a-glance__list--links">
              {workItemLinks.map((li) => (
                <li key={String(li.story_id)}>
                  Story <code className="le-mono">{li.story_id}</code>
                  {li.branch_url ? (
                    <>
                      {' '}
                      ·{' '}
                      <a href={li.branch_url} rel="noreferrer" target="_blank">
                        branch
                      </a>
                    </>
                  ) : null}
                  {li.pr_url ? (
                    <>
                      {' '}
                      ·{' '}
                      <a href={li.pr_url} rel="noreferrer" target="_blank">
                        PR #{li.pull_request_number ?? ''}
                      </a>
                    </>
                  ) : null}
                  {' '}
                  ·{' '}
                  <Link
                    to={`/plan?repo=${encodeURIComponent(projectName)}&id=${encodeURIComponent(String(li.story_id ?? ''))}&tab=story`}
                  >
                    Open in Plan
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="forge-support" style={{ margin: 0 }}>
              {PROJECT_OBJECT_HOME.atAGlanceLinkedWorkEmpty}
            </p>
          )}
        </div>

        <div className="le-project-at-a-glance__card le-project-at-a-glance__card--wide">
          <h3 className="le-project-at-a-glance__card-title">{PROJECT_OBJECT_HOME.atAGlanceEvidenceTitle}</h3>
          <p className="forge-support" style={{ margin: '0 0 0.35rem', fontSize: '0.78rem' }}>
            <span className="le-content-type-badge le-content-type-badge--evidence">Evidence</span>{' '}
            <span className="forge-support">Supporting material from this repo’s tree (not tutorials).</span>
          </p>
          <p className="forge-support" style={{ margin: '0 0 0.65rem' }}>
            {PROJECT_OBJECT_HOME.atAGlanceEvidenceLead}
          </p>
          <p className="forge-support" style={{ margin: '0 0 0.65rem', fontSize: '0.82rem' }}>
            <strong className="le-muted">Context:</strong> browsing scoped to{' '}
            <span className="le-mono">{projectName}</span> — return here from evidence via the project pill when
            present.
          </p>
          <Link className="le-btn le-btn--primary" to={evidenceHref}>
            {PROJECT_OBJECT_HOME.evidenceLinkLabel}
          </Link>
        </div>

        <div className="le-project-at-a-glance__card le-project-at-a-glance__card--wide le-project-at-a-glance__card--muted">
          <h3 className="le-project-at-a-glance__card-title">{PROJECT_OBJECT_HOME.atAGlanceMethodologyTitle}</h3>
          <p className="forge-support" style={{ margin: '0 0 0.5rem' }}>
            {PROJECT_OBJECT_HOME.atAGlanceMethodologyLead}
          </p>
          <p className="forge-support" style={{ margin: 0, fontSize: '0.82rem' }}>
            <span className="le-content-type-badge le-content-type-badge--decisions">Decisions</span>{' '}
            <Link to="/knowledge/methodology/decisions">{EVIDENCE_IA.methodologyDecisionsCta}</Link>
            {' · '}
            <span className="le-content-type-badge le-content-type-badge--graph">Graph evidence</span>{' '}
            <Link to="/knowledge/methodology/evidence">{EVIDENCE_IA.methodologyEvidenceCta}</Link>
            {' · '}
            <span className="le-content-type-badge le-content-type-badge--docs">Docs</span>{' '}
            <Link to="/tutorials">{STUDIO_VOCAB.tutorials}</Link>
          </p>
        </div>
      </div>
    </section>
  )
}
