/**
 * Step 0 — Mission. Stored on the server at `session.payload.mission` (v1 shape).
 * Experimental Blueprints Wizard only.
 */

import type { MissionType } from './wizardDomainTypes'

export const MISSION_TITLE_MAX = 200
export const MISSION_OUTCOME_MAX = 8000
export const MISSION_NOTES_MAX = 8000

/** Wizard-facing modes (distinct from domain `MissionType`). */
export const MISSION_MODES = [
  'start_from_idea',
  'assess_current_project',
  'resume_advance',
  'repair_stage',
] as const
export type MissionMode = (typeof MISSION_MODES)[number]

export const MISSION_MODE_OPTIONS: ReadonlyArray<{
  value: MissionMode
  label: string
  description: string
}> = [
  {
    value: 'start_from_idea',
    label: 'Start from idea',
    description: 'Shape something new from a rough concept or opportunity.',
  },
  {
    value: 'assess_current_project',
    label: 'Assess current project',
    description: 'Review how an existing effort is doing and what to change.',
  },
  {
    value: 'resume_advance',
    label: 'Resume and advance',
    description: 'Pick up prior wizard or blueprint work and move it forward.',
  },
  {
    value: 'repair_stage',
    label: 'Repair a stage',
    description: 'Fix a stuck gate, artifact, or methodology slice without restarting.',
  },
]

/** Maps wizard mode to persisted `wizard_domain.mission_type` (Forge domain enum). */
export function missionModeToMissionType(mode: MissionMode): MissionType {
  switch (mode) {
    case 'start_from_idea':
      return 'explore'
    case 'assess_current_project':
      return 'define'
    case 'resume_advance':
      return 'deliver'
    case 'repair_stage':
      return 'operate'
    default:
      return 'explore'
  }
}

/** Best-effort inverse when `payload.mission.mode` is absent (legacy sessions). */
export function missionTypeToMissionMode(t: MissionType | string): MissionMode {
  switch (t) {
    case 'explore':
      return 'start_from_idea'
    case 'define':
      return 'assess_current_project'
    case 'deliver':
      return 'resume_advance'
    case 'operate':
      return 'repair_stage'
    case 'sunset':
    default:
      return 'start_from_idea'
  }
}

function isMissionMode(v: unknown): v is MissionMode {
  return typeof v === 'string' && (MISSION_MODES as readonly string[]).includes(v)
}

/** Canonical JSON shape under `WizardSessionDocument.payload.mission`. */
export type MissionPayloadV1 = {
  /** How you are approaching this blueprint run (required to leave Mission step). */
  mode: MissionMode
  /** Short name for this initiative (required to leave Mission step). */
  title: string
  /** Problem, desired outcome, or success criteria (required to leave Mission step). */
  outcome: string
  /** Optional supporting detail (also surfaced in refine prompts when present). */
  notes?: string
}

export function emptyMissionPayload(): MissionPayloadV1 {
  return { mode: 'start_from_idea', title: '', outcome: '', notes: '' }
}

function isNonEmptyString(v: unknown): v is string {
  return typeof v === 'string'
}

/** Safe parse from persisted session.payload (ignores unknown keys). */
export function parseMissionFromPayload(payload: Record<string, unknown>): MissionPayloadV1 {
  const raw = payload.mission
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return emptyMissionPayload()
  }
  const o = raw as Record<string, unknown>
  const mode: MissionMode = isMissionMode(o.mode) ? o.mode : 'start_from_idea'
  const title = isNonEmptyString(o.title) ? o.title : ''
  const outcome = isNonEmptyString(o.outcome) ? o.outcome : ''
  const notes = isNonEmptyString(o.notes) ? o.notes : ''
  return {
    mode,
    title: title.slice(0, MISSION_TITLE_MAX),
    outcome: outcome.slice(0, MISSION_OUTCOME_MAX),
    notes: notes.slice(0, MISSION_NOTES_MAX),
  }
}

/** True when `payload.mission` includes an explicit `mode` the wizard understands. */
export function hasExplicitMissionMode(payload: Record<string, unknown>): boolean {
  const raw = payload.mission
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return false
  return isMissionMode((raw as Record<string, unknown>).mode)
}

export type MissionFieldErrors = {
  mode?: string
  title?: string
  outcome?: string
  notes?: string
}

/** Validation for advancing past Mission (step 0). Save Draft may still persist partial data. */
export function validateMissionForNext(m: MissionPayloadV1): { ok: boolean; errors: MissionFieldErrors } {
  const errors: MissionFieldErrors = {}
  if (!isMissionMode(m.mode)) {
    errors.mode = 'Choose how you want to run this mission.'
  }
  const title = m.title.trim()
  const outcome = m.outcome.trim()

  if (!title) {
    errors.title = 'Enter a short mission title.'
  } else if (title.length > MISSION_TITLE_MAX) {
    errors.title = `Title must be at most ${MISSION_TITLE_MAX} characters.`
  }

  if (!outcome) {
    errors.outcome = 'Describe the problem or outcome this work should address.'
  } else if (outcome.length > MISSION_OUTCOME_MAX) {
    errors.outcome = `Outcome must be at most ${MISSION_OUTCOME_MAX} characters.`
  }

  const rawNotes = m.notes ?? ''
  if (rawNotes.length > MISSION_NOTES_MAX) {
    errors.notes = `Notes must be at most ${MISSION_NOTES_MAX} characters.`
  }

  return { ok: Object.keys(errors).length === 0, errors }
}

export function clampMissionPayload(m: MissionPayloadV1): MissionPayloadV1 {
  const mode: MissionMode = isMissionMode(m.mode) ? m.mode : 'start_from_idea'
  return {
    mode,
    title: m.title.slice(0, MISSION_TITLE_MAX),
    outcome: m.outcome.slice(0, MISSION_OUTCOME_MAX),
    notes: (m.notes ?? '').slice(0, MISSION_NOTES_MAX),
  }
}

function missionModeLabel(mode: MissionMode): string {
  const opt = MISSION_MODE_OPTIONS.find((x) => x.value === mode)
  return opt?.label ?? mode
}

/** Flattens mission into stepNotes["0"] for prompts and legacy readers. */
export function formatMissionForStepNote(m: MissionPayloadV1): string {
  const lines: string[] = []
  const mode = isMissionMode(m.mode) ? m.mode : 'start_from_idea'
  lines.push(`Mode: ${missionModeLabel(mode)}`)
  const t = m.title.trim()
  const o = m.outcome.trim()
  const n = (m.notes ?? '').trim()
  if (t) lines.push(`Mission: ${t}`)
  if (o) lines.push(`Outcome: ${o}`)
  if (n) lines.push(`Notes: ${n}`)
  return lines.join('\n\n')
}
