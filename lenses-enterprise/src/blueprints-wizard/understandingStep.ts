/**
 * Step 3 — Understanding. `session.payload.understanding` → `wizard_domain.scope_spec.summary` / `constraints_note`.
 * Experimental Blueprints Wizard only.
 */

export const UNDERSTANDING_SUMMARY_MAX = 8000
export const UNDERSTANDING_GAPS_MAX = 8000

export type UnderstandingPayloadV1 = {
  /** What you believe is true about the problem space (required to advance). */
  summary: string
  /** Gaps, risks, or unknowns (optional; maps to scope constraints note). */
  knownGaps?: string
}

export function emptyUnderstandingPayload(): UnderstandingPayloadV1 {
  return { summary: '', knownGaps: '' }
}

function isStr(v: unknown): v is string {
  return typeof v === 'string'
}

export function parseUnderstandingFromPayload(payload: Record<string, unknown>): UnderstandingPayloadV1 {
  const raw = payload.understanding
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return emptyUnderstandingPayload()
  }
  const o = raw as Record<string, unknown>
  const summary = isStr(o.summary) ? o.summary : ''
  const knownGaps = isStr(o.knownGaps) ? o.knownGaps : ''
  return {
    summary: summary.slice(0, UNDERSTANDING_SUMMARY_MAX),
    knownGaps: knownGaps.slice(0, UNDERSTANDING_GAPS_MAX),
  }
}

/** When `payload.understanding` is absent, seed from `scope_spec` (legacy / domain-only sessions). */
export function understandingFromPayloadOrScope(
  payload: Record<string, unknown>,
  scopeSummary: string,
  constraintsNote: string,
): UnderstandingPayloadV1 {
  if (payload.understanding && typeof payload.understanding === 'object' && !Array.isArray(payload.understanding)) {
    return clampUnderstandingPayload(parseUnderstandingFromPayload(payload))
  }
  const s = scopeSummary.trim()
  const c = constraintsNote.trim()
  if (s || c) {
    return clampUnderstandingPayload({ summary: s, knownGaps: c })
  }
  return emptyUnderstandingPayload()
}

export type UnderstandingFieldErrors = {
  summary?: string
  knownGaps?: string
}

export function validateUnderstandingForNext(u: UnderstandingPayloadV1): {
  ok: boolean
  errors: UnderstandingFieldErrors
} {
  const errors: UnderstandingFieldErrors = {}
  const s = u.summary.trim()
  if (!s) {
    errors.summary = 'Summarize what you understand so far about the problem and constraints.'
  } else if (s.length > UNDERSTANDING_SUMMARY_MAX) {
    errors.summary = `Summary must be at most ${UNDERSTANDING_SUMMARY_MAX} characters.`
  }
  const g = (u.knownGaps ?? '').trim()
  if (g.length > UNDERSTANDING_GAPS_MAX) {
    errors.knownGaps = `Known gaps must be at most ${UNDERSTANDING_GAPS_MAX} characters.`
  }
  return { ok: Object.keys(errors).length === 0, errors }
}

export function clampUnderstandingPayload(u: UnderstandingPayloadV1): UnderstandingPayloadV1 {
  return {
    summary: u.summary.slice(0, UNDERSTANDING_SUMMARY_MAX),
    knownGaps: (u.knownGaps ?? '').slice(0, UNDERSTANDING_GAPS_MAX),
  }
}

export function formatUnderstandingForStepNote(u: UnderstandingPayloadV1): string {
  const lines: string[] = []
  const s = u.summary.trim()
  const g = (u.knownGaps ?? '').trim()
  if (s) lines.push(`Understanding: ${s}`)
  if (g) lines.push(`Gaps / unknowns: ${g}`)
  return lines.join('\n\n')
}
