import { normalizeSparklineValues } from '../../lib/kpiTrendUi'

type Props = {
  values: number[]
  className?: string
  /** SVG polyline stroke width (default thinner for KPI backgrounds). */
  strokeWidth?: number
}

/** Background sparkline; values should be non-negative for a sensible shape. */
export function Sparkline({ values, className, strokeWidth = 1.15 }: Props) {
  const n = values.length
  if (n < 2) return null
  const norm = normalizeSparklineValues(values)
  const w = 100
  const h = 32
  const pad = 2
  const points = norm
    .map((y, i) => {
      const x = n === 1 ? w / 2 : (i / (n - 1)) * w
      const yy = h - pad - y * (h - 2 * pad)
      return `${x},${yy}`
    })
    .join(' ')

  return (
    <svg
      className={className ?? 'le-sparkline'}
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
      aria-hidden
    >
      <polyline fill="none" stroke="currentColor" strokeWidth={strokeWidth} points={points} />
    </svg>
  )
}
