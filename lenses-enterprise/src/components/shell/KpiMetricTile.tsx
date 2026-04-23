import type { ReactNode } from 'react'
import { Link, type To } from 'react-router-dom'
import type { CompareModeId } from '../../context/ShellChromeContext'
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
  ariaLabel: string
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
  ariaLabel,
}: Props) {
  const tiltRef = useKsTilt(11)

  const sparkLayer =
    spark.length >= 2 ? (
      <div className="le-kpi-card__spark" aria-hidden>
        <Sparkline values={spark} strokeWidth={1.15} />
      </div>
    ) : null

  const valueBlock = (
    <>
      {sparkLayer}
      <div className="le-kpi-card__chrome">
        <div className="le-kpi-card__label">{label}</div>
        <div className="le-kpi-card__value-stack">
          <div className={`le-kpi-card__value ${tierClass}`}>{value}</div>
          {delta ? <DeltaPill {...delta} compareMode={compareMode} /> : null}
        </div>
      </div>
    </>
  )

  const innerClass = 'ks-tilt-inner le-kpi-card le-kpi-card--link'

  if (href) {
    return (
      <div ref={tiltRef} className="ks-tilt-wrap le-kpi-tilt" data-ks-tilt-max="11">
        <a href={href} className={innerClass} aria-label={ariaLabel}>
          {valueBlock}
        </a>
      </div>
    )
  }

  if (to) {
    return (
      <div ref={tiltRef} className="ks-tilt-wrap le-kpi-tilt" data-ks-tilt-max="11">
        <Link to={to} className={innerClass} aria-label={ariaLabel}>
          {valueBlock}
        </Link>
      </div>
    )
  }

  return (
    <div ref={tiltRef} className="ks-tilt-wrap le-kpi-tilt" data-ks-tilt-max="9">
      <div className="ks-tilt-inner le-kpi-card">{valueBlock}</div>
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
