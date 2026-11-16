import { describe, expect, it } from 'vitest'
import { contributionDefaultsForKind, defaultAutonomyMutationForKind } from './contributionSetupDefaults'

describe('contributionDefaultsForKind', () => {
  it('returns autonomy and gate labels for each scale', () => {
    expect(contributionDefaultsForKind('single').reviewGates).toContain('Self-check')
    expect(contributionDefaultsForKind('enterprise').artifactDepth).toContain('Full')
  })
})

describe('defaultAutonomyMutationForKind', () => {
  it('matches expected matrix', () => {
    expect(defaultAutonomyMutationForKind('single')).toEqual({
      autonomyLevel: 'l0_analyst',
      mutationPolicy: 'read_only_analysis',
    })
    expect(defaultAutonomyMutationForKind('team')).toEqual({
      autonomyLevel: 'l1_drafter',
      mutationPolicy: 'draft_downstream_only',
    })
    expect(defaultAutonomyMutationForKind('teams')).toEqual({
      autonomyLevel: 'l2_stage_autopilot',
      mutationPolicy: 'edit_downstream_drafts',
    })
    expect(defaultAutonomyMutationForKind('enterprise')).toEqual({
      autonomyLevel: 'l2_stage_autopilot',
      mutationPolicy: 'propose_upstream_only',
    })
  })
})
