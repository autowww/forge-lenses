/**
 * Step 6 — Autonomy & Mutation. `payload.autonomyMutation` ↔ `wizard_domain.autonomy_level` + `mutation_policy`.
 */

import { defaultAutonomyMutationForKind } from './contributionSetupDefaults'
import type {
  AutonomyLevel,
  ContributionSetupKind,
  MutationPolicy,
  WizardDomainJson,
} from './wizardDomainTypes'
import { AUTONOMY_LEVELS, MUTATION_POLICIES } from './wizardDomainTypes'

export type AutonomyMutationPayloadV1 = {
  autonomyLevel: AutonomyLevel
  mutationPolicy: MutationPolicy
  /** User chose values that differ from contribution-based defaults. */
  advancedOverride: boolean
  /** Required when validation demands acknowledgment (L3 + read_only, or tier-risk). */
  guardrailAcknowledged: boolean
}

function isAutonomy(v: unknown): v is AutonomyLevel {
  return typeof v === 'string' && (AUTONOMY_LEVELS as readonly string[]).includes(v)
}

function isMutation(v: unknown): v is MutationPolicy {
  return typeof v === 'string' && (MUTATION_POLICIES as readonly string[]).includes(v)
}

export const AUTONOMY_UI: Record<AutonomyLevel, { title: string; plain: string }> = {
  l0_analyst: {
    title: 'L0 Analyst',
    plain: 'Read-only analysis and suggestions — no drafts without you.',
  },
  l1_drafter: {
    title: 'L1 Drafter',
    plain: 'Produces drafts for your review before any share.',
  },
  l2_stage_autopilot: {
    title: 'L2 Stage Autopilot',
    plain: 'Runs multi-step work inside the current stage with gates.',
  },
  l3_goal_autopilot: {
    title: 'L3 Goal Autopilot',
    plain: 'Pursues stated goals across stages with explicit checkpoints.',
  },
}

export const MUTATION_UI: Record<MutationPolicy, { title: string; plain: string }> = {
  read_only_analysis: {
    title: 'Read-only analysis',
    plain: 'Inspect upstream; no generated edits.',
  },
  draft_downstream_only: {
    title: 'Draft downstream only',
    plain: 'New content only in downstream drafts.',
  },
  edit_downstream_drafts: {
    title: 'Edit downstream drafts',
    plain: 'Revise existing drafts that are downstream of approved scope.',
  },
  regenerate_downstream_from_approved_upstream: {
    title: 'Regenerate downstream from approved upstream',
    plain: 'Rebuild downstream artifacts when upstream is explicitly approved.',
  },
  propose_upstream_only: {
    title: 'Propose upstream changes only',
    plain: 'Suggestions for upstream — never applied silently.',
  },
}

export function emptyAutonomyMutationPayload(
  kind: ContributionSetupKind = 'single',
): AutonomyMutationPayloadV1 {
  const d = defaultAutonomyMutationForKind(kind)
  return {
    autonomyLevel: d.autonomyLevel,
    mutationPolicy: d.mutationPolicy,
    advancedOverride: false,
    guardrailAcknowledged: false,
  }
}

export function parseAutonomyMutationFromPayload(
  payload: Record<string, unknown>,
  kind: ContributionSetupKind,
  wd: WizardDomainJson,
): AutonomyMutationPayloadV1 {
  const raw = payload.autonomyMutation
  const fallback = emptyAutonomyMutationPayload(kind)
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return {
      ...fallback,
      autonomyLevel: (isAutonomy(wd.autonomy_level) ? wd.autonomy_level : fallback.autonomyLevel),
      mutationPolicy: (isMutation(wd.mutation_policy) ? wd.mutation_policy : fallback.mutationPolicy),
    }
  }
  const o = raw as Record<string, unknown>
  return {
    autonomyLevel: isAutonomy(o.autonomyLevel) ? o.autonomyLevel : fallback.autonomyLevel,
    mutationPolicy: isMutation(o.mutationPolicy) ? o.mutationPolicy : fallback.mutationPolicy,
    advancedOverride: o.advancedOverride === true,
    guardrailAcknowledged: o.guardrailAcknowledged === true,
  }
}

export function clampAutonomyMutationPayload(a: AutonomyMutationPayloadV1 | undefined): AutonomyMutationPayloadV1 {
  if (!a) return emptyAutonomyMutationPayload('single')
  return {
    autonomyLevel: isAutonomy(a.autonomyLevel) ? a.autonomyLevel : 'l0_analyst',
    mutationPolicy: isMutation(a.mutationPolicy) ? a.mutationPolicy : 'read_only_analysis',
    advancedOverride: a.advancedOverride === true,
    guardrailAcknowledged: a.guardrailAcknowledged === true,
  }
}

export type AutonomyMutationFieldErrors = {
  autonomyLevel?: string
  mutationPolicy?: string
  guardrail?: string
}

/** L3 + read_only_analysis is contradictory without acknowledgment. */
export function needsL3ReadonlyAck(a: AutonomyMutationPayloadV1): boolean {
  return a.autonomyLevel === 'l3_goal_autopilot' && a.mutationPolicy === 'read_only_analysis'
}

/** Small contributor scale with high blast radius. */
export function needsTierRiskAck(
  kind: ContributionSetupKind,
  a: AutonomyMutationPayloadV1,
): boolean {
  if (kind !== 'single') return false
  if (a.autonomyLevel === 'l3_goal_autopilot') return true
  return a.mutationPolicy === 'regenerate_downstream_from_approved_upstream'
}

export function validateAutonomyMutationForNext(
  a: AutonomyMutationPayloadV1,
  contributionKind: ContributionSetupKind,
): { ok: boolean; errors: AutonomyMutationFieldErrors } {
  const errors: AutonomyMutationFieldErrors = {}
  if (!isAutonomy(a.autonomyLevel)) errors.autonomyLevel = 'Pick an autonomy level.'
  if (!isMutation(a.mutationPolicy)) errors.mutationPolicy = 'Pick a mutation policy.'
  if ((needsL3ReadonlyAck(a) || needsTierRiskAck(contributionKind, a)) && !a.guardrailAcknowledged) {
    errors.guardrail = 'Confirm you accept this autonomy and mutation combination.'
  }
  return { ok: Object.keys(errors).length === 0, errors }
}

export function formatAutonomyMutationForStepNote(a: AutonomyMutationPayloadV1): string {
  const au = AUTONOMY_UI[a.autonomyLevel]?.title ?? a.autonomyLevel
  const mu = MUTATION_UI[a.mutationPolicy]?.title ?? a.mutationPolicy
  return [`Autonomy: ${au}`, `Mutation policy: ${mu}`].join('\n\n')
}
