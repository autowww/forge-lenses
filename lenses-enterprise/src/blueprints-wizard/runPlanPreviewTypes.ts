/**
 * Deterministic run-plan preview (step 8). Rich view only — persisted JSON remains `RunPlanJson`.
 */

import type { ClarificationPayloadV1 } from './clarificationStep'
import type { ContextIntakePayloadV1 } from './contextIntakeStep'
import type { ContributionSetupPayloadV1 } from './contributionSetupStep'
import type { AutonomyMutationPayloadV1 } from './autonomyMutationStep'
import type { ScopeSelectionPayloadV1 } from './scopeSelectionStep'
import type { TargetOutputPackPayloadV1 } from './targetOutputPackStep'
import type { UnderstandingPayloadV1 } from './understandingStep'
import type { InterpretationPayloadV1 } from './interpretationPayload'
import type { MissionPayloadV1 } from './missionStep'
import type {
  ArtifactStatus,
  AssumptionLedgerEntryJson,
  ContributionSetupKind,
  InterpretationFieldStatus,
  RunPlanJson,
  WizardDomainJson,
} from './wizardDomainTypes'

export type RiskSeverity = 'low' | 'medium' | 'high'

export type ArtifactPlanRow = {
  label: string
  /** Stable within preview; may align with pack item id when known. */
  ref?: string
  previousStatus?: ArtifactStatus | string
  nextStatus?: ArtifactStatus | string
  reason?: string
}

export type ReviewGatePreview = {
  id: string
  title: string
  rationale: string
}

export type RiskHotspotPreview = {
  id: string
  label: string
  severity: RiskSeverity
  detail: string
}

export type ConfidencePreview = {
  /** One-line summary for the panel. */
  summary: string
  /** 0–1 heuristic from field statuses + gates. */
  score01: number
}

export type CurrentStatePreview = {
  title: string
  bullets: string[]
}

export type TargetStatePreview = {
  title: string
  bullets: string[]
}

export type RunPlanPreview = {
  currentState: CurrentStatePreview
  targetState: TargetStatePreview
  artifactsCreate: ArtifactPlanRow[]
  artifactsUpdate: ArtifactPlanRow[]
  artifactsUntouched: ArtifactPlanRow[]
  reviewGates: ReviewGatePreview[]
  assumptionsReliedOn: string[]
  blockers: string[]
  riskHotspots: RiskHotspotPreview[]
  scopeBoundaries: string[]
  confidence: ConfidencePreview
  /** Aligns with editable `run_plan` (title + steps). */
  runPlan: RunPlanJson
}

export type RunPlanPreviewInput = {
  mission: MissionPayloadV1
  contributionSetup: ContributionSetupPayloadV1
  contributionSetupKind: ContributionSetupKind
  contextIntake: ContextIntakePayloadV1
  /** Same source as session UI (`effectiveFoundationBriefMarkdown`). */
  foundationBriefMarkdownEffective: string
  interpretation: InterpretationPayloadV1
  clarification: ClarificationPayloadV1
  targetOutputPack: TargetOutputPackPayloadV1
  autonomyMutation: AutonomyMutationPayloadV1
  scopeSelection: ScopeSelectionPayloadV1
  understanding: UnderstandingPayloadV1
  assumptionLedger: AssumptionLedgerEntryJson[]
  foundationBriefFieldStatuses: Record<string, InterpretationFieldStatus | string>
  /**
   * Last persisted `wizard_domain` (e.g. from loaded session). Used for previous artifact snapshot.
   */
  savedWizardDomain: WizardDomainJson | null
  /** Current editable run plan from shell. */
  runPlan: RunPlanJson
}
