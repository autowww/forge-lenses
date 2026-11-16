/**
 * Step 2 — Context Intake. Stored at `session.payload.contextIntake` (v1).
 * Experimental Blueprints Wizard only.
 */

import type { ContextSource } from './wizardDomainTypes'

export const CONTEXT_ROUGH_MAX = 8000
export const CONTEXT_REFERENCE_HINTS_MAX = 4000
export const CONTEXT_LEGACY_SOURCES_MAX = 800
export const CONTEXT_LEGACY_SUMMARY_MAX = 8000
export const CONTEXT_NOTES_MAX = 8000

export type ContextSourceFlagsV1 = {
  pastedPrompt: boolean
  existingDocs: boolean
  repoSummary: boolean
  ticketsBacklog: boolean
}

export type ContextAttachmentRefV1 = {
  kind: 'wbs' | 'doc' | 'repo' | 'ticket' | 'other'
  label: string
  ref?: string
}

/** Canonical JSON under `WizardSessionDocument.payload.contextIntake`. */
export type ContextIntakePayloadV1 = {
  /** Primary free-text context. */
  roughNotes: string
  /** Which intake channels apply (drives `wizard_domain.context_sources`). */
  sourceFlags: ContextSourceFlagsV1
  /** Ticket IDs, doc paths, links, or backlog pointers. */
  referenceHints: string
  /** Optional structured refs (e.g. WBS path picked from workspace). */
  attachments: ContextAttachmentRefV1[]
}

export function emptyContextSourceFlags(): ContextSourceFlagsV1 {
  return {
    pastedPrompt: false,
    existingDocs: false,
    repoSummary: false,
    ticketsBacklog: false,
  }
}

export function emptyContextIntakePayload(): ContextIntakePayloadV1 {
  return {
    roughNotes: '',
    sourceFlags: emptyContextSourceFlags(),
    referenceHints: '',
    attachments: [],
  }
}

function isNonEmptyString(v: unknown): v is string {
  return typeof v === 'string'
}

function parseAttachment(raw: unknown): ContextAttachmentRefV1 | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const o = raw as Record<string, unknown>
  const kindRaw = o.kind
  const label = isNonEmptyString(o.label) ? o.label.slice(0, 500) : ''
  if (!label) return null
  const kind =
    kindRaw === 'wbs' || kindRaw === 'doc' || kindRaw === 'repo' || kindRaw === 'ticket' || kindRaw === 'other'
      ? kindRaw
      : 'other'
  const ref = o.ref !== undefined && isNonEmptyString(o.ref) ? o.ref.slice(0, 2000) : undefined
  return { kind, label, ref }
}

function parseFlags(raw: unknown): ContextSourceFlagsV1 {
  const d = emptyContextSourceFlags()
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return d
  const o = raw as Record<string, unknown>
  return {
    pastedPrompt: Boolean(o.pastedPrompt),
    existingDocs: Boolean(o.existingDocs),
    repoSummary: Boolean(o.repoSummary),
    ticketsBacklog: Boolean(o.ticketsBacklog),
  }
}

/** Maps intake flags to `wizard_domain.context_sources` enum values. */
export function deriveContextSourcesFromIntake(intake: ContextIntakePayloadV1): ContextSource[] {
  const f = intake.sourceFlags
  const out: ContextSource[] = []
  if (f.pastedPrompt) out.push('other')
  if (f.existingDocs) out.push('docs')
  if (f.repoSummary) out.push('repo')
  if (f.ticketsBacklog) out.push('tickets')
  return [...new Set(out)]
}

/** Merge helper: prefer structured flags; fall back to rough notes → `other`. */
export function contextSourcesForWizardDomain(
  intake: ContextIntakePayloadV1,
  previous: readonly ContextSource[] | undefined,
): ContextSource[] {
  const fromFlags = deriveContextSourcesFromIntake(intake)
  if (fromFlags.length > 0) return fromFlags
  if (intake.roughNotes.trim().length > 0) return ['other']
  if (previous && previous.length > 0) return [...previous]
  return []
}

