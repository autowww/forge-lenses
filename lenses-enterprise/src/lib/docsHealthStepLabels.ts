/**
 * Canonical user-visible labels for docs remediation pipeline step ids.
 * Keep in sync across timeline, workflow stage bar, header utilities, and advanced actions.
 */
export const DOCS_HEALTH_PIPELINE_STEP_LABELS: Record<string, string> = {
  cluster_brief: 'Issue analysis',
  enrich: 'Enrich findings',
  draft: 'Draft documentation changes',
  diagram_draft: 'Draft architecture diagram',
  decision_stub: 'Draft decision record',
  review: 'Review and policy checks',
  apply: 'Approve and apply to branch',
  verify: 'Re-scan and verify',
}

/** Short labels for compact controls (sticky advanced steps, etc.). */
export const DOCS_HEALTH_PIPELINE_STEP_SHORT: Record<string, string> = {
  cluster_brief: 'Analysis',
  enrich: 'Enrich',
  draft: 'Draft',
  diagram_draft: 'Diagram',
  decision_stub: 'Decision',
  review: 'Review',
  apply: 'Apply',
  verify: 'Verify',
}
