import { describe, expect, it } from 'vitest'
import type { ClarificationQuestionItem } from './clarificationTypes'
import type { ClarificationResponse } from './clarificationTypes'
import type { AssumptionLedgerEntryJson } from './wizardDomainTypes'
import {
  CLARIFICATION_SECTION_END,
  CLARIFICATION_SECTION_MARKER,
  CLARIFICATION_SECTION_START,
  applyResponsesToAssumptionLedger,
  fieldStatusesAfterClarification,
  isUnresolvedAssumption,
  mergeClarificationIntoFoundationBrief,
  stripClarificationSection,
} from './clarificationMerge'

const q1: ClarificationQuestionItem = {
  id: 'q1',
  text: 'What is the deadline?',
  why_it_matters: 'Time drives scope.',
  answer_type: 'short_text',
  default_assumption_if_skipped: 'No fixed date.',
  priority: 50,
  foundation_brief_field_key: 'scope',
}

describe('mergeClarificationIntoFoundationBrief', () => {
  it('appends idempotent clarification section', () => {
    const responses: Record<string, ClarificationResponse> = {
      q1: { kind: 'answered', value: 'Friday' },
    }
    const md = mergeClarificationIntoFoundationBrief('# Hello\n\nBody', [q1], responses)
    expect(md).toContain(CLARIFICATION_SECTION_START)
    expect(md).toContain(CLARIFICATION_SECTION_END)
    expect(md).toContain('Clarification capture')
    expect(md).toContain('Friday')
    const again = mergeClarificationIntoFoundationBrief(md, [q1], responses)
    expect((again.match(new RegExp(CLARIFICATION_SECTION_START.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) ?? []).length).toBe(1)
  })

  it('stripClarificationSection removes bounded and legacy marker blocks', () => {
    const inner = mergeClarificationIntoFoundationBrief('', [q1], { q1: { kind: 'skipped' } })
    expect(stripClarificationSection(inner)).toBe('')
    const legacyOnly = `${CLARIFICATION_SECTION_MARKER}\n\n## Clarification capture\n\nx\n`
    expect(stripClarificationSection(legacyOnly).trim()).toBe('')
  })
})

describe('isUnresolvedAssumption', () => {
  it('marks open and marked_unknown', () => {
    expect(isUnresolvedAssumption({ id: 'a', text: 'x', status: 'open' })).toBe(true)
    expect(isUnresolvedAssumption({ id: 'a', text: 'x', status: 'marked_unknown' })).toBe(true)
    expect(isUnresolvedAssumption({ id: 'a', text: 'x', status: 'resolved' })).toBe(false)
  })
})

describe('applyResponsesToAssumptionLedger', () => {
  it('upserts clarify_ entries with statuses', () => {
    const responses: Record<string, ClarificationResponse> = {
      q1: { kind: 'accepted_default' },
    }
    const ledger: AssumptionLedgerEntryJson[] = []
    const out = applyResponsesToAssumptionLedger(ledger, [q1], responses)
    const row = out.find((e) => e.id === 'clarify_q1')
    expect(row).toBeDefined()
    expect(row?.status).toBe('accepted_system')
  })
})

describe('fieldStatusesAfterClarification', () => {
  it('sets explicit for answered', () => {
    const prev = { fb_scope: 'unknown' as const }
    const next = fieldStatusesAfterClarification(prev, [q1], { q1: { kind: 'answered', value: 'x' } })
    expect(next.fb_scope).toBe('explicit')
  })
})
