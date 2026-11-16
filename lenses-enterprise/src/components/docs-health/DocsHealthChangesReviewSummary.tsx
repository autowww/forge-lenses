import type { DocsHealthCluster, DocsHealthFinding, DocsHealthSessionPayload } from '../../api/docsHealth'
import { ForgeKeyValueGrid, type ForgeKeyValueItem } from '../../forgesdlc-kitchensink'
import {
  countAffectedPathsForChanges,
  describeApplyStrategy,
  describeWhatWillChange,
  deriveApprovalRiskLevel,
} from '../../lib/docsHealthChangesReview'

export type DocsHealthChangesReviewSummaryProps = {
  session: DocsHealthSessionPayload | null
  cluster?: Pick<DocsHealthCluster, 'primary_severity'> | null
  finding?: DocsHealthFinding | null
  /** When true, show pointer to pinned approval bar. */
  showApprovalHint?: boolean
}

/**
 * Concise review header for the Changes surface — no timeline noise.
 */
export function DocsHealthChangesReviewSummary({
  session,
  cluster,
  finding,
  showApprovalHint,
}: DocsHealthChangesReviewSummaryProps) {
  const n = countAffectedPathsForChanges(session)
  const items: ForgeKeyValueItem[] = [
    {
      label: 'What will change',
      value: describeWhatWillChange(session),
    },
    {
      label: 'Risk level',
      value: deriveApprovalRiskLevel(finding, cluster),
    },
    {
      label: 'Affected paths (count)',
      value: n != null ? String(n) : 'Not available',
    },
    {
      label: 'Apply strategy',
      value: describeApplyStrategy(session),
    },
  ]

  return (
    <div className="le-dh-changes-review" role="region" aria-label="Review summary">
      <h4 className="le-dh-changes-review__title">Review summary</h4>
      <ForgeKeyValueGrid items={items} aria-label="Proposal review summary" dense={false} />
      {showApprovalHint ? (
        <p className="forge-support le-dh-changes-review__hint">
          Use the{' '}
          <a href="#dh-primary-run-actions" className="le-dh-changes-review__anchor">
            pinned approval actions
          </a>{' '}
          at the bottom of the screen to approve, reject, or apply — avoid duplicating decisions here.
        </p>
      ) : null}
    </div>
  )
}
