/**
 * Structured clarification questions (Blueprints Wizard step 4, experimental).
 * Aligned with merge + ledger helpers; optional LLM only augments the question list server-side.
 */

import type { FoundationBriefDraftKey } from './interpretationPayload'

export const CLARIFICATION_ANSWER_TYPES = [
  'short_text',
  'long_text',
  'yes_no',
  'single_choice',
] as const
export type ClarificationAnswerType = (typeof CLARIFICATION_ANSWER_TYPES)[number]

export type ClarificationQuestionItem = {
  id: string
  text: string
  why_it_matters: string
  answer_type: ClarificationAnswerType
  /** Shown when the user skips or accepts the default without answering. */
  default_assumption_if_skipped: string
  foundation_brief_field_key?: FoundationBriefDraftKey
  /** Higher = asked first (deterministic rank). */
  priority: number
  /** For `single_choice`: option value keys. */
  choice_options?: { key: string; label: string }[]
}

export const CLARIFICATION_RESPONSE_KINDS = [
  'answered',
  'skipped',
  'unknown',
  'accepted_default',
] as const
export type ClarificationResponseKind = (typeof CLARIFICATION_RESPONSE_KINDS)[number]

export type ClarificationResponse = {
  kind: ClarificationResponseKind
  value?: string
  choice_key?: string
}
