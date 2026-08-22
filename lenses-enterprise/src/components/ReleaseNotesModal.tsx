import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { STUDIO_CHANGELOG_MARKDOWN } from '../data/studioChangelog'

export function ReleaseNotesModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="le-llm-settings-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="le-llm-settings-modal le-release-notes-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="le-release-notes-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="le-llm-settings-modal__head">
          <h2 id="le-release-notes-title" className="le-llm-settings-modal__title">
            Release notes
          </h2>
          <button type="button" className="le-llm-settings-modal__close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="le-llm-settings-modal__body">
          <div className="md-prose le-release-notes-modal__prose">
            <Markdown remarkPlugins={[remarkGfm]}>{STUDIO_CHANGELOG_MARKDOWN}</Markdown>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  )
}
