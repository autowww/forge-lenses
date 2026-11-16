import { describe, expect, it } from 'vitest'
import {
  emptyUnderstandingPayload,
  formatUnderstandingForStepNote,
  understandingFromPayloadOrScope,
  validateUnderstandingForNext,
} from './understandingStep'

describe('validateUnderstandingForNext', () => {
  it('requires summary', () => {
    const r = validateUnderstandingForNext(emptyUnderstandingPayload())
    expect(r.ok).toBe(false)
    expect(r.errors.summary).toBeDefined()
  })

  it('passes with summary', () => {
    expect(
      validateUnderstandingForNext({ summary: 'We know X.', knownGaps: '' }).ok,
    ).toBe(true)
  })
})

describe('understandingFromPayloadOrScope', () => {
  it('uses explicit payload', () => {
    const u = understandingFromPayloadOrScope(
      { understanding: { summary: 'A', knownGaps: 'B' } },
      'scope',
      'c',
    )
    expect(u.summary).toBe('A')
  })

  it('falls back to scope', () => {
    const u = understandingFromPayloadOrScope({}, 'from scope', 'gaps')
    expect(u.summary).toBe('from scope')
    expect(u.knownGaps).toBe('gaps')
  })
})

describe('formatUnderstandingForStepNote', () => {
  it('joins fields', () => {
    const s = formatUnderstandingForStepNote({ summary: 'S', knownGaps: 'G' })
    expect(s).toContain('Understanding: S')
    expect(s).toContain('Gaps / unknowns: G')
  })
})
