import type { ReactNode } from 'react'
import './blueprints-wizard-shell.css'
import type { ClarificationFieldErrors, ClarificationPayloadV1 } from './clarificationStep'
import type { ContextIntakeFieldErrors, ContextIntakePayloadV1 } from './contextIntakeStep'
import type { ContributionSetupFieldErrors, ContributionSetupPayloadV1 } from './contributionSetupStep'
import type { MissionFieldErrors, MissionPayloadV1 } from './missionStep'
import type { AutonomyMutationFieldErrors, AutonomyMutationPayloadV1 } from './autonomyMutationStep'
import type { ScopeSelectionFieldErrors, ScopeSelectionPayloadV1 } from './scopeSelectionStep'
import type { TargetOutputPackFieldErrors, TargetOutputPackPayloadV1 } from './targetOutputPackStep'
import type { InterpretationPayloadV1 } from './interpretationPayload'
import type { UnderstandingFieldErrors, UnderstandingPayloadV1 } from './understandingStep'
import type {
  ArtifactGenerationJson,
  ArtifactReviewApiAction,
  ArtifactSliceKey,
  AssumptionLedgerEntryJson,
  ContributionSetupKind,
  RecheckSummaryJson,
  RunPlanJson,
} from './wizardDomainTypes'
import type { RunPlanFieldErrors } from './runPlanStep'
import type { RunPlanPreview } from './runPlanPreviewTypes'
import { WizardShellFooter } from './WizardShellFooter'
import { WizardStepper } from './WizardStepper'
import { WizardStepBody } from './WizardStepBody'

type Props = {
  stepIndex: number
  draftNote: string
  onDraftChange: (value: string) => void
  mission: MissionPayloadV1
  onMissionChange: (m: MissionPayloadV1) => void
  missionFieldErrors?: MissionFieldErrors
  showMissionErrors?: boolean
  contributionSetup: ContributionSetupPayloadV1
  onContributionSetupChange: (c: ContributionSetupPayloadV1) => void
  contributionSetupKind: ContributionSetupKind
  onContributionSetupKindChange: (k: ContributionSetupKind) => void
  contributionFieldErrors?: ContributionSetupFieldErrors
  showContributionErrors?: boolean
  contextIntake: ContextIntakePayloadV1
  onContextIntakeChange: (x: ContextIntakePayloadV1) => void
  contextIntakeFieldErrors?: ContextIntakeFieldErrors
  showContextIntakeErrors?: boolean
  interpretation: InterpretationPayloadV1
  onInterpretationChange: (i: InterpretationPayloadV1) => void
  onRunInterpret?: () => void
  interpreting?: boolean
  interpretError?: string | null
  runInterpretAvailable?: boolean
  understanding: UnderstandingPayloadV1
  onUnderstandingChange: (u: UnderstandingPayloadV1) => void
  understandingFieldErrors?: UnderstandingFieldErrors
  showUnderstandingErrors?: boolean
  clarification: ClarificationPayloadV1
  onClarificationChange: (c: ClarificationPayloadV1) => void
  clarificationFieldErrors?: ClarificationFieldErrors
  showClarificationErrors?: boolean
  assumptionLedger: AssumptionLedgerEntryJson[]
  onRefreshClarificationQuestions: () => void
  onClarifyLlmSuggest?: () => void
  clarifySuggestAvailable?: boolean
  clarifyLlmBusy?: boolean
  clarifyLlmError?: string | null
  targetOutputPack: TargetOutputPackPayloadV1
  onTargetOutputPackChange: (t: TargetOutputPackPayloadV1) => void
  targetOutputPackFieldErrors?: TargetOutputPackFieldErrors
  showTargetOutputPackErrors?: boolean
  autonomyMutation: AutonomyMutationPayloadV1
  onAutonomyMutationChange: (a: AutonomyMutationPayloadV1) => void
  autonomyMutationFieldErrors?: AutonomyMutationFieldErrors
  showAutonomyMutationErrors?: boolean
  scopeSelection: ScopeSelectionPayloadV1
  onScopeSelectionChange: (s: ScopeSelectionPayloadV1) => void
  scopeSelectionFieldErrors?: ScopeSelectionFieldErrors
  showScopeSelectionErrors?: boolean
  runPlan: RunPlanJson
  onRunPlanChange: (r: RunPlanJson) => void
  onRegenerateRunPlan?: () => void
  runPlanFieldErrors?: RunPlanFieldErrors
  showRunPlanErrors?: boolean
  runPlanPreview?: RunPlanPreview | null
  onJumpToStep?: (stepIndex: number) => void
  artifactGeneration?: ArtifactGenerationJson
  reviewGenAvailable?: boolean
  onGenerateArtifacts?: (
    artifactKey: string | null,
    bundle?: import('./wizardDomainTypes').ArtifactGenerationBundle,
    artifactKeys?: ArtifactSliceKey[],
  ) => void
  onArtifactReview?: (
    action: ArtifactReviewApiAction,
    artifactKey: ArtifactSliceKey,
    feedback?: string,
  ) => void
  onApproveArtifactBundle?: (artifactKeys: ArtifactSliceKey[]) => void
  onExportArtifacts?: (artifactKeys: ArtifactSliceKey[]) => void
  artifactGenBusy?: boolean
  artifactGenError?: string | null
  recheckSummary?: RecheckSummaryJson | null
  onArtifactRecheck?: () => void
  /** Dry-run recheck: merges `recheck_summary` only; does not persist. */
  onArtifactRecheckPreview?: () => void
  recheckBusy?: boolean
  /** When set, step 10 shows distinct labels for persist vs preview. */
  recheckPersistBusy?: boolean
  recheckPreviewBusy?: boolean
  onRecheckRepairRegenerate?: (keys: ArtifactSliceKey[]) => void
  onApplyRecheckToScope?: (notes: string) => void
  onApplyRecheckRunPlan?: (plan: RunPlanJson) => void
  /** Step 11 — pass server session id for Cursor Launch Pack APIs. */
  wizardSessionId?: string
  onBack: () => void
  onNext: () => void
  onSaveDraft: () => void
  onExit: () => void
  /** Optional banner (e.g. server session id). */
  banner?: ReactNode
  /** Session setup (scope, product mode, optional GitHub draft). */
  setupPanel?: ReactNode
  /** Secondary content below the step body (e.g. LLM refine panel). */
  secondaryPanel?: ReactNode
  /** Disables step notes and most footer actions. */
  interactionDisabled?: boolean
}

