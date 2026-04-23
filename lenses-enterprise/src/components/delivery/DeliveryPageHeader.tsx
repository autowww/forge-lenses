import { useLocation } from 'react-router-dom'
import { NavLink } from 'react-router-dom'
import { useNavigationMode } from '../../nav/useNavigationMode'
import { getPlanningClusterPageIdentity } from '../../nav/planningClusterPageIdentity'
import { DELIVERY_LENS, FULL_WORKSPACE_UI, STUDIO_GLOSSARY } from '../../nav/studioVisibleCopy'
import { TechnicalDetails } from '../page/TechnicalDetails'

type Props = {
  classicPlanHref: string
}

export function DeliveryPageHeader({ classicPlanHref }: Props) {
  const { pathname, search } = useLocation()
  const { mode } = useNavigationMode()
  const identity = getPlanningClusterPageIdentity(pathname, search, mode)

  return (
    <header className="le-delivery-header">
      <div className="le-delivery-header__title-row">
        <h1 className="le-h1 le-delivery-header__h">{identity.title}</h1>
        <NavLink className="le-btn le-btn--small le-btn--primary" to="/plan?tab=plan">
          Open plan summary
        </NavLink>
      </div>
      <p className="le-delivery-header__purpose">
        Execution view for the selected scope—blockers, gates, and delivery signals first.
      </p>
      <TechnicalDetails summary="About Today vs plan & classic workspace">
        <p className="le-delivery-header__lens forge-support">{DELIVERY_LENS.todayVersusPlanning}</p>
        <p className="forge-support">
          <a href={classicPlanHref}>{FULL_WORKSPACE_UI.openPlanSameScope}</a>{' '}
          <span className="le-shortcut-pill">Full workspace</span>
          {' — '}
          <span title={STUDIO_GLOSSARY.fullWorkspaceUi.long}>{STUDIO_GLOSSARY.fullWorkspaceUi.short}</span>
        </p>
      </TechnicalDetails>
    </header>
  )
}
