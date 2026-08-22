import { useEffect, useId } from 'react'
import { createPortal } from 'react-dom'
import { StoryHubPanel } from './StoryHubPanel'

type Props = {
  open: boolean
  onClose: () => void
  nodeId: string
  story: Record<string, unknown> | null
  loading: boolean
  /** Jump to full-page Story tab with JSON / raw blocks. */
  onOpenFullStoryTab: () => void
}

export function StoryDetailModal({
  open,
  onClose,
  nodeId,
  story,
  loading,
  onOpenFullStoryTab,
}: Props) {
  const titleId = useId()

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
    <div className="le-story-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="le-story-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="le-story-modal__head">
          <h2 id={titleId} className="le-story-modal__title">
            Story details
          </h2>
          <div className="le-story-modal__actions">
            <button type="button" className="le-btn" onClick={onOpenFullStoryTab}>
              Open full story tab
            </button>
            <button type="button" className="le-story-modal__close" onClick={onClose} aria-label="Close">
              ×
            </button>
          </div>
        </div>
        <div className="le-story-modal__body">
          {loading ? (
            <p className="forge-support">Loading story…</p>
          ) : story && nodeId.trim() ? (
            <StoryHubPanel story={story} nodeId={nodeId} />
          ) : (
            <p className="forge-support">Could not load this story.</p>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
