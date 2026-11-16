import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  readFlowArtifactsBannerDismissed,
  readFlowArtifactsChipOverviewHidden,
  writeFlowArtifactsBannerDismissed,
  writeFlowArtifactsChipOverviewHidden,
} from '../../lib/flowArtifactsOnboardingStorage'
import { STUDIO_HELP_LENS_VALUE, STUDIO_HELP_QUERY } from '../../nav/studioHelpQuery'
import { STUDIO_GLOSSARY, STUDIO_ONBOARDING } from '../../nav/studioVisibleCopy'
import { FlowArtifactsExplainerBody } from './FlowArtifactsExplainerBody'

/**
 * Workspace overview: first-run expanded Flow vs Artifacts explainer; after dismissal, compact chip
 * that reopens the same content. Deep-link: `/?studioHelp=lens` (see `flowArtifactsHelpHomeTo`).
 */
export function FlowArtifactsOnboardingCallout() {
  const [, setSearchParams] = useSearchParams()
  const strippedQueryRef = useRef(false)

  const [bannerDismissed, setBannerDismissed] = useState(readFlowArtifactsBannerDismissed)
  const [chipHidden, setChipHidden] = useState(readFlowArtifactsChipOverviewHidden)
  const [panelFromChip, setPanelFromChip] = useState(false)
  const [queryTeach, setQueryTeach] = useState(false)

  useEffect(() => {
    if (strippedQueryRef.current) return
    strippedQueryRef.current = true
    const sp = new URLSearchParams(window.location.search)
    if (sp.get(STUDIO_HELP_QUERY) === STUDIO_HELP_LENS_VALUE) {
      setQueryTeach(true)
      sp.delete(STUDIO_HELP_QUERY)
      setSearchParams(sp, { replace: true })
    }
  }, [setSearchParams])

  const largeOpen = !bannerDismissed || panelFromChip || queryTeach

  const persistGotIt = useCallback(() => {
    writeFlowArtifactsBannerDismissed()
    setBannerDismissed(true)
    setPanelFromChip(false)
    setQueryTeach(false)
  }, [])

  const persistHideChip = useCallback(() => {
    writeFlowArtifactsBannerDismissed()
    writeFlowArtifactsChipOverviewHidden()
    setBannerDismissed(true)
    setChipHidden(true)
    setPanelFromChip(false)
    setQueryTeach(false)
  }, [])

  const collapsePanel = useCallback(() => {
    setPanelFromChip(false)
    setQueryTeach(false)
  }, [])

  const showChip = bannerDismissed && !chipHidden && !largeOpen

  return (
    <div className="le-fa-onboarding">
      {largeOpen ? (
        <section className="le-fa-onboarding__panel" role="region" aria-label="Flow vs Artifacts — workspace lens">
          <FlowArtifactsExplainerBody />
          <div className="le-fa-onboarding__actions">
            {bannerDismissed ? (
              <button type="button" className="le-btn le-btn--small le-btn--primary" onClick={collapsePanel}>
                {STUDIO_ONBOARDING.flowArtifactsCollapse}
              </button>
            ) : (
              <>
                <button type="button" className="le-btn le-btn--small le-btn--primary" onClick={persistGotIt}>
                  {STUDIO_ONBOARDING.flowArtifactsGotIt}
                </button>
                <button type="button" className="le-btn le-btn--small" onClick={persistHideChip}>
                  {STUDIO_ONBOARDING.flowArtifactsHideOverviewChip}
                </button>
              </>
            )}
          </div>
        </section>
      ) : null}

      {showChip ? (
        <div className="le-fa-onboarding__chip-row">
          <button
            type="button"
            className="le-fa-onboarding__chip"
            onClick={() => setPanelFromChip(true)}
            title={`${STUDIO_GLOSSARY.workspaceLens.short} ${STUDIO_ONBOARDING.flowArtifactsChipHint}`}
          >
            <span className="le-fa-onboarding__chip-label">{STUDIO_ONBOARDING.flowArtifactsChipLabel}</span>
            <span className="le-fa-onboarding__chip-sub" aria-hidden="true">
              Optional layout detail
            </span>
          </button>
          <span className="le-fa-onboarding__chip-hint forge-support">{STUDIO_ONBOARDING.flowArtifactsChipHint}</span>
        </div>
      ) : null}
    </div>
  )
}
