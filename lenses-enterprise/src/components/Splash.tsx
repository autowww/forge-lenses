import { studioBuildDetails, studioSplashBuildLine } from '../util/studioBuildInfo'

const STEPS: Record<string, { title: string; detail: string }> = {
  init: {
    title: 'Initializing…',
    detail: 'Preparing the Lenses Studio view.',
  },
  connect: {
    title: 'Connecting to Lenses…',
    detail: 'Reaching the Lenses app on your machine.',
  },
  scan: {
    title: 'Scanning workspace…',
    detail: 'Indexing repositories, sites, and planning hints. Large folders can take a little longer.',
  },
  receive: {
    title: 'Receiving workspace data…',
    detail: 'Waiting for the latest workspace snapshot from Lenses.',
  },
  parse: {
    title: 'Almost ready…',
    detail: 'Building the dashboard view.',
  },
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
            ? 'Read-only demo snapshot — connect the live app for a full workspace.'
            : 'Runs against the Lenses app on this machine (local use).'}
        </p>
        <p className="le-splash__build" title={studioBuildDetails()}>
          {studioSplashBuildLine()}
        </p>
      </div>
    </div>
  )
}
