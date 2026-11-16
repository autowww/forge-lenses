import { ClarificationStepPanel } from './ClarificationStepPanel'
import type { ClarificationFieldErrors, ClarificationPayloadV1 } from './clarificationStep'
import type { ContextIntakeFieldErrors, ContextIntakePayloadV1 } from './contextIntakeStep'
import { ContextIntakeStepFields } from './ContextIntakeStepFields'
import { contributionDefaultsForKind } from './contributionSetupDefaults'
import type { ContributionSetupFieldErrors, ContributionSetupPayloadV1 } from './contributionSetupStep'
import {
  CONTRIBUTION_LANDING_MAX,
  CONTRIBUTION_NOTES_MAX,
  CONTRIBUTION_DELIVERABLE_MAX,
} from './contributionSetupStep'
import type { MissionFieldErrors, MissionPayloadV1 } from './missionStep'
import {
  MISSION_MODE_OPTIONS,
  MISSION_NOTES_MAX,
  MISSION_OUTCOME_MAX,
  MISSION_TITLE_MAX,
} from './missionStep'
import type { AutonomyMutationFieldErrors, AutonomyMutationPayloadV1 } from './autonomyMutationStep'
import {
  AUTONOMY_UI,
  MUTATION_UI,
  needsL3ReadonlyAck,
  needsTierRiskAck,
} from './autonomyMutationStep'
import type { ScopeSelectionFieldErrors, ScopeSelectionPayloadV1 } from './scopeSelectionStep'
import {
  CLOSURE_OPTION_UI,
  SCOPE_BOUNDARY_UI,
} from './scopeSelectionStep'
import type { TargetOutputPackFieldErrors, TargetOutputPackPayloadV1 } from './targetOutputPackStep'
import {
  OUTPUT_PACK_KIND_UI,
  TARGET_ARTIFACT_LINES_MAX,
  TARGET_PACK_LABEL_MAX,
  TARGET_STAGE_UI,
  defaultPackLabelForKind,
} from './targetOutputPackStep'
import { InterpretationCanvas } from './InterpretationCanvas'
import type { InterpretationPayloadV1 } from './interpretationPayload'
import type { UnderstandingFieldErrors, UnderstandingPayloadV1 } from './understandingStep'
import type {
  ArtifactGenerationJson,
  ArtifactReviewApiAction,
  ArtifactSliceKey,
  AssumptionLedgerEntryJson,
  ContributionSetupKind,
  OutputPackKind,
  RecheckSummaryJson,
  RunPlanJson,
  TargetStage,
} from './wizardDomainTypes'
import { CONTRIBUTION_SETUP_KINDS, OUTPUT_PACK_KINDS, TARGET_STAGES } from './wizardDomainTypes'
import type { RunPlanPreview } from './runPlanPreviewTypes'
import { ExperimentalBuildStepPanel } from './ExperimentalBuildStepPanel'
import { RecheckRepairDashboard } from './RecheckRepairDashboard'
import { ReviewGenerateStepPanel } from './ReviewGenerateStepPanel'
import { RunPlanPreviewPanel } from './RunPlanPreviewPanel'
import {
  RUN_PLAN_MAX_STEPS,
  RUN_PLAN_STEP_DETAIL_MAX,
  RUN_PLAN_STEP_TITLE_MAX,
  RUN_PLAN_TITLE_MAX,
  clampRunPlan,
  type RunPlanFieldErrors,
} from './runPlanStep'
import { getStepTitle } from './wizardSteps'

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
  /** Optional — step 8 “Regenerate from context”. */
  onRegenerateRunPlan?: () => void
  runPlanFieldErrors?: RunPlanFieldErrors
  showRunPlanErrors?: boolean
  /** Deterministic preview for step 8 (Run Plan). */
  runPlanPreview?: RunPlanPreview | null
  onJumpToStep?: (stepIndex: number) => void
  disabled?: boolean
  /** Step 9 — artifact generation (optional; local mode omits). */
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
  onArtifactRecheckPreview?: () => void
  recheckBusy?: boolean
  recheckPersistBusy?: boolean
  recheckPreviewBusy?: boolean
  onRecheckRepairRegenerate?: (keys: ArtifactSliceKey[]) => void
  onApplyRecheckToScope?: (notes: string) => void
  onApplyRecheckRunPlan?: (plan: import('./wizardDomainTypes').RunPlanJson) => void
  /** Step 11 — Cursor Launch Pack (server session id). */
  wizardSessionId?: string
}

