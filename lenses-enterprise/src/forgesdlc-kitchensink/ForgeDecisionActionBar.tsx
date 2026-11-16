import type { ReactNode } from 'react'

export type ForgeDecisionActionBarProps = {
  children: ReactNode
  className?: string
  /** Sticky to viewport bottom (default true for review / approve flows). */
  sticky?: boolean
  'aria-label'?: string
}

/**
 * Sticky action strip for review, approve, reject, re-run, verify — host supplies buttons.
 */
export function ForgeDecisionActionBar({
  children,
  className = '',
  sticky = true,
  'aria-label': ariaLabel = 'Run actions',
}: ForgeDecisionActionBarProps) {
  return (
    <div
      className={`ks-fe-actionbar${sticky ? ' ks-fe-actionbar--sticky' : ''} ${className}`.trim()}
      role="toolbar"
      aria-label={ariaLabel}
    >
      <div className="ks-fe-actionbar__inner">{children}</div>
    </div>
  )
}
