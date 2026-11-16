import { describe, expect, it } from 'vitest'
import {
  emptyContributionSetupPayload,
  formatContributionSetupForStepNote,
  parseContributionSetupFromPayload,
  validateContributionSetupForNext,
} from './contributionSetupStep'

describe('validateContributionSetupForNext', () => {
  it('passes with empty optional fields', () => {
    const r = validateContributionSetupForNext(emptyContributionSetupPayload())
    expect(r.ok).toBe(true)
  })

  it('fails when notes exceed max', () => {
    const r = validateContributionSetupForNext({
      notes: 'x'.repeat(9000),
    })
    expect(r.ok).toBe(false)
    expect(r.errors.notes).toBeDefined()
  })
})

describe('parseContributionSetupFromPayload', () => {
  it('reads contributionSetup object', () => {
    const c = parseContributionSetupFromPayload({
      contributionSetup: { deliverable: 'D', landingPlace: 'L', notes: 'N' },
    })
    expect(c).toEqual({ deliverable: 'D', landingPlace: 'L', notes: 'N' })
  })
})

describe('formatContributionSetupForStepNote', () => {
  it('includes scale and optional parts', () => {
    const s = formatContributionSetupForStepNote(
      {
        deliverable: 'A',
        landingPlace: 'B',
        notes: 'C',
      },
      'team',
    )
    expect(s).toContain('Contribution scale: Team')
    expect(s).toContain('Deliverable: A')
    expect(s).toContain('Landing place: B')
    expect(s).toContain('Notes: C')
  })
})
