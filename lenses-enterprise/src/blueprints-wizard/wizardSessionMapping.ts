import type { WizardSessionDocumentJson } from '../api/blueprintsWizard'
import { clarificationFromPayloadOrRecipe, clampClarificationPayload, formatClarificationForStepNote } from './clarificationStep'
import {
  clampContextIntakePayload,
  contextSourcesForWizardDomain,
  formatContextIntakeForStepNote,
  parseContextIntakeFromPayload,
} from './contextIntakeStep'
import {
  clampContributionSetupPayload,
  formatContributionSetupForStepNote,
  parseContributionSetupFromPayload,
} from './contributionSetupStep'
import {
  clampMissionPayload,
  formatMissionForStepNote,
  hasExplicitMissionMode,
  missionModeToMissionType,
  missionTypeToMissionMode,
  parseMissionFromPayload,
} from './missionStep'
import {
  clampAutonomyMutationPayload,
  formatAutonomyMutationForStepNote,
  parseAutonomyMutationFromPayload,
} from './autonomyMutationStep'
import {
  clampScopeSelectionPayload,
  formatScopeSelectionForStepNote,
  parseScopeSelectionFromPayload,
  scopeSpecFromSelection,
} from './scopeSelectionStep'
import {
  artifactPackFromTargetPayload,
  clampTargetOutputPackPayload,
  formatTargetOutputPackForStepNote,
  targetOutputPackFromPayloadOrDomain,
} from './targetOutputPackStep'
import {
  clampInterpretationPayload,
  emptyInterpretationPayload,
  parseInterpretationFromPayload,
} from './interpretationPayload'
import { applyArtifactGenerationToArtifactPack } from './artifactGenerationPackSync'
import {
  buildMergedArtifactPackAfterGeneration,
  runPlanPreviewInputFromShell,
} from './runPlanPreviewEngine'
import { clampRunPlan, formatRunPlanForStepNote } from './runPlanStep'
import {
  UNDERSTANDING_GAPS_MAX,
  UNDERSTANDING_SUMMARY_MAX,
  clampUnderstandingPayload,
  formatUnderstandingForStepNote,
  understandingFromPayloadOrScope,
} from './understandingStep'
import { clampStepIndex } from './wizardSteps'
import { getStepNotesRecord } from './wizardStepModel'
import type { WizardShellState } from './wizardShellState'
import {
  applyResponsesToAssumptionLedger,
  fieldStatusesAfterClarification,
  mergeClarificationIntoFoundationBrief,
} from './clarificationMerge'
import { validateClarificationForNext } from './clarificationStep'
import {
  normalizeFoundationBrief,
  normalizePromptRecipe,
  normalizeScopeSpec,
  normalizeWizardDomain,
} from './wizardDomainNormalize'
import type {
  ContextSource,
  ContributionSetupKind,
  InterpretationFieldStatus,
  MissionType,
} from './wizardDomainTypes'

/** Map server session document → in-memory shell state (12-step indices). */
export function wizardDocumentToShellState(doc: WizardSessionDocumentJson): WizardShellState {
  const pl = doc.payload as Record<string, unknown>
  const wd = normalizeWizardDomain(pl.wizard_domain)
  let mission = clampMissionPayload(parseMissionFromPayload(doc.payload))
  if (!hasExplicitMissionMode(pl)) {
    mission = {
      ...mission,
      mode: missionTypeToMissionMode(wd.mission_type as MissionType),
    }
  }
  const contributionSetup = clampContributionSetupPayload(parseContributionSetupFromPayload(doc.payload))
  const contextIntake = clampContextIntakePayload(parseContextIntakeFromPayload(doc.payload))
  const interpretation = clampInterpretationPayload(parseInterpretationFromPayload(pl))
  let understanding = understandingFromPayloadOrScope(pl, wd.scope_spec.summary, wd.scope_spec.constraints_note)
  const hasInterp =
    interpretation.what_user_said.trim().length > 0 ||
    interpretation.inferred.length > 0 ||
    interpretation.needs_confirmation.length > 0 ||
    interpretation.unknowns.length > 0
  if (hasInterp) {
    understanding = clampUnderstandingPayload({
      summary: interpretation.what_user_said.trim()
        ? interpretation.what_user_said.slice(0, UNDERSTANDING_SUMMARY_MAX)
        : understanding.summary,
      knownGaps: interpretation.unknowns.length
        ? interpretation.unknowns.join('\n').slice(0, UNDERSTANDING_GAPS_MAX)
        : understanding.knownGaps,
    })
  }
  const clarification = clarificationFromPayloadOrRecipe(pl, wd.prompt_recipe.variables as Record<string, string>)
  const targetOutputPack = targetOutputPackFromPayloadOrDomain(pl, wd)
  const ck = wd.contribution_setup_kind as ContributionSetupKind
  const autonomyMutation = parseAutonomyMutationFromPayload(pl, ck, wd)
  const scopeSelection = parseScopeSelectionFromPayload(pl, wd.scope_spec)
  const runPlan = clampRunPlan(wd.run_plan)
  const fs = wd.foundation_brief.field_statuses ?? {}
  const foundationBriefFieldStatuses: Record<string, InterpretationFieldStatus> = {}
  for (const [k, v] of Object.entries(fs)) {
    foundationBriefFieldStatuses[k] = v as InterpretationFieldStatus
  }
  return {
    stepIndex: clampStepIndex(doc.step_index),
    stepNotes: { ...getStepNotesRecord(doc.payload) },
    mission,
    missionType: missionModeToMissionType(mission.mode),
    contributionSetup,
    contributionSetupKind: wd.contribution_setup_kind as ContributionSetupKind,
    contextIntake,
    interpretation,
    understanding,
    clarification,
    targetOutputPack,
    autonomyMutation,
    scopeSelection,
    runPlan,
    assumptionLedger: wd.assumption_ledger.map((e) => ({ ...e })),
    foundationBriefFieldStatuses,
  }
}

