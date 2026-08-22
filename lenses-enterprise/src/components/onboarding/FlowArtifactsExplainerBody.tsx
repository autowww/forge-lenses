import { Link } from 'react-router-dom'
import { GlossaryHint } from '../page/GlossaryHint'
import { STUDIO_GLOSSARY, STUDIO_ONBOARDING } from '../../nav/studioVisibleCopy'

type Props = {
  /** Slightly tighter spacing when nested (e.g. UX insights details). */
  density?: 'default' | 'compact'
}

/**
 * Canonical Flow vs Artifacts teaching: glossary short + long, breadcrumb rule, UX insights link.
 * Reused on the overview callout and under Settings → UX insights.
 */
export function FlowArtifactsExplainerBody({ density = 'default' }: Props) {
  const tight = density === 'compact'
  return (
    <div className={`le-fa-explainer${tight ? ' le-fa-explainer--compact' : ''}`}>
      <p className="le-fa-explainer__title">{STUDIO_ONBOARDING.flowArtifactsTitle}</p>
      <p className="le-fa-explainer__lede forge-support">
        The <GlossaryHint term="workspaceLens">workspace lens</GlossaryHint> (<strong>Flow</strong> or{' '}
        <strong>Artifacts</strong>): {STUDIO_GLOSSARY.workspaceLens.short}
      </p>
      <p className="le-fa-explainer__long forge-support">{STUDIO_GLOSSARY.workspaceLens.long}</p>
      <p className="le-fa-explainer__crumb forge-support">{STUDIO_ONBOARDING.breadcrumbLensRule}</p>
      <p className="le-fa-explainer__meta forge-support">
        <Link to="/settings/ux-insights">UX diagnostics</Link> (Settings → Admin &amp; inspect → UX diagnostics; this
        browser only) helps the team see route and sidebar usage during dogfood.
      </p>
    </div>
  )
}
