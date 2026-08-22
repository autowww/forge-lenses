import { clampStepIndex, stepIndexBack, stepIndexNext } from './wizardSteps'
import type { ClarificationPayloadV1 } from './clarificationStep'
import { emptyClarificationPayload } from './clarificationStep'
import type { ContextIntakePayloadV1 } from './contextIntakeStep'
import { emptyContextIntakePayload } from './contextIntakeStep'
import type { ContributionSetupPayloadV1 } from './contributionSetupStep'
import { emptyContributionSetupPayload } from './contributionSetupStep'
import type { MissionPayloadV1 } from './missionStep'
import { emptyMissionPayload, missionModeToMissionType } from './missionStep'
import type { AutonomyMutationPayloadV1 } from './autonomyMutationStep'
import { emptyAutonomyMutationPayload } from './autonomyMutationStep'
import type { ScopeSelectionPayloadV1 } from './scopeSelectionStep'
import { emptyScopeSelectionPayload } from './scopeSelectionStep'
import type { TargetOutputPackPayloadV1 } from './targetOutputPackStep'
import { emptyTargetOutputPackPayload } from './targetOutputPackStep'
import type { UnderstandingPayloadV1 } from './understandingStep'
import { emptyUnderstandingPayload } from './understandingStep'
import type {
  AssumptionLedgerEntryJson,
  ContributionSetupKind,
  InterpretationFieldStatus,
  MissionType,
  RunPlanJson,
  WizardDomainJson,
} from './wizardDomainTypes'
import type { InterpretationPayloadV1 } from './interpretationPayload'
import { emptyInterpretationPayload } from './interpretationPayload'
import { emptyRunPlanPayload } from './runPlanStep'

export type WizardShellState = {
  stepIndex: number
  /** Keyed by step index string ("0" … "11"). */
  stepNotes: Record<string, string>
  /** Step 0 structured fields; mirrored to `payload.mission` on save. */
  mission: MissionPayloadV1
  /** `payload.wizard_domain.mission_type` (Forge Blueprints domain enum). */
  missionType: MissionType
  /** Step 1 structured fields; mirrored to `payload.contributionSetup` on save. */
  contributionSetup: ContributionSetupPayloadV1
  /** `payload.wizard_domain.contribution_setup_kind` (scale: single / team / teams / enterprise). */
  contributionSetupKind: ContributionSetupKind
  /** Step 2 structured fields; mirrored to `payload.contextIntake` on save. */
  contextIntake: ContextIntakePayloadV1
  /** Step 3 — structured interpretation canvas + Foundation Brief draft (`payload.interpretation`). */
  interpretation: InterpretationPayloadV1
  /** Step 3 — understanding; drives `wizard_domain.scope_spec` (kept in sync with interpretation when editing canvas). */
  understanding: UnderstandingPayloadV1
  /** Step 4 — clarification; drives `prompt_recipe.variables`. */
  clarification: ClarificationPayloadV1
  /** Step 5 — target stage + artifact pack draft; drives `target_stage` + `artifact_packs`. */
  targetOutputPack: TargetOutputPackPayloadV1
  /** Step 6 — autonomy + mutation policy; drives `wizard_domain` enums. */
  autonomyMutation: AutonomyMutationPayloadV1
  /** Step 7 — scope boundary + closure; extends `wizard_domain.scope_spec`. */
  scopeSelection: ScopeSelectionPayloadV1
  /** Step 8 — run plan; persisted as `wizard_domain.run_plan`. */
  runPlan: RunPlanJson
  /** `payload.wizard_domain.assumption_ledger` — edited in refine panel, merged on PUT. */
  assumptionLedger: AssumptionLedgerEntryJson[]
  /** `payload.wizard_domain.foundation_brief.field_statuses` — interpretation confidence per field key. */
  foundationBriefFieldStatuses: Record<string, InterpretationFieldStatus>
  /**
   * Local-session snapshot of `wizard_domain` for merge-on-save (sessionStorage draft).
   * Omitted when using server-backed sessions only.
   */
  persistedWizardDomain?: WizardDomainJson
}

