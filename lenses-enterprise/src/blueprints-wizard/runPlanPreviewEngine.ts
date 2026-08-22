/**
 * Deterministic run-plan preview — pure functions, no LLM / I/O.
 */

import type { ClarificationResponse } from './clarificationTypes'
import { needsL3ReadonlyAck, needsTierRiskAck } from './autonomyMutationStep'
import { contextSourcesForWizardDomain } from './contextIntakeStep'
import type { ContextIntakePayloadV1 } from './contextIntakeStep'
import { artifactPackFromTargetPayload } from './targetOutputPackStep'
import { missionModeToMissionType } from './missionStep'
import {
  clampRunPlan,
  deriveDraftRunPlan,
  mergedScopeSpecForRunPlan,
  type DeriveDraftRunPlanInput,
} from './runPlanStep'
import { validateScopeSelectionForNext } from './scopeSelectionStep'
import type { WizardShellState } from './wizardShellState'
import { emptyWizardShellState } from './wizardShellState'
import type {
  ArtifactPackItemJson,
  ArtifactPackJson,
  ArtifactStatus,
  AssumptionLedgerEntryJson,
  ContextSource,
  WizardDomainJson,
} from './wizardDomainTypes'
import { artifactGenerationPreviewLines } from './artifactGenerationPackSync'
import {
  mutationLeavesReadyUntouched,
  packExpectsFoundationBrief,
  reviewGatesFor,
  riskHotspotsFromPolicy,
  targetStateSummaryLines,
  autonomySummaryLines,
} from './runPlanStageRules'
import type {
  ArtifactPlanRow,
  ConfidencePreview,
  CurrentStatePreview,
  RunPlanPreview,
  RunPlanPreviewInput,
  TargetStatePreview,
} from './runPlanPreviewTypes'

function normLabel(s: string): string {
  return s.trim().toLowerCase()
}

function contentSignature(foundationMd: string, ledger: RunPlanPreviewInput['assumptionLedger']): string {
  const open = ledger.filter((e) => (e.status ?? 'open') === 'open').length
  const t = foundationMd.trim()
  return `${t.length}:${t.slice(0, 200)}:open=${open}`
}

function prevItemByLabel(
  items: ArtifactPackItemJson[],
): Map<string, ArtifactPackItemJson> {
  const m = new Map<string, ArtifactPackItemJson>()
  for (const it of items) {
    m.set(normLabel(it.label), it)
  }
  return m
}

function clarificationIsAnswered(
  qid: string,
  responses: Record<string, ClarificationResponse>,
): boolean {
  const r = responses[qid]
  if (!r) return false
  if (r.kind === 'answered') {
    return Boolean((r.value && r.value.trim()) || r.choice_key)
  }
  if (r.kind === 'accepted_default') return true
  return false
}

export function classifyArtifactPlan(input: RunPlanPreviewInput): {
  create: ArtifactPlanRow[]
  update: ArtifactPlanRow[]
  untouched: ArtifactPlanRow[]
} {
  const saved = input.savedWizardDomain
  const packId = saved?.artifact_packs?.[0]?.id
  const prevItems = saved?.artifact_packs?.[0]?.items ?? []
  const nextPack = artifactPackFromTargetPayload(input.targetOutputPack, packId)
  const prevMap = prevItemByLabel(prevItems)
  const policy = input.autonomyMutation.mutationPolicy
  const sig = contentSignature(input.foundationBriefMarkdownEffective, input.assumptionLedger)
  const prevSig = saved
    ? contentSignature(
        saved.foundation_brief?.markdown ?? '',
        saved.assumption_ledger ?? [],
      )
    : ''

  const create: ArtifactPlanRow[] = []
  const update: ArtifactPlanRow[] = []
  const untouched: ArtifactPlanRow[] = []

  for (const it of nextPack.items) {
    const key = normLabel(it.label)
    const prev = prevMap.get(key)
    if (!prev) {
      create.push({
        label: it.label,
        ref: it.id,
        nextStatus: it.status,
        reason: 'New deliverable line vs last saved pack.',
      })
      continue
    }

    const st = (prev.status ?? 'draft') as ArtifactStatus | string
    const ready = st === 'ready'
    const contentChanged = sig !== prevSig

    const leaveReady =
      ready && mutationLeavesReadyUntouched(policy) && !contentChanged

    const row: ArtifactPlanRow = {
      label: it.label,
      ref: it.id,
      previousStatus: st,
      nextStatus: it.status,
      reason: leaveReady
        ? 'Marked ready; policy and upstream signature stable.'
        : contentChanged
          ? 'Foundation or ledger changed since last save; revisit affected rows.'
          : `Status ${String(st)} with current mutation policy (${String(policy)}).`,
    }

    if (leaveReady) untouched.push(row)
    else update.push(row)
  }

  return { create, update, untouched }
}

