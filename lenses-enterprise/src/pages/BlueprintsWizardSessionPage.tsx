import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMainContentInert } from '../context/MainContentInertContext'
import {
  getWizardSession,
  postWizardArtifactExport,
  postWizardArtifactRecheck,
  postWizardArtifactReview,
  postWizardClarifySuggest,
  postWizardCreateRepo,
  postWizardGenerateArtifacts,
  postWizardInterpret,
  postWizardRefine,
  postWizardTelemetry,
  putWizardSession,
  type WizardSessionDocumentJson,
} from '../api/blueprintsWizard'
import { BlueprintsWizardShell } from '../blueprints-wizard/BlueprintsWizardShell'
import { WizardSessionProbeChrome } from '../blueprints-wizard/WizardSessionProbeChrome'
import { StatePanel } from '../components/page'
import { promiseWithTimeout } from '../lib/promiseWithTimeout'
import { WIZARD_PROBE_COPY } from '../nav/studioVisibleCopy'
import {
  clampContextIntakePayload,
  validateContextIntakeForNext,
  type ContextIntakePayloadV1,
} from '../blueprints-wizard/contextIntakeStep'
import {
  clampContributionSetupPayload,
  validateContributionSetupForNext,
  type ContributionSetupPayloadV1,
} from '../blueprints-wizard/contributionSetupStep'
import { buildClarificationQuestions } from '../blueprints-wizard/clarificationQuestionBuilder'
import {
  clampClarificationPayload,
  parseClarificationQuestionItem,
  validateClarificationForNext,
  type ClarificationPayloadV1,
} from '../blueprints-wizard/clarificationStep'
import {
  clampMissionPayload,
  validateMissionForNext,
  type MissionPayloadV1,
} from '../blueprints-wizard/missionStep'
import {
  clampAutonomyMutationPayload,
  validateAutonomyMutationForNext,
  type AutonomyMutationPayloadV1,
} from '../blueprints-wizard/autonomyMutationStep'
import { defaultAutonomyMutationForKind } from '../blueprints-wizard/contributionSetupDefaults'
import {
  clampScopeSelectionPayload,
  validateScopeSelectionForNext,
  type ScopeSelectionPayloadV1,
} from '../blueprints-wizard/scopeSelectionStep'
import {
  clampRunPlan,
  deriveDraftRunPlanFromShell,
  validateRunPlanForNext,
} from '../blueprints-wizard/runPlanStep'
import {
  clampTargetOutputPackPayload,
  defaultPackLabelForKind,
  validateTargetOutputPackForNext,
  type TargetOutputPackPayloadV1,
} from '../blueprints-wizard/targetOutputPackStep'
import {
  effectiveFoundationBriefMarkdown,
  fieldStatusesAfterInterpretationSync,
  foundationBriefDraftHasRenderableContent,
  renderFoundationBriefDraftToMarkdown,
} from '../blueprints-wizard/foundationBriefSync'
import { SyncDraftPreviewDialog } from '../blueprints-wizard/SyncDraftPreviewDialog'
import { clampInterpretationPayload, type InterpretationPayloadV1 } from '../blueprints-wizard/interpretationPayload'
import {
  UNDERSTANDING_GAPS_MAX,
  UNDERSTANDING_SUMMARY_MAX,
  clampUnderstandingPayload,
  validateUnderstandingForNext,
  type UnderstandingPayloadV1,
} from '../blueprints-wizard/understandingStep'
import { WizardRefinePanel } from '../blueprints-wizard/WizardRefinePanel'
import { WizardSetupPanel } from '../blueprints-wizard/WizardSetupPanel'
import { mergeShellIntoWizardDocument, wizardDocumentToShellState } from '../blueprints-wizard/wizardSessionMapping'
import {
  appendAssumptionEntry,
  removeAssumptionById,
  updateAssumptionEntry,
} from '../blueprints-wizard/wizardAssumptionHelpers'
import {
  normalizeArtifactGeneration,
  normalizeRecheckSummary,
  normalizeWizardDomain,
} from '../blueprints-wizard/wizardDomainNormalize'
import type {
  ArtifactGenerationBundle,
  ArtifactReviewApiAction,
  ArtifactSliceKey,
  ContributionSetupKind,
  ContextSource,
  InterpretationFieldStatus,
  RunPlanJson,
} from '../blueprints-wizard/wizardDomainTypes'
import {
  emptyWizardShellState,
  setAutonomyMutation,
  setClarification,
  setContextIntake,
  setContributionSetup,
  setContributionSetupKind,
  setInterpretation,
  setMission,
  setScopeSelection,
  setRunPlan,
  setTargetOutputPack,
  setUnderstanding,
  type WizardShellState,
} from '../blueprints-wizard/wizardShellState'
import { buildRunPlanPreview, runPlanPreviewInputFromShell } from '../blueprints-wizard/runPlanPreviewEngine'
import { WizardRetryRow } from '../blueprints-wizard/wizardAsyncUi'
import { applyStepBack, applyStepNext } from '../blueprints-wizard/wizardStepModel'
import { WIZARD_STEP_COUNT, clampStepIndex } from '../blueprints-wizard/wizardSteps'
import { blueprintsWizardTelemetryClientEnabled } from '../util/experimentalFlags'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'

const WIZARD_SESSION_BOOT_MS = 22_000

function effectiveModelOverride(raw: string): string | undefined {
  const t = raw.trim()
  if (!t) return undefined
  const lower = t.toLowerCase()
  if (lower === 'optional' || lower === 'n/a' || lower === '—' || lower === '-') return undefined
  return t
}

function friendlyWizardSessionBootError(raw: string): { variant: 'error' | 'invalid'; description: string } {
  const r = raw.toLowerCase()
  if (r.includes('missing session id')) {
    return {
      variant: 'invalid',
      description:
        'The URL does not include a usable session id. Open the Blueprints Wizard hub and pick a session from the list.',
    }
  }
  if (r.includes('timed out') || r.includes('took too long')) {
    return { variant: 'error', description: WIZARD_PROBE_COPY.sessionLoadTimeout }
  }
  if (r.includes('404') || r.includes('not found') || r === 'http 404') {
    return { variant: 'invalid', description: WIZARD_PROBE_COPY.sessionNotFound }
  }
  return { variant: 'error', description: raw }
}

