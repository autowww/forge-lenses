import type { ReactNode } from 'react'
import { TechnicalDetails } from '../page/TechnicalDetails'
import type { PlanningClusterPageIdentity } from '../../nav/planningClusterPageIdentity'

export type PlanningClusterPageHeaderProps = {
  identity: PlanningClusterPageIdentity
  /** Default matches Flow plan summary shell; Delivery today uses `le-delivery-header`. */
  headerClassName?: string
  /** Optional row above the title (e.g. back link). */
  preface?: ReactNode
  /** Title row end: primary trace, scope pickers promoted from body, etc. */
  actions?: ReactNode
  /** Workspace scan / freshness (same slot as shared `PageHeader`). */
  freshness?: ReactNode
  /** One-line intent; defaults to registry subtitle when omitted. */
  purpose?: ReactNode
  children?: ReactNode
}

/**
 * H1 + purpose + optional story id; cross-IA hints live in progressive disclosure (not above the fold).
 */
export function PlanningClusterPageHeader({
  identity,
  headerClassName = 'le-plan-page-header',
  preface,
  actions,
  freshness,
  purpose,
  children,
}: PlanningClusterPageHeaderProps) {
  const purposeLine = purpose ?? identity.subtitle
  const hasHint = Boolean(identity.entryHint || identity.storyWorkItemLine)

  return (
    <header className={headerClassName}>
      {preface ? <div className="le-plan-page-header__preface">{preface}</div> : null}
      <div className="le-plan-page-header__title-row">
        <div className="le-plan-page-header__lead-block">
          <h1 className="le-h1 le-plan-page-header__h">{identity.title}</h1>
          {freshness ? <p className="le-plan-page-header__freshness forge-support">{freshness}</p> : null}
        </div>
        {actions ? <div className="le-plan-page-header__toolbar">{actions}</div> : null}
      </div>
      {purposeLine ? <p className="le-plan-page-header__purpose">{purposeLine}</p> : null}
      {hasHint ? (
        <TechnicalDetails summary="Planning entry context">
          {identity.storyWorkItemLine ? (
            <p className="le-plan-page-header__context le-muted">{identity.storyWorkItemLine}</p>
          ) : null}
          {identity.entryHint ? <p className="le-planning-entry-hint forge-support">{identity.entryHint}</p> : null}
        </TechnicalDetails>
      ) : null}
      {children}
    </header>
  )
}
