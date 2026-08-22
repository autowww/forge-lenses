import { useCallback, useMemo, useState } from 'react'
import type { WizardSessionDocumentJson } from '../api/blueprintsWizard'
import { BlueprintsWizardShell } from '../blueprints-wizard/BlueprintsWizardShell'
import { buildClarificationQuestions } from '../blueprints-wizard/clarificationQuestionBuilder'
import { clampClarificationPayload, validateClarificationForNext } from '../blueprints-wizard/clarificationStep'
import { effectiveFoundationBriefMarkdown } from '../blueprints-wizard/foundationBriefSync'
import { emptyWizardDomain, normalizeWizardDomain } from '../blueprints-wizard/wizardDomainNormalize'
import { validateContextIntakeForNext } from '../blueprints-wizard/contextIntakeStep'
import { validateContributionSetupForNext } from '../blueprints-wizard/contributionSetupStep'
import { validateMissionForNext } from '../blueprints-wizard/missionStep'
import { createSessionStorageWizardPersistence } from '../blueprints-wizard/wizardPersistence'
import { validateAutonomyMutationForNext } from '../blueprints-wizard/autonomyMutationStep'
import { validateScopeSelectionForNext } from '../blueprints-wizard/scopeSelectionStep'
import { buildRunPlanPreview, runPlanPreviewInputFromShell } from '../blueprints-wizard/runPlanPreviewEngine'
import { validateRunPlanForNext } from '../blueprints-wizard/runPlanStep'
import { validateTargetOutputPackForNext } from '../blueprints-wizard/targetOutputPackStep'
import { validateUnderstandingForNext } from '../blueprints-wizard/understandingStep'
import { useWizardShellState } from '../blueprints-wizard/useWizardShellState'
import { mergeShellIntoWizardDocument } from '../blueprints-wizard/wizardSessionMapping'

