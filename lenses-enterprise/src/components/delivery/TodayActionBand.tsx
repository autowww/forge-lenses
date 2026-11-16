import { Link, useLocation } from 'react-router-dom'
import { DEMO_ORCHESTRATION_STORY_ID } from '../../constants/demoOrchestration'
import { mergePlanningScopeIntoTo } from '../../lib/planningClusterScope'
import { DELIVERY_LENS, STUDIO_VOCAB } from '../../nav/studioVisibleCopy'
import { TraceabilityLaunchButton } from '../traceability'

type Props = {
  repoHint: string
  wbsSelected: boolean
}

/**
 * Today tab: primary operational jumps in one row (1–2 clicks to common next actions).
 */
export function TodayActionBand({ repoHint, wbsSelected }: Props) {
  const { search } = useLocation()
  const q = repoHint.trim() ? `?project=${encodeURIComponent(repoHint.trim())}` : ''
  const planSummaryTo = mergePlanningScopeIntoTo('/plan', search)
  const timelineTo = mergePlanningScopeIntoTo('/timeline', search)

  return (
    <section className="le-today-action-band" aria-label="Today quick actions">
      <p className="le-today-action-band__context forge-support" id="le-today-band-context">
        {DELIVERY_LENS.todayBandShortcutTitle}: workspace and portfolio links keep context when the URL allows.
      </p>
      <div className="le-today-action-band__inner" aria-describedby="le-today-band-context">
        <Link className="le-today-action-band__btn le-today-action-band__btn--primary" to={`/board${q}`}>
          {STUDIO_VOCAB.boards}
        </Link>
        <Link className="le-today-action-band__btn" to="/projects?filter=attention">
          {STUDIO_VOCAB.projects} (attention){' '}
          <span className="le-shortcut-pill">Shortcut</span>
        </Link>
        <Link className="le-today-action-band__btn" to={timelineTo}>
          {STUDIO_VOCAB.timeline} <span className="le-shortcut-pill">Shortcut</span>
        </Link>
        <Link className="le-today-action-band__btn" to="/workspace-md">
          {STUDIO_VOCAB.workspaceNotes} <span className="le-shortcut-pill">Shortcut</span>
        </Link>
        <Link className="le-today-action-band__btn" to={planSummaryTo}>
          {STUDIO_VOCAB.planSummary} <span className="le-shortcut-pill">Shortcut</span>
        </Link>
        <a className="le-today-action-band__btn" href="#le-plan-scope-anchor">
          {wbsSelected ? 'Adjust scope' : 'Set WBS scope'}
        </a>
        <TraceabilityLaunchButton
          rootId={DEMO_ORCHESTRATION_STORY_ID}
          label="Trace (demo)"
          visual="today-band"
          title="Delivery trace: demo story through code, CI, release, evidence"
        />
      </div>
      {!wbsSelected ? (
        <p className="le-today-action-band__hint forge-support">
          Pick a work backlog below so {STUDIO_VOCAB.today} charge, blockers, and commitments can load.
        </p>
      ) : null}
    </section>
  )
}
