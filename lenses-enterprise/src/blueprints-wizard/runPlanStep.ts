/**
 * Step 8 — Run Plan. `wizard_domain.run_plan` (RunPlanJson): title + ordered steps with detail.
 * Draft steps are derived from target stage, output pack kind, and merged scope_spec.
 */

import { OUTPUT_PACK_KIND_UI, TARGET_STAGE_UI } from './targetOutputPackStep'
import { scopeSpecFromSelection } from './scopeSelectionStep'
import type { WizardShellState } from './wizardShellState'
import { emptyWizardDomain, normalizeRunPlan, normalizeScopeSpec } from './wizardDomainNormalize'
import type {
  OutputPackKind,
  RunPlanJson,
  RunPlanStepJson,
  ScopeBoundary,
  ScopeSpecJson,
  TargetStage,
} from './wizardDomainTypes'
import { SCOPE_BOUNDARIES } from './wizardDomainTypes'

export const RUN_PLAN_TITLE_MAX = 500
export const RUN_PLAN_STEP_TITLE_MAX = 500
export const RUN_PLAN_STEP_DETAIL_MAX = 8000
/** Server and UI cap (aligned with PUT validation). */
export const RUN_PLAN_MAX_STEPS = 32

function isScopeBoundary(v: unknown): v is ScopeBoundary {
  return typeof v === 'string' && (SCOPE_BOUNDARIES as readonly string[]).includes(v)
}

export function emptyRunPlanPayload(): RunPlanJson {
  return normalizeRunPlan({})
}

export function clampRunPlan(raw: unknown): RunPlanJson {
  return normalizeRunPlan(raw)
}

function stagePrimaryStep(stage: TargetStage): { title: string; detail: string } {
  const m: Record<TargetStage, { title: string; detail: string }> = {
    idea: {
      title: 'Shape intent and options',
      detail:
        'Capture the problem, stakeholders, and candidate directions. Keep alternatives visible until the roadmap hardens.',
    },
    roadmap: {
      title: 'Align roadmap themes and sequencing',
      detail:
        'Lay out outcomes, dependencies, and bets across time. Tie each theme to evidence and owners.',
    },
    milestones: {
      title: 'Define milestones and acceptance',
      detail:
        'Name checkpoints with explicit acceptance signals. Link each milestone to dependencies and risks.',
    },
    wbes: {
      title: 'Decompose into WBEs',
      detail:
        'Break work into work breakdown elements with clear inputs, outputs, and handoffs.',
    },
    ore: {
      title: 'Gather inputs and sources',
      detail:
        'Collect raw inputs, references, and constraints that feed downstream refinement.',
    },
    ingots: {
      title: 'Refine reusable building blocks',
      detail:
        'Produce stable, reusable artifacts that downstream stages can consume without rework.',
    },
    sparks: {
      title: 'Run focused experiments',
      detail:
        'Execute small, time-boxed spikes to reduce uncertainty before committing broadly.',
    },
    charges: {
      title: 'Execute committed work items',
      detail:
        'Drive delivery with clear ownership, energy, and verification against scope.',
    },
  }
  return m[stage] ?? m.idea
}

function packEmphasisStep(kind: OutputPackKind): { title: string; detail: string } {
  const m: Record<OutputPackKind, { title: string; detail: string }> = {
    foundation_pack: {
      title: 'Stabilize foundation artifacts',
      detail: OUTPUT_PACK_KIND_UI.foundation_pack.plain,
    },
    strategy_pack: {
      title: 'Articulate strategy and tradeoffs',
      detail: OUTPUT_PACK_KIND_UI.strategy_pack.plain,
    },
    planning_pack: {
      title: 'Produce planning-ready artifacts',
      detail: OUTPUT_PACK_KIND_UI.planning_pack.plain,
    },
    engineering_pack: {
      title: 'Produce engineering-ready outputs',
      detail: OUTPUT_PACK_KIND_UI.engineering_pack.plain,
    },
    execution_pack: {
      title: 'Drive execution evidence',
      detail: OUTPUT_PACK_KIND_UI.execution_pack.plain,
    },
  }
  return m[kind] ?? m.foundation_pack
}

