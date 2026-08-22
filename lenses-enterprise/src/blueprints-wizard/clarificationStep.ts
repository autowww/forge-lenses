/**
 * Step 4 — Clarification. `session.payload.clarification` → `wizard_domain.prompt_recipe.variables`.
 * Experimental Blueprints Wizard only.
 */

import type {
  ClarificationAnswerType,
  ClarificationQuestionItem,
  ClarificationResponse,
  ClarificationResponseKind,
} from './clarificationTypes'
import {
  CLARIFICATION_ANSWER_TYPES,
  CLARIFICATION_RESPONSE_KINDS,
} from './clarificationTypes'
import { FOUNDATION_BRIEF_DRAFT_KEYS, type FoundationBriefDraftKey } from './interpretationPayload'

export const CLARIFICATION_QUESTIONS_MAX = 8000
export const CLARIFICATION_DECISIONS_MAX = 4000
export const CLARIFICATION_QUESTION_ITEMS_MAX = 7
export const CLARIFICATION_Q_TEXT_MAX = 2000
export const CLARIFICATION_WHY_MAX = 2000
export const CLARIFICATION_DEFAULT_ASSUMPTION_MAX = 4000

export type ClarificationPayloadV1 = {
  /** Open questions (legacy path when `questions` is empty). */
  openQuestions: string
  /** Decisions or approvals still needed (optional). */
  decisionsNeeded?: string
  /** Prioritized clarification questions (3–7 when set). */
  questions: ClarificationQuestionItem[]
  /** Responses keyed by question `id`. */
  responses: Record<string, ClarificationResponse>
}

export function emptyClarificationPayload(): ClarificationPayloadV1 {
  return { openQuestions: '', decisionsNeeded: '', questions: [], responses: {} }
}

function isStr(v: unknown): v is string {
  return typeof v === 'string'
}

function coerceAnswerType(v: unknown): ClarificationAnswerType {
  const s = typeof v === 'string' ? v.trim().toLowerCase().replace(/\s+/g, '_') : ''
  return (CLARIFICATION_ANSWER_TYPES as readonly string[]).includes(s)
    ? (s as ClarificationAnswerType)
    : 'short_text'
}

function coerceFieldKey(v: unknown): FoundationBriefDraftKey | undefined {
  if (typeof v !== 'string') return undefined
  const t = v.trim()
  return (FOUNDATION_BRIEF_DRAFT_KEYS as readonly string[]).includes(t) ? (t as FoundationBriefDraftKey) : undefined
}

function parseChoiceOptions(raw: unknown): { key: string; label: string }[] | undefined {
  if (!Array.isArray(raw)) return undefined
  const out: { key: string; label: string }[] = []
  for (const x of raw.slice(0, 32)) {
    if (!x || typeof x !== 'object' || Array.isArray(x)) continue
    const o = x as Record<string, unknown>
    const key = typeof o.key === 'string' ? o.key.trim().slice(0, 64) : ''
    const label = typeof o.label === 'string' ? o.label.trim().slice(0, 500) : ''
    if (key && label) out.push({ key, label })
  }
  return out.length ? out : undefined
}

export function parseClarificationQuestionItem(raw: unknown): ClarificationQuestionItem | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const o = raw as Record<string, unknown>
  const id = typeof o.id === 'string' ? o.id.trim().slice(0, 128) : ''
  if (!id) return null
  const text = typeof o.text === 'string' ? o.text.slice(0, CLARIFICATION_Q_TEXT_MAX) : ''
  const why_it_matters =
    typeof o.why_it_matters === 'string' ? o.why_it_matters.slice(0, CLARIFICATION_WHY_MAX) : ''
  const default_assumption_if_skipped =
    typeof o.default_assumption_if_skipped === 'string'
      ? o.default_assumption_if_skipped.slice(0, CLARIFICATION_DEFAULT_ASSUMPTION_MAX)
      : ''
  const answer_type = coerceAnswerType(o.answer_type)
  const fk = coerceFieldKey(o.foundation_brief_field_key)
  const priority = typeof o.priority === 'number' && Number.isFinite(o.priority) ? o.priority : 0
  const choice_options = parseChoiceOptions(o.choice_options)
  const q: ClarificationQuestionItem = {
    id,
    text,
    why_it_matters,
    answer_type,
    default_assumption_if_skipped,
    priority,
  }
  if (fk) q.foundation_brief_field_key = fk
  if (choice_options) q.choice_options = choice_options
  return q
}

function parseResponses(raw: unknown): Record<string, ClarificationResponse> {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
  const o = raw as Record<string, unknown>
  const out: Record<string, ClarificationResponse> = {}
  for (const [k, v] of Object.entries(o)) {
    const id = k.trim().slice(0, 128)
    if (!id) continue
    const resp = parseOneResponse(v)
    if (resp) out[id] = resp
  }
  return out
}

function coerceResponseKind(v: unknown): ClarificationResponseKind {
  const s = typeof v === 'string' ? v.trim().toLowerCase().replace(/\s+/g, '_') : ''
  return (CLARIFICATION_RESPONSE_KINDS as readonly string[]).includes(s)
    ? (s as ClarificationResponseKind)
    : 'answered'
}

function parseOneResponse(raw: unknown): ClarificationResponse | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const o = raw as Record<string, unknown>
  const kind = coerceResponseKind(o.kind)
  const value = typeof o.value === 'string' ? o.value.slice(0, CLARIFICATION_QUESTIONS_MAX) : undefined
  const choice_key = typeof o.choice_key === 'string' ? o.choice_key.slice(0, 64) : undefined
  const r: ClarificationResponse = { kind }
  if (value !== undefined && value.length) r.value = value
  if (choice_key !== undefined && choice_key.length) r.choice_key = choice_key
  return r
}

