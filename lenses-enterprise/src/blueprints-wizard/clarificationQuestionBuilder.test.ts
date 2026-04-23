import { describe, expect, it } from 'vitest'
import { emptyInterpretationPayload } from './interpretationPayload'
import { buildClarificationQuestions } from './clarificationQuestionBuilder'

describe('buildClarificationQuestions', () => {
  it('returns between 3 and 7 when signals exist', () => {
    const fs: Record<string, string> = {}
    for (const k of [
      'fb_problem_statement',
      'fb_desired_outcome',
      'fb_scope',
      'fb_success_metrics',
      'fb_constraints',
    ]) {
      fs[k] = 'unknown'
    }
    const out = buildClarificationQuestions({
      foundationBriefMarkdown: '# Foundation Brief\n\n## Problem statement\n\n',
      foundationBriefFieldStatuses: fs,
      interpretation: { ...emptyInterpretationPayload(), unknowns: ['gap a', 'gap b'] },
      understandingKnownGaps: 'more gap',
    })
    expect(out.length).toBeGreaterThanOrEqual(3)
    expect(out.length).toBeLessThanOrEqual(7)
  })

  it('is deterministic for fixed input', () => {
    const fs = { fb_scope: 'unknown' }
    const a = buildClarificationQuestions({
      foundationBriefMarkdown: '',
      foundationBriefFieldStatuses: fs,
      interpretation: emptyInterpretationPayload(),
      understandingKnownGaps: '',
    })
    const b = buildClarificationQuestions({
      foundationBriefMarkdown: '',
      foundationBriefFieldStatuses: fs,
      interpretation: emptyInterpretationPayload(),
      understandingKnownGaps: '',
    })
    expect(a.map((x) => x.id)).toEqual(b.map((x) => x.id))
  })
})
