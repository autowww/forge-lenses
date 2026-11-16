import { describe, expect, it } from 'vitest'
import {
  needsL3ReadonlyAck,
  needsTierRiskAck,
  validateAutonomyMutationForNext,
} from './autonomyMutationStep'

describe('validateAutonomyMutationForNext', () => {
  it('requires guardrail ack for L3 + read-only analysis', () => {
    const v = validateAutonomyMutationForNext(
      {
        autonomyLevel: 'l3_goal_autopilot',
        mutationPolicy: 'read_only_analysis',
        advancedOverride: true,
        guardrailAcknowledged: false,
      },
      'team',
    )
    expect(v.ok).toBe(false)
    expect(v.errors.guardrail).toBeDefined()
  })

  it('passes when guardrail acknowledged', () => {
    const v = validateAutonomyMutationForNext(
      {
        autonomyLevel: 'l3_goal_autopilot',
        mutationPolicy: 'read_only_analysis',
        advancedOverride: true,
        guardrailAcknowledged: true,
      },
      'team',
    )
    expect(v.ok).toBe(true)
  })

  it('flags single + regenerate downstream', () => {
    const v = validateAutonomyMutationForNext(
      {
        autonomyLevel: 'l1_drafter',
        mutationPolicy: 'regenerate_downstream_from_approved_upstream',
        advancedOverride: true,
        guardrailAcknowledged: false,
      },
      'single',
    )
    expect(v.ok).toBe(false)
  })
})

describe('needsL3ReadonlyAck', () => {
  it('detects contradictory pair', () => {
    expect(
      needsL3ReadonlyAck({
        autonomyLevel: 'l3_goal_autopilot',
        mutationPolicy: 'read_only_analysis',
        advancedOverride: false,
        guardrailAcknowledged: false,
      }),
    ).toBe(true)
  })
})

describe('needsTierRiskAck', () => {
  it('is true for single + L3', () => {
    expect(
      needsTierRiskAck('single', {
        autonomyLevel: 'l3_goal_autopilot',
        mutationPolicy: 'draft_downstream_only',
        advancedOverride: false,
        guardrailAcknowledged: false,
      }),
    ).toBe(true)
  })
})
