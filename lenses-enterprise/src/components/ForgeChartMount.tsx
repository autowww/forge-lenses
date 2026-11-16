import { useEffect, useRef } from 'react'

declare global {
  interface Window {
    ForgeDataCharts?: { mountAll: (root: ParentNode) => void }
  }
}

export type ForgeChartMountProps = {
  title: string
  chartKind: string
  /** Full URL to JSON API (e.g. /api/chart-data/overview) */
  dataUrl: string
}

/**
 * Renders the same DOM contract as Classic `chart_pages._chart_mount` so
 * `window.ForgeDataCharts.mountAll` can fetch and render SVG/HTML.
 * Wrapper ref must be a parent of `.ks-chart-mount` (mountAll uses querySelectorAll).
 */
export function ForgeChartMount({ title, chartKind, dataUrl }: ForgeChartMountProps) {
  const wrapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const root = wrapRef.current
    if (!root) return
    const run = () => window.ForgeDataCharts?.mountAll(root)
    run()
    const t = window.setTimeout(run, 0)
    return () => window.clearTimeout(t)
  }, [chartKind, dataUrl])

  return (
    <section
      className="le-panel forge-card mb-4"
      style={{ marginBottom: '1rem' }}
      data-ks-chart-wrap={chartKind}
    >
      <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>
        {title}
      </h3>
      <div ref={wrapRef}>
        <div
          className="ks-chart-mount"
          data-ks-chart=""
          data-ks-chart-kind={chartKind}
          data-ks-chart-url={dataUrl}
        />
      </div>
    </section>
  )
}