/**
 * After Review & Generate (step 9+): merge the target output pack with the last saved pack so only
 * create/update rows get new draft materialization; untouched rows keep prior ids and status.
 */
export function buildMergedArtifactPackAfterGeneration(
  input: RunPlanPreviewInput,
  nextPack: ArtifactPackJson,
): ArtifactPackJson {
  const prevItems = input.savedWizardDomain?.artifact_packs?.[0]?.items ?? []
  const prevByLabel = prevItemByLabel(prevItems)
  const { create, update, untouched } = classifyArtifactPlan(input)
  const untouchedSet = new Set(untouched.map((r) => normLabel(r.label)))
  const updateSet = new Set(update.map((r) => normLabel(r.label)))
  const createSet = new Set(create.map((r) => normLabel(r.label)))

  const items: ArtifactPackItemJson[] = []
  for (const it of nextPack.items) {
    const key = normLabel(it.label)
    if (untouchedSet.has(key)) {
      const p = prevByLabel.get(key)
      if (p) {
        items.push({ id: p.id, label: p.label, status: p.status })
      } else {
        items.push({ id: it.id, label: it.label, status: it.status })
      }
    } else if (updateSet.has(key)) {
      items.push({ id: it.id, label: it.label, status: 'draft' })
    } else if (createSet.has(key)) {
      items.push({ id: it.id, label: it.label, status: 'draft' })
    } else {
      items.push({ id: it.id, label: it.label, status: it.status })
    }
  }

  return {
    id: nextPack.id,
    label: nextPack.label,
    items,
  }
}

function contextIntakeBullets(x: ContextIntakePayloadV1): string[] {
  const lines: string[] = []
  const f = x.sourceFlags
  const channels: string[] = []
  if (f.pastedPrompt) channels.push('pasted prompt')
  if (f.existingDocs) channels.push('existing docs')
  if (f.repoSummary) channels.push('repo summary')
  if (f.ticketsBacklog) channels.push('tickets / backlog')
  if (channels.length) lines.push(`Intake channels: ${channels.join(', ')}`)
  if (x.referenceHints.trim()) {
    lines.push(`Reference hints: ${x.referenceHints.trim().slice(0, 400)}${x.referenceHints.length > 400 ? '…' : ''}`)
  }
  if (x.attachments?.length) {
    lines.push(`Attachments: ${x.attachments.length} structured ref(s)`)
  }
  if (x.roughNotes.trim()) {
    lines.push(`Notes captured (${x.roughNotes.trim().length} chars)`)
  }
  return lines
}

function buildCurrentState(input: RunPlanPreviewInput): CurrentStatePreview {
  const bullets: string[] = []
  bullets.push(`Mission: ${input.mission.title.trim() || '(untitled)'}`)
  bullets.push(
    `Contribution scale: ${input.contributionSetupKind}${input.contributionSetup.deliverable?.trim() ? ` — ${input.contributionSetup.deliverable.trim().slice(0, 120)}` : ''}`,
  )
  bullets.push(...contextIntakeBullets(input.contextIntake))

  const wd = input.savedWizardDomain
  if (wd?.context_sources?.length) {
    bullets.push(`Context sources (domain): ${wd.context_sources.join(', ')}`)
  } else {
    const prev = (wd?.context_sources ?? []) as ContextSource[]
    const synthetic = contextSourcesForWizardDomain(input.contextIntake, prev)
    if (synthetic.length) bullets.push(`Derived context sources: ${synthetic.join(', ')}`)
  }

  const fb = input.foundationBriefMarkdownEffective.trim()
  if (fb) {
    bullets.push(`Foundation brief: ${fb.length} characters present`)
  } else {
    bullets.push('Foundation brief: empty in session display')
  }

  if (input.understanding.summary.trim()) {
    bullets.push(
      `Understanding summary: ${input.understanding.summary.trim().slice(0, 280)}${input.understanding.summary.length > 280 ? '…' : ''}`,
    )
  }
  const agLines = artifactGenerationPreviewLines(input.savedWizardDomain ?? null)
  if (agLines.length) {
    bullets.push('--- Planning artifact generation ---')
    bullets.push(...agLines)
  }
  return {
    title: 'Detected state (from session inputs)',
    bullets,
  }
}

