/**
 * Deterministic clarification question generation (step 4).
 *
 * Ranking order (highest score first; stable tie-break by field key / text):
 * 1. Foundation Brief field_statuses: `unknown` (score 100) then `needs_confirmation` (80).
 * 2. Section present in Markdown but body empty or placeholder-only (score 60) — keyed by draft field.
 * 3. Interpretation `needs_confirmation` blocks (score 50).
 * 4. Interpretation `unknowns` strings + understanding `knownGaps` lines (score 40).
 *
 * We emit 3–7 questions (or fewer if fewer candidates). IDs are stable hashes from category + key
 * so refresh does not churn keys unnecessarily.
 */

import type { InterpretationPayloadV1 } from './interpretationPayload'
import { FOUNDATION_BRIEF_DRAFT_KEYS, type FoundationBriefDraftKey } from './interpretationPayload'
import type { ClarificationQuestionItem } from './clarificationTypes'
import type { InterpretationFieldStatus } from './wizardDomainTypes'

const MIN_QUESTIONS = 3
const MAX_QUESTIONS = 7

const SECTION_TITLE_BY_KEY: Record<FoundationBriefDraftKey, string> = {
  problem_statement: 'Problem statement',
  desired_outcome: 'Desired outcome',
  target_users_stakeholders: 'Target users / stakeholders',
  scope: 'Scope',
  non_goals: 'Non-goals',
  success_metrics: 'Success metrics',
  constraints: 'Constraints',
  assumptions: 'Assumptions',
  dependencies: 'Dependencies',
  risks: 'Risks',
  open_questions: 'Open questions',
  glossary_key_terms: 'Glossary / key terms',
}

const WHY_BY_KEY: Record<FoundationBriefDraftKey, string> = {
  problem_statement: 'Without a crisp problem, downstream scope and success metrics drift.',
  desired_outcome: 'Outcome clarity drives prioritization and acceptance checks.',
  target_users_stakeholders: 'Who is affected determines constraints and validation.',
  scope: 'Boundary clarity prevents late scope creep and rework.',
  non_goals: 'Explicit non-goals protect capacity and reduce debate.',
  success_metrics: 'Measurable success prevents subjective “done”.',
  constraints: 'Hidden constraints cause failed delivery or compliance gaps.',
  assumptions: 'Wrong assumptions compound; recording them reduces surprise.',
  dependencies: 'Missed dependencies block execution or integration.',
  risks: 'Unowned risks resurface as incidents or delays.',
  open_questions: 'Unresolved questions block commitment and estimates.',
  glossary_key_terms: 'Shared vocabulary avoids misaligned work.',
}

const DEFAULT_SKIP_BY_KEY: Record<FoundationBriefDraftKey, string> = {
  problem_statement: 'Assume the problem is as described in mission and context until disproven.',
  desired_outcome: 'Assume outcomes match the mission statement until refined.',
  target_users_stakeholders: 'Assume primary users are implied by the workspace context.',
  scope: 'Assume scope follows the current roadmap/WBS references when present.',
  non_goals: 'Assume no explicit non-goals beyond “out of scope for this increment”.',
  success_metrics: 'Assume qualitative success until metrics are agreed.',
  constraints: 'Assume standard org engineering constraints apply.',
  assumptions: 'Assume assumptions are captured elsewhere in notes until validated.',
  dependencies: 'Assume dependencies are discovered during planning.',
  risks: 'Assume risks are tracked informally until a formal pass.',
  open_questions: 'Assume open items are non-blocking for the next step.',
  glossary_key_terms: 'Assume terms use plain language from the brief.',
}

export type ClarificationBuilderInput = {
  foundationBriefMarkdown: string
  foundationBriefFieldStatuses: Record<string, InterpretationFieldStatus | string>
  interpretation: InterpretationPayloadV1
  understandingKnownGaps: string
}

function hashId(parts: string[]): string {
  const s = parts.join('|').slice(0, 500)
  let h = 2166136261
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return `cq_${(h >>> 0).toString(16).padStart(8, '0')}`
}

function scoreForFieldStatus(st: string | undefined): number {
  if (st === 'unknown') return 100
  if (st === 'needs_confirmation') return 80
  return 0
}

