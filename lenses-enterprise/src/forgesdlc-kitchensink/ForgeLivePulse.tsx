import './forge-live-ui.css'

export type ForgeLivePulseProps = {
  /** When true, shows animated dots (e.g. run in progress or SSE connected). */
  active: boolean
  /** Short caption after dots, e.g. "SSE" or "Working". */
  label?: string
  className?: string
}

/**
 * Compact “agent is working” affordance — three pulsing dots (Forge Studio / Lenses).
 */
export function ForgeLivePulse({ active, label, className = '' }: ForgeLivePulseProps) {
  if (!active) {
    return (
      <span className={`ks-fe-livepulse ks-fe-livepulse--idle ${className}`.trim()} aria-hidden>
        <span className="ks-fe-livepulse__idle-dot" />
        <span className="forge-support" style={{ marginLeft: '0.35rem', fontSize: '0.82rem' }}>
          {label ?? 'Idle'}
        </span>
      </span>
    )
  }
  return (
    <span className={`ks-fe-livepulse ks-fe-livepulse--active ${className}`.trim()} role="status" aria-live="polite">
      <span className="ks-fe-livepulse__dots" aria-hidden>
        <span className="ks-fe-livepulse__dot" />
        <span className="ks-fe-livepulse__dot" />
        <span className="ks-fe-livepulse__dot" />
      </span>
      {label ? (
        <span className="ks-fe-livepulse__label forge-support">{label}</span>
      ) : null}
    </span>
  )
}