function boundaryDetail(spec: ScopeSpecJson): { title: string; detail: string } {
  const b = isScopeBoundary(spec.scope_boundary) ? spec.scope_boundary : 'full_plan'
  const summary = spec.summary.trim()
  const constraints = spec.constraints_note.trim()
  const base = summary
    ? `Ground in: ${summary.slice(0, 400)}${summary.length > 400 ? '…' : ''}`
    : 'Align automation and exports to the chosen boundary so downstream artifacts stay consistent.'
  const extra =
    constraints && constraints.length > 0
      ? `\n\nConstraints / gaps called out: ${constraints.slice(0, 1200)}${constraints.length > 1200 ? '…' : ''}`
      : ''
  switch (b) {
    case 'milestone':
      return {
        title: 'Stay within the milestone slice',
        detail:
          (spec.milestone_ref.trim()
            ? `Milestone: ${spec.milestone_ref.trim().slice(0, 500)}.\n\n`
            : '') + base + extra,
      }
    case 'wbe_subtree':
      return {
        title: 'Stay within the WBE subtree',
        detail:
          (spec.wbe_path.trim()
            ? `WBE path:\n${spec.wbe_path.trim().slice(0, 2000)}${spec.wbe_path.length > 2000 ? '…' : ''}\n\n`
            : '') + base + extra,
      }
    case 'capability':
      return {
        title: 'Focus the capability / feature slice',
        detail:
          (spec.capability_label.trim()
            ? `Capability: ${spec.capability_label.trim().slice(0, 500)}.\n\n`
            : '') + base + extra,
      }
    case 'team_slice':
      return {
        title: 'Focus the team slice',
        detail:
          (spec.team_label.trim() ? `Team: ${spec.team_label.trim().slice(0, 500)}.\n\n` : '') + base + extra,
      }
    case 'repo_path':
      return {
        title: 'Scope to repository paths',
        detail:
          (spec.repo_paths?.length
            ? `Paths:\n${spec.repo_paths.slice(0, 24).join('\n')}${spec.repo_paths.length > 24 ? '\n…' : ''}\n\n`
            : '') + base + extra,
      }
    case 'recheck_subset':
      return {
        title: 'Recheck / repair subset',
        detail:
          (spec.recheck_issue_refs.trim()
            ? `Notes:\n${spec.recheck_issue_refs.trim().slice(0, 2000)}${spec.recheck_issue_refs.length > 2000 ? '…' : ''}\n\n`
            : '') + base + extra,
      }
    case 'full_plan':
    default:
      return {
        title: 'Span the full initiative',
        detail: base + extra,
      }
  }
}

export type DeriveDraftRunPlanInput = {
  missionTitle: string
  targetStage: TargetStage
  outputPackKind: OutputPackKind
  scopeSpec: ScopeSpecJson
}

/**
 * Deterministic draft run plan from methodology stage, output pack kind, and normalized scope.
 */
