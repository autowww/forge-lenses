import type { ReactNode } from 'react'
import type { ForgeStatusBannerVariant } from './forgeRunTypes'

export type ForgeStatusBannerProps = {
  variant: ForgeStatusBannerVariant
  title: string
  description?: ReactNode
  children?: ReactNode
  className?: string
  role?: 'status' | 'alert'
}

const VARIANT_CLASS: Record<ForgeStatusBannerVariant, string> = {
  cancelled: 'ks-fe-banner--cancelled',
  failed: 'ks-fe-banner--failed',
  awaiting_approval: 'ks-fe-banner--await',
  awaiting_input: 'ks-fe-banner--await',
  verified: 'ks-fe-banner--verified',
  info: 'ks-fe-banner--info',
  success: 'ks-fe-banner--success',
  warning: 'ks-fe-banner--warning',
}

/**
 * Prominent state banner for governed runs — cancelled, failed, awaiting human input, verified, etc.
 */
export function ForgeStatusBanner({
  variant,
  title,
  description,
  children,
  className = '',
  role = 'status',
}: ForgeStatusBannerProps) {
  const vc = VARIANT_CLASS[variant] || 'ks-fe-banner--info'
  return (
    <div className={`ks-fe-banner ${vc} ${className}`.trim()} role={role}>
      <div className="ks-fe-banner__body">
        <strong className="ks-fe-banner__title">{title}</strong>
        {description ? <div className="ks-fe-banner__desc">{description}</div> : null}
      </div>
      {children ? <div className="ks-fe-banner__actions">{children}</div> : null}
    </div>
  )
}
