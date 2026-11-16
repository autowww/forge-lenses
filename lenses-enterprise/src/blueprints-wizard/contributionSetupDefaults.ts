/**
 * Display defaults for Contribution Setup scale (step 1) and seed values for Autonomy & Mutation (step 6).
 */

import type { AutonomyLevel, ContributionSetupKind, MutationPolicy } from './wizardDomainTypes'

export type ContributionDefaultsRow = {
  autonomy: AutonomyLevel
  autonomyLabel: string
  reviewGates: string
  artifactDepth: string
}

const ROWS: Record<ContributionSetupKind, ContributionDefaultsRow> = {
  single: {
    autonomy: 'l0_analyst',
    autonomyLabel: 'L0 Analyst',
    reviewGates: 'Self-check before share',
    artifactDepth: 'Light — outlines and pointers',
  },
  team: {
    autonomy: 'l1_drafter',
    autonomyLabel: 'L1 Drafter',
    reviewGates: 'Peer review on material changes',
    artifactDepth: 'Standard — sections and checklists',
  },
  teams: {
    autonomy: 'l2_stage_autopilot',
    autonomyLabel: 'L2 Stage Autopilot',
    reviewGates: 'Lead + peer gates on merges',
    artifactDepth: 'Deep — versioned packs and evidence',
  },
  enterprise: {
    autonomy: 'l2_stage_autopilot',
    autonomyLabel: 'L2 Stage Autopilot',
    reviewGates: 'Policy gates, audit trail, sign-off',
    artifactDepth: 'Full — traceable artifacts and records',
  },
}

export function contributionDefaultsForKind(kind: ContributionSetupKind): ContributionDefaultsRow {
  return ROWS[kind] ?? ROWS.single
}

/**
 * Default autonomy + mutation when entering step 6 or when contribution scale changes
 * (unless `advancedOverride` on autonomy payload). Tuned: tighter for single contributor,
 * more explicit upstream governance for enterprise.
 */
export function defaultAutonomyMutationForKind(kind: ContributionSetupKind): {
  autonomyLevel: AutonomyLevel
  mutationPolicy: MutationPolicy
} {
  const m: Record<
    ContributionSetupKind,
    { autonomyLevel: AutonomyLevel; mutationPolicy: MutationPolicy }
  > = {
    single: { autonomyLevel: 'l0_analyst', mutationPolicy: 'read_only_analysis' },
    team: { autonomyLevel: 'l1_drafter', mutationPolicy: 'draft_downstream_only' },
    teams: { autonomyLevel: 'l2_stage_autopilot', mutationPolicy: 'edit_downstream_drafts' },
    enterprise: { autonomyLevel: 'l2_stage_autopilot', mutationPolicy: 'propose_upstream_only' },
  }
  return m[kind] ?? m.single
}
