import { useMemo, useState } from 'react'
import type { PlanMilestone } from '../../lib/planMetrics'

type Props = {
  milestones: PlanMilestone[]
  /** Opens the story detail modal (stays on Plan overview). */
  onOpenStoryDetails: (storyId: string) => void
  maxVisible?: number
}

function milestoneSummary(ms: PlanMilestone): string {
  const stories = ms.stories ?? []
  const n = stories.length
  let tasks = 0
  for (const s of stories) {
    if (typeof s.task_count === 'number') tasks += s.task_count
  }
  if (n === 0) return 'No stories in this milestone'
  if (tasks > 0) return `${n} stor${n === 1 ? 'y' : 'ies'} · ${tasks} tasks (in WBS)`
  return `${n} stor${n === 1 ? 'y' : 'ies'}`
}

export function MilestoneMap({ milestones, onOpenStoryDetails, maxVisible = 20 }: Props) {
  const [expanded, setExpanded] = useState(milestones.length <= maxVisible)
  const visible = expanded ? milestones : milestones.slice(0, maxVisible)

  const totalStories = useMemo(
    () => milestones.reduce((acc, m) => acc + (m.stories?.length ?? 0), 0),
    [milestones],
  )

  return (
    <section className="le-plan-section" aria-labelledby="le-plan-milestones-h">
      <h2 id="le-plan-milestones-h" className="le-plan-section__title">
        Backlog by milestone
      </h2>
      <p className="le-plan-section__lead">
        Grouped from your <strong>WBS</strong> (work breakdown). Each milestone bundles user-visible outcomes; open a
        story to see tasks, acceptance notes, and dependencies in a focused panel.
      </p>
      {milestones.length > 0 ? (
        <p className="le-plan-milestone-map__rollup forge-support" role="status">
          {milestones.length} milestone{milestones.length === 1 ? '' : 's'} · {totalStories} stor
          {totalStories === 1 ? 'y' : 'ies'} total
        </p>
      ) : null}
      {milestones.length === 0 ? (
        <p className="le-plan-section__empty">No milestones in spine — check WBS and plan-spine response.</p>
      ) : (
        <>
          <div className="le-plan-milestone-map__grid">
            {visible.map((ms) => (
              <article key={String(ms.title ?? ms.epic_key)} className="le-plan-milestone-card">
                <header className="le-plan-milestone-card__head">
                  <span className="le-plan-milestone-card__badge" title="Milestone / epic from WBS">
                    {ms.epic_key ?? 'Milestone'}
                  </span>
                  <h3 className="le-plan-milestone-card__title">{ms.title ?? ms.epic_key ?? 'Untitled'}</h3>
                  {ms.theme ? <p className="le-plan-milestone-card__theme">{ms.theme}</p> : null}
                  <p className="le-plan-milestone-card__summary">{milestoneSummary(ms)}</p>
                </header>
                <ul className="le-plan-milestone-card__stories">
                  {(ms.stories ?? []).map((st) => (
                    <li key={st.id}>
                      <button
                        type="button"
                        className="le-plan-milestone-card__story-btn"
                        onClick={() => onOpenStoryDetails(st.id)}
                      >
                        <span className="le-plan-milestone-card__story-id">{st.id}</span>
                        <span className="le-plan-milestone-card__story-title">{st.title ?? 'Untitled story'}</span>
                        {st.task_count != null ? (
                          <span className="le-plan-milestone-card__tasks">{st.task_count} tasks</span>
                        ) : null}
                      </button>
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
          {milestones.length > maxVisible && (
            <button type="button" className="le-btn" onClick={() => setExpanded(!expanded)}>
              {expanded ? 'Show fewer milestones' : `Show all ${milestones.length} milestones`}
            </button>
          )}
        </>
      )}
    </section>
  )
}