export function deriveDraftRunPlan(input: DeriveDraftRunPlanInput): RunPlanJson {
  const missionLabel = input.missionTitle.trim() || 'Initiative'
  const stageLabel = TARGET_STAGE_UI[input.targetStage]?.forgeLabel ?? String(input.targetStage)
  const packLabel = OUTPUT_PACK_KIND_UI[input.outputPackKind]?.forgeLabel ?? String(input.outputPackKind)
  const title = `Run plan — ${missionLabel} · ${stageLabel} · ${packLabel}`.slice(0, RUN_PLAN_TITLE_MAX)

  const stageStep = stagePrimaryStep(input.targetStage)
  const packStep = packEmphasisStep(input.outputPackKind)
  const boundaryStep = boundaryDetail(input.scopeSpec)
  const scopeSummary = input.scopeSpec.summary.trim()
  const gaps = input.scopeSpec.constraints_note.trim()
  const closureLine =
    (input.scopeSpec.closure_options ?? []).length > 0
      ? `Closure options: ${(input.scopeSpec.closure_options ?? []).map(String).join(', ')}.`
      : ''
  const openDetail = [
    scopeSummary ? `Understanding summary: ${scopeSummary.slice(0, 600)}${scopeSummary.length > 600 ? '…' : ''}` : '',
    gaps ? `Gaps / constraints: ${gaps.slice(0, 1200)}${gaps.length > 1200 ? '…' : ''}` : '',
    closureLine,
  ]
    .filter(Boolean)
    .join('\n\n')
  const firstDetail =
    openDetail ||
    'Review understanding, constraints, and closure options before executing downstream steps.'

  const steps: RunPlanStepJson[] = [
    {
      id: '',
      title: 'Confirm scope and success criteria',
      detail: firstDetail.slice(0, RUN_PLAN_STEP_DETAIL_MAX),
    },
    { id: '', title: stageStep.title, detail: stageStep.detail.slice(0, RUN_PLAN_STEP_DETAIL_MAX) },
    { id: '', title: packStep.title, detail: packStep.detail.slice(0, RUN_PLAN_STEP_DETAIL_MAX) },
    { id: '', title: boundaryStep.title, detail: boundaryStep.detail.slice(0, RUN_PLAN_STEP_DETAIL_MAX) },
    {
      id: '',
      title: 'Review outputs and next gates',
      detail:
        'Validate drafts against scope, refresh assumptions, and move to review / export when ready.',
    },
  ]

  return normalizeRunPlan({ id: '', title, steps })
}

/** Build merged scope_spec the same way as session merge (understanding + scope selection). */
export function mergedScopeSpecForRunPlan(shell: WizardShellState): ScopeSpecJson {
  const base = normalizeScopeSpec({
    ...emptyWizardDomain().scope_spec,
    summary: shell.understanding.summary,
    constraints_note: shell.understanding.knownGaps ?? '',
  })
  return normalizeScopeSpec(scopeSpecFromSelection(base, shell.scopeSelection))
}

export function deriveDraftRunPlanFromShell(shell: WizardShellState): RunPlanJson {
  return deriveDraftRunPlan({
    missionTitle: shell.mission.title,
    targetStage: shell.targetOutputPack.targetStage,
    outputPackKind: shell.targetOutputPack.outputPackKind,
    scopeSpec: mergedScopeSpecForRunPlan(shell),
  })
}

export type RunPlanFieldErrors = {
  title?: string
  steps?: string
}

export function validateRunPlanForNext(rp: RunPlanJson | undefined | null): { ok: boolean; errors: RunPlanFieldErrors } {
  const plan = clampRunPlan(rp)
  const errors: RunPlanFieldErrors = {}
  const title = plan.title.trim()
  if (!title) {
    errors.title = 'Add a short title for this run plan.'
  }
  if (!plan.steps.length) {
    errors.steps = 'Add at least one run step.'
  }
  if (plan.steps.length > RUN_PLAN_MAX_STEPS) {
    errors.steps = `At most ${RUN_PLAN_MAX_STEPS} steps.`
  }
  for (let i = 0; i < plan.steps.length; i++) {
    if (!plan.steps[i].title.trim()) {
      errors.steps = `Step ${i + 1} needs a title.`
      break
    }
  }
  return { ok: Object.keys(errors).length === 0, errors }
}

export function formatRunPlanForStepNote(rp: RunPlanJson): string {
  const c = clampRunPlan(rp)
  const lines: string[] = []
  if (c.title.trim()) lines.push(c.title.trim())
  for (let i = 0; i < c.steps.length; i++) {
    const s = c.steps[i]
    const head = `${i + 1}. ${s.title.trim()}`.trim()
    lines.push(head)
    if (s.detail.trim()) {
      lines.push(s.detail.trim().split('\n').map((ln) => `   ${ln}`).join('\n'))
    }
  }
  return lines.join('\n').slice(0, 12000)
}
