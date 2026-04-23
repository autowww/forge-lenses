import { useEffect, useId, useRef, useState } from 'react'
import {
  downloadStudioMainPagePdf,
  downloadStudioMainPagePng,
  getStudioExportRootElement,
} from '../lib/studioPageExport'

function IconExport() {
  return (
    <svg className="le-header-icon-svg" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        fill="currentColor"
        d="M19 12v7H5v-7H3v7c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2v-7h-2zm-6 .67l2.59-2.58L17 11.5l-5 5-5-5 1.41-1.41L11 12.67V3h2v9.67z"
      />
    </svg>
  )
}

export function StudioPageExportMenu() {
  const menuId = useId()
  const wrapRef = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    function onDoc(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const close = () => {
    setOpen(false)
    setError(null)
  }

  async function run(kind: 'png' | 'pdf') {
    if (!getStudioExportRootElement()) {
      setError('Page is not ready to export yet.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      if (kind === 'png') {
        await downloadStudioMainPagePng()
      } else {
        await downloadStudioMainPagePdf()
      }
      close()
    } catch (e) {
      const msg =
        e instanceof Error
          ? e.message
          : 'Export failed. If this page embeds external content, try a view without cross-origin previews.'
      setError(msg)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="le-settings-menu-wrap" ref={wrapRef}>
      <button
        type="button"
        className="le-icon-btn le-icon-btn--panel"
        aria-expanded={open}
        aria-haspopup="true"
        aria-controls={menuId}
        title="Export scrollable center column — full height including scrolled content; PNG snapshot or text PDF (sidebar, evidence rail, and Copilot excluded)"
        aria-label="Export center column"
        disabled={busy}
        aria-busy={busy}
        onClick={() => {
          setError(null)
          setOpen((o) => !o)
        }}
      >
        <IconExport />
      </button>
      {open ? (
        <div id={menuId} className="le-settings-menu" role="menu">
          <p className="le-settings-menu__section">Export page</p>
          <p className="le-settings-menu__micro" id={`${menuId}-hint`}>
            Saves the full scrollable center column (all vertical scroll, including nested panes reset to the
            top for capture). Sidebar and Copilot are excluded; the evidence rail is omitted. PNG matches
            pixels. PDF uses selectable text (not a screenshot); charts may look different than on screen.
            Embedded previews may be blank if the browser blocks cross-origin capture.
          </p>
          <button
            type="button"
            className="le-settings-menu__item le-settings-menu__item--link"
            role="menuitem"
            disabled={busy}
            aria-describedby={`${menuId}-hint`}
            onClick={() => void run('png')}
          >
            Download PNG…
          </button>
          <button
            type="button"
            className="le-settings-menu__item le-settings-menu__item--link"
            role="menuitem"
            disabled={busy}
            aria-describedby={`${menuId}-hint`}
            onClick={() => void run('pdf')}
          >
            Download PDF (text)…
          </button>
          {busy ? (
            <p className="le-settings-menu__micro" role="status" aria-live="polite">
              Rendering…
            </p>
          ) : null}
          {error ? (
            <p className="le-settings-menu__micro le-settings-menu__error" role="alert">
              {error}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
