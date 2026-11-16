/**
 * Render `payload.interpretation.foundation_brief_draft` to Markdown for
 * `wizard_domain.foundation_brief.markdown` without calling an LLM.
 *
 * Merge rules (when both Refine output and interpretation exist):
 * - **Sync** replaces the entire Markdown body with this render; it does not append or
 *   three-way-merge with prior LLM text. The Studio shows a two-column preview before overwrite
 *   when current Markdown is non-empty.
 * - **field_statuses**: Per-section keys `fb_<draftKey>` mirror each draft section’s provenance.
 *   Keys `foundation_brief_markdown_source` = `explicit` and `llm_foundation_brief` = `unknown`
 *   record that the visible Markdown no longer reflects a pure LLM Refine run.
 */

import {
  FOUNDATION_BRIEF_DRAFT_KEYS,
  type FoundationBriefDraftKey,
  type FoundationBriefDraftSection,
} from './interpretationPayload'
import { normalizeWizardDomain } from './wizardDomainNormalize'
import type { InterpretationFieldStatus } from './wizardDomainTypes'

/**
 * Text shown in Refine / preview: prefer `wizard_domain.foundation_brief.markdown`, else legacy
 * `payload.foundation_brief` when it is a non-empty string.
 */
export function effectiveFoundationBriefMarkdown(payload: Record<string, unknown>): string {
  const wd = normalizeWizardDomain(payload.wizard_domain)
  const dm = (wd.foundation_brief.markdown ?? '').trim()
  if (dm) return wd.foundation_brief.markdown ?? ''
  const leg = payload.foundation_brief
  if (typeof leg === 'string' && leg.trim()) return leg
  return ''
}

const SECTION_TITLES: Record<FoundationBriefDraftKey, string> = {
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

export function foundationBriefDraftHasRenderableContent(
  draft: Record<FoundationBriefDraftKey, FoundationBriefDraftSection>,
): boolean {
  return FOUNDATION_BRIEF_DRAFT_KEYS.some((k) => (draft[k]?.text ?? '').trim().length > 0)
}

/** Markdown suitable for `foundation_brief.markdown` (clamped by normalize later). */
export function renderFoundationBriefDraftToMarkdown(
  draft: Record<FoundationBriefDraftKey, FoundationBriefDraftSection>,
): string {
  const lines: string[] = [
    '# Foundation Brief',
    '',
    '_This Markdown was generated from the structured interpretation draft (sync), not from LLM Refine._',
    '',
  ]
  for (const key of FOUNDATION_BRIEF_DRAFT_KEYS) {
    const sec = draft[key]
    const body = (sec?.text ?? '').trim()
    if (!body) continue
    const title = SECTION_TITLES[key]
    lines.push(`## ${title}`, '', body, '')
  }
  return lines.join('\n').trimEnd()
}

/**
 * Merge field status map after a structured-draft sync: per-section keys plus provenance for
 * the Markdown blob vs. prior LLM refine.
 */
export function fieldStatusesAfterInterpretationSync(
  existing: Record<string, InterpretationFieldStatus>,
  draft: Record<FoundationBriefDraftKey, FoundationBriefDraftSection>,
): Record<string, InterpretationFieldStatus> {
  const next: Record<string, InterpretationFieldStatus> = { ...existing }
  for (const key of FOUNDATION_BRIEF_DRAFT_KEYS) {
    next[`fb_${key}`] = draft[key]?.status ?? 'unknown'
  }
  next.foundation_brief_markdown_source = 'explicit'
  next.llm_foundation_brief = 'unknown'
  return next
}