export function BlueprintsWizardSessionPage() {
  const navigate = useNavigate()
  const { sessionId: sessionIdParam } = useParams<{ sessionId: string }>()
  const sessionId = sessionIdParam ? decodeURIComponent(sessionIdParam) : ''
  useLensesCopilotPage({ route: 'blueprints-wizard', entityId: sessionId || undefined })

  const [document, setDocument] = useState<WizardSessionDocumentJson | null>(null)
  const [shell, setShell] = useState<WizardShellState>(emptyWizardShellState())
  const [missionAttempted, setMissionAttempted] = useState(false)
  const [contributionAttempted, setContributionAttempted] = useState(false)
  const [contextIntakeAttempted, setContextIntakeAttempted] = useState(false)
  const [understandingAttempted, setUnderstandingAttempted] = useState(false)
  const [clarificationAttempted, setClarificationAttempted] = useState(false)
  const [targetOutputPackAttempted, setTargetOutputPackAttempted] = useState(false)
  const [autonomyMutationAttempted, setAutonomyMutationAttempted] = useState(false)
  const [scopeSelectionAttempted, setScopeSelectionAttempted] = useState(false)
  const [runPlanAttempted, setRunPlanAttempted] = useState(false)

  const [bootLoading, setBootLoading] = useState(false)
  const [bootError, setBootError] = useState<string | null>(() =>
    !sessionIdParam?.trim() ? 'Missing session id in URL.' : null,
  )
  const [bootKey, setBootKey] = useState(0)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const [refineProvider, setRefineProvider] = useState('ollama')
  const [refineModel, setRefineModel] = useState('')
  const [refineChain, setRefineChain] = useState(false)
  const [refining, setRefining] = useState(false)
  const [refineError, setRefineError] = useState<string | null>(null)
  const [interpreting, setInterpreting] = useState(false)
  const [interpretError, setInterpretError] = useState<string | null>(null)
  const [syncingDraft, setSyncingDraft] = useState(false)
  const [syncDraftError, setSyncDraftError] = useState<string | null>(null)
  const [syncPreview, setSyncPreview] = useState<{
    currentMarkdown: string
    nextMarkdown: string
    nextShell: WizardShellState
  } | null>(null)

  const { setMainContentInert } = useMainContentInert()
  useEffect(() => {
    setMainContentInert(syncPreview !== null)
    return () => setMainContentInert(false)
  }, [syncPreview, setMainContentInert])

  const [createRepoBusy, setCreateRepoBusy] = useState(false)
  const [createRepoError, setCreateRepoError] = useState<string | null>(null)
  const [clarifyLlmBusy, setClarifyLlmBusy] = useState(false)
  const [clarifyLlmError, setClarifyLlmError] = useState<string | null>(null)
  const [generatingArtifacts, setGeneratingArtifacts] = useState(false)
  const [artifactGenError, setArtifactGenError] = useState<string | null>(null)
  const [artifactGenNotice, setArtifactGenNotice] = useState<string | null>(null)
  const [recheckBusy, setRecheckBusy] = useState(false)
  const [recheckPreviewBusy, setRecheckPreviewBusy] = useState(false)
  const recheckAnyBusy = recheckBusy || recheckPreviewBusy

  const documentRef = useRef(document)
  const prevWizardStepRef = useRef(shell.stepIndex)
  const prevStepForAutonomyRef = useRef(shell.stepIndex)
  documentRef.current = document
  const assumptionPersistTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!sessionId.trim()) {
      setDocument(null)
      return
    }
    let cancelled = false
    setBootError(null)

    async function bootstrap() {
      setBootLoading(true)
      try {
        const s = await promiseWithTimeout(
          getWizardSession(sessionId),
          WIZARD_SESSION_BOOT_MS,
          () => new Error(WIZARD_PROBE_COPY.sessionLoadTimeout),
        )
        if (cancelled) return
        setDocument(s)
        setShell(wizardDocumentToShellState(s))
      } catch (e: unknown) {
        if (!cancelled) {
          setDocument(null)
          setShell(emptyWizardShellState())
          setBootError(e instanceof Error ? e.message : String(e))
        }
      } finally {
        if (!cancelled) setBootLoading(false)
      }
    }

    void bootstrap()
    return () => {
      cancelled = true
    }
  }, [sessionId, bootKey])

  useEffect(() => {
    if (!sessionId || !blueprintsWizardTelemetryClientEnabled()) return
    if (bootLoading || !document) return
    const t = window.setTimeout(() => {
      void postWizardTelemetry({
        event: 'step_view',
        session_id: sessionId,
        step_index: shell.stepIndex,
        mission_mode: shell.mission.mode,
      }).catch(() => {})
    }, 600)
    return () => window.clearTimeout(t)
  }, [sessionId, shell.stepIndex, shell.mission.mode, bootLoading, document])

  const persistSession = useCallback(
    async (next: WizardSessionDocumentJson, opts?: { silent?: boolean }) => {
      if (!sessionId) return
      const silent = opts?.silent === true
      if (!silent) {
        setSaveError(null)
        setSaving(true)
      }
      try {
        await putWizardSession(sessionId, next)
        setDocument(next)
        setSaveError(null)
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e)
        setSaveError(msg)
      } finally {
        if (!silent) setSaving(false)
      }
    },
    [sessionId],
  )

  const onRetrySave = useCallback(() => {
    const d = documentRef.current
    if (!d || !sessionId) return
    setSaveError(null)
    void persistSession(mergeShellIntoWizardDocument(d, shell))
  }, [sessionId, shell, persistSession])

  /** Session setup edits persist on every change; must not toggle `saving` or inputs disable and lose focus. */
  const applyDocument = useCallback(
    (next: WizardSessionDocumentJson) => {
      setDocument(next)
      void persistSession(next, { silent: true })
    },
    [persistSession],
  )

  const onSetupApply = useCallback(
    (next: WizardSessionDocumentJson) => {
      const merged = mergeShellIntoWizardDocument(next, shell)
      applyDocument(merged)
    },
    [shell, applyDocument],
  )

  const draftNote = shell.stepNotes[String(shell.stepIndex)] ?? ''

  const setDraftNote = useCallback((text: string) => {
    setShell((s) => ({
      ...s,
      stepNotes: { ...s.stepNotes, [String(s.stepIndex)]: text },
    }))
  }, [])

  const onMissionChange = useCallback((m: MissionPayloadV1) => {
    setShell((s) => setMission(s, clampMissionPayload(m)))
  }, [])

  const onContributionSetupChange = useCallback((c: ContributionSetupPayloadV1) => {
    setShell((s) => setContributionSetup(s, clampContributionSetupPayload(c)))
  }, [])

  const onContributionSetupKindChange = useCallback((k: ContributionSetupKind) => {
    setShell((s) => {
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

  const onContextIntakeChange = useCallback((x: ContextIntakePayloadV1) => {
    setShell((s) => setContextIntake(s, clampContextIntakePayload(x)))
  }, [])

  const onUnderstandingChange = useCallback((u: UnderstandingPayloadV1) => {
    setShell((s) => setUnderstanding(s, clampUnderstandingPayload(u)))
  }, [])

  const onInterpretationChange = useCallback((i: InterpretationPayloadV1) => {
    const clamped = clampInterpretationPayload(i)
    setShell((s) =>
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

  const onClarificationChange = useCallback((c: ClarificationPayloadV1) => {
    setShell((s) => setClarification(s, clampClarificationPayload(c)))
  }, [])

  const onTargetOutputPackChange = useCallback((t: TargetOutputPackPayloadV1) => {
    setShell((s) => {
      let next = clampTargetOutputPackPayload(t)
      if (!next.useCustomPackLabel) {
        next = { ...next, packLabel: defaultPackLabelForKind(next.outputPackKind) }
      }
      return setTargetOutputPack(s, next)
    })
  }, [])

  const onAutonomyMutationChange = useCallback((a: AutonomyMutationPayloadV1) => {
    setShell((s) => setAutonomyMutation(s, clampAutonomyMutationPayload(a)))
  }, [])

  const onScopeSelectionChange = useCallback((sc: ScopeSelectionPayloadV1) => {
    setShell((s) => setScopeSelection(s, clampScopeSelectionPayload(sc)))
  }, [])

  const onRunPlanChange = useCallback((rp: RunPlanJson) => {
    setShell((s) => setRunPlan(s, clampRunPlan(rp)))
  }, [])

  const onRegenerateRunPlan = useCallback(() => {
    setShell((s) => setRunPlan(s, deriveDraftRunPlanFromShell(s)))
  }, [])

  const persistMergedShell = useCallback(
    (nextShell: WizardShellState) => {
      const d = documentRef.current
      if (!d || !sessionId) return
      void persistSession(mergeShellIntoWizardDocument(d, nextShell))
    },
    [sessionId, persistSession],
  )

  const onAppendAssumption = useCallback(() => {
    setShell((prev) => {
      const ledger = appendAssumptionEntry(prev.assumptionLedger, { text: '' })
      const next = { ...prev, assumptionLedger: ledger }
      queueMicrotask(() => persistMergedShell(next))
      return next
    })
  }, [persistMergedShell])

  const onRemoveAssumption = useCallback(
    (id: string) => {
      setShell((prev) => {
        const ledger = removeAssumptionById(prev.assumptionLedger, id)
        const next = { ...prev, assumptionLedger: ledger }
        queueMicrotask(() => persistMergedShell(next))
        return next
      })
    },
    [persistMergedShell],
  )

  const onChangeAssumptionText = useCallback(
    (id: string, text: string) => {
      setShell((prev) => ({
        ...prev,
        assumptionLedger: updateAssumptionEntry(prev.assumptionLedger, id, { text }),
      }))
      if (assumptionPersistTimerRef.current) clearTimeout(assumptionPersistTimerRef.current)
      assumptionPersistTimerRef.current = setTimeout(() => {
        setShell((prev) => {
          const d = documentRef.current
          if (!d || !sessionId) return prev
          void persistSession(mergeShellIntoWizardDocument(d, prev))
          return prev
        })
      }, 450)
    },
    [sessionId, persistSession],
  )

  const onChangeAssumptionSource = useCallback(
    (id: string, source: string | undefined) => {
      setShell((prev) => {
        const ledger = updateAssumptionEntry(prev.assumptionLedger, id, {
          source: source as ContextSource | undefined,
        })
        const next = { ...prev, assumptionLedger: ledger }
        queueMicrotask(() => persistMergedShell(next))
        return next
      })
    },
    [persistMergedShell],
  )

  const onFoundationBriefFieldStatusesChange = useCallback(
    (next: Record<string, InterpretationFieldStatus>) => {
      setShell((prev) => {
        const s = { ...prev, foundationBriefFieldStatuses: next }
        queueMicrotask(() => persistMergedShell(s))
        return s
      })
    },
    [persistMergedShell],
  )

  const missionValidation = validateMissionForNext(shell.mission)
  const contributionValidation = validateContributionSetupForNext(shell.contributionSetup)
  const contextIntakeValidation = validateContextIntakeForNext(shell.contextIntake)
  const understandingValidation = validateUnderstandingForNext(shell.understanding)
  const clarificationValidation = validateClarificationForNext(shell.clarification)
  const targetOutputPackValidation = validateTargetOutputPackForNext(shell.targetOutputPack)
  const autonomyMutationValidation = validateAutonomyMutationForNext(
    shell.autonomyMutation,
    shell.contributionSetupKind,
  )
  const scopeSelectionValidation = validateScopeSelectionForNext(shell.scopeSelection)
  const runPlanValidation = validateRunPlanForNext(shell.runPlan)

  const runPlanPreview = useMemo(() => {
    if (!document) return null
    return buildRunPlanPreview(
      runPlanPreviewInputFromShell(shell, {
        foundationBriefMarkdownEffective: effectiveFoundationBriefMarkdown(document.payload),
        savedWizardDomain: normalizeWizardDomain(document.payload.wizard_domain),
      }),
    )
  }, [document, shell])

  const artifactGeneration = useMemo(() => {
    if (!document) return normalizeArtifactGeneration({})
    return normalizeWizardDomain(document.payload.wizard_domain).artifact_generation
  }, [document])

  const recheckSummary = useMemo(() => {
    if (!document) return null
    return normalizeWizardDomain(document.payload.wizard_domain).recheck_summary
  }, [document])

  const onNext = useCallback(() => {
    if (!document || saving || refining || interpreting || syncingDraft) return
    if (shell.stepIndex === 0) {
      const v = validateMissionForNext(shell.mission)
      if (!v.ok) {
        setMissionAttempted(true)
        return
      }
    }
    if (shell.stepIndex === 1) {
      const v = validateContributionSetupForNext(shell.contributionSetup)
      if (!v.ok) {
        setContributionAttempted(true)
        return
      }
    }
    if (shell.stepIndex === 2) {
      const v = validateContextIntakeForNext(shell.contextIntake)
      if (!v.ok) {
        setContextIntakeAttempted(true)
        return
      }
    }
    if (shell.stepIndex === 3) {
      const v = validateUnderstandingForNext(shell.understanding)
      if (!v.ok) {
        setUnderstandingAttempted(true)
        return
      }
    }
    if (shell.stepIndex === 4) {
      const v = validateClarificationForNext(shell.clarification)
      if (!v.ok) {
        setClarificationAttempted(true)
        return
      }
    }
    if (shell.stepIndex === 5) {
      const v = validateTargetOutputPackForNext(shell.targetOutputPack)
      if (!v.ok) {
        setTargetOutputPackAttempted(true)
        return
      }
    }
    if (shell.stepIndex === 6) {
      const v = validateAutonomyMutationForNext(shell.autonomyMutation, shell.contributionSetupKind)
      if (!v.ok) {
        setAutonomyMutationAttempted(true)
        return
      }
    }
    if (shell.stepIndex === 7) {
      const v = validateScopeSelectionForNext(shell.scopeSelection)
      if (!v.ok) {
        setScopeSelectionAttempted(true)
        return
      }
    }
    if (shell.stepIndex === 8) {
      const v = validateRunPlanForNext(shell.runPlan)
      if (!v.ok) {
        setRunPlanAttempted(true)
        return
      }
    }
    const merged = mergeShellIntoWizardDocument(document, shell)
    if (merged.step_index >= WIZARD_STEP_COUNT - 1) return
    const nextDoc = applyStepNext(merged)
    setShell(wizardDocumentToShellState(nextDoc))
    void persistSession(nextDoc)
  }, [document, shell, saving, refining, interpreting, syncingDraft, persistSession])

  const onBack = useCallback(() => {
    if (!document || saving || refining || interpreting || syncingDraft) return
    const merged = mergeShellIntoWizardDocument(document, shell)
    if (merged.step_index <= 0) return
    const prevDoc = applyStepBack(merged)
    setShell(wizardDocumentToShellState(prevDoc))
    void persistSession(prevDoc)
  }, [document, shell, saving, refining, interpreting, syncingDraft, persistSession])

  const onJumpToStep = useCallback(
    (index: number) => {
      if (!document || saving || refining || interpreting || syncingDraft || clarifyLlmBusy) return
      const nextIndex = clampStepIndex(index)
      const merged = mergeShellIntoWizardDocument(document, { ...shell, stepIndex: nextIndex })
      setShell(wizardDocumentToShellState(merged))
      void persistSession(merged)
    },
    [document, shell, saving, refining, interpreting, syncingDraft, clarifyLlmBusy, persistSession],
  )

  const onSaveDraft = useCallback(() => {
    if (!document || saving || refining || interpreting || syncingDraft) return
    const merged = mergeShellIntoWizardDocument(document, shell)
    setShell(wizardDocumentToShellState(merged))
    void persistSession(merged)
  }, [document, shell, saving, refining, interpreting, syncingDraft, persistSession])

  const wizardDomainNormalized = document ? normalizeWizardDomain(document.payload.wizard_domain) : null
  const domainFoundationMarkdown = wizardDomainNormalized?.foundation_brief.markdown ?? ''
  const legacyFoundationBrief =
    document && typeof document.payload.foundation_brief === 'string' ? document.payload.foundation_brief : ''

  useEffect(() => {
    if (!document) return
    const prev = prevWizardStepRef.current
    prevWizardStepRef.current = shell.stepIndex
    const enteredStep4 = prev !== 4 && shell.stepIndex === 4
    if (!enteredStep4) return
    if (shell.clarification.questions.length > 0) return
    if (shell.clarification.openQuestions.trim() !== '') return
    const built = buildClarificationQuestions({
      foundationBriefMarkdown: effectiveFoundationBriefMarkdown(document.payload),
      foundationBriefFieldStatuses: shell.foundationBriefFieldStatuses,
      interpretation: shell.interpretation,
      understandingKnownGaps: shell.understanding.knownGaps ?? '',
    })
    if (built.length === 0) return
    setShell((s) =>
      setClarification(
        s,
        clampClarificationPayload({ ...s.clarification, questions: built, responses: {} }),
      ),
    )
  }, [document, shell.stepIndex, shell.clarification.questions.length, shell.clarification.openQuestions, shell.foundationBriefFieldStatuses, shell.interpretation, shell.understanding.knownGaps])

  useEffect(() => {
    const entered6 = prevStepForAutonomyRef.current !== 6 && shell.stepIndex === 6
    prevStepForAutonomyRef.current = shell.stepIndex
    if (!entered6) return
    if (shell.autonomyMutation.advancedOverride) return
    const d = defaultAutonomyMutationForKind(shell.contributionSetupKind)
    setShell((s) =>
      setAutonomyMutation(s, {
        ...s.autonomyMutation,
        autonomyLevel: d.autonomyLevel,
        mutationPolicy: d.mutationPolicy,
        guardrailAcknowledged: false,
      }),
    )
  }, [shell.stepIndex, shell.contributionSetupKind, shell.autonomyMutation.advancedOverride])

  const prevStepForRunPlanRef = useRef(shell.stepIndex)
  useEffect(() => {
    const entered8 = prevStepForRunPlanRef.current !== 8 && shell.stepIndex === 8
    prevStepForRunPlanRef.current = shell.stepIndex
    if (!entered8) return
    if (shell.runPlan.steps.length > 0) return
    setShell((s) => setRunPlan(s, deriveDraftRunPlanFromShell(s)))
  }, [shell.stepIndex, shell.runPlan.steps.length])

  const onRefreshClarificationQuestions = useCallback(() => {
    if (!document) return
    setShell((s) => {
      const built = buildClarificationQuestions({
        foundationBriefMarkdown: effectiveFoundationBriefMarkdown(document.payload),
        foundationBriefFieldStatuses: s.foundationBriefFieldStatuses,
        interpretation: s.interpretation,
        understandingKnownGaps: s.understanding.knownGaps ?? '',
      })
      return setClarification(
        s,
        clampClarificationPayload({ ...s.clarification, questions: built, responses: {} }),
      )
    })
  }, [document])

  const onClarifyLlmSuggest = useCallback(() => {
    if (!sessionId || !document || saving || refining || interpreting || syncingDraft || clarifyLlmBusy) return
    setClarifyLlmError(null)
    setClarifyLlmBusy(true)
    void (async () => {
      try {
        const det = shell.clarification.questions.map((q) => ({ ...q }))
        const mo = effectiveModelOverride(refineModel)
        const res = await postWizardClarifySuggest(sessionId, {
          deterministic_questions: det,
          use_llm: true,
          provider: refineProvider,
          ...(mo ? { model: mo } : {}),
          refine: refineChain,
        })
        if (!res.ok) {
          const detail = res.detail ? ` (${String(res.detail).slice(0, 400)})` : ''
          setClarifyLlmError(`${res.error || 'clarify_suggest_failed'}${detail}`)
          return
        }
        const raw = res.questions
        if (!Array.isArray(raw)) {
          setClarifyLlmError('Invalid response shape')
          return
        }
        const parsed = raw
          .map((x) => parseClarificationQuestionItem(x))
          .filter((x): x is NonNullable<typeof x> => x !== null)
        setShell((s) =>
          setClarification(
            s,
            clampClarificationPayload({
              ...s.clarification,
              questions: parsed,
              responses: {},
            }),
          ),
        )
      } catch (e: unknown) {
        setClarifyLlmError(e instanceof Error ? e.message : String(e))
      } finally {
        setClarifyLlmBusy(false)
      }
    })()
  }, [
    sessionId,
    document,
    clarifyLlmBusy,
    shell.clarification.questions,
    refineProvider,
    refineModel,
    refineChain,
  ])

  const onRunInterpret = useCallback(() => {
    if (!document || !sessionId || saving || refining || interpreting || syncingDraft) return
    setInterpretError(null)
    const merged = mergeShellIntoWizardDocument(document, shell)
    setInterpreting(true)
    void (async () => {
      try {
        await putWizardSession(sessionId, merged)
        setDocument(merged)
        const body: { provider: string; model?: string; refine?: boolean } = {
          provider: refineProvider,
          refine: refineChain,
        }
        const mo = effectiveModelOverride(refineModel)
        if (mo) body.model = mo
        const res = await postWizardInterpret(sessionId, body)
        if (res.ok && res.session) {
          setDocument(res.session)
          setShell(wizardDocumentToShellState(res.session))
        } else if (res.ok) {
          const s = await getWizardSession(sessionId)
          setDocument(s)
          setShell(wizardDocumentToShellState(s))
        } else {
          const detail = res.detail ? ` (${res.detail})` : ''
          setInterpretError(`${res.error || 'interpret_failed'}${detail}`)
        }
      } catch (e: unknown) {
        setInterpretError(e instanceof Error ? e.message : String(e))
      } finally {
        setInterpreting(false)
      }
    })()
  }, [
    document,
    sessionId,
    saving,
    refining,
    interpreting,
    shell,
    refineProvider,
    refineModel,
    refineChain,
    syncingDraft,
  ])

  const onGenerateArtifacts = useCallback(
    (
      artifactKey: string | null,
      bundle?: ArtifactGenerationBundle,
      artifactKeysList?: ArtifactSliceKey[],
    ) => {
      if (
        !document ||
        !sessionId ||
        saving ||
        refining ||
        interpreting ||
        syncingDraft ||
        generatingArtifacts ||
        clarifyLlmBusy
      )
        return
      setArtifactGenError(null)
      setArtifactGenNotice(null)
      setGeneratingArtifacts(true)
      void (async () => {
        try {
          const merged = mergeShellIntoWizardDocument(document, shell)
          await putWizardSession(sessionId, merged)
          setDocument(merged)
          const body: {
            provider: string
            refine?: boolean
            model?: string
            artifact?: string
            artifact_bundle?: ArtifactGenerationBundle
            artifact_keys?: string[]
          } = {
            provider: refineProvider,
            refine: refineChain,
          }
          const mo = effectiveModelOverride(refineModel)
          if (mo) body.model = mo
          if (artifactKeysList && artifactKeysList.length > 0) {
            body.artifact_keys = artifactKeysList
          } else if (artifactKey !== null) {
            body.artifact = artifactKey
          } else if (bundle) {
            body.artifact_bundle = bundle
          }
          const res = await postWizardGenerateArtifacts(sessionId, body)
          if (res.warnings && res.warnings.length > 0) {
            setArtifactGenNotice(res.warnings.slice(0, 8).join(' · '))
          }
          if (res.ok && res.session) {
            setDocument(res.session)
            setShell(wizardDocumentToShellState(res.session))
          } else if (res.ok) {
            const s = await getWizardSession(sessionId)
            setDocument(s)
            setShell(wizardDocumentToShellState(s))
          } else {
            const detail = res.detail ? ` (${res.detail})` : ''
            const fk = res.failed_artifact_keys?.length
              ? ` — keys: ${res.failed_artifact_keys.join(', ')}`
              : ''
            setArtifactGenError(`${res.error || 'generate_failed'}${detail}${fk}`)
          }
        } catch (e: unknown) {
          setArtifactGenError(e instanceof Error ? e.message : String(e))
        } finally {
          setGeneratingArtifacts(false)
        }
      })()
    },
    [
      document,
      sessionId,
      saving,
      refining,
      interpreting,
      syncingDraft,
      generatingArtifacts,
      clarifyLlmBusy,
      shell,
      refineProvider,
      refineModel,
      refineChain,
    ],
  )

  const onArtifactReview = useCallback(
    (action: ArtifactReviewApiAction, artifactKey: ArtifactSliceKey, feedback?: string) => {
      if (
        !sessionId ||
        saving ||
        refining ||
        interpreting ||
        syncingDraft ||
        generatingArtifacts ||
        clarifyLlmBusy
      )
        return
      setArtifactGenError(null)
      setGeneratingArtifacts(true)
      void (async () => {
        try {
          const res = await postWizardArtifactReview(sessionId, {
            action,
            artifact_key: artifactKey,
            feedback: feedback ?? '',
          })
          if (res.ok && res.session) {
            setDocument(res.session)
            setShell(wizardDocumentToShellState(res.session))
          } else {
            const detail = res.detail ? ` (${res.detail})` : ''
            setArtifactGenError(`${res.error || 'review_failed'}${detail}`)
          }
        } catch (e: unknown) {
          setArtifactGenError(e instanceof Error ? e.message : String(e))
        } finally {
          setGeneratingArtifacts(false)
        }
      })()
    },
    [
      sessionId,
      saving,
      refining,
      interpreting,
      syncingDraft,
      generatingArtifacts,
      clarifyLlmBusy,
    ],
  )

  const onApproveArtifactBundle = useCallback(
    (artifactKeys: ArtifactSliceKey[]) => {
      if (
        !sessionId ||
        saving ||
        refining ||
        interpreting ||
        syncingDraft ||
        generatingArtifacts ||
        clarifyLlmBusy ||
        artifactKeys.length === 0
      )
        return
      setArtifactGenError(null)
      setGeneratingArtifacts(true)
      void (async () => {
        try {
          const res = await postWizardArtifactReview(sessionId, {
            action: 'approve_bundle',
            artifact_keys: artifactKeys,
          })
          if (res.ok && res.session) {
            setDocument(res.session)
            setShell(wizardDocumentToShellState(res.session))
          } else {
            const detail = res.detail ? ` (${res.detail})` : ''
            setArtifactGenError(`${res.error || 'review_failed'}${detail}`)
          }
        } catch (e: unknown) {
          setArtifactGenError(e instanceof Error ? e.message : String(e))
        } finally {
          setGeneratingArtifacts(false)
        }
      })()
    },
    [
      sessionId,
      saving,
      refining,
      interpreting,
      syncingDraft,
      generatingArtifacts,
      clarifyLlmBusy,
    ],
  )

  const onExportArtifacts = useCallback(
    (artifactKeys: ArtifactSliceKey[]) => {
      if (!sessionId || artifactKeys.length === 0) return
      setArtifactGenError(null)
      void (async () => {
        try {
          const res = await postWizardArtifactExport(sessionId, { artifact_keys: artifactKeys })
          if (res.ok && res.markdown) {
            const blob = new Blob([res.markdown], { type: 'text/markdown;charset=utf-8' })
            const url = URL.createObjectURL(blob)
            const a = globalThis.document.createElement('a')
            a.href = url
            a.download = `blueprints-wizard-artifacts-${sessionId.slice(0, 8)}.md`
            a.rel = 'noopener'
            globalThis.document.body.appendChild(a)
            a.click()
            globalThis.document.body.removeChild(a)
            URL.revokeObjectURL(url)
          } else {
            const detail = res.detail ? ` (${res.detail})` : ''
            setArtifactGenError(`${res.error || 'export_failed'}${detail}`)
          }
        } catch (e: unknown) {
          setArtifactGenError(e instanceof Error ? e.message : String(e))
        }
      })()
    },
    [sessionId],
  )

  const onArtifactRecheck = useCallback(() => {
    if (!sessionId || saving || refining || interpreting || syncingDraft || recheckAnyBusy || clarifyLlmBusy) return
    setArtifactGenError(null)
    setRecheckBusy(true)
    void (async () => {
      try {
        const res = await postWizardArtifactRecheck(sessionId, {})
        if (res.ok && res.session) {
          setDocument(res.session)
          setShell(wizardDocumentToShellState(res.session))
        } else {
          const detail = res.error ? String(res.error) : 'recheck_failed'
          setArtifactGenError(detail)
        }
      } catch (e: unknown) {
        setArtifactGenError(e instanceof Error ? e.message : String(e))
      } finally {
        setRecheckBusy(false)
      }
    })()
  }, [sessionId, saving, refining, interpreting, syncingDraft, recheckAnyBusy, clarifyLlmBusy])

  const onArtifactRecheckPreview = useCallback(() => {
    if (!document || !sessionId || saving || refining || interpreting || syncingDraft || recheckAnyBusy || clarifyLlmBusy)
      return
    setRecheckPreviewBusy(true)
    setArtifactGenError(null)
    void (async () => {
      try {
        const res = await postWizardArtifactRecheck(sessionId, { dry_run: true })
        if (!res.ok || !res.dry_run || !res.recheck_summary) {
          setArtifactGenError(res.error ?? 'recheck_preview_failed')
          return
        }
        const rs = normalizeRecheckSummary(res.recheck_summary)
        setDocument((prev) => {
          if (!prev) return prev
          const pl = prev.payload as Record<string, unknown>
          const wd = normalizeWizardDomain(pl.wizard_domain)
          return {
            ...prev,
            payload: {
              ...pl,
              wizard_domain: normalizeWizardDomain({
                ...wd,
                recheck_summary: rs,
              }),
            },
          }
        })
      } catch (e: unknown) {
        setArtifactGenError(e instanceof Error ? e.message : String(e))
      } finally {
        setRecheckPreviewBusy(false)
      }
    })()
  }, [document, sessionId, saving, refining, interpreting, syncingDraft, recheckAnyBusy, clarifyLlmBusy])

  const onRecheckRepairRegenerate = useCallback(
    (keys: ArtifactSliceKey[]) => {
      onGenerateArtifacts(null, undefined, keys)
    },
    [onGenerateArtifacts],
  )

  const onApplyRecheckToScope = useCallback(
    (notes: string) => {
      if (!document || saving || refining || interpreting || syncingDraft) return
      const trimmed = notes.trim().slice(0, 8000)
      const nextRefs = [shell.scopeSelection.recheckIssueRefs, trimmed].filter(Boolean).join('\n\n').slice(0, 8000)
      const nextShell = {
        ...shell,
        scopeSelection: clampScopeSelectionPayload({
          ...shell.scopeSelection,
          scopeBoundary: 'recheck_subset',
          recheckIssueRefs: nextRefs,
        }),
      }
      const merged = mergeShellIntoWizardDocument(document, nextShell)
      setShell(wizardDocumentToShellState(merged))
      void persistSession(merged)
      onJumpToStep(7)
    },
    [document, shell, saving, refining, interpreting, syncingDraft, persistSession, onJumpToStep],
  )

  const onApplyRecheckRunPlan = useCallback(
    (plan: RunPlanJson) => {
      if (!document || saving || refining || interpreting || syncingDraft) return
      const nextShell = { ...shell, runPlan: clampRunPlan(plan) }
      const merged = mergeShellIntoWizardDocument(document, nextShell)
      setShell(wizardDocumentToShellState(merged))
      void persistSession(merged)
      onJumpToStep(8)
    },
    [document, shell, saving, refining, interpreting, syncingDraft, persistSession, onJumpToStep],
  )

  const executeSyncDraftToMarkdown = useCallback(
    async (nextShell: WizardShellState, md: string): Promise<boolean> => {
      const d = documentRef.current
      const sid = sessionId
      if (!d || !sid) return false
      setSyncingDraft(true)
      setSyncDraftError(null)
      try {
        const merged = mergeShellIntoWizardDocument(d, nextShell, {
          foundationBriefMarkdownOverride: md,
        })
        await putWizardSession(sid, merged)
        setDocument(merged)
        setShell(wizardDocumentToShellState(merged))
        return true
      } catch (e: unknown) {
        setSyncDraftError(e instanceof Error ? e.message : String(e))
        return false
      } finally {
        setSyncingDraft(false)
      }
    },
    [sessionId],
  )

  const onSyncDraftToMarkdown = useCallback(() => {
    if (!document || !sessionId || saving || refining || interpreting || syncingDraft) return
    setSyncDraftError(null)
    const draft = shell.interpretation.foundation_brief_draft
    if (!foundationBriefDraftHasRenderableContent(draft)) {
      setSyncDraftError('Add at least one Foundation Brief draft section on the Understanding step first.')
      return
    }
    const newMd = renderFoundationBriefDraftToMarkdown(draft)
    const nextShell: WizardShellState = {
      ...shell,
      foundationBriefFieldStatuses: fieldStatusesAfterInterpretationSync(
        shell.foundationBriefFieldStatuses,
        draft,
      ),
    }
    const pl = document.payload as Record<string, unknown>
    const currentDisplay = effectiveFoundationBriefMarkdown(pl).trim()
    if (!currentDisplay) {
      void executeSyncDraftToMarkdown(nextShell, newMd)
      return
    }
    setSyncPreview({
      currentMarkdown: effectiveFoundationBriefMarkdown(pl),
      nextMarkdown: newMd,
      nextShell,
    })
  }, [
    document,
    sessionId,
    saving,
    refining,
    interpreting,
    syncingDraft,
    shell,
    executeSyncDraftToMarkdown,
  ])

  const onSyncPreviewConfirm = useCallback(() => {
    if (!syncPreview) return
    void executeSyncDraftToMarkdown(syncPreview.nextShell, syncPreview.nextMarkdown).then((ok) => {
      if (ok) setSyncPreview(null)
    })
  }, [syncPreview, executeSyncDraftToMarkdown])

  const onSyncPreviewCancel = useCallback(() => {
    if (!syncingDraft) setSyncPreview(null)
  }, [syncingDraft])

  const onRefineFoundationBrief = useCallback(() => {
    if (!document || !sessionId || saving || refining || interpreting || syncingDraft) return
    setRefineError(null)
    const merged = mergeShellIntoWizardDocument(document, shell)
    setRefining(true)
    void (async () => {
      try {
        await putWizardSession(sessionId, merged)
        setDocument(merged)
        const body: { provider: string; model?: string; refine?: boolean } = {
          provider: refineProvider,
          refine: refineChain,
        }
        const mo = effectiveModelOverride(refineModel)
        if (mo) body.model = mo
        const res = await postWizardRefine(sessionId, body)
        if (res.ok && res.session) {
          setDocument(res.session)
          setShell(wizardDocumentToShellState(res.session))
        } else if (res.ok) {
          const s = await getWizardSession(sessionId)
          setDocument(s)
          setShell(wizardDocumentToShellState(s))
        } else {
          const detail = res.detail ? ` (${res.detail})` : ''
          setRefineError(`${res.error || 'refine_failed'}${detail}`)
        }
      } catch (e: unknown) {
        setRefineError(e instanceof Error ? e.message : String(e))
      } finally {
        setRefining(false)
      }
    })()
  }, [document, sessionId, saving, refining, interpreting, syncingDraft, shell, refineProvider, refineModel, refineChain])

  const onCreateRepo = useCallback(() => {
    if (!sessionId || !document) return
    const ok = window.confirm(
      'Create a GitHub repository using the draft metadata in this session? This cannot be undone from Lenses.',
    )
    if (!ok) return
    setCreateRepoError(null)
    setCreateRepoBusy(true)
    void (async () => {
      try {
        const res = await postWizardCreateRepo(sessionId, { confirm: true })
        if (res.ok && res.session) {
          setDocument(res.session)
          setShell(wizardDocumentToShellState(res.session))
        } else {
          const detail = res.detail ? ` ${String(res.detail).slice(0, 400)}` : ''
          setCreateRepoError(`${res.error || 'create_failed'}${detail}`)
        }
      } catch (e: unknown) {
        setCreateRepoError(e instanceof Error ? e.message : String(e))
      } finally {
        setCreateRepoBusy(false)
      }
    })()
  }, [sessionId, document])

  const stepIndex = shell.stepIndex

  const banner =
    sessionId && !bootError && !bootLoading ? (
      <p className="forge-support" style={{ marginTop: '0.5rem' }}>
        Session <code className="le-mono">{sessionId}</code> —{' '}
        <button type="button" className="forge-support" onClick={() => navigate('/blueprints/wizard')}>
          Back to sessions
        </button>
      </p>
    ) : null

  const setupPanel =
    document && sessionId && !bootError ? (
      <WizardSetupPanel
        document={document}
        onApply={onSetupApply}
        disabled={saving || refining || interpreting || syncingDraft || bootLoading}
        createRepoBusy={createRepoBusy}
        createRepoError={createRepoError}
        onCreateRepo={onCreateRepo}
      />
    ) : null

  const secondaryPanel =
    document && sessionId && !bootError ? (
      <WizardRefinePanel
        domainFoundationMarkdown={domainFoundationMarkdown}
        legacyFoundationBrief={legacyFoundationBrief}
        foundationBriefFieldStatuses={shell.foundationBriefFieldStatuses}
        onFoundationBriefFieldStatusesChange={onFoundationBriefFieldStatusesChange}
        assumptionLedger={shell.assumptionLedger}
        onAppendAssumption={onAppendAssumption}
        onRemoveAssumption={onRemoveAssumption}
        onChangeAssumptionText={onChangeAssumptionText}
        onChangeAssumptionSource={onChangeAssumptionSource}
        refineProvider={refineProvider}
        refineModel={refineModel}
        refineChain={refineChain}
        refining={refining}
        refineError={refineError}
        interpretationDraftReady={foundationBriefDraftHasRenderableContent(
          shell.interpretation.foundation_brief_draft,
        )}
        onSyncDraftToMarkdown={onSyncDraftToMarkdown}
        syncingDraft={syncingDraft}
        syncDraftError={syncDraftError}
        disabled={saving || refining || interpreting || bootLoading || syncingDraft}
        onRefineProviderChange={setRefineProvider}
        onRefineModelChange={setRefineModel}
        onRefineChainChange={setRefineChain}
        onRefine={onRefineFoundationBrief}
      />
    ) : null

  if (bootLoading && !document) {
    return (
      <WizardSessionProbeChrome>
        <StatePanel
          variant="loading"
          title="Loading wizard session"
          description={WIZARD_PROBE_COPY.sessionLoading}
        />
      </WizardSessionProbeChrome>
    )
  }

  if (bootError && !document) {
    const { variant, description } = friendlyWizardSessionBootError(bootError)
    return (
      <WizardSessionProbeChrome>
        <StatePanel
          variant={variant}
          title="Could not open this session"
          description={description}
          technicalDetail={bootError}
          actions={
            <>
              <button
                type="button"
                className="le-btn le-btn--primary"
                onClick={() => {
                  setBootError(null)
                  setBootKey((k) => k + 1)
                }}
              >
                Retry load
              </button>
              <Link className="le-btn" to="/blueprints/wizard">
                Wizard hub
              </Link>
            </>
          }
        />
      </WizardSessionProbeChrome>
    )
  }

  if (!document || !sessionId) {
    return (
      <WizardSessionProbeChrome>
        <StatePanel
          variant="invalid"
          title="Session unavailable"
          description="The wizard could not load a session document. Return to the hub or retry from a valid link."
          actions={
            <Link className="le-btn le-btn--primary" to="/blueprints/wizard">
              Wizard hub
            </Link>
          }
        />
      </WizardSessionProbeChrome>
    )
  }

  return (
    <>
      <SyncDraftPreviewDialog
        open={syncPreview !== null}
        currentMarkdown={syncPreview?.currentMarkdown ?? ''}
        nextMarkdown={syncPreview?.nextMarkdown ?? ''}
        onCancel={onSyncPreviewCancel}
        onConfirm={onSyncPreviewConfirm}
        confirmBusy={syncingDraft}
      />
      {saveError && (
        <WizardRetryRow
          message={`Save failed (static museum builds cannot persist; use the live Lenses server): ${saveError}`}
          onRetry={onRetrySave}
          retryLabel="Retry save"
          disabled={saving}
        />
      )}
      {artifactGenNotice ? (
        <p className="forge-support" role="status" style={{ marginTop: '0.5rem' }}>
          {artifactGenNotice}
        </p>
      ) : null}
      <BlueprintsWizardShell
        stepIndex={stepIndex}
        draftNote={draftNote}
        onDraftChange={setDraftNote}
        mission={shell.mission}
        onMissionChange={onMissionChange}
        missionFieldErrors={missionAttempted ? missionValidation.errors : {}}
        showMissionErrors={missionAttempted}
        contributionSetup={shell.contributionSetup}
        onContributionSetupChange={onContributionSetupChange}
        contributionSetupKind={shell.contributionSetupKind}
        onContributionSetupKindChange={onContributionSetupKindChange}
        contributionFieldErrors={contributionAttempted ? contributionValidation.errors : {}}
        showContributionErrors={contributionAttempted}
        contextIntake={shell.contextIntake}
        onContextIntakeChange={onContextIntakeChange}
        contextIntakeFieldErrors={contextIntakeAttempted ? contextIntakeValidation.errors : {}}
        showContextIntakeErrors={contextIntakeAttempted}
        interpretation={shell.interpretation}
        onInterpretationChange={onInterpretationChange}
        onRunInterpret={onRunInterpret}
        interpreting={interpreting}
        interpretError={interpretError}
        runInterpretAvailable
        understanding={shell.understanding}
        onUnderstandingChange={onUnderstandingChange}
        understandingFieldErrors={understandingAttempted ? understandingValidation.errors : {}}
        showUnderstandingErrors={understandingAttempted}
        clarification={shell.clarification}
        onClarificationChange={onClarificationChange}
        clarificationFieldErrors={clarificationAttempted ? clarificationValidation.errors : {}}
        showClarificationErrors={clarificationAttempted}
        assumptionLedger={shell.assumptionLedger}
        onRefreshClarificationQuestions={onRefreshClarificationQuestions}
        onClarifyLlmSuggest={onClarifyLlmSuggest}
        clarifySuggestAvailable={Boolean(sessionId) && !bootLoading}
        clarifyLlmBusy={clarifyLlmBusy}
        clarifyLlmError={clarifyLlmError}
        targetOutputPack={shell.targetOutputPack}
        onTargetOutputPackChange={onTargetOutputPackChange}
        targetOutputPackFieldErrors={targetOutputPackAttempted ? targetOutputPackValidation.errors : {}}
        showTargetOutputPackErrors={targetOutputPackAttempted}
        autonomyMutation={shell.autonomyMutation}
        onAutonomyMutationChange={onAutonomyMutationChange}
        autonomyMutationFieldErrors={autonomyMutationAttempted ? autonomyMutationValidation.errors : {}}
        showAutonomyMutationErrors={autonomyMutationAttempted}
        scopeSelection={shell.scopeSelection}
        onScopeSelectionChange={onScopeSelectionChange}
        scopeSelectionFieldErrors={scopeSelectionAttempted ? scopeSelectionValidation.errors : {}}
        showScopeSelectionErrors={scopeSelectionAttempted}
        runPlan={shell.runPlan}
        onRunPlanChange={onRunPlanChange}
        onRegenerateRunPlan={onRegenerateRunPlan}
        runPlanFieldErrors={runPlanAttempted ? runPlanValidation.errors : {}}
        showRunPlanErrors={runPlanAttempted}
        runPlanPreview={runPlanPreview}
        onJumpToStep={onJumpToStep}
        artifactGeneration={artifactGeneration}
        recheckSummary={recheckSummary}
        reviewGenAvailable={Boolean(sessionId) && !bootLoading}
        onGenerateArtifacts={onGenerateArtifacts}
        onArtifactReview={onArtifactReview}
        onApproveArtifactBundle={onApproveArtifactBundle}
        onExportArtifacts={onExportArtifacts}
        onArtifactRecheck={onArtifactRecheck}
        onArtifactRecheckPreview={onArtifactRecheckPreview}
        onRecheckRepairRegenerate={onRecheckRepairRegenerate}
        onApplyRecheckToScope={onApplyRecheckToScope}
        onApplyRecheckRunPlan={onApplyRecheckRunPlan}
        wizardSessionId={sessionId}
        artifactGenBusy={generatingArtifacts}
        recheckBusy={recheckAnyBusy}
        recheckPersistBusy={recheckBusy}
        recheckPreviewBusy={recheckPreviewBusy}
        artifactGenError={artifactGenError}
        onBack={onBack}
        onNext={onNext}
        onSaveDraft={onSaveDraft}
        onExit={() => navigate('/')}
        banner={banner}
        setupPanel={setupPanel}
        secondaryPanel={secondaryPanel}
        interactionDisabled={
          saving || refining || interpreting || syncingDraft || clarifyLlmBusy || generatingArtifacts
        }
      />
    </>
  )
}
