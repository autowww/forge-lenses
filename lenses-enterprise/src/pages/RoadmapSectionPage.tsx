import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiGetJson } from '../api/http'
import { NestedRoadmapWorkspaceFrame, PlanningClusterLocalNav } from '../components/plan'
import { FULL_WORKSPACE_UI } from '../nav/studioVisibleCopy'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'

export function RoadmapSectionPage() {
  useLensesCopilotPage({ route: 'roadmap-section' })
  const [sp] = useSearchParams()
  const p = sp.get('p') || ''
  const section = sp.get('section') || ''
  const [html, setHtml] = useState<string | null>(null)

  useEffect(() => {
    if (!p || !section) {
      setHtml(null)
      return
    }
    apiGetJson<{ ok?: boolean; html?: string }>(
      `/api/roadmap-section?p=${encodeURIComponent(p)}&section=${encodeURIComponent(section)}`,
    )
      .then((r) => setHtml(r.html ?? null))
      .catch(() => setHtml(null))
  }, [p, section])

  return (
    <>
      <PlanningClusterLocalNav />
      <h1 className="le-h1">Roadmap section preview</h1>
      <p className="forge-support">
        Fragment from <code>/api/roadmap-section</code>. Query: <code>p</code>, <code>section</code>. Secondary full
        workspace:{' '}
        <a href="/roadmaps/summary" title={FULL_WORKSPACE_UI.navHint}>
          {FULL_WORKSPACE_UI.openRoadmapsSummary}
        </a>
        .
      </p>
      <section className="le-roadmap-section-horizon" aria-label="Roadmap horizon">
        <h2 className="le-plan-section__title">Roadmap horizon</h2>
        <p className="forge-support le-plan-section__lead">
          When <code>p</code> points at a roadmap file, the horizon view uses it as the focused roadmap; merge other
          scope params from the URL when present.
        </p>
        <NestedRoadmapWorkspaceFrame frameMinHeight="min(44vh, 24rem)" />
      </section>
      {html && (
        <div
          className="lenses-roadmap-preview-doc md-prose"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      )}
    </>
  )
}
