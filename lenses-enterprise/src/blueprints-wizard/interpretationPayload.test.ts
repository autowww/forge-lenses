import { describe, expect, it } from 'vitest'
import {
  FOUNDATION_BRIEF_DRAFT_KEYS,
  clampInterpretationPayload,
  emptyInterpretationPayload,
  parseInterpretationFromPayload,
} from './interpretationPayload'

describe('parseInterpretationFromPayload', () => {
  it('returns defaults when missing', () => {
    const o = parseInterpretationFromPayload({})
    expect(o.schema_version).toBe(1)
    expect(o.what_user_said).toBe('')
    expect(Object.keys(o.foundation_brief_draft).sort()).toEqual([...FOUNDATION_BRIEF_DRAFT_KEYS].sort())
  })

  it('clamps confidence on sections', () => {
    const o = parseInterpretationFromPayload({
      interpretation: {
        foundation_brief_draft: {
          problem_statement: { text: 'p', status: 'explicit', confidence: 2 },
        },
      },
    })
    expect(o.foundation_brief_draft.problem_statement.confidence).toBe(1)
  })
})

describe('clampInterpretationPayload', () => {
  it('handles undefined input', () => {
    expect(clampInterpretationPayload(undefined as unknown as never)).toEqual(emptyInterpretationPayload())
  })
})
