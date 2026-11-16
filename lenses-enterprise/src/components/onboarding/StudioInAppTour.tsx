import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'
import { recordTourStep } from '../../telemetry/studioTelemetry'

const DISMISS_KEY = 'lenses.studio.inAppTour.dismissed'

/** Five-stop StudioTour: Home → Project → Today → Evidence → Publish */
export const tourSteps = [
  {
    id: 'home',
    title: STUDIO_VOCAB.home,
    lead: 'Scan-first overview — attention, docs health, and portfolio signals before you dive into delivery.',
    to: '/',
  },
  {
    id: 'project',
    title: STUDIO_VOCAB.projects,
    lead: 'Pick a repository dashboard for health, risks, and evidence scoped to one codebase.',
    to: '/projects',
  },
  {
    id: 'today',
    title: STUDIO_VOCAB.today,
    lead: 'Execute the current slice — boards, blockers, and delivery cards in one place.',
    to: '/plan?tab=today',
  },
  {
    id: 'evidence',
    title: 'Evidence',
    lead: 'Browse proof and methodology-linked material — charge logs, decisions, and graph evidence.',
    to: '/knowledge/methodology/evidence',
  },
  {
    id: 'publish',
    title: STUDIO_VOCAB.publish,
    lead: 'Preview shipped sites and blog outputs when the scan finds static or Firebase roots.',
    to: '/websites',
  },
] as const

function readDismissed(): boolean {
  try {
    return localStorage.getItem(DISMISS_KEY) === '1'
  } catch {
    return false
  }
}

function writeDismissed() {
  try {
    localStorage.setItem(DISMISS_KEY, '1')
  } catch {
    /* ignore */
  }
}

/**
 * OnboardingTour — lightweight in-app tour surfaced from Home after first-run wizard.
 */
export function StudioInAppTour() {
  const [dismissed, setDismissed] = useState(readDismissed)
  const [index, setIndex] = useState(0)
  const step = tourSteps[index]!

  useEffect(() => {
    setDismissed(readDismissed())
  }, [])

  const dismiss = useCallback(() => {
    recordTourStep(step.id, 'dismiss')
    writeDismissed()
    setDismissed(true)
  }, [step.id])

  useEffect(() => {
    if (dismissed) return
    recordTourStep(step.id, 'view')
  }, [dismissed, step.id])

  if (dismissed) return null

  const isLast = index >= tourSteps.length - 1

  return (
    <section className="le-card le-in-app-tour" aria-label="Studio guided tour" data-ks-type="onboarding">
      <div className="le-in-app-tour__head">
        <h2 className="le-in-app-tour__title">Studio tour · step {index + 1} of {tourSteps.length}</h2>
        <button type="button" className="le-btn le-btn--small" onClick={dismiss}>
          Dismiss tour
        </button>
      </div>
      <p className="forge-support" style={{ margin: '0.35rem 0 0.65rem' }}>
        <strong>{step.title}</strong> — {step.lead}
      </p>
      <div className="le-in-app-tour__actions">
        <Link className="le-btn le-btn--primary" to={step.to}>
          Open {step.title}
        </Link>
        {!isLast ? (
          <button
            type="button"
            className="le-btn"
            onClick={() => {
              recordTourStep(step.id, 'next')
              setIndex((i) => Math.min(i + 1, tourSteps.length - 1))
            }}
          >
            Next stop
          </button>
        ) : (
          <button
            type="button"
            className="le-btn le-btn--primary"
            onClick={() => {
              recordTourStep(step.id, 'finish')
              dismiss()
            }}
          >
            Finish tour
          </button>
        )}
        {index > 0 ? (
          <button type="button" className="le-btn le-btn--small" onClick={() => setIndex((i) => Math.max(0, i - 1))}>
            Back
          </button>
        ) : null}
      </div>
      <ol className="le-in-app-tour__stops forge-support" aria-label="Tour stops">
        {tourSteps.map((s, i) => (
          <li key={s.id} className={i === index ? 'le-in-app-tour__stop--active' : undefined}>
            {s.title}
          </li>
        ))}
      </ol>
    </section>
  )
}
