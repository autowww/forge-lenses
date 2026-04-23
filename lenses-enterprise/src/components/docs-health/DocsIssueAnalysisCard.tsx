import type { DocsHealthCluster, DocsHealthFinding } from '../../api/docsHealth'

export type DocsIssueAnalysisCardProps = {
  cluster?: Pick<DocsHealthCluster, 'label' | 'suggested_next' | 'expected_score_gain_if_cleared'> | null
  /** Representative finding for narrative fields (first in cluster or chosen server-side). */
  finding?: Pick<
    DocsHealthFinding,
    'plain_language_summary' | 'summary' | 'title' | 'why_it_matters' | 'severity'
  > | null
}

/**
 * Structured issue brief: problem, impact, recommendation, next step.
 */
export function DocsIssueAnalysisCard({ cluster, finding }: DocsIssueAnalysisCardProps) {
  const problem = finding?.plain_language_summary || finding?.summary || finding?.title || 'Not recorded'
  const why = finding?.why_it_matters || 'Reduces documentation risk and keeps scans aligned with repo reality.'
  const recommendation =
    cluster?.suggested_next ||
    'Start with issue analysis and enrichment, draft documentation updates, then re-scan and verify.'
  const nextStep =
    cluster?.suggested_next ||
    'Use the workflow controls, approve and apply when policy allows, then run Re-scan and verify.'

  return (
    <section className="le-dh-issue-card" aria-label="Issue analysis">
      <p className="le-dh-issue-card__label">Problem</p>
      <p className="le-dh-issue-card__body">{problem}</p>
      <p className="le-dh-issue-card__label" style={{ marginTop: '0.65rem' }}>
        Why it matters
      </p>
      <p className="le-dh-issue-card__body">{why}</p>
      <p className="le-dh-issue-card__label" style={{ marginTop: '0.65rem' }}>
        Recommendation
      </p>
      <p className="le-dh-issue-card__body">{recommendation}</p>
      {typeof cluster?.expected_score_gain_if_cleared === 'number' ? (
        <p className="forge-support" style={{ marginTop: '0.5rem', fontSize: '0.82rem' }}>
          Expected score gain if cleared: <strong>+{cluster.expected_score_gain_if_cleared.toFixed(1)}</strong>
        </p>
      ) : null}
      <p className="le-dh-issue-card__label" style={{ marginTop: '0.65rem' }}>
        Next step
      </p>
      <p className="le-dh-issue-card__body">{nextStep}</p>
    </section>
  )
}