/** True if `## Title` section exists but has no non-whitespace body (or TBD-only). */
function sectionEmptyForKey(md: string, key: FoundationBriefDraftKey): boolean {
  const title = SECTION_TITLE_BY_KEY[key]
  const re = new RegExp(`^##\\s+${escapeRe(title)}\\s*$`, 'im')
  const m = md.match(re)
  if (!m || m.index === undefined) return false
  const start = m.index + m[0].length
  const rest = md.slice(start)
  const nextHdr = rest.search(/^##\s+/m)
  const chunk = (nextHdr === -1 ? rest : rest.slice(0, nextHdr)).trim()
  if (!chunk) return true
  const tbd = /^(tbd|todo|n\/a|\?)\s*\.?$/i
  return tbd.test(chunk.replace(/\s+/g, ' '))
}

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

type Candidate = {
  score: number
  sortKey: string
  build: () => ClarificationQuestionItem
}

function pushFieldCandidates(input: ClarificationBuilderInput, out: Candidate[]): void {
  const md = input.foundationBriefMarkdown
  const fs = input.foundationBriefFieldStatuses
  for (const key of FOUNDATION_BRIEF_DRAFT_KEYS) {
    const fbKey = `fb_${key}`
    const st = (fs[fbKey] ?? fs[key] ?? '') as string
    let score = scoreForFieldStatus(st)
    if (score === 0 && sectionEmptyForKey(md, key)) {
      score = Math.max(score, 60)
    }
    if (score === 0) continue
    const sortKey = `fb:${key}`
    out.push({
      score,
      sortKey,
      build: () => ({
        id: hashId(['fb', key]),
        text: `Confirm or refine: **${SECTION_TITLE_BY_KEY[key]}**`,
        why_it_matters: WHY_BY_KEY[key],
        answer_type: score >= 80 ? 'short_text' : 'long_text',
        default_assumption_if_skipped: DEFAULT_SKIP_BY_KEY[key],
        foundation_brief_field_key: key,
        priority: score,
      }),
    })
  }
}

function pushInterpretationCandidates(input: ClarificationBuilderInput, out: Candidate[]): void {
  const interp = input.interpretation
  for (const b of interp.needs_confirmation) {
    const t = (b.text ?? '').trim()
    if (!t) continue
    const sortKey = `nc:${b.id}`
    out.push({
      score: 50,
      sortKey,
      build: () => ({
        id: hashId(['nc', b.id]),
        text: `Confirm: ${t.slice(0, 500)}${t.length > 500 ? '…' : ''}`,
        why_it_matters: 'This item was flagged as needing confirmation before proceeding.',
        answer_type: 'yes_no',
        default_assumption_if_skipped: 'Treat as confirmed only for planning; revisit before commit.',
        priority: 50,
      }),
    })
  }
}

function pushGapCandidates(input: ClarificationBuilderInput, out: Candidate[]): void {
  const lines: string[] = []
  for (const u of input.interpretation.unknowns) {
    const t = u.trim()
    if (t) lines.push(t)
  }
  for (const line of input.understandingKnownGaps.split(/\r?\n/)) {
    const t = line.trim()
    if (t) lines.push(t)
  }
  const seen = new Set<string>()
  for (const t of lines) {
    const norm = t.toLowerCase().slice(0, 200)
    if (seen.has(norm)) continue
    seen.add(norm)
    const sortKey = `gap:${norm}`
    out.push({
      score: 40,
      sortKey,
      build: () => ({
        id: hashId(['gap', norm]),
        text: `Resolve gap: ${t.slice(0, 600)}${t.length > 600 ? '…' : ''}`,
        why_it_matters: 'Unresolved gaps reduce artifact quality and cause rework.',
        answer_type: 'short_text',
        default_assumption_if_skipped: 'Defer resolution; capture as an explicit risk in the brief.',
        priority: 40,
      }),
    })
  }
}

/**
 * Build 3–7 prioritized questions. If fewer than 3 candidates exist, returns all (may be 0–2).
 */
export function buildClarificationQuestions(input: ClarificationBuilderInput): ClarificationQuestionItem[] {
  const candidates: Candidate[] = []
  pushFieldCandidates(input, candidates)
  pushInterpretationCandidates(input, candidates)
  pushGapCandidates(input, candidates)

  candidates.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score
    return a.sortKey.localeCompare(b.sortKey)
  })

  const seenId = new Set<string>()
  const picked: ClarificationQuestionItem[] = []
  for (const c of candidates) {
    const q = c.build()
    if (seenId.has(q.id)) continue
    seenId.add(q.id)
    picked.push(q)
    if (picked.length >= MAX_QUESTIONS) break
  }

  if (picked.length >= MIN_QUESTIONS) return picked
  if (picked.length === 0) return []

  /** Pad with generic prompts so the user has at least three when we had partial signal. */
  const padTexts: { text: string; why: string; skip: string }[] = [
    {
      text: 'What single decision, if clarified now, would most reduce rework later?',
      why: 'High-value clarification reduces thrash across the rest of the run.',
      skip: 'Assume no extra high-leverage decisions beyond what is already captured.',
    },
    {
      text: 'Who is the accountable approver for scope changes on this effort?',
      why: 'Ownership prevents stalled decisions and informal churn.',
      skip: 'Assume the mission owner listed in earlier steps is the default approver.',
    },
    {
      text: 'What is the hard deadline or “must not miss” date, if any?',
      why: 'Time bounds drive sequencing and trade-offs.',
      skip: 'Assume no fixed external deadline unless discovered later.',
    },
  ]
  const pad: ClarificationQuestionItem[] = [...picked]
  let n = 0
  while (pad.length < MIN_QUESTIONS && n < padTexts.length) {
    const p = padTexts[n]!
    n += 1
    pad.push({
      id: hashId(['pad', String(n), String(picked.length)]),
      text: p.text,
      why_it_matters: p.why,
      answer_type: 'short_text',
      default_assumption_if_skipped: p.skip,
      priority: 10,
    })
  }
  return pad.slice(0, MAX_QUESTIONS)
}