function buildTargetState(input: RunPlanPreviewInput): TargetStatePreview {
  const bullets: string[] = [...targetStateSummaryLines(input), ...autonomySummaryLines(input.autonomyMutation)]
  const ss = input.scopeSelection
  bullets.push(`Scope boundary: ${ss.scopeBoundary}`)
  return {
    title: 'Target run',
    bullets,
  }
}

function assumptionsList(input: RunPlanPreviewInput): string[] {
  const out: string[] = []
  for (const e of input.assumptionLedger) {
    const t = e.text?.trim()
    if (t) out.push(`${e.status === 'open' || !e.status ? '[open] ' : ''}${t}`)
  }
  for (const q of input.clarification.questions) {
    if (!clarificationIsAnswered(q.id, input.clarification.responses)) {
      if (q.default_assumption_if_skipped.trim()) {
        out.push(`If unanswered, assume: ${q.default_assumption_if_skipped.trim().slice(0, 500)}`)
      } else {
        out.push(`Clarification pending: ${q.text.trim().slice(0, 200)}`)
      }
    }
  }
  return out.slice(0, 48)
}

function blockersList(input: RunPlanPreviewInput): string[] {
  const b: string[] = []
  const md = input.foundationBriefMarkdownEffective.trim()
  if (packExpectsFoundationBrief(input.targetOutputPack.outputPackKind) && !md) {
    b.push(
      `Foundation brief is empty — ${input.targetOutputPack.outputPackKind} usually needs a baseline brief.`,
    )
  }

  const scopeV = validateScopeSelectionForNext(input.scopeSelection)
  if (!scopeV.ok) {
    if (scopeV.errors.detail) b.push(scopeV.errors.detail)
    if (scopeV.errors.scopeBoundary) b.push(scopeV.errors.scopeBoundary)
  }

  const a = input.autonomyMutation
  if ((needsL3ReadonlyAck(a) || needsTierRiskAck(input.contributionSetupKind, a)) && !a.guardrailAcknowledged) {
    b.push('Autonomy / mutation guardrail not acknowledged — confirm before running.')
  }

  for (const e of input.assumptionLedger) {
    if ((e.status ?? 'open') === 'open' && e.text.trim()) {
      b.push(`Open assumption: ${e.text.trim().slice(0, 200)}${e.text.length > 200 ? '…' : ''}`)
    }
  }

  for (const q of input.clarification.questions) {
    if (!clarificationIsAnswered(q.id, input.clarification.responses)) {
      b.push(`Unanswered clarification: ${q.text.trim().slice(0, 160)}${q.text.length > 160 ? '…' : ''}`)
    }
  }

  return b.slice(0, 32)
}

function scopeBoundaryLines(input: RunPlanPreviewInput): string[] {
  const spec = mergedScopeSpecForRunPlan(shellFromInput(input))
  const lines: string[] = [
    `Boundary kind: ${spec.scope_boundary}`,
    spec.summary.trim() ? `Understanding summary: ${spec.summary.trim().slice(0, 500)}` : '',
    spec.constraints_note.trim() ? `Constraints / gaps: ${spec.constraints_note.trim().slice(0, 500)}` : '',
  ].filter(Boolean) as string[]
  if (spec.milestone_ref.trim()) lines.push(`Milestone ref: ${spec.milestone_ref.trim()}`)
  if (spec.wbe_path.trim()) lines.push(`WBE path: ${spec.wbe_path.trim().slice(0, 800)}`)
  if (spec.capability_label.trim()) lines.push(`Capability: ${spec.capability_label.trim()}`)
  if (spec.team_label.trim()) lines.push(`Team: ${spec.team_label.trim()}`)
  if (spec.repo_paths?.length) lines.push(`Repo paths: ${spec.repo_paths.slice(0, 12).join(', ')}${spec.repo_paths.length > 12 ? '…' : ''}`)
  if (spec.recheck_issue_refs.trim()) lines.push(`Recheck refs: ${spec.recheck_issue_refs.trim().slice(0, 400)}`)
  if (spec.closure_options?.length) {
    lines.push(`Closure options: ${spec.closure_options.join(', ')}`)
  }
  return lines
}

