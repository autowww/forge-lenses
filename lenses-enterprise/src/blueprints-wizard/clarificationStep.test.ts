import { describe, expect, it } from 'vitest'
import {
  clarificationFromPayloadOrRecipe,
  emptyClarificationPayload,
  formatClarificationForStepNote,
  validateClarificationForNext,
} from './clarificationStep'

describe('validateClarificationForNext', () => {
  it('requires open questions', () => {
    const r = validateClarificationForNext(emptyClarificationPayload())
    expect(r.ok).toBe(false)
  })

  it('passes with questions', () => {
    expect(
      validateClarificationForNext({
        openQuestions: 'Q?',
        decisionsNeeded: '',
        questions: [],
        responses: {},
      }).ok,
    ).toBe(true)
  })

  it('requires responses when structured questions are set', () => {
    const r = validateClarificationForNext({
      openQuestions: '',
      decisionsNeeded: '',
      questions: [
        {
          id: 'q1',
          text: 'T',
          why_it_matters: 'W',
          answer_type: 'short_text',
          default_assumption_if_skipped: 'D',
          priority: 1,
        },
      ],
      responses: {},
    })
    expect(r.ok).toBe(false)
  })
})

describe('clarificationFromPayloadOrRecipe', () => {
  it('reads variables when payload missing', () => {
    const c = clarificationFromPayloadOrRecipe(
      {},
      { clarification_open_questions: 'From recipe', clarification_decisions_needed: 'D' },
    )
    expect(c.openQuestions).toContain('From recipe')
    expect(c.decisionsNeeded).toContain('D')
  })
})

describe('formatClarificationForStepNote', () => {
  it('joins', () => {
    const s = formatClarificationForStepNote({
      openQuestions: 'Q',
      decisionsNeeded: 'D',
      questions: [],
      responses: {},
    })
    expect(s).toContain('Open questions: Q')
    expect(s).toContain('Decisions needed: D')
  })
})
