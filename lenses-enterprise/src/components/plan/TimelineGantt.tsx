export type GanttBar = {
  id: string
  label: string
  start: number
  end: number
  status?: string
  start_label?: string
  end_label?: string
}

type Props = {
  milestones: string[]
  bars: GanttBar[]
}

function statusClass(status: string | undefined): string {
  const s = (status ?? '').toLowerCase()
  if (s.includes('done') || s.includes('complete')) return 'le-timeline-gantt__bar--done'
  if (s.includes('risk') || s.includes('block')) return 'le-timeline-gantt__bar--risk'
  if (s.includes('progress') || s.includes('active')) return 'le-timeline-gantt__bar--active'
  return 'le-timeline-gantt__bar--planned'
}

/**
 * React Gantt shell — replaces default HTML injection for timeline bars.
 */
export function TimelineGantt({ milestones, bars }: Props) {
  if (!milestones.length || !bars.length) {
    return (
      <p className="forge-support" role="status">
        No Gantt bars for this roadmap scope. Add milestone tables and epic horizon rows in the roadmap file.
      </p>
    )
  }

  const span = Math.max(milestones.length - 1, 1)

  return (
    <section className="le-panel le-timeline-gantt" aria-label="Roadmap Gantt">
      <div className="le-timeline-gantt__axis" role="list" aria-label="Milestones">
        {milestones.map((m) => (
          <span key={m} className="le-timeline-gantt__milestone" role="listitem">
            {m}
          </span>
        ))}
      </div>
      <ul className="le-timeline-gantt__bars">
        {bars.map((bar) => {
          const left = (bar.start / span) * 100
          const width = Math.max(((bar.end - bar.start + 1) / (span + 1)) * 100, 4)
          const range =
            bar.start_label && bar.end_label
              ? `${bar.start_label} – ${bar.end_label}`
              : `Milestone ${bar.start + 1}–${bar.end + 1}`
          return (
            <li key={bar.id} className="le-timeline-gantt__row">
              <span className="le-timeline-gantt__label">{bar.label}</span>
              <div className="le-timeline-gantt__track" aria-hidden>
                <button
                  type="button"
                  className={`le-timeline-gantt__bar ${statusClass(bar.status)}`}
                  style={{ left: `${left}%`, width: `${width}%` }}
                  title={`${bar.label} · ${range}${bar.status ? ` · ${bar.status}` : ''}`}
                  aria-label={`${bar.label}, ${range}${bar.status ? `, status ${bar.status}` : ''}`}
                />
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
