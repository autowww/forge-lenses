import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import type { ClarificationQuestionItem, ClarificationResponse } from './clarificationTypes'
import {
  CLARIFICATION_SECTION_END,
  CLARIFICATION_SECTION_START,
  mergeClarificationIntoFoundationBrief,
} from './clarificationMerge'

const _dir = dirname(fileURLToPath(import.meta.url))

function readFixture(name: string): string {
  return readFileSync(join(_dir, 'fixtures', name), 'utf-8').replace(/\r\n/g, '\n').trimEnd()
}

const goldenQ1: ClarificationQuestionItem = {
  id: 'q1',
  text: 'What is the deadline?',
  why_it_matters: 'Time drives scope.',
  answer_type: 'short_text',
  default_assumption_if_skipped: 'No fixed date.',
  priority: 50,
  foundation_brief_field_key: 'scope',
}

const goldenResponses: Record<string, ClarificationResponse> = {
  q1: { kind: 'answered', value: 'Friday' },
}

describe('clarification merge golden files', () => {
  it('golden-01 matches expected Markdown after merge', () => {
    const before = readFixture('clarification-golden-01-before.md')
    const expected = readFixture('clarification-golden-01-expected.md')
    const out = mergeClarificationIntoFoundationBrief(before, [goldenQ1], goldenResponses)
    expect(out.trimEnd()).toBe(expected)
  })

  it('golden-02 strips duplicate bounded blocks then merges once', () => {
    const before = readFixture('clarification-golden-02-before.md')
    const expected = readFixture('clarification-golden-02-expected.md')
    const out = mergeClarificationIntoFoundationBrief(before, [goldenQ1], goldenResponses)
    expect(out.trimEnd()).toBe(expected)
  })

  it('re-applying merge is idempotent (golden-01)', () => {
    const before = readFixture('clarification-golden-01-before.md')
    const expected = readFixture('clarification-golden-01-expected.md')
    const once = mergeClarificationIntoFoundationBrief(before, [goldenQ1], goldenResponses)
    const twice = mergeClarificationIntoFoundationBrief(once, [goldenQ1], goldenResponses)
    expect(twice.trimEnd()).toBe(expected)
    expect((twice.match(new RegExp(CLARIFICATION_SECTION_START.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) ?? []).length).toBe(1)
    expect((twice.match(new RegExp(CLARIFICATION_SECTION_END.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) ?? []).length).toBe(1)
  })
})
