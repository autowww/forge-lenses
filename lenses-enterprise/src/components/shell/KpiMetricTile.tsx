import type { ReactNode } from 'react'
import { Link, type To } from 'react-router-dom'
import type { CompareModeId } from '../../context/ShellChromeContext'
import type { OverviewJobHint } from '../../api/chartOverview'
import { useKsTilt } from '../../hooks/useKsTilt'
import { DeltaPill, Sparkline } from '../metrics'

type DeltaShape = { text: string; label: string } | null

type Props = {
  label: string
  /** Sparkline series (last point = current period). */
  spark: number[]
  value: ReactNode
  tierClass: string
  delta: DeltaShape
  compareMode: CompareModeId
  /** In-app route (e.g. `/projects` or hash jump). */
  to?: To
  /** External or API href (e.g. chart JSON). */
  href?: string
  /** Button handler for fly-out drill (no navigation). */
  onActivate?: () => void
  /** 0–1 async job fill for heavy metrics. */
  progress?: number | null
  jobHint?: OverviewJobHint | null
  ariaLabel: string
}

function jobTooltip(hint: OverviewJobHint | null | undefined): string | undefined {
  if (!hint) return undefined
  const parts = [
    hint.jobId ? `job ${hint.jobId.slice(0, 8)}` : null,
    hint.phase ? `phase ${hint.phase}` : null,
    hint.detail ? hint.detail : null,
    hint.repoTotal > 0 ? `repos ${hint.repoDone}/${hint.repoTotal}` : null,
    hint.elapsedSec != null ? `${hint.elapsedSec}s` : null,
    hint.status ? hint.status : null,
  ].filter(Boolean)
  return parts.length ? parts.join(' · ') : undefined
}

export function KpiMetricTile({
  label,
  spark,
  value,
  tierClass,
  delta,
  compareMode,
  to,
  href,
  onActivate,
  progress,
  jobHint,
  ariaLabel,
}: Props) {
  const tiltRef = useKsTilt(11)
  const showProgress = typeof progress === 'number' && progress >= 0 && progress < 1
  const title = jobTooltip(jobHint)

  const sparkLayer =
    spark.length >= 2 ? (
      <div className="le-kpi-card__spark" aria-hidden>
        <Sparkline values={spark} strokeWidth={1.15} />
      </div>
    ) : null

  const progressLayer = showProgress ? (
    <div className="le-kpi-card__progress" aria-hidden>
      <div className="le-kpi-card__progress-fill" style={{ width: `${Math.round(progress * 100)}%` }} />
    </div>
  ) : null

  const valueBlock = (
    <>
      {sparkLayer}
      {progressLayer}
      <div className="le-kpi-card__chrome">
        <div className="le-kpi-card__label">{label}</div>
        <div className="le-kpi-card__value-stack">
          <div className={`le-kpi-card__value ${tierClass}`}>{value}</div>
          {delta ? <DeltaPill {...delta} compareMode={compareMode} /> : null}
        </div>
        {title ? (
          <p className="le-kpi-card__job-hint" title={title}>
            {jobHint?.phase ? `${jobHint.phase}` : 'Refreshing'}
            {jobHint?.repoTotal ? ` · ${jobHint.repoDone}/${jobHint.repoTotal}` : ''}
          </p>
        ) : null}
      </div>
    </>
  )

  const innerClass = 'ks-tilt-inner le-kpi-card le-kpi-card--link'

  if (onActivate) {
    return (
      <div ref={tiltRef} className="ks-tilt-wrap le-kpi-tilt" data-ks-tilt-max="11">
        <button
          type="button"
          className={innerClass}
          aria-label={ariaLabel}
          title={title}
          onClick={onActivate}
        >
          {valueBlock}
        </button>
      </div>
    )
  }

  if (href) {
    return (
      <div ref={tiltRef} className="ks-tilt-wrap le-kpi-tilt" data-ks-tilt-max="11">
        <a href={href} className={innerClass} aria-label={ariaLabel} title={title}>
          {valueBlock}
        </a>
      </div>
    )
  }

  if (to) {
    return (
      <div ref={tiltRef} className="ks-tilt-wrap le-kpi-tilt" data-ks-tilt-max="11">
        <Link to={to} className={innerClass} aria-label={ariaLabel} title={title}>
          {valueBlock}
        </Link>
      </div>
    )
  }

  return (
    <div ref={tiltRef} className="ks-tilt-wrap le-kpi-tilt" data-ks-tilt-max="9">
      <div className="ks-tilt-inner le-kpi-card" title={title}>
        {valueBlock}
      </div>
    </div>
  )
}

type SnapshotProps = {
  resolvedLabel: string
  confidenceLine: string
}

/** Non-metric snapshot card: scan time + confidence (tilt, no navigation). */
export function KpiSnapshotTile({ resolvedLabel, confidenceLine }: SnapshotProps) {
  const tiltRef = useKsTilt(8)
  return (
    <div ref={tiltRef} className="ks-tilt-wrap le-kpi-tilt" data-ks-tilt-max="8">
      <div className="ks-tilt-inner le-kpi-card le-kpi-card--static le-kpi-card--snapshot">
        <div className="le-kpi-card__chrome le-kpi-card__chrome--snapshot">
          <div className="le-kpi-card__label">Snapshot time</div>
          <div className="le-kpi-card__value-row le-kpi-card__value-row--snapshot">
            <div className="le-kpi-card__value le-kpi-card__value--small">{resolvedLabel}</div>
          </div>
          <p className="le-kpi-card__snapshot-hint">{confidenceLine}</p>
        </div>
      </div>
    </div>
  )
}