export function emptyWizardShellState(): WizardShellState {
  return {
    stepIndex: 0,
    stepNotes: {},
    mission: emptyMissionPayload(),
    missionType: 'explore',
    contributionSetup: emptyContributionSetupPayload(),
    contributionSetupKind: 'single',
    contextIntake: emptyContextIntakePayload(),
    interpretation: emptyInterpretationPayload(),
    understanding: emptyUnderstandingPayload(),
    clarification: emptyClarificationPayload(),
    targetOutputPack: emptyTargetOutputPackPayload(),
    autonomyMutation: emptyAutonomyMutationPayload('single'),
    scopeSelection: emptyScopeSelectionPayload(),
    runPlan: emptyRunPlanPayload(),
    assumptionLedger: [],
    foundationBriefFieldStatuses: {},
  }
}

export function getNoteForStep(state: WizardShellState, stepIndex: number): string {
  return state.stepNotes[String(clampStepIndex(stepIndex))] ?? ''
}

export function setNoteForStep(
  state: WizardShellState,
  stepIndex: number,
  text: string,
): WizardShellState {
  const i = clampStepIndex(stepIndex)
  return {
    ...state,
    stepNotes: { ...state.stepNotes, [String(i)]: text },
  }
}

export function setMission(state: WizardShellState, mission: MissionPayloadV1): WizardShellState {
  const m = { ...mission }
  return {
    ...state,
    mission: m,
    missionType: missionModeToMissionType(m.mode),
  }
}

export function setMissionType(state: WizardShellState, missionType: MissionType): WizardShellState {
  return { ...state, missionType }
}

export function setContributionSetup(
  state: WizardShellState,
  contributionSetup: ContributionSetupPayloadV1,
): WizardShellState {
  return { ...state, contributionSetup: { ...contributionSetup } }
}

export function setContributionSetupKind(
  state: WizardShellState,
  contributionSetupKind: ContributionSetupKind,
): WizardShellState {
  return { ...state, contributionSetupKind }
}

export function setContextIntake(
  state: WizardShellState,
  contextIntake: ContextIntakePayloadV1,
): WizardShellState {
  return { ...state, contextIntake: { ...contextIntake } }
}

export function setInterpretation(state: WizardShellState, i: InterpretationPayloadV1): WizardShellState {
  return { ...state, interpretation: { ...i } }
}

export function setUnderstanding(state: WizardShellState, u: UnderstandingPayloadV1): WizardShellState {
  return { ...state, understanding: { ...u } }
}

export function setClarification(state: WizardShellState, c: ClarificationPayloadV1): WizardShellState {
  return { ...state, clarification: { ...c } }
}

export function setTargetOutputPack(state: WizardShellState, t: TargetOutputPackPayloadV1): WizardShellState {
  return { ...state, targetOutputPack: { ...t } }
}

export function setAutonomyMutation(state: WizardShellState, a: AutonomyMutationPayloadV1): WizardShellState {
  return { ...state, autonomyMutation: { ...a } }
}

export function setScopeSelection(state: WizardShellState, s: ScopeSelectionPayloadV1): WizardShellState {
  return { ...state, scopeSelection: { ...s } }
}

export function setRunPlan(state: WizardShellState, runPlan: RunPlanJson): WizardShellState {
  return { ...state, runPlan: { ...runPlan, steps: runPlan.steps.map((x) => ({ ...x })) } }
}

export function setAssumptionLedger(
  state: WizardShellState,
  assumptionLedger: AssumptionLedgerEntryJson[],
): WizardShellState {
  return { ...state, assumptionLedger: [...assumptionLedger] }
}

export function setFoundationBriefFieldStatuses(
  state: WizardShellState,
  foundationBriefFieldStatuses: Record<string, InterpretationFieldStatus>,
): WizardShellState {
  return { ...state, foundationBriefFieldStatuses: { ...foundationBriefFieldStatuses } }
}

export function goNext(state: WizardShellState): WizardShellState {
  return { ...state, stepIndex: stepIndexNext(state.stepIndex) }
}

export function goBack(state: WizardShellState): WizardShellState {
  return { ...state, stepIndex: stepIndexBack(state.stepIndex) }
}
