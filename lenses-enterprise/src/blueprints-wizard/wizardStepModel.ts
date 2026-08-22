import type { WizardSessionDocumentJson } from '../api/blueprintsWizard'
import { clampStepIndex, WIZARD_STEPS } from './wizardSteps'

/** Alias for session/API code; canonical list is WIZARD_STEPS in wizardSteps. */
export const WIZARD_STEP_TITLES = WIZARD_STEPS

export { WIZARD_STEP_COUNT, clampStepIndex } from './wizardSteps'

export function applyStepNext(session: WizardSessionDocumentJson): WizardSessionDocumentJson {
  return {
    ...session,
    step_index: clampStepIndex(session.step_index + 1),
  }
}

export function applyStepBack(session: WizardSessionDocumentJson): WizardSessionDocumentJson {
  return {
    ...session,
    step_index: clampStepIndex(session.step_index - 1),
  }
}

const STEP_NOTES_KEY = 'stepNotes'

export function getStepNotesRecord(payload: Record<string, unknown>): Record<string, string> {
  const raw = payload[STEP_NOTES_KEY]
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
  const out: Record<string, string> = {}
  for (const [k, v] of Object.entries(raw)) {
    if (typeof v === 'string') out[k] = v
  }
  return out
}

export function getStepNote(payload: Record<string, unknown>, stepIndex: number): string {
  return getStepNotesRecord(payload)[String(stepIndex)] ?? ''
}

export function setStepNote(
  session: WizardSessionDocumentJson,
  stepIndex: number,
  text: string,
): WizardSessionDocumentJson {
  const notes = { ...getStepNotesRecord(session.payload), [String(stepIndex)]: text }
  return {
    ...session,
    payload: { ...session.payload, [STEP_NOTES_KEY]: notes },
  }
}
