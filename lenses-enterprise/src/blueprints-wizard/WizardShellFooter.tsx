import { WIZARD_STEP_COUNT } from './wizardSteps'

type Props = {
  stepIndex: number
  onBack: () => void
  onNext: () => void
  onSaveDraft: () => void
  onExit: () => void
  /** Disables Back, Next, and Save Draft (e.g. while saving to server). */
  interactionDisabled?: boolean
}

export function WizardShellFooter({
  stepIndex,
  onBack,
  onNext,
  onSaveDraft,
  onExit,
  interactionDisabled = false,
}: Props) {
  const atFirst = stepIndex <= 0
  const atLast = stepIndex >= WIZARD_STEP_COUNT - 1
  const navLock = interactionDisabled

  return (
    <footer className="le-bpwizard__footer">
      <button type="button" className="le-btn" onClick={onExit}>
        Exit
      </button>
      <div className="le-bpwizard__footer-actions">
        <button type="button" className="le-btn" disabled={navLock || atFirst} onClick={onBack}>
          Back
        </button>
        <button type="button" className="le-btn le-btn--primary" disabled={navLock || atLast} onClick={onNext}>
          Next
        </button>
        <button type="button" className="le-btn" disabled={navLock} onClick={onSaveDraft}>
          Save Draft
        </button>
      </div>
    </footer>
  )
}