export function parseContextIntakeFromPayload(payload: Record<string, unknown>): ContextIntakePayloadV1 {
  const raw = payload.contextIntake
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return emptyContextIntakePayload()
  }
  const o = raw as Record<string, unknown>

  if ('roughNotes' in o || 'sourceFlags' in o || 'attachments' in o || 'referenceHints' in o) {
    const roughNotes = isNonEmptyString(o.roughNotes) ? o.roughNotes : ''
    const referenceHints = isNonEmptyString(o.referenceHints) ? o.referenceHints : ''
    const att: ContextAttachmentRefV1[] = []
    if (Array.isArray(o.attachments)) {
      for (const a of o.attachments) {
        const p = parseAttachment(a)
        if (p) att.push(p)
      }
    }
    return {
      roughNotes: roughNotes.slice(0, CONTEXT_ROUGH_MAX),
      sourceFlags: parseFlags(o.sourceFlags),
      referenceHints: referenceHints.slice(0, CONTEXT_REFERENCE_HINTS_MAX),
      attachments: att,
    }
  }

  const sources = isNonEmptyString(o.sources) ? o.sources : ''
  const summary = isNonEmptyString(o.summary) ? o.summary : ''
  const notes = isNonEmptyString(o.notes) ? o.notes : ''
  const legacyRough = [sources.trim(), summary.trim(), notes.trim()].filter(Boolean).join('\n\n')
  return {
    roughNotes: legacyRough.slice(0, CONTEXT_ROUGH_MAX),
    sourceFlags: emptyContextSourceFlags(),
    referenceHints: '',
    attachments: [],
  }
}

export type ContextIntakeFieldErrors = {
  roughNotes?: string
  referenceHints?: string
  notes?: string
}

/** Require rough notes OR (≥1 source flag and non-empty reference hints). */
export function validateContextIntakeForNext(
  x: ContextIntakePayloadV1,
): { ok: boolean; errors: ContextIntakeFieldErrors } {
  const errors: ContextIntakeFieldErrors = {}
  const rough = x.roughNotes.trim()
  const hints = x.referenceHints.trim()
  const anyFlag =
    x.sourceFlags.pastedPrompt ||
    x.sourceFlags.existingDocs ||
    x.sourceFlags.repoSummary ||
    x.sourceFlags.ticketsBacklog

  if (!rough && !(anyFlag && hints)) {
    errors.roughNotes =
      'Add rough notes, or turn on at least one context source and add references (tickets, paths, or links).'
  } else if (rough.length > CONTEXT_ROUGH_MAX) {
    errors.roughNotes = `Rough notes must be at most ${CONTEXT_ROUGH_MAX} characters.`
  }

  if (hints.length > CONTEXT_REFERENCE_HINTS_MAX) {
    errors.referenceHints = `References must be at most ${CONTEXT_REFERENCE_HINTS_MAX} characters.`
  }

  return { ok: Object.keys(errors).length === 0, errors }
}

export function clampContextIntakePayload(x: ContextIntakePayloadV1): ContextIntakePayloadV1 {
  const att = (x.attachments ?? []).slice(0, 32).map((a) => ({
    kind: a.kind,
    label: a.label.slice(0, 500),
    ref: a.ref?.slice(0, 2000),
  }))
  return {
    roughNotes: x.roughNotes.slice(0, CONTEXT_ROUGH_MAX),
    sourceFlags: {
      pastedPrompt: Boolean(x.sourceFlags?.pastedPrompt),
      existingDocs: Boolean(x.sourceFlags?.existingDocs),
      repoSummary: Boolean(x.sourceFlags?.repoSummary),
      ticketsBacklog: Boolean(x.sourceFlags?.ticketsBacklog),
    },
    referenceHints: x.referenceHints.slice(0, CONTEXT_REFERENCE_HINTS_MAX),
    attachments: att,
  }
}

export function formatContextIntakeForStepNote(x: ContextIntakePayloadV1): string {
  const lines: string[] = []
  const rough = x.roughNotes.trim()
  const hints = x.referenceHints.trim()
  const f = x.sourceFlags
  const flagsOn = [
    f.pastedPrompt && 'pasted/notes',
    f.existingDocs && 'docs/artifacts',
    f.repoSummary && 'repo summary',
    f.ticketsBacklog && 'tickets/backlog',
  ].filter(Boolean) as string[]
  if (flagsOn.length) lines.push(`Sources: ${flagsOn.join(', ')}`)
  if (rough) lines.push(`Rough notes: ${rough}`)
  if (hints) lines.push(`References: ${hints}`)
  if (x.attachments?.length) {
    lines.push(
      `Attached: ${x.attachments.map((a) => (a.ref ? `${a.label} (${a.ref})` : a.label)).join('; ')}`,
    )
  }
  return lines.join('\n\n')
}
