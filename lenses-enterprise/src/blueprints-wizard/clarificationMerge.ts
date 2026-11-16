/**
 * Merge clarification responses into Foundation Brief Markdown and assumption ledger.
 * Idempotent: replaces the bounded region between start/end markers, with fallbacks for legacy shapes.
 */

import type { ClarificationQuestionItem, ClarificationResponse } from './clarificationTypes'
import type { AssumptionLedgerEntryJson, InterpretationFieldStatus } from './wizardDomainTypes'
import { appendAssumptionEntry, updateAssumptionEntry } from './wizardAssumptionHelpers'

/** @deprecated Legacy single marker; stripping still supported. Prefer start/end pair. */
export const CLARIFICATION_SECTION_MARKER = '<!-- lenses:clarification-capture -->'

export const CLARIFICATION_SECTION_START = '<!-- lenses:clarification-capture:start -->'
export const CLARIFICATION_SECTION_END = '<!-- lenses:clarification-capture:end -->'

const SECTION_HEADING = '## Clarification capture'

export function isUnresolvedAssumption(e: AssumptionLedgerEntryJson): boolean {
  const st = e.status ?? 'open'
  return st === 'open' || st === 'marked_unknown'
}

function outcomeLine(q: ClarificationQuestionItem, r: ClarificationResponse): string {
  switch (r.kind) {
    case 'answered': {
      if (q.answer_type === 'yes_no') {
        const v = (r.value ?? '').trim().toLowerCase()
        return `Outcome: ${v || '(answered)'}`
      }
      if (q.answer_type === 'single_choice' && r.choice_key) {
        const opt = q.choice_options?.find((o) => o.key === r.choice_key)
        return `Outcome: ${opt?.label ?? r.choice_key}`
      }
      return `Outcome: ${(r.value ?? '').trim() || '(answered)'}`
    }
    case 'skipped':
      return `Outcome: skipped — using default assumption: ${q.default_assumption_if_skipped}`
    case 'unknown':
      return 'Outcome: marked unknown — not committing to an answer in this pass.'
    case 'accepted_default':
      return `Outcome: accepted system default — ${q.default_assumption_if_skipped}`
    default:
      return 'Outcome: (pending)'
  }
}

function bulletBlock(questions: ClarificationQuestionItem[], responses: Record<string, ClarificationResponse>): string {
  const lines: string[] = [SECTION_HEADING, '']
  for (const q of questions) {
    const r = responses[q.id]
    if (!r) continue
    lines.push(`- **Q:** ${q.text}`)
    lines.push(`  - ${outcomeLine(q, r)}`)
    lines.push('')
  }
  return lines.join('\n').trimEnd()
}

/** Build the bounded clarification block (new format). */
export function buildClarificationBlock(
  questions: ClarificationQuestionItem[],
  responses: Record<string, ClarificationResponse>,
): string {
  return [CLARIFICATION_SECTION_START, '', bulletBlock(questions, responses), '', CLARIFICATION_SECTION_END].join('\n')
}

/**
 * Remove every clarification region: paired start/end, legacy single marker to EOF, and duplicate
 * `## Clarification capture` sections (heading-only legacy).
 */
export function stripClarificationSection(markdown: string): string {
  let md = markdown ?? ''

  // Paired markers (repeat: tolerate duplicate inserts)
  while (true) {
    const s = md.indexOf(CLARIFICATION_SECTION_START)
    if (s === -1) break
    const e = md.indexOf(CLARIFICATION_SECTION_END, s + CLARIFICATION_SECTION_START.length)
    if (e === -1) {
      md = md.slice(0, s).trimEnd()
      break
    }
    const afterEnd = e + CLARIFICATION_SECTION_END.length
    md = (md.slice(0, s) + md.slice(afterEnd)).replace(/\n{3,}/g, '\n\n')
  }

  // Legacy: single HTML comment through EOF (older merge)
  const legacy = CLARIFICATION_SECTION_MARKER
  const li = md.indexOf(legacy)
  if (li !== -1) {
    md = md.slice(0, li).trimEnd()
  }

  md = stripLegacyClarificationHeadingSections(md)

  return md.trimEnd()
}

function stripLegacyClarificationHeadingSections(md: string): string {
  let out = md
  const headingRe = /^##\s+Clarification capture\s*$/im
  while (true) {
    const m = out.match(headingRe)
    if (!m || m.index === undefined) break
    const start = m.index
    const afterHeading = start + m[0].length
    const tail = out.slice(afterHeading)
    const nextH2 = tail.search(/^##\s+/m)
    const end = nextH2 === -1 ? out.length : afterHeading + nextH2
    out = (out.slice(0, start) + out.slice(end)).replace(/\n{3,}/g, '\n\n')
  }
  return out.trimEnd()
}

/**
 * Replace or append the Clarification capture section. Strips any prior clarification regions first.
 */
export function mergeClarificationIntoFoundationBrief(
  markdown: string,
  questions: ClarificationQuestionItem[],
  responses: Record<string, ClarificationResponse>,
): string {
  const block = buildClarificationBlock(questions, responses)
  const stripped = stripClarificationSection(markdown ?? '')
  if (!stripped.trim()) return block
  return `${stripped.trimEnd()}\n\n${block}\n`
}

/**
 * Bump field status for linked FB keys when we have a substantive answer.
 */
export function fieldStatusesAfterClarification(
  prev: Record<string, InterpretationFieldStatus>,
  questions: ClarificationQuestionItem[],
  responses: Record<string, ClarificationResponse>,
): Record<string, InterpretationFieldStatus> {
  const next = { ...prev }
  for (const q of questions) {
    const key = q.foundation_brief_field_key
    if (!key) continue
    const r = responses[q.id]
    if (!r) continue
    const fbKey = `fb_${key}`
    const legacyKey = key
    if (r.kind === 'answered' || r.kind === 'accepted_default') {
      next[fbKey] = 'explicit'
      next[legacyKey] = 'explicit'
    } else if (r.kind === 'unknown') {
      next[fbKey] = 'needs_confirmation'
      next[legacyKey] = 'needs_confirmation'
    }
  }
  return next
}

/**
 * Apply clarification responses to the assumption ledger: one entry per question, upserted by stable id `clarify_${questionId}`.
 */
export function applyResponsesToAssumptionLedger(
  ledger: AssumptionLedgerEntryJson[],
  questions: ClarificationQuestionItem[],
  responses: Record<string, ClarificationResponse>,
): AssumptionLedgerEntryJson[] {
  let out = [...ledger]
  for (const q of questions) {
    const r = responses[q.id]
    if (!r) continue
    const entryId = `clarify_${q.id}`.slice(0, 128)
    const existing = out.find((e) => e.id === entryId)

    let text: string
    let status: AssumptionLedgerEntryJson['status']
    if (r.kind === 'answered') {
      text = `Clarification: ${q.text} → ${outcomeLine(q, r)}`
      status = 'resolved'
    } else if (r.kind === 'skipped') {
      text = `Clarification (pending): ${q.text} — default if skipped: ${q.default_assumption_if_skipped}`
      status = 'open'
    } else if (r.kind === 'unknown') {
      text = `Clarification (unknown): ${q.text}`
      status = 'marked_unknown'
    } else {
      text = `Clarification (accepted default): ${q.text} — ${q.default_assumption_if_skipped}`
      status = 'accepted_system'
    }

    if (existing) {
      out = updateAssumptionEntry(out, entryId, {
        text,
        status,
        source: 'stakeholders',
      })
    } else {
      out = appendAssumptionEntry(out, {
        id: entryId,
        text,
        status,
        source: 'stakeholders',
      })
    }
  }
  return out
}
