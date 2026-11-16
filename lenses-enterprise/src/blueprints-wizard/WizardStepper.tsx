import { WIZARD_STEP_COUNT, WIZARD_STEPS } from './wizardSteps'

type Props = {
  stepIndex: number
}

export function WizardStepper({ stepIndex }: Props) {
  return (
    <nav className="le-bpwizard-stepper" aria-label="Wizard steps">
      {WIZARD_STEPS.map((title, i) => {
        const isCurrent = i === stepIndex
        const isDone = i < stepIndex
        const cls = [
          'le-bpwizard-stepper__item',
          isCurrent ? 'le-bpwizard-stepper__item--current' : '',
          isDone ? 'le-bpwizard-stepper__item--done' : '',
        ]
          .filter(Boolean)
          .join(' ')
        return (
          <span key={title} className={cls} aria-current={isCurrent ? 'step' : undefined}>
            <span className="le-bpwizard-stepper__num">
              {i + 1}/{WIZARD_STEP_COUNT}
            </span>
            <span>{title}</span>
          </span>
        )
      })}
    </nav>
  )
}
