import type { CSSProperties, ReactNode } from 'react'

type WizardAlertProps = {
  role?: 'alert' | 'status'
  children: ReactNode
  className?: string
  style?: CSSProperties
}

/** Inline alert for wizard async errors — uses existing forge-support typography. */
export function WizardAlert({ role = 'alert', children, className, style }: WizardAlertProps) {
  return (
    <p className={className ?? 'forge-support'} role={role} style={{ marginTop: '0.75rem', ...style }}>
      {children}
    </p>
  )
}

type WizardRetryRowProps = {
  message: string
  onRetry: () => void
  retryLabel?: string
  disabled?: boolean
}

export function WizardRetryRow({ message, onRetry, retryLabel = 'Retry', disabled }: WizardRetryRowProps) {
  return (
    <div className="forge-support" style={{ marginTop: '0.75rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
      <span role="alert">{message}</span>
      <button type="button" className="le-btn le-btn--primary" disabled={disabled} onClick={onRetry}>
        {retryLabel}
      </button>
    </div>
  )
}