export function BlueprintsWizardLocalMode({
  onExit,
  flagWarning,
  onRetryServerProbe,
}: {
  onExit: () => void
  flagWarning?: string | null
  /** When the server ``/enabled`` probe failed, offer reconnecting to full session APIs. */
  onRetryServerProbe?: () => void
}) {
  const persistence = useMemo(() => createSessionStorageWizardPersistence(), [])
  const {
    state,
    stepIndex,
    draftNote,
    setDraftNote,
    mission,
    setMission,
    contributionSetup,
    setContributionSetup,
    contributionSetupKind,
    setContributionSetupKind,
    contextIntake,
    setContextIntake,
    interpretation,
    setInterpretation,
    understanding,
    setUnderstanding,
    clarification,
    setClarification,
    assumptionLedger,
    foundationBriefFieldStatuses,
    persistedWizardDomain,
    targetOutputPack,
    setTargetOutputPack,
    autonomyMutation,
    setAutonomyMutation,
    scopeSelection,
    setScopeSelection,
    runPlan,
    setRunPlan,
    regenerateRunPlanFromContext,
    next: advanceStep,
    back,
    saveDraft,
  } = useWizardShellState(persistence)
  const [missionAttempted, setMissionAttempted] = useState(false)
  const [contributionAttempted, setContributionAttempted] = useState(false)
  const [contextIntakeAttempted, setContextIntakeAttempted] = useState(false)
  const [understandingAttempted, setUnderstandingAttempted] = useState(false)
  const [clarificationAttempted, setClarificationAttempted] = useState(false)
  const [targetOutputPackAttempted, setTargetOutputPackAttempted] = useState(false)
  const [autonomyMutationAttempted, setAutonomyMutationAttempted] = useState(false)
  const [scopeSelectionAttempted, setScopeSelectionAttempted] = useState(false)
  const [runPlanAttempted, setRunPlanAttempted] = useState(false)

  const missionCheck = validateMissionForNext(mission)
  const contributionCheck = validateContributionSetupForNext(contributionSetup)
  const contextIntakeCheck = validateContextIntakeForNext(contextIntake)
  const understandingCheck = validateUnderstandingForNext(understanding)
  const clarificationCheck = validateClarificationForNext(clarification)
  const targetOutputPackCheck = validateTargetOutputPackForNext(targetOutputPack)
  const autonomyMutationCheck = validateAutonomyMutationForNext(autonomyMutation, contributionSetupKind)
  const scopeSelectionCheck = validateScopeSelectionForNext(scopeSelection)
  const runPlanCheck = validateRunPlanForNext(runPlan)

  const runPlanPreview = useMemo(() => {
    const baseWd = state.persistedWizardDomain ?? emptyWizardDomain()
    const fake: WizardSessionDocumentJson = {
      version: 1,
      updated_at: '',
      step_index: state.stepIndex,
      payload: { wizard_domain: baseWd },
    }
    const merged = mergeShellIntoWizardDocument(fake, state)
    const pl = merged.payload as Record<string, unknown>
    return buildRunPlanPreview(
      runPlanPreviewInputFromShell(state, {
        foundationBriefMarkdownEffective: effectiveFoundationBriefMarkdown(pl),
        savedWizardDomain: normalizeWizardDomain(baseWd),
      }),
    )
  }, [state])

  const onRefreshClarificationQuestions = useCallback(() => {
    const wd = persistedWizardDomain ?? emptyWizardDomain()
    const fakePayload: Record<string, unknown> = { wizard_domain: wd }
    const built = buildClarificationQuestions({
      foundationBriefMarkdown: effectiveFoundationBriefMarkdown(fakePayload),
      foundationBriefFieldStatuses,
      interpretation,
      understandingKnownGaps: understanding.knownGaps ?? '',
    })
    setClarification(
      clampClarificationPayload({ ...clarification, questions: built, responses: {} }),
    )
  }, [
    persistedWizardDomain,
    foundationBriefFieldStatuses,
    interpretation,
    understanding.knownGaps,
    clarification,
    setClarification,
  ])

  const handleNext = useCallback(() => {
    if (stepIndex === 0) {
      const v = validateMissionForNext(mission)
      if (!v.ok) {
        setMissionAttempted(true)
        return
      }
    }
    if (stepIndex === 1) {
      const v = validateContributionSetupForNext(contributionSetup)
      if (!v.ok) {
        setContributionAttempted(true)
        return
      }
    }
    if (stepIndex === 2) {
      const v = validateContextIntakeForNext(contextIntake)
      if (!v.ok) {
        setContextIntakeAttempted(true)
        return
      }
    }
    if (stepIndex === 3) {
      const v = validateUnderstandingForNext(understanding)
      if (!v.ok) {
        setUnderstandingAttempted(true)
        return
      }
    }
    if (stepIndex === 4) {
      const v = validateClarificationForNext(clarification)
      if (!v.ok) {
        setClarificationAttempted(true)
        return
      }
    }
    if (stepIndex === 5) {
      const v = validateTargetOutputPackForNext(targetOutputPack)
      if (!v.ok) {
        setTargetOutputPackAttempted(true)
        return
      }
    }
    if (stepIndex === 6) {
      const v = validateAutonomyMutationForNext(autonomyMutation, contributionSetupKind)
      if (!v.ok) {
        setAutonomyMutationAttempted(true)
        return
      }
    }
    if (stepIndex === 7) {
      const v = validateScopeSelectionForNext(scopeSelection)
      if (!v.ok) {
        setScopeSelectionAttempted(true)
        return
      }
    }
    if (stepIndex === 8) {
      const v = validateRunPlanForNext(runPlan)
      if (!v.ok) {
        setRunPlanAttempted(true)
        return
      }
    }
    advanceStep()
  }, [
    stepIndex,
    mission,
    contributionSetup,
    contextIntake,
    interpretation,
    understanding,
    clarification,
    targetOutputPack,
    autonomyMutation,
    contributionSetupKind,
    scopeSelection,
    runPlan,
    advanceStep,
  ])

  return (
    <>
      {flagWarning && (
        <p className="forge-support" role="alert">
          {flagWarning}
        </p>
      )}
      {onRetryServerProbe ? (
        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          <button type="button" className="le-btn le-btn--primary" onClick={onRetryServerProbe}>
            Retry server connection
          </button>
        </p>
      ) : null}
      <BlueprintsWizardShell
        stepIndex={stepIndex}
        draftNote={draftNote}
        onDraftChange={setDraftNote}
        mission={mission}
        onMissionChange={setMission}
        missionFieldErrors={missionAttempted ? missionCheck.errors : {}}
        showMissionErrors={missionAttempted}
        contributionSetup={contributionSetup}
        onContributionSetupChange={setContributionSetup}
        contributionSetupKind={contributionSetupKind}
        onContributionSetupKindChange={setContributionSetupKind}
        contributionFieldErrors={contributionAttempted ? contributionCheck.errors : {}}
        showContributionErrors={contributionAttempted}
        contextIntake={contextIntake}
        onContextIntakeChange={setContextIntake}
        contextIntakeFieldErrors={contextIntakeAttempted ? contextIntakeCheck.errors : {}}
        showContextIntakeErrors={contextIntakeAttempted}
        interpretation={interpretation}
        onInterpretationChange={setInterpretation}
        understanding={understanding}
        onUnderstandingChange={setUnderstanding}
        understandingFieldErrors={understandingAttempted ? understandingCheck.errors : {}}
        showUnderstandingErrors={understandingAttempted}
        clarification={clarification}
        onClarificationChange={setClarification}
        clarificationFieldErrors={clarificationAttempted ? clarificationCheck.errors : {}}
        showClarificationErrors={clarificationAttempted}
        assumptionLedger={assumptionLedger}
        onRefreshClarificationQuestions={onRefreshClarificationQuestions}
        targetOutputPack={targetOutputPack}
        onTargetOutputPackChange={setTargetOutputPack}
        targetOutputPackFieldErrors={targetOutputPackAttempted ? targetOutputPackCheck.errors : {}}
        showTargetOutputPackErrors={targetOutputPackAttempted}
        autonomyMutation={autonomyMutation}
        onAutonomyMutationChange={setAutonomyMutation}
        autonomyMutationFieldErrors={autonomyMutationAttempted ? autonomyMutationCheck.errors : {}}
        showAutonomyMutationErrors={autonomyMutationAttempted}
        scopeSelection={scopeSelection}
        onScopeSelectionChange={setScopeSelection}
        scopeSelectionFieldErrors={scopeSelectionAttempted ? scopeSelectionCheck.errors : {}}
        showScopeSelectionErrors={scopeSelectionAttempted}
        runPlan={runPlan}
        onRunPlanChange={setRunPlan}
        onRegenerateRunPlan={regenerateRunPlanFromContext}
        runPlanFieldErrors={runPlanAttempted ? runPlanCheck.errors : {}}
        showRunPlanErrors={runPlanAttempted}
        runPlanPreview={runPlanPreview}
        reviewGenAvailable={false}
        onBack={back}
        onNext={handleNext}
        onSaveDraft={saveDraft}
        onExit={onExit}
      />
    </>
  )
}
