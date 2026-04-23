import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { ContextBar } from './ContextBar'
import { ExecutiveSummaryStrip } from './ExecutiveSummaryStrip'
import { EvidenceRail } from './EvidenceRail'

/** Universal enterprise shell: main + evidence rail; overview KPI chrome only on home (`/`). */
export function StudioShellChrome({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const showOverviewChrome = pathname === '/' || pathname === ''

  return (
    <div className="le-main-column">
      {showOverviewChrome ? (
        <>
          <ContextBar />
          <ExecutiveSummaryStrip />
        </>
      ) : null}
      <div className="le-page-rail-wrap">
        <div className="le-page le-page--main">{children}</div>
        <EvidenceRail />
      </div>
    </div>
  )
}
