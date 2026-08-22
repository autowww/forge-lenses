import type { ReactNode } from 'react'
import { PageHeaderActionsMenu, type PageHeaderSecondaryItem } from './PageHeaderActionsMenu'

export type PageHeaderStatusChip = { label: string; tone?: 'ok' | 'warn' | 'muted' }

export type PageHeaderProps = {
  title: string
  /** One-line scan-first purpose; shown prominently under the title row. */
  purpose?: ReactNode
  /** Optional supporting line (smaller than purpose). */
  subtitle?: ReactNode
  /** Freshness / last-updated (e.g. last workspace scan). */
  freshness?: ReactNode
  /** Single dominant CTA for the page. */
  primaryAction?: ReactNode
  /** Secondary destinations in an overflow menu (keyboard reachable). */
  secondaryMenuItems?: PageHeaderSecondaryItem[]
  statusChips?: PageHeaderStatusChip[]
  preface?: ReactNode
  /**
   * Legacy toolbar actions (multiple controls). Prefer `primaryAction` + `secondaryMenuItems`
   * for new pages; when both `primaryAction` and `actions` are set, `actions` render as an
   * inline cluster after the primary control.
   */
  actions?: ReactNode
  titleId?: string
  className?: string
}

/**
 * Shared top-of-page chrome: preface, title + meta/actions, purpose, optional subtitle.
 * Land users on title → purpose → primary action; tuck the rest in overflow or below.
 */
export function PageHeader({
  title,
  purpose,
  subtitle,
  freshness,
  primaryAction,
  secondaryMenuItems,
  statusChips,
  preface,
  actions,
  titleId = 'le-page-title',
  className = '',
}: PageHeaderProps) {
  const chips = statusChips?.length ? (
    <ul className="le-page-header__chips" aria-label="Status">
      {statusChips.map((c, i) => (
        <li key={`${c.label}-${i}`}>
          <span className={`le-page-header__chip le-page-header__chip--${c.tone ?? 'muted'}`}>{c.label}</span>
        </li>
      ))}
    </ul>
  ) : null

  const overflow = secondaryMenuItems?.length ? (
    <PageHeaderActionsMenu items={secondaryMenuItems} />
  ) : null

  const toolbar =
    primaryAction || overflow || actions || chips ? (
      <div className="le-page-header__toolbar">
        {chips}
        {primaryAction ? <div className="le-page-header__primary">{primaryAction}</div> : null}
        {overflow}
        {actions ? <div className="le-page-header__actions">{actions}</div> : null}
      </div>
    ) : null

  return (
    <header
      className={`le-page-header le-page-header--shared${className ? ` ${className}` : ''}`}
      role="region"
      aria-labelledby={titleId}
    >
      {preface ? <div className="le-page-header__preface">{preface}</div> : null}
      <div className="le-page-header__title-row">
        <div className="le-page-header__lead">
          <h1 className="le-h1 le-page-header__title" id={titleId}>
            {title}
          </h1>
          {freshness ? <p className="le-page-header__freshness forge-support">{freshness}</p> : null}
        </div>
        {toolbar}
      </div>
      {purpose ? <p className="le-page-header__purpose">{purpose}</p> : null}
      {subtitle ? <p className="le-page-header__subtitle forge-support">{subtitle}</p> : null}
    </header>
  )
}
