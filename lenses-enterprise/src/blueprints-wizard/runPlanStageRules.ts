/**
 * Data-driven stage / pack / policy rules for run-plan preview (pure, no I/O).
 */

import type { AutonomyMutationPayloadV1 } from './autonomyMutationStep'
import { AUTONOMY_UI, MUTATION_UI, needsL3ReadonlyAck, needsTierRiskAck } from './autonomyMutationStep'
import { OUTPUT_PACK_KIND_UI, TARGET_STAGE_UI } from './targetOutputPackStep'
import type { ContributionSetupKind, MutationPolicy, OutputPackKind, TargetStage } from './wizardDomainTypes'
import type { RiskHotspotPreview, ReviewGatePreview } from './runPlanPreviewTypes'
import type { RunPlanPreviewInput } from './runPlanPreviewTypes'

/** Packs that assume a non-empty foundation brief for credible downstream work. */
export const PACKS_EXPECTING_FOUNDATION: ReadonlySet<OutputPackKind> = new Set([
  'strategy_pack',
  'planning_pack',
  'engineering_pack',
  'execution_pack',
])

export function packExpectsFoundationBrief(kind: OutputPackKind): boolean {
  return PACKS_EXPECTING_FOUNDATION.has(kind)
}

/** Policies that treat existing “ready” artifacts as leave-alone when labels match. */
export function mutationLeavesReadyUntouched(policy: MutationPolicy): boolean {
  return policy === 'read_only_analysis' || policy === 'propose_upstream_only'
}

/** Policies that imply rewriting or heavy touch on existing draft/stale rows. */
export function mutationImpliesRefresh(policy: MutationPolicy): boolean {
  return (
    policy === 'edit_downstream_drafts' ||
    policy === 'regenerate_downstream_from_approved_upstream' ||
    policy === 'draft_downstream_only'
  )
}

type GateDef = { id: string; title: string; rationale: string }

const BASE_GATES: GateDef[] = [
  {
    id: 'gate_scope',
    title: 'Scope boundary and closure options',
    rationale: 'Automation and exports stay inside the selected boundary and closure rules.',
  },
  {
    id: 'gate_assumptions',
    title: 'Assumption ledger reviewed',
    rationale: 'Open assumptions are visible; accepted or system-marked items are documented.',
  },
]

function stageGate(stage: TargetStage): GateDef | null {
  const m: Partial<Record<TargetStage, GateDef>> = {
    idea: {
      id: 'gate_idea',
      title: 'Intent and options are visible',
      rationale: 'Problem, stakeholders, and candidate directions are captured before hardening.',
    },
    roadmap: {
      id: 'gate_roadmap',
      title: 'Roadmap themes sequenced',
      rationale: 'Outcomes, dependencies, and bets are aligned to evidence and owners.',
    },
    milestones: {
      id: 'gate_milestones',
      title: 'Milestone acceptance is explicit',
      rationale: 'Each checkpoint has acceptance signals and dependencies.',
    },
    wbes: {
      id: 'gate_wbes',
      title: 'WBE decomposition is coherent',
      rationale: 'Work elements have clear inputs, outputs, and handoffs.',
    },
  }
  return m[stage] ?? null
}

function packGate(kind: OutputPackKind): GateDef | null {
  const m: Partial<Record<OutputPackKind, GateDef>> = {
    foundation_pack: {
      id: 'gate_foundation_pack',
      title: 'Foundation pack completeness',
      rationale: 'Mission, context, and baseline assumptions are stable enough to build on.',
    },
    strategy_pack: {
      id: 'gate_strategy_pack',
      title: 'Strategy tradeoffs articulated',
      rationale: 'Goals, bets, and tradeoffs are explicit for downstream planning.',
    },
    planning_pack: {
      id: 'gate_planning_pack',
      title: 'Planning artifacts are dependency-aware',
      rationale: 'Milestones, WBEs, and dependencies are consistent with scope.',
    },
    engineering_pack: {
      id: 'gate_engineering_pack',
      title: 'Technical interfaces reviewed',
      rationale: 'Design and interface notes match scope and upstream approvals.',
    },
    execution_pack: {
      id: 'gate_execution_pack',
      title: 'Execution evidence path',
      rationale: 'Run plans, checklists, and evidence align to committed scope.',
    },
  }
  return m[kind] ?? null
}

