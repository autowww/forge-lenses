import { useEffect, type ReactNode } from 'react'
import { assistShortcutsForContext, type AssistShortcutSpec } from '../../lib/uxPageState'
import { recordStatePanelView } from '../../telemetry/studioTelemetry'
import { StatePanelAiRecovery } from './StatePanelAiRecovery'
import { StatePanelAssistShortcuts } from './StatePanelAssistShortcuts'

export type StatePanelVariant =
  | 'loading'
  | 'empty'
  | 'error'
  | 'invalid'
  | 'stale'
  | 'legacy'
  /** Service or connector unreachable (softer than fatal error). */
  | 'unavailable'
  /** Missing prerequisites, feature flag off, or empty configuration. */
  | 'not_configured'
  /** Auth / role blocked. */
  | 'permission'
  /** Experimental or preview surfaces. */
  | 'beta'

export type StatePanelProps = {
  variant: StatePanelVariant
  title: string
  description?: ReactNode
  /** Raw message, status code, or JSON snippet — shown in a collapsible block. */
  technicalDetail?: string | null
  /** Optional Chat link with a prefilled recovery / “why empty” prompt. */
  aiRecovery?: { prompt: string; label?: string }
  /**
   * Adds “Explain this state”, “What can I do next?”, etc. (Copilot deep-links).
   * Use on primary pages when empty, blocked, or degraded.
   */
  assistShortcuts?: AssistShortcutSpec
  actions?: ReactNode
  /** Tighter padding for nested sections (e.g. inside home cards). */
  density?: 'default' | 'compact'
  className?: string
  id?: string
  /**
   * When set, records one UX telemetry sample per mount (skipped for `loading`) for empty/error frequency.
   */
  telemetryTag?: string
}

/**
 * Recovery-oriented status block: explains what happened, what to do next, and optional technical detail.
 */
export function StatePanel({
  variant,
  title,
  description,
  technicalDetail,
  aiRecovery,
  assistShortcuts,
  actions,
  density = 'default',
  className = '',
  id,
  telemetryTag,
}: StatePanelProps) {
  useEffect(() => {
    if (!telemetryTag || variant === 'loading') return
    recordStatePanelView(variant, telemetryTag)
  }, [variant, telemetryTag])

  const busy = variant === 'loading'
  const alertish = variant === 'error' || variant === 'invalid' || variant === 'permission'
  const role = alertish ? 'alert' : 'status'
  const rootClass = [
    'le-state-panel',
    `le-state-panel--${variant}`,
    density === 'compact' ? 'le-state-panel--compact' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <section
      id={id}
      className={rootClass}
      role={role}
      aria-busy={busy || undefined}
      aria-live={variant === 'loading' ? 'polite' : undefined}
    >
      <h2 className="le-state-panel__title">{title}</h2>
      {description ? <div className="le-state-panel__desc">{description}</div> : null}
      {aiRecovery ? <StatePanelAiRecovery prompt={aiRecovery.prompt} label={aiRecovery.label} /> : null}
      {assistShortcuts ? (
        <StatePanelAssistShortcuts actions={assistShortcutsForContext(assistShortcuts)} />
      ) : null}
      {technicalDetail ? (
        <details className="le-state-panel__technical">
          <summary>
            <span className="le-state-panel__technical-summary-text">Show technical details</span>
          </summary>
          <pre className="le-state-panel__technical-pre">{technicalDetail}</pre>
        </details>
      ) : null}
      {actions ? <div className="le-state-panel__actions">{actions}</div> : null}
    </section>
  )
}
