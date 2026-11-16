/**
 * Step 1 — Contribution Setup. Stored at `session.payload.contributionSetup` (v1).
 * Scale is persisted via `wizard_domain.contribution_setup_kind`; optional text fields are legacy / extra detail.
 * Experimental Blueprints Wizard only.
 */

import type { ContributionSetupKind } from './wizardDomainTypes'

export const CONTRIBUTION_DELIVERABLE_MAX = 400
export const CONTRIBUTION_LANDING_MAX = 800
export const CONTRIBUTION_NOTES_MAX = 8000

/** Canonical JSON under `WizardSessionDocument.payload.contributionSetup`. */
export type ContributionSetupPayloadV1 = {
  /** Optional — artifact or pack name (legacy / extra). */
  deliverable?: string
  /** Optional — where it lands (legacy / extra). */
  landingPlace?: string
  /** Optional detail for reviewers or refine. */
  notes?: string
}

export function emptyContributionSetupPayload(): ContributionSetupPayloadV1 {
  return { deliverable: '', landingPlace: '', notes: '' }
}

function isNonEmptyString(v: unknown): v is string {
  return typeof v === 'string'
}

export function parseContributionSetupFromPayload(payload: Record<string, unknown>): ContributionSetupPayloadV1 {
  const raw = payload.contributionSetup
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return emptyContributionSetupPayload()
  }
  const o = raw as Record<string, unknown>
  const deliverable = isNonEmptyString(o.deliverable) ? o.deliverable : ''
  const landingPlace = isNonEmptyString(o.landingPlace) ? o.landingPlace : ''
  const notes = isNonEmptyString(o.notes) ? o.notes : ''
  return {
    deliverable: deliverable.slice(0, CONTRIBUTION_DELIVERABLE_MAX),
    landingPlace: landingPlace.slice(0, CONTRIBUTION_LANDING_MAX),
    notes: notes.slice(0, CONTRIBUTION_NOTES_MAX),
  }
}

export type ContributionSetupFieldErrors = {
  deliverable?: string
  landingPlace?: string
  notes?: string
}

/** Next requires only valid field lengths; scale is `contributionSetupKind` on shell. */
export function validateContributionSetupForNext(
  c: ContributionSetupPayloadV1,
): { ok: boolean; errors: ContributionSetupFieldErrors } {
  const errors: ContributionSetupFieldErrors = {}
  const d = (c.deliverable ?? '').trim()
  const l = (c.landingPlace ?? '').trim()

  if (d.length > CONTRIBUTION_DELIVERABLE_MAX) {
    errors.deliverable = `Deliverable must be at most ${CONTRIBUTION_DELIVERABLE_MAX} characters.`
  }

  if (l.length > CONTRIBUTION_LANDING_MAX) {
    errors.landingPlace = `Landing place must be at most ${CONTRIBUTION_LANDING_MAX} characters.`
  }

  const rawNotes = c.notes ?? ''
  if (rawNotes.length > CONTRIBUTION_NOTES_MAX) {
    errors.notes = `Notes must be at most ${CONTRIBUTION_NOTES_MAX} characters.`
  }

  return { ok: Object.keys(errors).length === 0, errors }
}

export function clampContributionSetupPayload(c: ContributionSetupPayloadV1): ContributionSetupPayloadV1 {
  return {
    deliverable: (c.deliverable ?? '').slice(0, CONTRIBUTION_DELIVERABLE_MAX),
    landingPlace: (c.landingPlace ?? '').slice(0, CONTRIBUTION_LANDING_MAX),
    notes: (c.notes ?? '').slice(0, CONTRIBUTION_NOTES_MAX),
  }
}

const KIND_LABEL: Record<ContributionSetupKind, string> = {
  single: 'Single',
  team: 'Team',
  teams: 'Teams',
  enterprise: 'Enterprise',
}

/** Flatten into stepNotes["1"] for refine and legacy readers. */
export function formatContributionSetupForStepNote(
  c: ContributionSetupPayloadV1,
  kind: ContributionSetupKind,
): string {
  const lines: string[] = []
  lines.push(`Contribution scale: ${KIND_LABEL[kind] ?? kind}`)
  const d = (c.deliverable ?? '').trim()
  const l = (c.landingPlace ?? '').trim()
  const n = (c.notes ?? '').trim()
  if (d) lines.push(`Deliverable: ${d}`)
  if (l) lines.push(`Landing place: ${l}`)
  if (n) lines.push(`Notes: ${n}`)
  return lines.join('\n\n')
}
