import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { ContextBar } from './ContextBar'
import { ExecutiveSummaryStrip } from './ExecutiveSummaryStrip'
import { EvidenceRail } from './EvidenceRail'
import { virtualCameraElectronMode } from '../../lib/studioElectronMode'

/** Universal enterprise shell: main + evidence rail; overview KPI chrome only on home (`/`). */
export function StudioShellChrome({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const minimalStudio = virtualCameraElectronMode()
  const showOverviewChrome = !minimalStudio && (pathname === '/' || pathname === '')

  if (minimalStudio) {
    return (
      <div className="le-main-column le-main-column--minimal-studio">
        <div className="le-page le-page--main">{children}</div>
      </div>
    )
  }

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