export function BlueprintsWizardShell({
  stepIndex,
  draftNote,
  onDraftChange,
  mission,
  onMissionChange,
  missionFieldErrors,
  showMissionErrors,
  contributionSetup,
  onContributionSetupChange,
  contributionSetupKind,
  onContributionSetupKindChange,
  contributionFieldErrors,
  showContributionErrors,
  contextIntake,
  onContextIntakeChange,
  contextIntakeFieldErrors,
  showContextIntakeErrors,
  interpretation,
  onInterpretationChange,
  onRunInterpret,
  interpreting,
  interpretError,
  runInterpretAvailable,
  understanding,
  onUnderstandingChange,
  understandingFieldErrors,
  showUnderstandingErrors,
  clarification,
  onClarificationChange,
  clarificationFieldErrors,
  showClarificationErrors,
  assumptionLedger,
  onRefreshClarificationQuestions,
  onClarifyLlmSuggest,
  clarifySuggestAvailable = true,
  clarifyLlmBusy,
  clarifyLlmError,
  targetOutputPack,
  onTargetOutputPackChange,
  targetOutputPackFieldErrors,
  showTargetOutputPackErrors,
  autonomyMutation,
  onAutonomyMutationChange,
  autonomyMutationFieldErrors,
  showAutonomyMutationErrors,
  scopeSelection,
  onScopeSelectionChange,
  scopeSelectionFieldErrors,
  showScopeSelectionErrors,
  runPlan,
  onRunPlanChange,
  onRegenerateRunPlan,
  runPlanFieldErrors,
  showRunPlanErrors,
  runPlanPreview,
  onJumpToStep,
  artifactGeneration,
  reviewGenAvailable = true,
  onGenerateArtifacts,
  onArtifactReview,
  onApproveArtifactBundle,
  onExportArtifacts,
  artifactGenBusy = false,
  artifactGenError = null,
  recheckSummary = null,
  onArtifactRecheck,
  onArtifactRecheckPreview,
  recheckBusy = false,
  recheckPersistBusy = false,
  recheckPreviewBusy = false,
  onRecheckRepairRegenerate,
  onApplyRecheckToScope,
  onApplyRecheckRunPlan,
  wizardSessionId,
  onBack,
  onNext,
  onSaveDraft,
  onExit,
  banner,
  setupPanel,
  secondaryPanel,
  interactionDisabled = false,
}: Props) {
  return (
    <div className="le-bpwizard">
      <header className="le-bpwizard__header">
        <h1 className="le-h1">Blueprints Wizard</h1>
        <p className="forge-support">
          Experimental — guided Blueprints-aligned flow through understanding, clarification, and target
          pack before autonomy and scope.
        </p>
        {banner}
      </header>
      {setupPanel}
      <div className="le-bpwizard__stepper-wrap">
        <WizardStepper stepIndex={stepIndex} />
      </div>
      <div className="le-bpwizard__main">
        <WizardStepBody
          stepIndex={stepIndex}
          draftNote={draftNote}
          onDraftChange={onDraftChange}
          mission={mission}
          onMissionChange={onMissionChange}
          missionFieldErrors={missionFieldErrors}
          showMissionErrors={showMissionErrors}
          contributionSetup={contributionSetup}
          onContributionSetupChange={onContributionSetupChange}
          contributionSetupKind={contributionSetupKind}
          onContributionSetupKindChange={onContributionSetupKindChange}
          contributionFieldErrors={contributionFieldErrors}
          showContributionErrors={showContributionErrors}
          contextIntake={contextIntake}
          onContextIntakeChange={onContextIntakeChange}
          contextIntakeFieldErrors={contextIntakeFieldErrors}
          showContextIntakeErrors={showContextIntakeErrors}
          interpretation={interpretation}
          onInterpretationChange={onInterpretationChange}
          onRunInterpret={onRunInterpret}
          interpreting={interpreting}
          interpretError={interpretError}
          runInterpretAvailable={runInterpretAvailable}
          understanding={understanding}
          onUnderstandingChange={onUnderstandingChange}
          understandingFieldErrors={understandingFieldErrors}
          showUnderstandingErrors={showUnderstandingErrors}
          clarification={clarification}
          onClarificationChange={onClarificationChange}
          clarificationFieldErrors={clarificationFieldErrors}
          showClarificationErrors={showClarificationErrors}
          assumptionLedger={assumptionLedger}
          onRefreshClarificationQuestions={onRefreshClarificationQuestions}
          onClarifyLlmSuggest={onClarifyLlmSuggest}
          clarifySuggestAvailable={clarifySuggestAvailable}
          clarifyLlmBusy={clarifyLlmBusy}
          clarifyLlmError={clarifyLlmError}
          targetOutputPack={targetOutputPack}
          onTargetOutputPackChange={onTargetOutputPackChange}
          targetOutputPackFieldErrors={targetOutputPackFieldErrors}
          showTargetOutputPackErrors={showTargetOutputPackErrors}
          autonomyMutation={autonomyMutation}
          onAutonomyMutationChange={onAutonomyMutationChange}
          autonomyMutationFieldErrors={autonomyMutationFieldErrors}
          showAutonomyMutationErrors={showAutonomyMutationErrors}
          scopeSelection={scopeSelection}
          onScopeSelectionChange={onScopeSelectionChange}
          scopeSelectionFieldErrors={scopeSelectionFieldErrors}
          showScopeSelectionErrors={showScopeSelectionErrors}
          runPlan={runPlan}
          onRunPlanChange={onRunPlanChange}
          onRegenerateRunPlan={onRegenerateRunPlan}
          runPlanFieldErrors={runPlanFieldErrors}
          showRunPlanErrors={showRunPlanErrors}
          runPlanPreview={runPlanPreview}
          onJumpToStep={onJumpToStep}
          disabled={interactionDisabled}
          artifactGeneration={artifactGeneration}
          reviewGenAvailable={reviewGenAvailable}
          onGenerateArtifacts={onGenerateArtifacts}
          onArtifactReview={onArtifactReview}
          onApproveArtifactBundle={onApproveArtifactBundle}
          onExportArtifacts={onExportArtifacts}
          artifactGenBusy={artifactGenBusy}
          artifactGenError={artifactGenError}
          recheckSummary={recheckSummary}
          onArtifactRecheck={onArtifactRecheck}
          onArtifactRecheckPreview={onArtifactRecheckPreview}
          recheckBusy={recheckBusy}
          recheckPersistBusy={recheckPersistBusy}
          recheckPreviewBusy={recheckPreviewBusy}
          onRecheckRepairRegenerate={onRecheckRepairRegenerate}
          onApplyRecheckToScope={onApplyRecheckToScope}
          onApplyRecheckRunPlan={onApplyRecheckRunPlan}
          wizardSessionId={wizardSessionId}
        />
        {secondaryPanel}
      </div>
      <WizardShellFooter
        stepIndex={stepIndex}
        onBack={onBack}
        onNext={onNext}
        onSaveDraft={onSaveDraft}
        onExit={onExit}
        interactionDisabled={interactionDisabled}
      />
    </div>
  )
}
