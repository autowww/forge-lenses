import { studioBuildDetails, studioBuildFooterLine } from '../util/studioBuildInfo'

const PROGRESS_STAGES = ['init', 'connect', 'scan', 'receive', 'parse'] as const

const STEPS: Record<(typeof PROGRESS_STAGES)[number], { title: string; detail: string }> = {
  init: {
    title: 'Starting Studio…',
    detail: 'Preparing your workspace view.',
  },
  connect: {
    title: 'Connecting to Lenses…',
    detail: 'Reaching the Lenses app on this machine.',
  },
  scan: {
    title: 'Scanning your workspace…',
    detail: 'Indexing repositories, sites, and planning files. Large folders can take a little longer.',
  },
  receive: {
    title: 'Loading workspace data…',
    detail: 'Pulling the latest scan results from Lenses.',
  },
  parse: {
    title: 'Almost ready…',
    detail: 'Building your dashboard.',
  },
}

function progressStageIndex(step: keyof typeof STEPS): number {
  const i = PROGRESS_STAGES.indexOf(step)
  return i >= 0 ? i : 0
}

type Props = {
  step: keyof typeof STEPS
  error: string | null
  errorDescription?: string | null
  errorDetail?: string | null
  onRetry: () => void
  hidden: boolean
}

export function Splash({ step, error, errorDescription, errorDetail, onRetry, hidden }: Props) {
  const s = STEPS[step] ?? STEPS.init
  const busy = !error
  const stageIndex = progressStageIndex(step)
  const progressPct = Math.round(((stageIndex + 1) / PROGRESS_STAGES.length) * 100)

  return (
    <div
      className={`le-splash${error ? ' le-splash--error' : ''}`}
      hidden={hidden}
      aria-busy={busy}
    >
      <div className="le-splash__panel">
        <p className="le-splash__eyebrow">Forge Lenses</p>
        <h1 className="le-splash__logo">Studio</h1>
        {!error && <div className="le-splash__spinner" aria-hidden />}
        <h2 className="le-splash__title" id="le-splash-title" role={error ? 'alert' : undefined}>
          {error ? error : s.title}
        </h2>
        <p className="le-splash__detail" id="le-splash-detail">
          {error ? errorDescription || 'Lenses could not finish loading your workspace.' : s.detail}
        </p>
        {!error ? (
          <div
            className="le-splash__progress"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progressPct}
            aria-labelledby="le-splash-title"
            aria-describedby="le-splash-detail"
          >
            <div className="le-splash__progress-track">
              <div className="le-splash__progress-fill" style={{ width: `${progressPct}%` }} />
            </div>
            <p className="le-splash__progress-stage" aria-live="polite">
              Step {stageIndex + 1} of {PROGRESS_STAGES.length}: {s.title}
            </p>
          </div>
        ) : null}
        {error && (
          <>
            {errorDetail ? (
              <details className="le-splash__technical">
                <summary>Show technical details</summary>
                <pre className="le-splash__technical-pre">{errorDetail}</pre>
              </details>
            ) : null}
            <button
              type="button"
              className="le-splash__retry"
              id="le-splash-retry"
              onClick={onRetry}
            >
              Retry
            </button>
          </>
        )}
        <p className="le-splash__hint">
          {import.meta.env.VITE_STATIC_MUSEUM === 'true'
            ? 'Read-only demo — connect the live app for a full workspace.'
            : 'Runs on this machine with the Lenses workspace app.'}
        </p>
        <details className="le-splash__technical le-splash__build-inspect">
          <summary>Build details (inspect)</summary>
          <p className="le-splash__build">{studioBuildFooterLine()}</p>
          <pre className="le-splash__technical-pre">{studioBuildDetails()}</pre>
        </details>
      </div>
    </div>
  )
}