function contributionGate(kind: ContributionSetupKind): GateDef | null {
  if (kind === 'enterprise') {
    return {
      id: 'gate_enterprise_coord',
      title: 'Cross-team coordination',
      rationale: 'Enterprise-scale delivery needs explicit ownership and dependency visibility.',
    }
  }
  if (kind === 'teams' || kind === 'team') {
    return {
      id: 'gate_team_alignment',
      title: 'Team alignment',
      rationale: 'Multiple contributors need shared understanding of scope and gates.',
    }
  }
  return null
}

export function reviewGatesFor(input: RunPlanPreviewInput): ReviewGatePreview[] {
  const out: ReviewGatePreview[] = BASE_GATES.map((g) => ({ ...g }))
  const sg = stageGate(input.targetOutputPack.targetStage)
  if (sg) out.push({ ...sg })
  const pg = packGate(input.targetOutputPack.outputPackKind)
  if (pg) out.push({ ...pg })
  const cg = contributionGate(input.contributionSetupKind)
  if (cg) out.push({ ...cg })
  if (input.foundationBriefMarkdownEffective.trim().length > 0) {
    out.unshift({
      id: 'gate_foundation_brief',
      title: 'Foundation brief present',
      rationale: 'A foundation brief body exists; review field confidence before export.',
    })
  }
  return out
}

export function riskHotspotsFromPolicy(
  input: RunPlanPreviewInput,
): RiskHotspotPreview[] {
  const out: RiskHotspotPreview[] = []
  const a = input.autonomyMutation
  const kind = input.contributionSetupKind

  if (needsL3ReadonlyAck(a)) {
    out.push({
      id: 'risk_l3_readonly',
      label: 'L3 autonomy vs read-only mutation',
      severity: 'high',
      detail:
        'L3 goal autopilot with read-only analysis is contradictory — confirm guardrails or adjust policy before running.',
    })
  }
  if (needsTierRiskAck(kind, a) && !a.guardrailAcknowledged) {
    out.push({
      id: 'risk_tier_blast',
      label: 'High blast radius at contributor scale',
      severity: 'high',
      detail:
        'L3 or regenerate-style policies on a small contributor footprint need explicit acknowledgment.',
    })
  }
  if (a.autonomyLevel === 'l3_goal_autopilot' && kind === 'single') {
    out.push({
      id: 'risk_l3_single',
      label: 'L3 autonomy on single-contributor mode',
      severity: 'medium',
      detail: 'Cross-stage pursuit with minimal org surface area — keep checkpoints visible.',
    })
  }

  const unknownFields = Object.values(input.foundationBriefFieldStatuses).filter((s) => s === 'unknown').length
  if (unknownFields >= 3) {
    out.push({
      id: 'risk_unknown_fields',
      label: 'Foundation field confidence',
      severity: 'medium',
      detail: `${unknownFields} foundation fields marked unknown — clarify before relying on exports.`,
    })
  }

  return out
}

export function targetStateSummaryLines(input: RunPlanPreviewInput): string[] {
  const tp = input.targetOutputPack
  const st = TARGET_STAGE_UI[tp.targetStage]?.forgeLabel ?? tp.targetStage
  const pk = OUTPUT_PACK_KIND_UI[tp.outputPackKind]?.forgeLabel ?? tp.outputPackKind
  const lines = [
    `Target methodology stage: ${st} (${tp.targetStage})`,
    `Output pack kind: ${pk}`,
    `Primary pack label: ${tp.packLabel.trim() || '(unnamed)'}`,
  ]
  return lines
}

export function autonomySummaryLines(a: AutonomyMutationPayloadV1): string[] {
  return [
    `Autonomy: ${AUTONOMY_UI[a.autonomyLevel]?.title ?? a.autonomyLevel}`,
    `Mutation policy: ${MUTATION_UI[a.mutationPolicy]?.title ?? a.mutationPolicy}`,
  ]
}
