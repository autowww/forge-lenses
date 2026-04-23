/**
 * `payload.interpretation` — Blueprints Wizard experimental, v1.
 * Keep aligned with `lenses/blueprints_wizard/interpretation_normalize.py`.
 */

import type { InterpretationFieldStatus } from './wizardDomainTypes'
import { INTERPRETATION_FIELD_STATUSES } from './wizardDomainTypes'

export const FOUNDATION_BRIEF_DRAFT_KEYS = [
  'problem_statement',
  'desired_outcome',
  'target_users_stakeholders',
  'scope',
  'non_goals',
  'success_metrics',
  'constraints',
  'assumptions',
  'dependencies',
  'risks',
  'open_questions',
  'glossary_key_terms',
] as const

export type FoundationBriefDraftKey = (typeof FOUNDATION_BRIEF_DRAFT_KEYS)[number]

export type InterpretationBlock = {
  id: string
  text: string
  status: InterpretationFieldStatus
  confidence?: number
}

export type FoundationBriefDraftSection = {
  text: string
  status: InterpretationFieldStatus
  confidence?: number
}

export type InterpretationPayloadV1 = {
  schema_version: number
  what_user_said: string
  inferred: InterpretationBlock[]
  needs_confirmation: InterpretationBlock[]
  unknowns: string[]
  foundation_brief_draft: Record<FoundationBriefDraftKey, FoundationBriefDraftSection>
  updated_at?: string
}

const MAX_WHAT = 32_000
const MAX_BLOCK = 16_000
const MAX_UNKNOWN_ITEM = 8_000
const MAX_FOUNDATION = 24_000

function coerceStatus(v: unknown): InterpretationFieldStatus {
  const s = typeof v === 'string' ? v : ''
  return (INTERPRETATION_FIELD_STATUSES as readonly string[]).includes(s)
    ? (s as InterpretationFieldStatus)
    : 'unknown'
}

function clampConf(v: unknown): number | undefined {
  if (v === null || v === undefined) return undefined
  const n = Number(v)
  if (Number.isNaN(n)) return undefined
  return Math.max(0, Math.min(1, n))
}

function normalizeBlock(raw: unknown): InterpretationBlock | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const o = raw as Record<string, unknown>
  const id = typeof o.id === 'string' ? o.id.trim().slice(0, 256) : ''
  if (!id) return null
  const text = typeof o.text === 'string' ? o.text.slice(0, MAX_BLOCK) : ''
  const b: InterpretationBlock = {
    id,
    text,
    status: coerceStatus(o.status),
  }
  const c = clampConf(o.confidence)
  if (c !== undefined) b.confidence = c
  return b
}

function normalizeBlocks(raw: unknown): InterpretationBlock[] {
  if (!Array.isArray(raw)) return []
  const out: InterpretationBlock[] = []
  for (const item of raw.slice(0, 256)) {
    const b = normalizeBlock(item)
    if (b) out.push(b)
  }
  return out
}

function normalizeUnknowns(raw: unknown): string[] {
  if (!Array.isArray(raw)) return []
  const out: string[] = []
  for (const item of raw.slice(0, 64)) {
    if (typeof item === 'string' && item.trim()) {
      out.push(item.trim().slice(0, MAX_UNKNOWN_ITEM))
    }
  }
  return out
}

function normalizeFoundationSection(raw: unknown): FoundationBriefDraftSection {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return { text: '', status: 'unknown' }
  }
  const o = raw as Record<string, unknown>
  const text = typeof o.text === 'string' ? o.text.slice(0, MAX_FOUNDATION) : ''
  const sec: FoundationBriefDraftSection = {
    text,
    status: coerceStatus(o.status),
  }
  const c = clampConf(o.confidence)
  if (c !== undefined) sec.confidence = c
  return sec
}

function normalizeFoundationDraft(raw: unknown): Record<FoundationBriefDraftKey, FoundationBriefDraftSection> {
  const o = raw && typeof raw === 'object' && !Array.isArray(raw) ? (raw as Record<string, unknown>) : {}
  const out = {} as Record<FoundationBriefDraftKey, FoundationBriefDraftSection>
  for (const k of FOUNDATION_BRIEF_DRAFT_KEYS) {
    out[k] = normalizeFoundationSection(o[k])
  }
  return out
}

export function emptyInterpretationPayload(): InterpretationPayloadV1 {
  return {
    schema_version: 1,
    what_user_said: '',
    inferred: [],
    needs_confirmation: [],
    unknowns: [],
    foundation_brief_draft: normalizeFoundationDraft({}),
  }
}

export function parseInterpretationFromPayload(payload: Record<string, unknown>): InterpretationPayloadV1 {
  const raw = payload.interpretation
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return emptyInterpretationPayload()
  }
  const o = raw as Record<string, unknown>
  const sv = o.schema_version
  let schema_version = 1
  if (typeof sv === 'number' && Number.isFinite(sv)) schema_version = Math.max(1, Math.min(99, Math.floor(sv)))
  else if (typeof sv === 'string' && /^\d+$/.test(sv)) schema_version = Math.max(1, Math.min(99, parseInt(sv, 10)))

  const base = emptyInterpretationPayload()
  const what =
    typeof o.what_user_said === 'string' ? o.what_user_said.slice(0, MAX_WHAT) : base.what_user_said
  const ua = o.updated_at
  const updated_at = typeof ua === 'string' && ua.trim() ? ua.trim().slice(0, 64) : undefined

  const parsed: InterpretationPayloadV1 = {
    schema_version,
    what_user_said: what,
    inferred: normalizeBlocks(o.inferred),
    needs_confirmation: normalizeBlocks(o.needs_confirmation),
    unknowns: normalizeUnknowns(o.unknowns),
    foundation_brief_draft: normalizeFoundationDraft(o.foundation_brief_draft),
  }
  if (updated_at !== undefined) parsed.updated_at = updated_at
  return parsed
}

export function clampInterpretationPayload(i: InterpretationPayloadV1): InterpretationPayloadV1 {
  if (!i || typeof i !== 'object') {
    return emptyInterpretationPayload()
  }
  const draftIn = i.foundation_brief_draft ?? {}
  const fd = {} as Record<FoundationBriefDraftKey, FoundationBriefDraftSection>
  for (const k of FOUNDATION_BRIEF_DRAFT_KEYS) {
    const s = draftIn[k] ?? { text: '', status: 'unknown' as const }
    const c = clampConf(s.confidence)
    const sec: FoundationBriefDraftSection = {
      text: (s.text ?? '').slice(0, MAX_FOUNDATION),
      status: coerceStatus(s.status),
    }
    if (c !== undefined) sec.confidence = c
    fd[k] = sec
  }
  const out: InterpretationPayloadV1 = {
    schema_version: Math.max(1, Math.min(99, i.schema_version || 1)),
    what_user_said: (i.what_user_said ?? '').slice(0, MAX_WHAT),
    inferred: normalizeBlocks(i.inferred),
    needs_confirmation: normalizeBlocks(i.needs_confirmation),
    unknowns: normalizeUnknowns(i.unknowns),
    foundation_brief_draft: fd,
  }
  if (i.updated_at !== undefined) {
    out.updated_at = i.updated_at.slice(0, 64)
  }
  return out
}