function shellFromInput(input: RunPlanPreviewInput): WizardShellState {
  return {
    ...emptyWizardShellState(),
    mission: input.mission,
    missionType: missionModeToMissionType(input.mission.mode),
    contributionSetup: input.contributionSetup,
    contributionSetupKind: input.contributionSetupKind,
    contextIntake: input.contextIntake,
    interpretation: input.interpretation,
    understanding: input.understanding,
    clarification: input.clarification,
    targetOutputPack: input.targetOutputPack,
    autonomyMutation: input.autonomyMutation,
    scopeSelection: input.scopeSelection,
    runPlan: input.runPlan,
    assumptionLedger: input.assumptionLedger,
    foundationBriefFieldStatuses: input.foundationBriefFieldStatuses as WizardShellState['foundationBriefFieldStatuses'],
  }
}

function confidenceFrom(input: RunPlanPreviewInput): ConfidencePreview {
  const statuses = Object.values(input.foundationBriefFieldStatuses)
  const n = statuses.length || 1
  const unknownRatio = statuses.filter((s) => s === 'unknown').length / n
  const needsConf = statuses.filter((s) => s === 'needs_confirmation').length / n
  let score = 1 - unknownRatio * 0.4 - needsConf * 0.2
  if (!input.foundationBriefMarkdownEffective.trim()) score -= 0.25
  if (input.clarification.questions.some((q) => !clarificationIsAnswered(q.id, input.clarification.responses))) {
    score -= 0.1
  }
  score = Math.max(0, Math.min(1, score))
  let summary = 'Confidence: moderate — review gates and assumptions before export.'
  if (score >= 0.75) summary = 'Confidence: relatively high — remaining items are listed under risks and assumptions.'
  if (score < 0.45) summary = 'Confidence: low — resolve blockers and strengthen foundation signals first.'
  return { summary, score01: score }
}

/**
 * Build a full deterministic preview for the Run Plan step.
 */
export function buildRunPlanPreview(input: RunPlanPreviewInput): RunPlanPreview {
  const shell = shellFromInput(input)
  const deriveIn: DeriveDraftRunPlanInput = {
    missionTitle: input.mission.title,
    targetStage: input.targetOutputPack.targetStage,
    outputPackKind: input.targetOutputPack.outputPackKind,
    scopeSpec: mergedScopeSpecForRunPlan(shell),
  }
  const derived = deriveDraftRunPlan(deriveIn)
  const runPlan = clampRunPlan({
    ...input.runPlan,
    title: input.runPlan.title.trim() ? input.runPlan.title : derived.title,
    steps: input.runPlan.steps.length > 0 ? input.runPlan.steps : derived.steps,
  })

  const { create, update, untouched } = classifyArtifactPlan(input)

  return {
    currentState: buildCurrentState(input),
    targetState: buildTargetState(input),
    artifactsCreate: create,
    artifactsUpdate: update,
    artifactsUntouched: untouched,
    reviewGates: reviewGatesFor(input),
    assumptionsReliedOn: assumptionsList(input),
    blockers: blockersList(input),
    riskHotspots: riskHotspotsFromPolicy(input),
    scopeBoundaries: scopeBoundaryLines(input),
    confidence: confidenceFrom(input),
    runPlan,
  }
}

export function runPlanPreviewInputFromShell(
  shell: WizardShellState,
  opts: {
    foundationBriefMarkdownEffective: string
    savedWizardDomain: WizardDomainJson | null
    /** During session merge, post-clarification ledger (optional). */
    assumptionLedger?: AssumptionLedgerEntryJson[]
  },
): RunPlanPreviewInput {
  return {
    mission: shell.mission,
    contributionSetup: shell.contributionSetup,
    contributionSetupKind: shell.contributionSetupKind,
    contextIntake: shell.contextIntake,
    foundationBriefMarkdownEffective: opts.foundationBriefMarkdownEffective,
    interpretation: shell.interpretation,
    clarification: shell.clarification,
    targetOutputPack: shell.targetOutputPack,
    autonomyMutation: shell.autonomyMutation,
    scopeSelection: shell.scopeSelection,
    understanding: shell.understanding,
    assumptionLedger: opts.assumptionLedger ?? shell.assumptionLedger,
    foundationBriefFieldStatuses: shell.foundationBriefFieldStatuses,
    savedWizardDomain: opts.savedWizardDomain,
    runPlan: shell.runPlan,
  }
}
