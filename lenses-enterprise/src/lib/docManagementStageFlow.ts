/** User-facing workflow stages for Doc Management sessions. */

export type DocManagementWorkflowStageId =
  | 'intake'
  | 'route_and_draft'
  | 'extract_claims'
  | 'review'
  | 'promote'
  | 'verify'

export const DOC_MGMT_WORKFLOW_ORDER: readonly DocManagementWorkflowStageId[] = [
  'intake',
  'route_and_draft',
  'extract_claims',
  'review',
  'promote',
  'verify',
] as const

export const DOC_MGMT_WORKFLOW_LABELS: Record<DocManagementWorkflowStageId, string> = {
  intake: 'Intake sources',
  route_and_draft: 'Route & draft',
  extract_claims: 'Extract claims',
  review: 'Review & approve',
  promote: 'Promote',
  verify: 'Verify',
}

export const WIZARD_STEPS = [
  { id: 'source', label: 'Source' },
  { id: 'normalize', label: 'Seeds' },
  { id: 'audience', label: 'Audience' },
  { id: 'targets', label: 'Targets' },
  { id: 'run_options', label: 'Run options' },
] as const

export type WizardStepId = (typeof WIZARD_STEPS)[number]['id']
