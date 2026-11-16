import { Link } from 'react-router-dom'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

const LINKS: { label: string; to: string; hint: string }[] = [
  { label: STUDIO_VOCAB.plan, to: '/plan', hint: 'Backlog, roadmap, story detail' },
  { label: STUDIO_VOCAB.today, to: '/plan?tab=today', hint: 'Queue, blockers, boards' },
  { label: STUDIO_VOCAB.projects, to: '/projects', hint: 'Health, filters, dashboards' },
  { label: STUDIO_VOCAB.websites, to: '/websites', hint: 'Published sites' },
]

export function QuickDrilldowns() {
  return (
    <section className="le-cc-section" aria-labelledby="le-cc-drill">
      <h2 id="le-cc-drill" className="le-cc-section__title">
        Navigate
      </h2>
      <p className="le-cc-section__lead">
        Jump to major surfaces; the control tower above stays the fastest path for operational questions.
      </p>
      <div className="le-cc-drill-grid">
        {LINKS.map((x) => (
          <Link key={x.to} className="le-cc-drill-card" to={x.to}>
            <span className="le-cc-drill-card__label">{x.label}</span>
            <span className="le-cc-drill-card__hint">{x.hint}</span>
          </Link>
        ))}
      </div>
    </section>
  )
}