export function parseClarificationFromPayload(payload: Record<string, unknown>): ClarificationPayloadV1 {
  const raw = payload.clarification
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return emptyClarificationPayload()
  }
  const o = raw as Record<string, unknown>
  const openQuestions = isStr(o.openQuestions) ? o.openQuestions : ''
  const decisionsNeeded = isStr(o.decisionsNeeded) ? o.decisionsNeeded : ''
  const questionsRaw = o.questions
  const questions: ClarificationQuestionItem[] = []
  if (Array.isArray(questionsRaw)) {
    for (const q of questionsRaw.slice(0, CLARIFICATION_QUESTION_ITEMS_MAX)) {
      const p = parseClarificationQuestionItem(q)
      if (p) questions.push(p)
    }
  }
  const responses = parseResponses(o.responses)
  return {
    openQuestions: openQuestions.slice(0, CLARIFICATION_QUESTIONS_MAX),
    decisionsNeeded: decisionsNeeded.slice(0, CLARIFICATION_DECISIONS_MAX),
    questions,
    responses,
  }
}

/** When `payload.clarification` is absent, seed from `prompt_recipe.variables` (domain-only sessions). */
export function clarificationFromPayloadOrRecipe(
  payload: Record<string, unknown>,
  variables: Record<string, string>,
): ClarificationPayloadV1 {
  if (payload.clarification && typeof payload.clarification === 'object' && !Array.isArray(payload.clarification)) {
    return clampClarificationPayload(parseClarificationFromPayload(payload))
  }
  const oq = variables.clarification_open_questions ?? ''
  const dn = variables.clarification_decisions_needed ?? ''
  if (oq.trim() || dn.trim()) {
    return clampClarificationPayload({ openQuestions: oq, decisionsNeeded: dn, questions: [], responses: {} })
  }
  return emptyClarificationPayload()
}

export type ClarificationFieldErrors = {
  openQuestions?: string
  decisionsNeeded?: string
  questions?: string
  responses?: string
}

export function validateClarificationForNext(c: ClarificationPayloadV1): {
  ok: boolean
  errors: ClarificationFieldErrors
} {
  const errors: ClarificationFieldErrors = {}
  const d = (c.decisionsNeeded ?? '').trim()
  if (d.length > CLARIFICATION_DECISIONS_MAX) {
    errors.decisionsNeeded = `Decisions field must be at most ${CLARIFICATION_DECISIONS_MAX} characters.`
  }

  const qs = c.questions ?? []
  if (qs.length > 0) {
    for (const q of qs) {
      const r = c.responses[q.id]
      if (!r || !r.kind) {
        errors.responses = 'Answer, skip, mark unknown, or accept the default for each question.'
        break
      }
      if (r.kind === 'answered') {
        const hasChoice = q.answer_type === 'single_choice' && (q.choice_options?.length ?? 0) > 0
        if (hasChoice) {
          if (!r.choice_key?.trim()) {
            errors.responses = 'Select an option or choose another response for each question.'
            break
          }
        } else if (q.answer_type === 'yes_no') {
          const v = (r.value ?? '').trim().toLowerCase()
          if (v !== 'yes' && v !== 'no') {
            errors.responses = 'Choose Yes or No, or use skip / unknown / accept default.'
            break
          }
        } else if (!(r.value ?? '').trim()) {
          errors.responses = 'Provide an answer or choose skip / unknown / accept default.'
          break
        }
      }
    }
    if (!errors.responses && c.openQuestions.length > CLARIFICATION_QUESTIONS_MAX) {
      errors.openQuestions = `Notes must be at most ${CLARIFICATION_QUESTIONS_MAX} characters.`
    }
    return { ok: Object.keys(errors).length === 0, errors }
  }

  const q = c.openQuestions.trim()
  if (!q) {
    errors.openQuestions = 'List questions that still need answers or confirmation.'
  } else if (q.length > CLARIFICATION_QUESTIONS_MAX) {
    errors.openQuestions = `Questions must be at most ${CLARIFICATION_QUESTIONS_MAX} characters.`
  }
  return { ok: Object.keys(errors).length === 0, errors }
}

export function clampClarificationPayload(c: ClarificationPayloadV1): ClarificationPayloadV1 {
  const questions = (c.questions ?? [])
    .slice(0, CLARIFICATION_QUESTION_ITEMS_MAX)
    .map((q) => parseClarificationQuestionItem(q))
    .filter((x): x is ClarificationQuestionItem => x !== null)
  const responsesIn = c.responses ?? {}
  const responses: Record<string, ClarificationResponse> = {}
  const idSet = new Set(questions.map((q) => q.id))
  for (const [k, v] of Object.entries(responsesIn)) {
    if (!idSet.has(k)) continue
    const r = parseOneResponse(v)
    if (r) responses[k] = r
  }
  return {
    openQuestions: c.openQuestions.slice(0, CLARIFICATION_QUESTIONS_MAX),
    decisionsNeeded: (c.decisionsNeeded ?? '').slice(0, CLARIFICATION_DECISIONS_MAX),
    questions,
    responses,
  }
}

export function formatClarificationForStepNote(c: ClarificationPayloadV1): string {
  const lines: string[] = []
  const qs = c.questions ?? []
  if (qs.length > 0) {
    for (const q of qs) {
      const r = (c.responses ?? {})[q.id]
      const tag = r ? `${r.kind}${r.value ? `: ${r.value}` : ''}` : 'pending'
      lines.push(`Q: ${q.text} [${tag}]`)
    }
  }
  const q = c.openQuestions.trim()
  const d = (c.decisionsNeeded ?? '').trim()
  if (q) lines.push(`Open questions: ${q}`)
  if (d) lines.push(`Decisions needed: ${d}`)
  return lines.join('\n\n')
}