export type MergeShellOptions = {
  /**
   * When set, replaces `wizard_domain.foundation_brief.markdown` (e.g. structured draft sync).
   * If `base.payload.foundation_brief` is a legacy string, it is updated to the same value.
   */
  foundationBriefMarkdownOverride?: string
}

/** Merge shell navigation + notes + structured steps into a session for PUT (preserves other payload keys). */
export function mergeShellIntoWizardDocument(
  base: WizardSessionDocumentJson,
  shell: WizardShellState,
  options?: MergeShellOptions,
): WizardSessionDocumentJson {
  const m = clampMissionPayload(shell.mission)
  const c = clampContributionSetupPayload(shell.contributionSetup)
  const x = clampContextIntakePayload(shell.contextIntake)
  const interp = clampInterpretationPayload(shell.interpretation ?? emptyInterpretationPayload())
  const u = clampUnderstandingPayload(shell.understanding)
  const cl = clampClarificationPayload(shell.clarification)
  const tp = clampTargetOutputPackPayload(shell.targetOutputPack)
  const am = clampAutonomyMutationPayload(shell.autonomyMutation)
  const ss = clampScopeSelectionPayload(shell.scopeSelection)
  const rp = clampRunPlan(shell.runPlan)
  const stepNotes = {
    ...shell.stepNotes,
    '0': formatMissionForStepNote(m),
    '1': formatContributionSetupForStepNote(c, shell.contributionSetupKind),
    '2': formatContextIntakeForStepNote(x),
    '3': formatUnderstandingForStepNote(u),
    '4': formatClarificationForStepNote(cl),
    '5': formatTargetOutputPackForStepNote(tp),
    '6': formatAutonomyMutationForStepNote(am),
    '7': formatScopeSelectionForStepNote(ss),
    '8': formatRunPlanForStepNote(rp),
  }
  const basePl = base.payload as Record<string, unknown>
  const prevWd = normalizeWizardDomain(basePl.wizard_domain)
  const vars: Record<string, string> = { ...(prevWd.prompt_recipe.variables ?? {}) }
  vars.clarification_open_questions = cl.openQuestions
  vars.clarification_decisions_needed = cl.decisionsNeeded ?? ''

  const clarComplete =
    cl.questions.length > 0 && validateClarificationForNext(cl).ok && !options?.foundationBriefMarkdownOverride
  let fbMarkdown =
    options?.foundationBriefMarkdownOverride !== undefined
      ? options.foundationBriefMarkdownOverride
      : prevWd.foundation_brief.markdown
  let fbStatuses = shell.foundationBriefFieldStatuses
  let ledgerOut = shell.assumptionLedger
  if (clarComplete) {
    fbMarkdown = mergeClarificationIntoFoundationBrief(fbMarkdown, cl.questions, cl.responses)
    fbStatuses = fieldStatusesAfterClarification(shell.foundationBriefFieldStatuses, cl.questions, cl.responses)
    ledgerOut = applyResponsesToAssumptionLedger(shell.assumptionLedger, cl.questions, cl.responses)
  }

  const nextPack = artifactPackFromTargetPayload(tp, prevWd.artifact_packs[0]?.id)
  let pack = nextPack
  if (clampStepIndex(shell.stepIndex) >= 9 && nextPack.items.length > 0) {
    const previewInput = runPlanPreviewInputFromShell(shell, {
      foundationBriefMarkdownEffective: fbMarkdown,
      savedWizardDomain: prevWd,
      assumptionLedger: ledgerOut,
    })
    pack = buildMergedArtifactPackAfterGeneration(previewInput, nextPack)
    pack = applyArtifactGenerationToArtifactPack(pack, prevWd)
  }

  const scopeForMerge = normalizeScopeSpec(
    scopeSpecFromSelection(
      normalizeScopeSpec({
        ...prevWd.scope_spec,
        summary: u.summary,
        constraints_note: u.knownGaps ?? '',
      }),
      ss,
    ),
  )

  const wizard_domain = normalizeWizardDomain({
    ...prevWd,
    mission_type: missionModeToMissionType(clampMissionPayload(shell.mission).mode),
    contribution_setup_kind: shell.contributionSetupKind,
    context_sources: contextSourcesForWizardDomain(x, prevWd.context_sources as ContextSource[]),
    scope_spec: scopeForMerge,
    autonomy_level: am.autonomyLevel,
    mutation_policy: am.mutationPolicy,
    prompt_recipe: normalizePromptRecipe({
      ...prevWd.prompt_recipe,
      variables: vars,
    }),
    target_stage: tp.targetStage,
    artifact_packs: pack.items.length > 0 ? [pack] : prevWd.artifact_packs,
    assumption_ledger: ledgerOut,
    foundation_brief: normalizeFoundationBrief({
      markdown: fbMarkdown,
      field_statuses: fbStatuses,
    }),
    run_plan: rp,
  })
  const nextPayload: Record<string, unknown> = {
    ...base.payload,
    stepNotes,
    mission: m,
    contributionSetup: c,
    contextIntake: x,
    understanding: u,
    clarification: cl,
    targetOutputPack: tp,
    autonomyMutation: am,
    scopeSelection: ss,
    interpretation: interp,
    wizard_domain,
  }
  if (
    options?.foundationBriefMarkdownOverride !== undefined &&
    typeof basePl.foundation_brief === 'string'
  ) {
    nextPayload.foundation_brief = options.foundationBriefMarkdownOverride
  }
  return {
    ...base,
    step_index: clampStepIndex(shell.stepIndex),
    payload: nextPayload,
  }
}
