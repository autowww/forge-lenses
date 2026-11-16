/**
 * Read-only two-column preview before replacing Foundation Brief Markdown from a structured draft sync.
 */
import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import './blueprints-wizard-shell.css'

type Props = {
  open: boolean
  /** Markdown currently shown (wizard domain or legacy string). */
  currentMarkdown: string
  /** Markdown that will be written on confirm. */
  nextMarkdown: string
  onCancel: () => void
  onConfirm: () => void
  confirmBusy: boolean
}

function collectFocusables(container: HTMLElement): HTMLElement[] {
  const sel =
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  return Array.from(container.querySelectorAll<HTMLElement>(sel)).filter(
    (el) => !el.hasAttribute('disabled') && el.getAttribute('aria-hidden') !== 'true',
  )
}

export function SyncDraftPreviewDialog({
  open,
  currentMarkdown,
  nextMarkdown,
  onCancel,
  onConfirm,
  confirmBusy,
}: Props) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const cancelButtonRef = useRef<HTMLButtonElement>(null)
  const previouslyFocusedRef = useRef<HTMLElement | null>(null)
  const titleId = useId()
  const descriptionId = useId()

  useEffect(() => {
    if (!open) return
    previouslyFocusedRef.current = (document.activeElement as HTMLElement) ?? null
    const id = window.requestAnimationFrame(() => {
      cancelButtonRef.current?.focus()
    })
    return () => {
      window.cancelAnimationFrame(id)
      const prev = previouslyFocusedRef.current
      if (prev && typeof prev.focus === 'function') {
        prev.focus()
      }
    }
  }, [open])

  useEffect(() => {
    if (!open) return

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (!confirmBusy) {
          e.preventDefault()
          e.stopPropagation()
          onCancel()
        }
        return
      }

      if (e.key !== 'Tab' || !dialogRef.current) return
      const container = dialogRef.current
      const list = collectFocusables(container)
      if (list.length === 0) return

      const active = document.activeElement as HTMLElement | null
      if (!active || !container.contains(active)) {
        e.preventDefault()
        list[0]?.focus()
        return
      }

      const first = list[0]
      const last = list[list.length - 1]
      if (e.shiftKey) {
        if (active === first) {
          e.preventDefault()
          last.focus()
        }
      } else if (active === last) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown, true)
    return () => document.removeEventListener('keydown', onKeyDown, true)
  }, [open, confirmBusy, onCancel])

  if (!open) return null

  const modal = (
    <div
      className="le-bpwizard-sync-preview-backdrop"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget && !confirmBusy) onCancel()
      }}
    >
      <div
        ref={dialogRef}
        className="le-bpwizard-sync-preview-dialog forge-support"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id={titleId} style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '0.5rem' }}>
          Replace Foundation Brief Markdown?
        </h2>
        <p id={descriptionId} style={{ fontSize: '0.9rem', opacity: 0.92, marginBottom: '0.75rem' }}>
          Compare current content (left) with the Markdown generated from the interpretation draft (right). This
          replaces both <code className="le-mono">wizard_domain.foundation_brief.markdown</code> and, when present,
          the legacy <code className="le-mono">payload.foundation_brief</code> string.
        </p>
        <div
          className="le-bpwizard-sync-preview-columns"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(14rem, 1fr))',
            gap: '0.75rem',
            alignItems: 'start',
            marginBottom: '1rem',
          }}
        >
          <div style={{ minWidth: 0 }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.35rem' }}>Current</h3>
            <pre
              className="le-preview"
              style={{
                margin: 0,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                maxHeight: 'min(42vh, 24rem)',
                overflow: 'auto',
                fontSize: '0.82rem',
              }}
            >
              {currentMarkdown || '(empty)'}
            </pre>
          </div>
          <div style={{ minWidth: 0 }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.35rem' }}>After sync</h3>
            <pre
              className="le-preview"
              style={{
                margin: 0,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                maxHeight: 'min(42vh, 24rem)',
                overflow: 'auto',
                fontSize: '0.82rem',
              }}
            >
              {nextMarkdown}
            </pre>
          </div>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', justifyContent: 'flex-end' }}>
          <button
            ref={cancelButtonRef}
            type="button"
            className="forge-support"
            disabled={confirmBusy}
            onClick={onCancel}
          >
            Cancel
          </button>
          <button type="button" className="le-btn le-btn--primary" disabled={confirmBusy} onClick={onConfirm}>
            {confirmBusy ? 'Replacing…' : 'Replace'}
          </button>
        </div>
      </div>
    </div>
  )

  /* Outside #root so `MainContentInert` can target studio chrome without silencing this dialog. */
  return createPortal(modal, document.body)
}
