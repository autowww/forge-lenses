import type { ReactNode } from 'react'
import type { ForgeBadgeTone } from './forgeRunTypes'

export type ForgeRunBadge = {
  label: string
  tone?: ForgeBadgeTone
}

export type ForgeRunHeaderProps = {
  title: ReactNode
  subtitle?: ReactNode
  badges?: ForgeRunBadge[]
  /** Primary metadata area — often a ForgeKeyValueGrid or custom rows. */
  meta?: ReactNode
  /** Right-side or trailing actions (stop, export, etc.). */
  actions?: ReactNode
  className?: string
  headingId?: string
}

function badgeClass(tone: ForgeBadgeTone | undefined) {
  switch (tone) {
    case 'success':
      return 'ks-fe-badge ks-fe-badge--success'
    case 'warning':
      return 'ks-fe-badge ks-fe-badge--warning'
    case 'danger':
      return 'ks-fe-badge ks-fe-badge--danger'
    case 'info':
      return 'ks-fe-badge ks-fe-badge--info'
    default:
      return 'ks-fe-badge ks-fe-badge--neutral'
  }
}

/**
 * Enterprise header for governed run / case pages: title, subtitle, badges, metadata region, action slot.
 */
export function ForgeRunHeader({
  title,
  subtitle,
  badges,
  meta,
  actions,
  className = '',
  headingId,
}: ForgeRunHeaderProps) {
  return (
    <header className={`ks-fe-run-header ${className}`.trim()}>
      <div className="ks-fe-run-header__top">
        <div className="ks-fe-run-header__titles">
          <h2 className="ks-fe-run-header__title" id={headingId}>
            {title}
          </h2>
          {subtitle ? <p className="ks-fe-run-header__subtitle">{subtitle}</p> : null}
        </div>
        <div className="ks-fe-run-header__actions">{actions}</div>
      </div>
      {badges && badges.length > 0 ? (
        <ul className="ks-fe-run-header__badges" aria-label="Run badges">
          {badges.map((b, i) => (
            <li key={`${b.label}-${i}`}>
              <span className={badgeClass(b.tone)}>{b.label}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {meta ? <div className="ks-fe-run-header__meta">{meta}</div> : null}
    </header>
  )
}
