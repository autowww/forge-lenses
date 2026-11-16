type TimelineMetricsData = {
  horizon_counts?: Record<string, number>
  epic_bars?: { label: string; percent: number }[]
}

type TimelineMetricsProps = {
  metrics: TimelineMetricsData | null | undefined
}

export function TimelineMetrics({ metrics }: TimelineMetricsProps) {
  if (!metrics) return null
  const horizons = metrics.horizon_counts ?? {}
  const horizonEntries = Object.entries(horizons).filter(([, n]) => Number(n) > 0)
  const epicBars = metrics.epic_bars ?? []

  if (!horizonEntries.length && !epicBars.length) {
    return (
      <p className="forge-support">
        No horizon badges or epic progress metrics found in this roadmap slice.
      </p>
    )
  }

  return (
    <section className="le-timeline-metrics" aria-label="Timeline metrics">
      {horizonEntries.length ? (
        <div className="le-timeline-metrics__horizons">
          <h3 className="le-plan-section__title">Horizons</h3>
          <ul className="le-badge-row">
            {horizonEntries.map(([name, count]) => (
              <li key={name}>
                <span className="le-badge le-badge--muted">
                  {name}: {count}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {epicBars.length ? (
        <div className="le-timeline-metrics__epics">
          <h3 className="le-plan-section__title">Epic progress</h3>
          <ul className="le-timeline-metrics__bars">
            {epicBars.map((bar) => {
              const pct = Math.max(0, Math.min(100, Number(bar.percent) || 0))
              return (
                <li key={bar.label} className="le-timeline-metrics__bar-row">
                  <span className="le-timeline-metrics__bar-label">{bar.label}</span>
                  <span className="le-timeline-metrics__bar-track" aria-hidden>
                    <span className="le-timeline-metrics__bar-fill" style={{ width: `${pct}%` }} />
                  </span>
                  <span className="le-timeline-metrics__bar-pct">{pct}%</span>
                </li>
              )
            })}
          </ul>
        </div>
      ) : null}
    </section>
  )
}
