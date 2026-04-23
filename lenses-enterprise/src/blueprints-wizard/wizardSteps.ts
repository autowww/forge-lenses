/** 12-step Blueprints Wizard shell (titles only; business logic comes later). */

export const WIZARD_STEPS = [
  'Mission',
  'Contribution Setup',
  'Context Intake',
  'Understanding',
  'Clarification',
  'Target & Output Pack',
  'Autonomy & Mutation',
  'Scope Selection',
  'Run Plan',
  'Review & Generate',
  'Recheck / Repair',
  'Experimental Build',
] as const

export type WizardStepTitle = (typeof WIZARD_STEPS)[number]

export const WIZARD_STEP_COUNT = WIZARD_STEPS.length

export function getStepTitle(stepIndex: number): string {
  const i = clampStepIndex(stepIndex)
  return WIZARD_STEPS[i] ?? WIZARD_STEPS[0]
}

export function clampStepIndex(step: number): number {
  const i = Math.floor(Number.isFinite(step) ? step : 0)
  return Math.max(0, Math.min(WIZARD_STEP_COUNT - 1, i))
}

export function stepIndexNext(current: number): number {
  return clampStepIndex(current + 1)
}

export function stepIndexBack(current: number): number {
  return clampStepIndex(current - 1)
}
