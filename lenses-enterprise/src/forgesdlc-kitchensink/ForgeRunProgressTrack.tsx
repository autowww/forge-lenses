import './forge-live-ui.css'

export type ForgeRunProgressMilestone = {
  id: string
  /** Short label under the tick. */
  label: string
  /** Done / current / upcoming visual. */
  state: 'done' | 'current' | 'upcoming' | 'hold'
}

export type ForgeRunProgressTrackProps = {
  /** 0–100 fill on the track. */
  percent: number
  milestones: ForgeRunProgressMilestone[]
  className?: string
  'aria-label'?: string
}

/**
 * Thin horizontal progress track plus milestone ticks (remediation / agent runs).
 */
export function ForgeRunProgressTrack({
  percent,
  milestones,
  className = '',
  'aria-label': ariaLabel = 'Run progress',
}: ForgeRunProgressTrackProps) {
  const p = Math.max(0, Math.min(100, percent))
  return (
    <div className={`ks-fe-runtrack ${className}`.trim()} aria-label={ariaLabel}>
      <div className="ks-fe-runtrack__bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(p)}>
        <div className="ks-fe-runtrack__fill" style={{ width: `${p}%` }} />
      </div>
      {milestones.length ? (
        <ol className="ks-fe-runtrack__ticks">
          {milestones.map((m) => (
            <li key={m.id} className={`ks-fe-runtrack__tick ks-fe-runtrack__tick--${m.state}`} title={m.label}>
              <span className="ks-fe-runtrack__dot" aria-hidden />
              <span className="ks-fe-runtrack__tick-label">{m.label}</span>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  )
}
