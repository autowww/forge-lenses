import { Link } from 'react-router-dom'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'
import { useDocsHealthSummary } from '../../context/DocsHealthSummaryContext'

/**
 * Human documentation review summary — counts and next fix, for Home and project surfaces.
 */
export function DocsHealthSummary({ compact = false }: { compact?: boolean }) {
  const { data } = useDocsHealthSummary()

  if (!data?.ok) return null

  const attention = (data.projects ?? []).filter((p) => p.needs_attention)
  const rollup = data.rollup
  const avg = rollup?.average_last_score
  const crit = rollup?.projects_with_critical_open_findings ?? 0
  const awaiting = rollup?.open_docs_work_items_total ?? 0
  const nextFix = attention[0]

  return (
    <section
      className={compact ? 'le-docs-health-summary le-docs-health-summary--compact' : 'le-docs-health-summary le-panel'}
      aria-labelledby="le-docs-health-summary-title"
    >
      <h2 id="le-docs-health-summary-title" className="le-panel__title" style={{ marginTop: compact ? undefined : 0 }}>
        {STUDIO_VOCAB.docsHealth}
      </h2>
      <p className="forge-support documentationReviewSummary" style={{ marginTop: 0 }}>
        Documentation review across {(data.projects ?? []).length} project(s)
        {avg != null ? ` — average score ${avg}/100` : ''}.
        {crit > 0 ? ` ${crit} with critical open findings.` : ' No critical findings in the last run.'}
        {awaiting > 0 ? ` ${awaiting} follow-up(s) awaiting action.` : ''}
      </p>
      {nextFix ? (
        <p className="forge-support" style={{ marginBottom: compact ? 0 : '0.5rem' }}>
          Next fix:{' '}
          <Link to={`/projects/${encodeURIComponent(nextFix.project)}/docs-health`}>
            {nextFix.project}
          </Link>
          {nextFix.last_score != null ? ` (score ${nextFix.last_score}/100)` : ''}
        </p>
      ) : (
        <p className="forge-support" style={{ marginBottom: compact ? 0 : '0.5rem' }}>
          No urgent documentation signals — spot-check projects before release.
        </p>
      )}
    </section>
  )
}
