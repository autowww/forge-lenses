import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import type { WorkspaceWebsite } from '../api/workspace'
import { type PublishHealthSummary } from '../lib/publishHealthSummary'
import { siteHealthSummary } from '../lib/siteHealthSummary'

type PublishHealthPopoverProps = {
  open: boolean
  onClose: () => void
  websites: WorkspaceWebsite[] | undefined
  summary: PublishHealthSummary
  anchorRef: React.RefObject<HTMLElement | null>
}

export function PublishHealthPopover({
  open,
  onClose,
  websites,
  summary,
  anchorRef,
}: PublishHealthPopoverProps) {
  const titleId = useId()
  const panelRef = useRef<HTMLDivElement | null>(null)
  const sites = websites ?? []

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  useEffect(() => {
    if (!open) return
    const focusable = panelRef.current?.querySelector<HTMLElement>(
      'button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    )
    focusable?.focus()
  }, [open])

  if (!open) return null

  return createPortal(
    <div className="le-publish-health-popover" role="presentation">
      <button
        type="button"
        className="le-publish-health-popover__backdrop"
        aria-label="Close publish health details"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        className="le-publish-health-popover__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        style={
          anchorRef.current
            ? {
                top: anchorRef.current.getBoundingClientRect().bottom + 8,
                left: Math.max(8, anchorRef.current.getBoundingClientRect().left - 120),
              }
            : undefined
        }
      >
        <header className="le-publish-health-popover__header">
          <h2 id={titleId}>Publish health</h2>
          <button type="button" className="le-btn le-btn--ghost" onClick={onClose}>
            Close
          </button>
        </header>
        <p className={`le-publish-health-popover__summary le-top-nav__publish-health--${summary.tone}`}>
          {summary.label}
        </p>
        {sites.length ? (
          <ul className="le-publish-health-popover__sites">
            {sites.map((w) => {
              const { healthSummary, readinessScore } = siteHealthSummary(w.html_total)
              return (
                <li key={w.name}>
                  <strong>{w.name}</strong>
                  <span className="forge-support">
                    {healthSummary} · {readinessScore}
                  </span>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="forge-support">No static sites were found in the latest workspace scan.</p>
        )}
        <footer className="le-publish-health-popover__footer">
          <Link className="le-btn le-btn--primary" to="/websites" onClick={onClose}>
            View all sites
          </Link>
        </footer>
      </div>
    </div>,
    document.body,
  )
}
