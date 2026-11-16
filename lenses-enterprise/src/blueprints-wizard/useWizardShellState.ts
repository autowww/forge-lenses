import { useCallback, useEffect, useRef, useState } from 'react'
import type { WizardSessionDocumentJson } from '../api/blueprintsWizard'
import { clampContextIntakePayload, type ContextIntakePayloadV1 } from './contextIntakeStep'
import { clampContributionSetupPayload, type ContributionSetupPayloadV1 } from './contributionSetupStep'
import { clampMissionPayload, type MissionPayloadV1 } from './missionStep'
import { clampStepIndex } from './wizardSteps'
import type { WizardShellPersistence, WizardPersistedState } from './wizardPersistence'
import { emptyWizardDomain, normalizeWizardDomain } from './wizardDomainNormalize'
import type { ClarificationPayloadV1 } from './clarificationStep'
import {
  clampInterpretationPayload,
  type InterpretationPayloadV1,
} from './interpretationPayload'
import { defaultAutonomyMutationForKind } from './contributionSetupDefaults'
import type { ContributionSetupKind, MissionType, RunPlanJson } from './wizardDomainTypes'
import { mergeShellIntoWizardDocument, wizardDocumentToShellState } from './wizardSessionMapping'
import type { AutonomyMutationPayloadV1 } from './autonomyMutationStep'
import type { ScopeSelectionPayloadV1 } from './scopeSelectionStep'
import {
  clampTargetOutputPackPayload,
  defaultPackLabelForKind,
  type TargetOutputPackPayloadV1,
} from './targetOutputPackStep'
import type { UnderstandingPayloadV1 } from './understandingStep'
import { deriveDraftRunPlanFromShell } from './runPlanStep'
import {
  emptyWizardShellState,
  getNoteForStep,
  goBack,
  goNext,
  setAutonomyMutation,
  setClarification,
  setContextIntake,
  setContributionSetup,
  setContributionSetupKind,
  setMission,
  setMissionType,
  setNoteForStep,
  setRunPlan,
  setScopeSelection,
  setTargetOutputPack,
  setInterpretation,
  setUnderstanding,
  type WizardShellState,
} from './wizardShellState'
import {
  UNDERSTANDING_GAPS_MAX,
  UNDERSTANDING_SUMMARY_MAX,
  clampUnderstandingPayload,
} from './understandingStep'

function shellFromLoaded(loaded: WizardPersistedState): WizardShellState {
  const wd = loaded.wizardDomain ?? loaded.persistedWizardDomain ?? emptyWizardDomain()
  const fakeDoc: WizardSessionDocumentJson = {
    version: 1,
    updated_at: '',
    step_index: loaded.stepIndex,
    payload: {
      stepNotes: loaded.stepNotes,
      mission: loaded.mission,
      contributionSetup: loaded.contributionSetup,
      contextIntake: loaded.contextIntake,
      interpretation: loaded.interpretation,
      understanding: loaded.understanding,
      clarification: loaded.clarification,
      targetOutputPack: loaded.targetOutputPack,
      wizard_domain: wd,
    },
  }
  return {
    ...wizardDocumentToShellState(fakeDoc),
    persistedWizardDomain: normalizeWizardDomain(wd),
  }
}