export function WizardStepBody({
  stepIndex,
  draftNote,
  onDraftChange,
  mission,
  onMissionChange,
  missionFieldErrors = {},
  showMissionErrors = false,
  contributionSetup,
  onContributionSetupChange,
  contributionSetupKind,
  onContributionSetupKindChange,
  contributionFieldErrors = {},
  showContributionErrors = false,
  contextIntake,
  onContextIntakeChange,
  contextIntakeFieldErrors = {},
  showContextIntakeErrors = false,
  interpretation,
  onInterpretationChange,
  onRunInterpret,
  interpreting = false,
  interpretError = null,
  runInterpretAvailable = true,
  understanding: _understanding,
  onUnderstandingChange: _onUnderstandingChange,
  understandingFieldErrors = {},
  showUnderstandingErrors = false,
  clarification,
  onClarificationChange,
  clarificationFieldErrors = {},
  showClarificationErrors = false,
  assumptionLedger,
  onRefreshClarificationQuestions,
  onClarifyLlmSuggest,
  clarifySuggestAvailable = true,
  clarifyLlmBusy = false,
  clarifyLlmError = null,
  targetOutputPack,
  onTargetOutputPackChange,
  targetOutputPackFieldErrors = {},
  showTargetOutputPackErrors = false,
  autonomyMutation,
  onAutonomyMutationChange,
  autonomyMutationFieldErrors = {},
  showAutonomyMutationErrors = false,
  scopeSelection,
  onScopeSelectionChange,
  scopeSelectionFieldErrors = {},
  showScopeSelectionErrors = false,
  runPlan,
  onRunPlanChange,
  onRegenerateRunPlan,
  runPlanFieldErrors = {},
  showRunPlanErrors = false,
  runPlanPreview = null,
  onJumpToStep,
  disabled = false,
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
}: Props) {
  const title = getStepTitle(stepIndex)

  if (stepIndex === 0) {
    const errMode = showMissionErrors ? missionFieldErrors.mode : undefined
    const errTitle = showMissionErrors ? missionFieldErrors.title : undefined
    const errOutcome = showMissionErrors ? missionFieldErrors.outcome : undefined
    const errNotes = showMissionErrors ? missionFieldErrors.notes : undefined

    return (
      <section className="forge-support" aria-labelledby="bpw-step-heading">
        <h2 id="bpw-step-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
          {title}
        </h2>
        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          Choose how you are running this session, then name the initiative and outcome.
        </p>
        <fieldset style={{ marginTop: '0.75rem', border: 'none', padding: 0 }}>
          <legend className="forge-support" style={{ marginBottom: '0.35rem' }}>
            Mission mode <span aria-hidden="true">*</span>
          </legend>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {MISSION_MODE_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className="forge-support"
                style={{
                  display: 'flex',
                  gap: '0.5rem',
                  alignItems: 'flex-start',
                  cursor: disabled ? 'default' : 'pointer',
                }}
              >
                <input
                  type="radio"
                  name="bpw-mission-mode"
                  checked={mission.mode === opt.value}
                  disabled={disabled}
                  onChange={() => onMissionChange({ ...mission, mode: opt.value })}
                  aria-describedby={`bpw-mission-mode-desc-${opt.value}`}
                />
                <span>
                  <span style={{ fontWeight: 600 }}>{opt.label}</span>
                  <span id={`bpw-mission-mode-desc-${opt.value}`} className="forge-support" style={{ display: 'block', opacity: 0.9, marginTop: '0.15rem' }}>
                    {opt.description}
                  </span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        {errMode && (
          <p className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
            {errMode}
          </p>
        )}
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-mission-title" style={{ display: 'block' }}>
            Mission title <span aria-hidden="true">*</span>
          </label>
          <input
            id="bpw-mission-title"
            className="le-input"
            type="text"
            maxLength={MISSION_TITLE_MAX}
            value={mission.title}
            disabled={disabled}
            onChange={(e) => onMissionChange({ ...mission, title: e.target.value })}
            placeholder="e.g. Harden onboarding for new squads"
            aria-invalid={Boolean(errTitle)}
            aria-describedby={errTitle ? 'bpw-mission-title-err' : undefined}
            style={{ width: '100%', marginTop: '0.35rem' }}
          />
          {errTitle && (
            <p id="bpw-mission-title-err" className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
              {errTitle}
            </p>
          )}
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-mission-outcome" style={{ display: 'block' }}>
            Outcome / problem <span aria-hidden="true">*</span>
          </label>
          <textarea
            id="bpw-mission-outcome"
            className="le-input"
            maxLength={MISSION_OUTCOME_MAX}
            value={mission.outcome}
            disabled={disabled}
            onChange={(e) => onMissionChange({ ...mission, outcome: e.target.value })}
            placeholder="What problem are you solving or what does success look like?"
            aria-invalid={Boolean(errOutcome)}
            aria-describedby={errOutcome ? 'bpw-mission-outcome-err' : undefined}
            style={{ width: '100%', minHeight: '5rem', marginTop: '0.35rem' }}
          />
          {errOutcome && (
            <p id="bpw-mission-outcome-err" className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
              {errOutcome}
            </p>
          )}
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-mission-notes" style={{ display: 'block' }}>
            Additional notes <span className="forge-support" style={{ opacity: 0.85 }}>(optional)</span>
          </label>
          <textarea
            id="bpw-mission-notes"
            className="le-input"
            maxLength={MISSION_NOTES_MAX}
            value={mission.notes ?? ''}
            disabled={disabled}
            onChange={(e) => onMissionChange({ ...mission, notes: e.target.value })}
            placeholder="Constraints, stakeholders, links…"
            aria-invalid={Boolean(errNotes)}
            aria-describedby={errNotes ? 'bpw-mission-notes-err' : undefined}
            style={{ width: '100%', minHeight: '4rem', marginTop: '0.35rem' }}
          />
          {errNotes && (
            <p id="bpw-mission-notes-err" className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
              {errNotes}
            </p>
          )}
        </div>
      </section>
    )
  }

  if (stepIndex === 1) {
    const errDel = showContributionErrors ? contributionFieldErrors.deliverable : undefined
    const errLand = showContributionErrors ? contributionFieldErrors.landingPlace : undefined
    const errN = showContributionErrors ? contributionFieldErrors.notes : undefined
    const def = contributionDefaultsForKind(contributionSetupKind)
    const scaleLabel: Record<string, string> = {
      single: 'Single',
      team: 'Team',
      teams: 'Teams',
      enterprise: 'Enterprise',
    }

    return (
      <section className="forge-support" aria-labelledby="bpw-step-heading">
        <h2 id="bpw-step-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
          {title}
        </h2>
        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          Choose collaboration scale. Defaults below are a preview only—you will tune autonomy and gates in later steps.
        </p>
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-contrib-scale" style={{ display: 'block' }}>
            Scale <span aria-hidden="true">*</span>
          </label>
          <select
            id="bpw-contrib-scale"
            className="le-select"
            value={contributionSetupKind}
            disabled={disabled}
            onChange={(e) => onContributionSetupKindChange(e.target.value as ContributionSetupKind)}
            aria-label="Contribution scale"
            style={{ marginTop: '0.35rem', minWidth: '12rem' }}
          >
            {CONTRIBUTION_SETUP_KINDS.map((k) => (
              <option key={k} value={k}>
                {scaleLabel[k] ?? k}
              </option>
            ))}
          </select>
        </div>
        <div
          className="forge-support le-preview"
          style={{ marginTop: '0.75rem', padding: '0.5rem 0.65rem', borderRadius: '4px' }}
          aria-live="polite"
        >
          <div style={{ fontWeight: 600, marginBottom: '0.35rem' }}>Default expectations for this scale</div>
          <table className="forge-support" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.95rem' }}>
            <tbody>
              <tr>
                <td style={{ padding: '0.2rem 0.5rem 0.2rem 0', verticalAlign: 'top', opacity: 0.9 }}>Autonomy</td>
                <td style={{ padding: '0.2rem 0' }}>{def.autonomyLabel}</td>
              </tr>
              <tr>
                <td style={{ padding: '0.2rem 0.5rem 0.2rem 0', verticalAlign: 'top', opacity: 0.9 }}>Review gates</td>
                <td style={{ padding: '0.2rem 0' }}>{def.reviewGates}</td>
              </tr>
              <tr>
                <td style={{ padding: '0.2rem 0.5rem 0.2rem 0', verticalAlign: 'top', opacity: 0.9 }}>Artifact depth</td>
                <td style={{ padding: '0.2rem 0' }}>{def.artifactDepth}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-contrib-deliverable" style={{ display: 'block' }}>
            Deliverable <span className="forge-support" style={{ opacity: 0.85 }}>(optional)</span>
          </label>
          <input
            id="bpw-contrib-deliverable"
            className="le-input"
            type="text"
            maxLength={CONTRIBUTION_DELIVERABLE_MAX}
            value={contributionSetup.deliverable ?? ''}
            disabled={disabled}
            onChange={(e) => onContributionSetupChange({ ...contributionSetup, deliverable: e.target.value })}
            placeholder="e.g. Handbook slice, SDL template pack"
            aria-invalid={Boolean(errDel)}
            aria-describedby={errDel ? 'bpw-contrib-deliverable-err' : undefined}
            style={{ width: '100%', marginTop: '0.35rem' }}
          />
          {errDel && (
            <p id="bpw-contrib-deliverable-err" className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
              {errDel}
            </p>
          )}
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-contrib-landing" style={{ display: 'block' }}>
            Landing place <span className="forge-support" style={{ opacity: 0.85 }}>(optional)</span>
          </label>
          <input
            id="bpw-contrib-landing"
            className="le-input"
            type="text"
            maxLength={CONTRIBUTION_LANDING_MAX}
            value={contributionSetup.landingPlace ?? ''}
            disabled={disabled}
            onChange={(e) => onContributionSetupChange({ ...contributionSetup, landingPlace: e.target.value })}
            placeholder="Repo URL, product, workspace path, or team"
            aria-invalid={Boolean(errLand)}
            aria-describedby={errLand ? 'bpw-contrib-landing-err' : undefined}
            style={{ width: '100%', marginTop: '0.35rem' }}
          />
          {errLand && (
            <p id="bpw-contrib-landing-err" className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
              {errLand}
            </p>
          )}
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-contrib-notes" style={{ display: 'block' }}>
            Notes <span className="forge-support" style={{ opacity: 0.85 }}>(optional)</span>
          </label>
          <textarea
            id="bpw-contrib-notes"
            className="le-input"
            maxLength={CONTRIBUTION_NOTES_MAX}
            value={contributionSetup.notes ?? ''}
            disabled={disabled}
            onChange={(e) => onContributionSetupChange({ ...contributionSetup, notes: e.target.value })}
            placeholder="Branching model, review expectations, or links"
            aria-invalid={Boolean(errN)}
            aria-describedby={errN ? 'bpw-contrib-notes-err' : undefined}
            style={{ width: '100%', minHeight: '4rem', marginTop: '0.35rem' }}
          />
          {errN && (
            <p id="bpw-contrib-notes-err" className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
              {errN}
            </p>
          )}
        </div>
      </section>
    )
  }

  if (stepIndex === 2) {
    return (
      <section className="forge-support" aria-labelledby="bpw-step-heading">
        <h2 id="bpw-step-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
          {title}
        </h2>
        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          Capture rough intent and where context should come from. Snippet previews are mock-only until ingestion is wired.
        </p>
        <ContextIntakeStepFields
          value={contextIntake}
          onChange={onContextIntakeChange}
          fieldErrors={contextIntakeFieldErrors}
          showErrors={showContextIntakeErrors}
          disabled={disabled}
        />
      </section>
    )
  }

  if (stepIndex === 3) {
    const errS = showUnderstandingErrors ? understandingFieldErrors.summary : undefined
    return (
      <section className="forge-support" aria-labelledby="bpw-step-heading">
        <h2 id="bpw-step-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
          {title}
        </h2>
        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          Interpretation canvas: what you said, what Blueprints inferred, and what needs confirmation. Scope summary on
          save follows the &quot;What you said&quot; column.
        </p>
        <InterpretationCanvas
          value={interpretation}
          onChange={onInterpretationChange}
          disabled={disabled}
          onRunInterpret={onRunInterpret}
          interpreting={interpreting}
          interpretError={interpretError}
          runInterpretAvailable={runInterpretAvailable}
        />
        {errS && (
          <p id="bpw-understand-sum-err" className="forge-support" role="alert" style={{ marginTop: '0.75rem', color: 'var(--le-danger, #f87171)' }}>
            {errS}
          </p>
        )}
      </section>
    )
  }

  if (stepIndex === 4) {
    return (
      <section className="forge-support" aria-labelledby="bpw-step-heading">
        <h2 id="bpw-step-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
          {title}
        </h2>
        <ClarificationStepPanel
          clarification={clarification}
          onClarificationChange={onClarificationChange}
          clarificationFieldErrors={clarificationFieldErrors}
          showClarificationErrors={showClarificationErrors}
          assumptionLedger={assumptionLedger}
          onRefreshQuestions={onRefreshClarificationQuestions}
          onClarifyLlmSuggest={onClarifyLlmSuggest}
          clarifySuggestAvailable={clarifySuggestAvailable}
          clarifyLlmBusy={clarifyLlmBusy}
          clarifyLlmError={clarifyLlmError}
          disabled={disabled}
        />
      </section>
    )
  }

  if (stepIndex === 5) {
    const errSt = showTargetOutputPackErrors ? targetOutputPackFieldErrors.targetStage : undefined
    const errL = showTargetOutputPackErrors ? targetOutputPackFieldErrors.packLabel : undefined
    const errA = showTargetOutputPackErrors ? targetOutputPackFieldErrors.artifactLines : undefined
    const errPk = showTargetOutputPackErrors ? targetOutputPackFieldErrors.outputPackKind : undefined
    return (
      <section className="forge-support" aria-labelledby="bpw-step-heading">
        <h2 id="bpw-step-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
          {title}
        </h2>
        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          Pick a Forge target stage and output pack kind, then list artifact rows. One line per deliverable becomes draft items
          in the artifact pack.
        </p>
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-target-stage" style={{ display: 'block' }}>
            Target stage <span aria-hidden="true">*</span>
          </label>
          <select
            id="bpw-target-stage"
            className="le-select"
            value={targetOutputPack.targetStage}
            disabled={disabled}
            onChange={(e) =>
              onTargetOutputPackChange({
                ...targetOutputPack,
                targetStage: e.target.value as TargetStage,
              })
            }
            aria-invalid={Boolean(errSt)}
            aria-describedby="bpw-target-stage-hint"
            style={{ marginTop: '0.35rem', minWidth: '18rem' }}
          >
            {TARGET_STAGES.map((st) => (
              <option key={st} value={st} title={TARGET_STAGE_UI[st].plain}>
                {TARGET_STAGE_UI[st].forgeLabel}
              </option>
            ))}
          </select>
          <p id="bpw-target-stage-hint" className="forge-support" style={{ marginTop: '0.35rem', opacity: 0.9 }}>
            {TARGET_STAGE_UI[targetOutputPack.targetStage]?.plain}
          </p>
          {errSt && (
            <p className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
              {errSt}
            </p>
          )}
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-output-pack-kind" style={{ display: 'block' }}>
            Output pack kind <span aria-hidden="true">*</span>
          </label>
          <select
            id="bpw-output-pack-kind"
            className="le-select"
            value={targetOutputPack.outputPackKind}
            disabled={disabled}
            onChange={(e) => {
              const outputPackKind = e.target.value as OutputPackKind
              const next = {
                ...targetOutputPack,
                outputPackKind,
                packLabel: targetOutputPack.useCustomPackLabel
                  ? targetOutputPack.packLabel
                  : defaultPackLabelForKind(outputPackKind),
              }
              onTargetOutputPackChange(next)
            }}
            aria-describedby="bpw-output-pack-kind-hint"
            style={{ marginTop: '0.35rem', minWidth: '18rem' }}
          >
            {OUTPUT_PACK_KINDS.map((k) => (
              <option key={k} value={k} title={OUTPUT_PACK_KIND_UI[k].plain}>
                {OUTPUT_PACK_KIND_UI[k].forgeLabel}
              </option>
            ))}
          </select>
          <p id="bpw-output-pack-kind-hint" className="forge-support" style={{ marginTop: '0.35rem', opacity: 0.9 }}>
            {OUTPUT_PACK_KIND_UI[targetOutputPack.outputPackKind]?.plain}
          </p>
          {errPk && (
            <p className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
              {errPk}
            </p>
          )}
        </div>
        <div style={{ marginTop: '0.5rem' }}>
          <label className="forge-support" style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={targetOutputPack.useCustomPackLabel}
              disabled={disabled}
              onChange={(e) => {
                const useCustomPackLabel = e.target.checked
                onTargetOutputPackChange({
                  ...targetOutputPack,
                  useCustomPackLabel,
                  packLabel: useCustomPackLabel
                    ? targetOutputPack.packLabel
                    : defaultPackLabelForKind(targetOutputPack.outputPackKind),
                })
              }}
            />
            Custom pack name (advanced)
          </label>
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-pack-label" style={{ display: 'block' }}>
            Output pack name <span aria-hidden="true">*</span>
          </label>
          <input
            id="bpw-pack-label"
            className="le-input"
            type="text"
            maxLength={TARGET_PACK_LABEL_MAX}
            value={targetOutputPack.packLabel}
            disabled={disabled || !targetOutputPack.useCustomPackLabel}
            onChange={(e) => onTargetOutputPackChange({ ...targetOutputPack, packLabel: e.target.value, useCustomPackLabel: true })}
            placeholder="e.g. Onboarding blueprint slice"
            aria-invalid={Boolean(errL)}
            aria-describedby={errL ? 'bpw-pack-label-err' : undefined}
            style={{ width: '100%', marginTop: '0.35rem' }}
          />
          {errL && (
            <p id="bpw-pack-label-err" className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
              {errL}
            </p>
          )}
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-artifact-lines" style={{ display: 'block' }}>
            Artifacts (one per line) <span aria-hidden="true">*</span>
          </label>
          <textarea
            id="bpw-artifact-lines"
            className="le-input"
            maxLength={TARGET_ARTIFACT_LINES_MAX}
            value={targetOutputPack.artifactLines}
            disabled={disabled}
            onChange={(e) => onTargetOutputPackChange({ ...targetOutputPack, artifactLines: e.target.value })}
            placeholder={'Foundation Brief draft\nRun plan outline\nReview checklist'}
            aria-invalid={Boolean(errA)}
            aria-describedby={errA ? 'bpw-artifact-lines-err' : undefined}
            style={{ width: '100%', minHeight: '8rem', marginTop: '0.35rem', fontFamily: 'inherit' }}
          />
          {errA && (
            <p id="bpw-artifact-lines-err" className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
              {errA}
            </p>
          )}
        </div>
      </section>
    )
  }

  if (stepIndex === 6) {
    const errA = showAutonomyMutationErrors ? autonomyMutationFieldErrors.autonomyLevel : undefined
    const errM = showAutonomyMutationErrors ? autonomyMutationFieldErrors.mutationPolicy : undefined
    const errG = showAutonomyMutationErrors ? autonomyMutationFieldErrors.guardrail : undefined
    const showGuardrail =
      needsL3ReadonlyAck(autonomyMutation) || needsTierRiskAck(contributionSetupKind, autonomyMutation)
    return (
      <section className="forge-support" aria-labelledby="bpw-step-heading">
        <h2 id="bpw-step-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
          {title}
        </h2>
        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          Choose how much the assistant automates and what kinds of edits are allowed. Defaults match your contribution scale.
        </p>
        <div style={{ marginTop: '0.5rem' }}>
          <label className="forge-support" style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={autonomyMutation.advancedOverride}
              disabled={disabled}
              onChange={(e) =>
                onAutonomyMutationChange({
                  ...autonomyMutation,
                  advancedOverride: e.target.checked,
                  guardrailAcknowledged: false,
                })
              }
            />
            Advanced — keep my autonomy and mutation choices when contribution scale changes
          </label>
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-autonomy" style={{ display: 'block' }}>
            Autonomy <span aria-hidden="true">*</span>
          </label>
          <select
            id="bpw-autonomy"
            className="le-select"
            value={autonomyMutation.autonomyLevel}
            disabled={disabled}
            onChange={(e) =>
              onAutonomyMutationChange({
                ...autonomyMutation,
                autonomyLevel: e.target.value as AutonomyMutationPayloadV1['autonomyLevel'],
                guardrailAcknowledged: false,
              })
            }
            aria-describedby="bpw-autonomy-hint"
            style={{ marginTop: '0.35rem', minWidth: '20rem' }}
          >
            {(['l0_analyst', 'l1_drafter', 'l2_stage_autopilot', 'l3_goal_autopilot'] as const).map((lv) => (
              <option key={lv} value={lv} title={AUTONOMY_UI[lv].plain}>
                {AUTONOMY_UI[lv].title}
              </option>
            ))}
          </select>
          <p id="bpw-autonomy-hint" className="forge-support" style={{ marginTop: '0.35rem', opacity: 0.9 }}>
            {AUTONOMY_UI[autonomyMutation.autonomyLevel]?.plain}
          </p>
          {errA && (
            <p className="forge-support" role="alert" style={{ color: 'var(--le-danger, #f87171)' }}>
              {errA}
            </p>
          )}
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-mutation" style={{ display: 'block' }}>
            Mutation policy <span aria-hidden="true">*</span>
          </label>
          <select
            id="bpw-mutation"
            className="le-select"
            value={autonomyMutation.mutationPolicy}
            disabled={disabled}
            onChange={(e) =>
              onAutonomyMutationChange({
                ...autonomyMutation,
                mutationPolicy: e.target.value as AutonomyMutationPayloadV1['mutationPolicy'],
                guardrailAcknowledged: false,
              })
            }
            aria-describedby="bpw-mutation-hint"
            style={{ marginTop: '0.35rem', minWidth: '22rem', maxWidth: '100%' }}
          >
            {(
              [
                'read_only_analysis',
                'draft_downstream_only',
                'edit_downstream_drafts',
                'regenerate_downstream_from_approved_upstream',
                'propose_upstream_only',
              ] as const
            ).map((p) => (
              <option key={p} value={p} title={MUTATION_UI[p].plain}>
                {MUTATION_UI[p].title}
              </option>
            ))}
          </select>
          <p id="bpw-mutation-hint" className="forge-support" style={{ marginTop: '0.35rem', opacity: 0.9 }}>
            {MUTATION_UI[autonomyMutation.mutationPolicy]?.plain}
          </p>
          {errM && (
            <p className="forge-support" role="alert" style={{ color: 'var(--le-danger, #f87171)' }}>
              {errM}
            </p>
          )}
        </div>
        {showGuardrail && (
          <div style={{ marginTop: '0.75rem' }}>
            <label className="forge-support" style={{ display: 'flex', gap: '0.35rem', alignItems: 'flex-start' }}>
              <input
                type="checkbox"
                checked={autonomyMutation.guardrailAcknowledged}
                disabled={disabled}
                onChange={(e) =>
                  onAutonomyMutationChange({ ...autonomyMutation, guardrailAcknowledged: e.target.checked })
                }
              />
              <span>
                I understand this autonomy and mutation combination.
                {errG && (
                  <span className="forge-support" role="alert" style={{ display: 'block', color: 'var(--le-danger, #f87171)', marginTop: '0.25rem' }}>
                    {errG}
                  </span>
                )}
              </span>
            </label>
          </div>
        )}
      </section>
    )
  }

  if (stepIndex === 7) {
    const errB = showScopeSelectionErrors ? scopeSelectionFieldErrors.scopeBoundary : undefined
    const errD = showScopeSelectionErrors ? scopeSelectionFieldErrors.detail : undefined
    const boundary = scopeSelection.scopeBoundary
    return (
      <section className="forge-support" aria-labelledby="bpw-step-heading">
        <h2 id="bpw-step-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
          {title}
        </h2>
        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          Narrow where this session applies. Summary lines come from your Understanding step; scope boundaries add structure for
          automation and exports.
        </p>
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-scope-boundary" style={{ display: 'block' }}>
            Scope boundary <span aria-hidden="true">*</span>
          </label>
          <select
            id="bpw-scope-boundary"
            className="le-select"
            value={boundary}
            disabled={disabled}
            onChange={(e) =>
              onScopeSelectionChange({
                ...scopeSelection,
                scopeBoundary: e.target.value as ScopeSelectionPayloadV1['scopeBoundary'],
              })
            }
            aria-describedby="bpw-scope-boundary-hint"
            style={{ marginTop: '0.35rem', minWidth: '20rem', maxWidth: '100%' }}
          >
            {(
              [
                'full_plan',
                'milestone',
                'wbe_subtree',
                'capability',
                'team_slice',
                'repo_path',
                'recheck_subset',
              ] as const
            ).map((b) => (
              <option key={b} value={b} title={SCOPE_BOUNDARY_UI[b].plain}>
                {SCOPE_BOUNDARY_UI[b].title}
              </option>
            ))}
          </select>
          <p id="bpw-scope-boundary-hint" className="forge-support" style={{ marginTop: '0.35rem', opacity: 0.9 }}>
            {SCOPE_BOUNDARY_UI[boundary]?.plain}
          </p>
          {errB && (
            <p className="forge-support" role="alert" style={{ color: 'var(--le-danger, #f87171)' }}>
              {errB}
            </p>
          )}
        </div>
        <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {boundary === 'milestone' && (
              <div>
                <label className="forge-support" htmlFor="bpw-milestone-ref" style={{ display: 'block' }}>
                  Milestone reference
                </label>
                <input
                  id="bpw-milestone-ref"
            className="le-input"
                  value={scopeSelection.milestoneRef}
                  disabled={disabled}
                  onChange={(e) => onScopeSelectionChange({ ...scopeSelection, milestoneRef: e.target.value })}
                  style={{ width: '100%', marginTop: '0.25rem' }}
                />
              </div>
            )}
            {boundary === 'wbe_subtree' && (
              <div>
                <label className="forge-support" htmlFor="bpw-wbe-path" style={{ display: 'block' }}>
                  WBE path
                </label>
                <textarea
                  id="bpw-wbe-path"
            className="le-input"
                  value={scopeSelection.wbePath}
                  disabled={disabled}
                  onChange={(e) => onScopeSelectionChange({ ...scopeSelection, wbePath: e.target.value })}
                  style={{ width: '100%', marginTop: '0.25rem', minHeight: '4rem' }}
                />
              </div>
            )}
            {boundary === 'capability' && (
              <div>
                <label className="forge-support" htmlFor="bpw-cap-label" style={{ display: 'block' }}>
                  Capability / feature
                </label>
                <input
                  id="bpw-cap-label"
            className="le-input"
                  value={scopeSelection.capabilityLabel}
                  disabled={disabled}
                  onChange={(e) => onScopeSelectionChange({ ...scopeSelection, capabilityLabel: e.target.value })}
                  style={{ width: '100%', marginTop: '0.25rem' }}
                />
              </div>
            )}
            {boundary === 'team_slice' && (
              <div>
                <label className="forge-support" htmlFor="bpw-team" style={{ display: 'block' }}>
                  Team
                </label>
                <input
                  id="bpw-team"
            className="le-input"
                  value={scopeSelection.teamLabel}
                  disabled={disabled}
                  onChange={(e) => onScopeSelectionChange({ ...scopeSelection, teamLabel: e.target.value })}
                  style={{ width: '100%', marginTop: '0.25rem' }}
                />
              </div>
            )}
            {boundary === 'repo_path' && (
              <div>
                <label className="forge-support" htmlFor="bpw-repo-paths" style={{ display: 'block' }}>
                  Repo paths (one per line)
                </label>
                <textarea
                  id="bpw-repo-paths"
            className="le-input"
                  value={scopeSelection.repoPathsText}
                  disabled={disabled}
                  onChange={(e) => onScopeSelectionChange({ ...scopeSelection, repoPathsText: e.target.value })}
                  style={{ width: '100%', marginTop: '0.25rem', minHeight: '5rem', fontFamily: 'inherit' }}
                />
              </div>
            )}
            {boundary === 'recheck_subset' && (
              <div>
                <label className="forge-support" htmlFor="bpw-recheck" style={{ display: 'block' }}>
                  Stale / conflicting / recheck notes
                </label>
                <textarea
                  id="bpw-recheck"
            className="le-input"
                  value={scopeSelection.recheckIssueRefs}
                  disabled={disabled}
                  onChange={(e) => onScopeSelectionChange({ ...scopeSelection, recheckIssueRefs: e.target.value })}
                  style={{ width: '100%', marginTop: '0.25rem', minHeight: '5rem' }}
                />
              </div>
            )}
        </div>
        <div style={{ marginTop: '0.5rem' }}>
          <label className="forge-support" style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={scopeSelection.advancedScopeExpanded}
              disabled={disabled}
              onChange={(e) => onScopeSelectionChange({ ...scopeSelection, advancedScopeExpanded: e.target.checked })}
            />
            Advanced — closure options (exact slice, upstream, contracts, downstream, verification)
          </label>
        </div>
        {scopeSelection.advancedScopeExpanded && (
          <fieldset style={{ border: 'none', padding: 0, marginTop: '0.75rem' }}>
            <legend className="forge-support" style={{ marginBottom: '0.35rem' }}>
              Closure options
            </legend>
            {(
              [
                'exact_only',
                'include_required_upstream',
                'include_shared_contracts',
                'include_downstream_impacted',
                'include_verification_artifacts',
              ] as const
            ).map((co) => (
              <label
                key={co}
                className="forge-support"
                style={{ display: 'flex', gap: '0.35rem', alignItems: 'flex-start', marginBottom: '0.25rem' }}
              >
                <input
                  type="checkbox"
                  checked={scopeSelection.closureOptions.includes(co)}
                  disabled={disabled}
                  onChange={(e) => {
                    const on = e.target.checked
                    const next = on
                      ? [...scopeSelection.closureOptions, co]
                      : scopeSelection.closureOptions.filter((x) => x !== co)
                    onScopeSelectionChange({ ...scopeSelection, closureOptions: next })
                  }}
                />
                {CLOSURE_OPTION_UI[co]}
              </label>
            ))}
          </fieldset>
        )}
        {errD && (
          <p className="forge-support" role="alert" style={{ marginTop: '0.75rem', color: 'var(--le-danger, #f87171)' }}>
            {errD}
          </p>
        )}
      </section>
    )
  }

  if (stepIndex === 8) {
    const errT = showRunPlanErrors ? runPlanFieldErrors.title : undefined
    const errS = showRunPlanErrors ? runPlanFieldErrors.steps : undefined
    const rp = runPlan
    return (
      <section className="forge-support" aria-labelledby="bpw-step-heading">
        <h2 id="bpw-step-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
          {title}
        </h2>
        {runPlanPreview ? (
          <RunPlanPreviewPanel preview={runPlanPreview} onJumpToStep={onJumpToStep} disabled={disabled} />
        ) : null}
        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          Outline how you will execute: a short plan title plus ordered steps. Draft text is generated from your target stage,
          output pack kind, and scope — edit freely.
        </p>
        <div style={{ marginTop: '0.75rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
          {onRegenerateRunPlan && (
            <button
              type="button"
              className="forge-support"
              disabled={disabled}
              onClick={() => onRegenerateRunPlan()}
            >
              Regenerate from context
            </button>
          )}
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-run-plan-title" style={{ display: 'block' }}>
            Plan title <span aria-hidden="true">*</span>
          </label>
          <input
            id="bpw-run-plan-title"
            className="le-input"
            type="text"
            maxLength={RUN_PLAN_TITLE_MAX}
            value={rp.title}
            disabled={disabled}
            onChange={(e) =>
              onRunPlanChange(clampRunPlan({ ...rp, title: e.target.value }))
            }
            aria-invalid={Boolean(errT)}
            aria-describedby={errT ? 'bpw-run-plan-title-err' : undefined}
            style={{ width: '100%', marginTop: '0.35rem' }}
          />
          {errT && (
            <p id="bpw-run-plan-title-err" className="forge-support" role="alert" style={{ color: 'var(--le-danger, #f87171)', marginTop: '0.35rem' }}>
              {errT}
            </p>
          )}
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <p className="forge-support" style={{ fontWeight: 600 }}>
            Steps <span aria-hidden="true">*</span>
          </p>
          {rp.steps.map((step, idx) => (
            <div
              key={step.id || `idx-${idx}`}
              style={{
                marginTop: '0.75rem',
                padding: '0.75rem',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: '6px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', alignItems: 'center' }}>
                <span className="forge-support" style={{ fontWeight: 600 }}>
                  Step {idx + 1}
                </span>
                <button
                  type="button"
                  className="forge-support"
                  disabled={disabled || rp.steps.length <= 1}
                  onClick={() => {
                    const nextSteps = rp.steps.filter((_, i) => i !== idx)
                    onRunPlanChange(clampRunPlan({ ...rp, steps: nextSteps }))
                  }}
                >
                  Remove
                </button>
              </div>
              <label className="forge-support" htmlFor={`bpw-rp-step-title-${idx}`} style={{ display: 'block', marginTop: '0.5rem' }}>
                Title <span aria-hidden="true">*</span>
              </label>
              <input
                id={`bpw-rp-step-title-${idx}`}
                className="le-input"
                type="text"
                maxLength={RUN_PLAN_STEP_TITLE_MAX}
                value={step.title}
                disabled={disabled}
                onChange={(e) => {
                  const steps = rp.steps.map((s, i) =>
                    i === idx ? { ...s, title: e.target.value } : s,
                  )
                  onRunPlanChange(clampRunPlan({ ...rp, steps }))
                }}
                style={{ width: '100%', marginTop: '0.25rem' }}
              />
              <label className="forge-support" htmlFor={`bpw-rp-step-detail-${idx}`} style={{ display: 'block', marginTop: '0.5rem' }}>
                Detail
              </label>
              <textarea
                id={`bpw-rp-step-detail-${idx}`}
                className="le-input"
                maxLength={RUN_PLAN_STEP_DETAIL_MAX}
                value={step.detail}
                disabled={disabled}
                onChange={(e) => {
                  const steps = rp.steps.map((s, i) =>
                    i === idx ? { ...s, detail: e.target.value } : s,
                  )
                  onRunPlanChange(clampRunPlan({ ...rp, steps }))
                }}
                style={{ width: '100%', minHeight: '4.5rem', marginTop: '0.25rem', fontFamily: 'inherit' }}
              />
            </div>
          ))}
          {errS && (
            <p className="forge-support" role="alert" style={{ color: 'var(--le-danger, #f87171)', marginTop: '0.5rem' }}>
              {errS}
            </p>
          )}
          <button
            type="button"
            className="forge-support"
            style={{ marginTop: '0.75rem' }}
            disabled={disabled || rp.steps.length >= RUN_PLAN_MAX_STEPS}
            onClick={() =>
              onRunPlanChange(
                clampRunPlan({
                  ...rp,
                  steps: [...rp.steps, { id: '', title: 'New step', detail: '' }],
                }),
              )
            }
          >
            Add step
          </button>
        </div>
      </section>
    )
  }

  if (stepIndex === 9) {
    return (
      <section className="forge-support" aria-labelledby="bpw-step-heading">
        <h2 id="bpw-step-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
          {title}
        </h2>
        <ReviewGenerateStepPanel
          preview={runPlanPreview ?? null}
          draftNote={draftNote}
          onDraftChange={onDraftChange}
          disabled={disabled}
          artifactGeneration={artifactGeneration}
          recheckSummary={recheckSummary}
          reviewGenAvailable={reviewGenAvailable}
          onGenerateArtifacts={onGenerateArtifacts}
          onArtifactReview={onArtifactReview}
          onApproveArtifactBundle={onApproveArtifactBundle}
          onExportArtifacts={onExportArtifacts}
          onArtifactRecheck={onArtifactRecheck}
          artifactGenBusy={artifactGenBusy}
          recheckBusy={recheckBusy}
          artifactGenError={artifactGenError}
        />
      </section>
    )
  }

  if (stepIndex === 10) {
    if (
      onRecheckRepairRegenerate &&
      onApplyRecheckToScope &&
      onApplyRecheckRunPlan &&
      onArtifactReview &&
      onJumpToStep
    ) {
      return (
        <RecheckRepairDashboard
          recheckSummary={recheckSummary ?? null}
          onArtifactRecheck={onArtifactRecheck}
          onArtifactRecheckPreview={onArtifactRecheckPreview}
          recheckBusy={recheckBusy}
          recheckPersistBusy={recheckPersistBusy}
          recheckPreviewBusy={recheckPreviewBusy}
          disabled={disabled}
          artifactGenBusy={artifactGenBusy}
          artifactGenError={artifactGenError}
          onRegenerateKeys={onRecheckRepairRegenerate}
          onArtifactReview={onArtifactReview}
          onApplyToScope={onApplyRecheckToScope}
          onApplyRunPlan={onApplyRecheckRunPlan}
          onJumpToStep={onJumpToStep}
        />
      )
    }
    return (
      <section className="forge-support" aria-labelledby="bpw-step-heading">
        <h2 id="bpw-step-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
          {title}
        </h2>
        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          Recheck / Repair dashboard requires a live session with artifact APIs. Use local draft notes below, or open
          this wizard with the Lenses server.
        </p>
        <label className="forge-support" htmlFor="bpw-draft-note-recheck" style={{ display: 'block', marginTop: '0.75rem' }}>
          Notes for this step (saved with the session)
        </label>
        <textarea
          id="bpw-draft-note-recheck"
          className="le-input"
          style={{ width: '100%', minHeight: '6rem', marginTop: '0.35rem' }}
          value={draftNote}
          disabled={disabled}
          onChange={(e) => onDraftChange(e.target.value)}
          placeholder="Optional notes…"
        />
      </section>
    )
  }

  if (stepIndex === 11) {
    const sid = wizardSessionId?.trim() ?? ''
    if (sid) {
      return (
        <ExperimentalBuildStepPanel
          sessionId={sid}
          artifactGeneration={artifactGeneration}
          closureOptionsDefault={scopeSelection.closureOptions}
          disabled={disabled}
        />
      )
    }
    return (
      <section className="forge-support" aria-labelledby="bpw-step-heading">
        <h2 id="bpw-step-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
          {title}
        </h2>
        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          Cursor Launch Pack requires a live Lenses session. Open this wizard with the server, or use draft notes
          below.
        </p>
        <label className="forge-support" htmlFor="bpw-draft-note-build" style={{ display: 'block', marginTop: '0.75rem' }}>
          Notes for this step (saved with the session)
        </label>
        <textarea
          id="bpw-draft-note-build"
          className="le-input"
          style={{ width: '100%', minHeight: '6rem', marginTop: '0.35rem' }}
          value={draftNote}
          disabled={disabled}
          onChange={(e) => onDraftChange(e.target.value)}
          placeholder="Optional notes…"
        />
      </section>
    )
  }

  return (
    <section className="forge-support" aria-labelledby="bpw-step-heading">
      <h2 id="bpw-step-heading" className="forge-support" style={{ fontSize: '1.15rem', fontWeight: 600 }}>
        {title}
      </h2>
      <p className="forge-support" style={{ marginTop: '0.5rem' }}>
        Placeholder content for this step. Details will ship in a later iteration.
      </p>
      <label className="forge-support" htmlFor="bpw-draft-note" style={{ display: 'block', marginTop: '0.75rem' }}>
        Notes for this step (saved with the session)
      </label>
      <textarea
        id="bpw-draft-note"
        className="le-input"
        style={{ width: '100%', minHeight: '6rem', marginTop: '0.35rem' }}
        value={draftNote}
        disabled={disabled}
        onChange={(e) => onDraftChange(e.target.value)}
        placeholder="Optional notes…"
      />
    </section>
  )
}
