import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiGetJson } from '../api/http'
import { NestedRoadmapWorkspaceFrame, PlanningClusterLocalNav, RoadmapSectionPreview } from '../components/plan'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'

type RoadmapSectionPayload = {
  ok?: boolean
  title?: string
  section_id?: string
  body_lines?: string[]
}

export function RoadmapSectionPage() {
  useLensesCopilotPage({ route: 'roadmap-section' })
  const [sp] = useSearchParams()
  const p = sp.get('p') || ''
  const section = sp.get('section') || ''
  const [payload, setPayload] = useState<RoadmapSectionPayload | null>(null)

  useEffect(() => {
    if (!p || !section) {
      setPayload(null)
      return
    }
    apiGetJson<RoadmapSectionPayload>(
      `/api/roadmap-section?p=${encodeURIComponent(p)}&section=${encodeURIComponent(section)}`,
    )
      .then(setPayload)
      .catch(() => setPayload(null))
  }, [p, section])

  return (
    <>
      <PlanningClusterLocalNav />
      <h1 className="le-h1">Roadmap section preview</h1>
      <p className="forge-support">
        Structured section body from <code>/api/roadmap-section</code>. Query: <code>p</code>, <code>section</code>.
      </p>
      <section className="le-roadmap-section-horizon" aria-label="Roadmap horizon">
        <h2 className="le-plan-section__title">Roadmap horizon</h2>
        <p className="forge-support le-plan-section__lead">
          When <code>p</code> points at a roadmap file, the horizon view uses it as the focused roadmap; merge other
          scope params from the URL when present.
        </p>
        <NestedRoadmapWorkspaceFrame frameMinHeight="min(44vh, 24rem)" />
      </section>
      {payload?.ok ? (
        <RoadmapSectionPreview
          title={payload.title ?? section}
          bodyLines={payload.body_lines ?? []}
          sectionId={payload.section_id ?? section}
        />
      ) : null}
    </>
  )
}
