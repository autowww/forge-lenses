import { useCallback, useRef, type ReactNode } from 'react'
import {
  STUDIO_VIEWER,
  VIEWER_EMBED_DISCLOSURE,
  type StudioEmbeddedPreviewKind,
} from '../nav/studioVisibleCopy'

/**
 * Sandboxed embed: blocks navigating the Studio top window (e.g. target=_top) while
 * keeping scripts, same-origin APIs, and new tabs/popups working for previews.
 */
export const EMBED_IFRAME_SANDBOX =
  'allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-modals allow-downloads'

type EmbeddedPreviewFrameProps = {
  title: string
  /** Initial iframe URL; also used by “Reset preview”. */
  src: string
  /** Extra controls before the standard preview actions (Overview, etc.). */
  toolbarBefore?: ReactNode
  /** CSS min-height for the frame (default matches docs/site preview). */
  frameMinHeight?: string
  /** When set, shows a Studio disclosure strip (embedded vs legacy vs cached). */
  disclosureKind?: StudioEmbeddedPreviewKind
  /** When false, omit the recovery hint under the frame (e.g. very short embeds). Default true. */
  showRecoveryHint?: boolean
}

/**
 * Static handbook / local-site / legacy Sites / blog mirror: toolbar stays outside the iframe
 * so Studio chrome is never lost; back/reset/reload operate on the embedded document only.
 */
export function EmbeddedPreviewFrame({
  title,
  src,
  toolbarBefore,
  frameMinHeight = 'min(70vh, 36rem)',
  disclosureKind,
  showRecoveryHint = true,
}: EmbeddedPreviewFrameProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const disc = disclosureKind ? VIEWER_EMBED_DISCLOSURE[disclosureKind] : null

  const goBackInPreview = useCallback(() => {
    try {
      iframeRef.current?.contentWindow?.history.back()
    } catch {
      /* cross-origin */
    }
  }, [])

  const resetPreview = useCallback(() => {
    const el = iframeRef.current
    if (!el) return
    el.src = src
  }, [src])

  const reloadPreview = useCallback(() => {
    const el = iframeRef.current
    if (!el) return
    try {
      el.contentWindow?.location.reload()
    } catch {
      const url = el.src
      el.src = ''
      el.src = url
    }
  }, [])

  return (
    <>
      {disc ? (
        <div
          className="le-viewer-embed-disclosure"
          role="status"
          aria-label="Preview type"
        >
          <span className="le-shortcut-pill" title={disc.lead}>
            {disc.pill}
          </span>
          <span className="le-viewer-embed-disclosure__lead forge-support">{disc.lead}</span>
        </div>
      ) : null}
      <div className="le-static-embed-toolbar forge-support">
        {toolbarBefore}
        <button
          type="button"
          className="le-btn"
          onClick={goBackInPreview}
          title="Go back one step inside the embedded page"
          aria-label="Back inside embedded preview"
        >
          ← In preview
        </button>
        <button
          type="button"
          className="le-btn"
          onClick={resetPreview}
          title="Reload the starting URL for this Studio view"
          aria-label="Reset embedded preview to starting page"
        >
          Reset preview
        </button>
        <button
          type="button"
          className="le-btn"
          onClick={reloadPreview}
          title="Reload the current embedded page"
          aria-label="Reload embedded preview"
        >
          Reload
        </button>
      </div>
      <div
        className="le-static-embed-frame-wrap"
        style={{ minHeight: frameMinHeight }}
      >
        <iframe
          ref={iframeRef}
          key={src}
          className="le-static-embed-frame"
          title={title}
          src={src}
          sandbox={EMBED_IFRAME_SANDBOX}
          style={{ minHeight: frameMinHeight }}
        />
      </div>
      {showRecoveryHint ? (
        <p className="le-viewer-embed-recovery forge-support" role="note">
          {STUDIO_VIEWER.embedRecoveryHint}
        </p>
      ) : null}
      <style>{`
        .le-viewer-embed-disclosure {
          display: flex;
          flex-wrap: wrap;
          align-items: flex-start;
          gap: 0.5rem 0.75rem;
          margin-bottom: 0.65rem;
          padding: 0.5rem 0.65rem;
          border: 1px solid var(--le-border, #334155);
          border-radius: 8px;
          background: rgba(0, 0, 0, 0.18);
        }
        .le-viewer-embed-disclosure__lead {
          flex: 1 1 12rem;
          margin: 0;
          line-height: 1.45;
          font-size: 0.82rem;
        }
        .le-viewer-embed-recovery {
          margin: 0.65rem 0 0;
          font-size: 0.78rem;
          line-height: 1.4;
          opacity: 0.92;
        }
        .le-static-embed-toolbar {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-bottom: 0.75rem;
          align-items: center;
        }
        .le-static-embed-frame-wrap {
          border: 1px solid var(--le-border, #334155);
          border-radius: 8px;
          overflow: hidden;
          background: #020617;
        }
        .le-static-embed-frame {
          width: 100%;
          border: 0;
          display: block;
        }
      `}</style>
    </>
  )
}