export function useWizardShellState(persistence: WizardShellPersistence) {
  const [state, setState] = useState<WizardShellState>(() => {
    const loaded = persistence.load()
    if (loaded) {
      return shellFromLoaded(loaded)
    }
    return emptyWizardShellState()
  })

  const prevAutonomyStepRef = useRef(state.stepIndex)
  useEffect(() => {
    const entered6 = prevAutonomyStepRef.current !== 6 && state.stepIndex === 6
    prevAutonomyStepRef.current = state.stepIndex
    if (!entered6) return
    if (state.autonomyMutation.advancedOverride) return
    const d = defaultAutonomyMutationForKind(state.contributionSetupKind)
    setState((s) =>
      setAutonomyMutation(s, {
        ...s.autonomyMutation,
        autonomyLevel: d.autonomyLevel,
        mutationPolicy: d.mutationPolicy,
        guardrailAcknowledged: false,
      }),
    )
  }, [state.stepIndex, state.contributionSetupKind, state.autonomyMutation.advancedOverride])

  const prevRunPlanStepRef = useRef(state.stepIndex)
  useEffect(() => {
    const entered8 = prevRunPlanStepRef.current !== 8 && state.stepIndex === 8
    prevRunPlanStepRef.current = state.stepIndex
    if (!entered8) return
    if (state.runPlan.steps.length > 0) return
    setState((s) => setRunPlan(s, deriveDraftRunPlanFromShell(s)))
  }, [state.stepIndex, state.runPlan.steps.length])

  const draftNote = getNoteForStep(state, state.stepIndex)

  const setDraftNote = useCallback((text: string) => {
    setState((s) => setNoteForStep(s, s.stepIndex, text))
  }, [])

  const setMissionFields = useCallback((mission: MissionPayloadV1) => {
    setState((s) => setMission(s, clampMissionPayload(mission)))
  }, [])

  const setMissionTypeField = useCallback((missionType: MissionType) => {
    setState((s) => setMissionType(s, missionType))
  }, [])

  const setContributionSetupFields = useCallback((cs: ContributionSetupPayloadV1) => {
    setState((s) => setContributionSetup(s, clampContributionSetupPayload(cs)))
  }, [])

  const setContributionSetupKindField = useCallback((k: ContributionSetupKind) => {
    setState((s) => {
      let next = setContributionSetupKind(s, k)
      if (!next.autonomyMutation.advancedOverride) {
        const d = defaultAutonomyMutationForKind(k)
        next = setAutonomyMutation(next, {
          ...next.autonomyMutation,
          autonomyLevel: d.autonomyLevel,
          mutationPolicy: d.mutationPolicy,
          guardrailAcknowledged: false,
        })
      }
      return next
    })
  }, [])

  const setContextIntakeFields = useCallback((ci: ContextIntakePayloadV1) => {
    setState((s) => setContextIntake(s, clampContextIntakePayload(ci)))
  }, [])

  const setUnderstandingFields = useCallback((u: UnderstandingPayloadV1) => {
    setState((s) => setUnderstanding(s, u))
  }, [])

  const setInterpretationFields = useCallback((i: InterpretationPayloadV1) => {
    const clamped = clampInterpretationPayload(i)
    setState((s) =>
      setUnderstanding(
        setInterpretation(s, clamped),
        clampUnderstandingPayload({
          summary: clamped.what_user_said.slice(0, UNDERSTANDING_SUMMARY_MAX),
          knownGaps: clamped.unknowns
            .map((x) => x.trim())
            .filter(Boolean)
            .join('\n')
            .slice(0, UNDERSTANDING_GAPS_MAX),
        }),
      ),
    )
  }, [])

  const setClarificationFields = useCallback((c: ClarificationPayloadV1) => {
    setState((s) => setClarification(s, c))
  }, [])

  const setTargetOutputPackFields = useCallback((t: TargetOutputPackPayloadV1) => {
    setState((s) => {
      let next = clampTargetOutputPackPayload(t)
      if (!next.useCustomPackLabel) {
        next = { ...next, packLabel: defaultPackLabelForKind(next.outputPackKind) }
      }
      return setTargetOutputPack(s, next)
    })
  }, [])

  const setAutonomyMutationFields = useCallback((a: AutonomyMutationPayloadV1) => {
    setState((s) => setAutonomyMutation(s, a))
  }, [])

  const setScopeSelectionFields = useCallback((sc: ScopeSelectionPayloadV1) => {
    setState((s) => setScopeSelection(s, sc))
  }, [])

  const setRunPlanFields = useCallback((next: RunPlanJson) => {
    setState((s) => setRunPlan(s, next))
  }, [])

  const regenerateRunPlanFromContext = useCallback(() => {
    setState((s) => setRunPlan(s, deriveDraftRunPlanFromShell(s)))
  }, [])

  const next = useCallback(() => {
    setState((s) => goNext(s))
  }, [])

  const back = useCallback(() => {
    setState((s) => goBack(s))
  }, [])

  const saveDraft = useCallback(() => {
    const baseWd = state.persistedWizardDomain ?? emptyWizardDomain()
    const fake: WizardSessionDocumentJson = {
      version: 1,
      updated_at: '',
      step_index: state.stepIndex,
      payload: { wizard_domain: baseWd },
    }
    const merged = mergeShellIntoWizardDocument(fake, state)
    const wd = normalizeWizardDomain(merged.payload.wizard_domain)
    const nextShell = wizardDocumentToShellState(merged)
    const toSave: WizardPersistedState = {
      ...nextShell,
      persistedWizardDomain: wd,
      wizardDomain: wd,
    }
    persistence.save(toSave)
    setState((s) => ({
      ...nextShell,
      persistedWizardDomain: wd,
      stepNotes: nextShell.stepNotes,
      stepIndex: s.stepIndex,
    }))
  }, [persistence, state])

  const clearDraft = useCallback(() => {
    persistence.clear()
    setState(emptyWizardShellState())
  }, [persistence])

  return {
    state,
    persistedWizardDomain: state.persistedWizardDomain,
    stepIndex: clampStepIndex(state.stepIndex),
    mission: state.mission,
    setMission: setMissionFields,
    missionType: state.missionType,
    setMissionType: setMissionTypeField,
    contributionSetup: state.contributionSetup,
    setContributionSetup: setContributionSetupFields,
    contributionSetupKind: state.contributionSetupKind,
    setContributionSetupKind: setContributionSetupKindField,
    contextIntake: state.contextIntake,
    setContextIntake: setContextIntakeFields,
    interpretation: state.interpretation,
    setInterpretation: setInterpretationFields,
    understanding: state.understanding,
    setUnderstanding: setUnderstandingFields,
    clarification: state.clarification,
    setClarification: setClarificationFields,
    assumptionLedger: state.assumptionLedger,
    foundationBriefFieldStatuses: state.foundationBriefFieldStatuses,
    targetOutputPack: state.targetOutputPack,
    setTargetOutputPack: setTargetOutputPackFields,
    autonomyMutation: state.autonomyMutation,
    setAutonomyMutation: setAutonomyMutationFields,
    scopeSelection: state.scopeSelection,
    setScopeSelection: setScopeSelectionFields,
    runPlan: state.runPlan,
    setRunPlan: setRunPlanFields,
    regenerateRunPlanFromContext,
    draftNote,
    setDraftNote,
    next,
    back,
    saveDraft,
    clearDraft,
  }
}
