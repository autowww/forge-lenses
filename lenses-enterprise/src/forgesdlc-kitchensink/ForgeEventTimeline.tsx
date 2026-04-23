import { useId, useState, type ReactNode } from 'react'

export type ForgeTimelineEvent = {
  id: string
  ts?: string
  /** Short state label (e.g. completed, running). */
  state?: string
  summary: ReactNode
  details?: ReactNode
  defaultOpen?: boolean
}

export type ForgeEventTimelineProps = {
  events: ForgeTimelineEvent[]
  className?: string
  emptyLabel?: string
}

/**
 * Chronological timeline: state, timestamp, summary, optional expandable details.
 */
export function ForgeEventTimeline({
  events,
  className = '',
  emptyLabel = 'No events yet.',
}: ForgeEventTimelineProps) {
  const baseId = useId()
  const [open, setOpen] = useState<Record<string, boolean>>({})

  if (!events.length) {
    return <p className="ks-fe-timeline ks-fe-timeline--empty forge-support">{emptyLabel}</p>
  }

  return (
    <ol className={`ks-fe-timeline ${className}`.trim()} aria-label="Event timeline">
      {events.map((ev) => {
        const expanded = open[ev.id] ?? ev.defaultOpen ?? false
        const panelId = `${baseId}-panel-${ev.id}`
        const triggerId = `${baseId}-trigger-${ev.id}`
        return (
          <li key={ev.id} className="ks-fe-timeline__item">
            <div className="ks-fe-timeline__rail" aria-hidden />
            <div className="ks-fe-timeline__card">
              <div className="ks-fe-timeline__meta">
                {ev.ts ? (
                  <time className="ks-fe-timeline__ts" dateTime={ev.ts}>
                    {ev.ts}
                  </time>
                ) : null}
                {ev.state ? <span className="ks-fe-timeline__state">{ev.state}</span> : null}
              </div>
              <div className="ks-fe-timeline__summary">{ev.summary}</div>
              {ev.details ? (
                <div className="ks-fe-timeline__details-wrap">
                  <button
                    type="button"
                    id={triggerId}
                    className="ks-fe-timeline__toggle le-btn le-btn--small le-btn--ghost"
                    aria-expanded={expanded}
                    aria-controls={panelId}
                    onClick={() => setOpen((o) => ({ ...o, [ev.id]: !expanded }))}
                  >
                    {expanded ? 'Hide details' : 'Show details'}
                  </button>
                  {expanded ? (
                    <div id={panelId} role="region" aria-labelledby={triggerId} className="ks-fe-timeline__details">
                      {ev.details}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
