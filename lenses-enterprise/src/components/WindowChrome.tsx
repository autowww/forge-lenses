import { useCallback, useEffect, useState } from 'react'

function IconMinimize() {
  return (
    <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
      <path fill="currentColor" d="M0 5.5h12v1.5H0z" />
    </svg>
  )
}

function IconMaximize() {
  return (
    <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        d="M2.5 2.5h7v7h-7z"
      />
    </svg>
  )
}

function IconRestore() {
  return (
    <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        d="M4 2.5h5.5v5.5H4zM2.5 4v5.5h5.5"
      />
    </svg>
  )
}

function IconClose() {
  return (
    <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.35"
        strokeLinecap="round"
        d="M2.5 2.5l7 7m0-7l-7 7"
      />
    </svg>
  )
}

/**
 * Minimize / maximize / close for the frameless Electron shell (Studio only).
 * Renders nothing in the browser.
 */
export function WindowChrome() {
  const api = typeof window !== 'undefined' ? window.lensesElectron : undefined
  const [maximized, setMaximized] = useState(false)

  const refreshMax = useCallback(async () => {
    if (!api) return
    try {
      setMaximized(await api.isMaximized())
    } catch {
      /* ignore */
    }
  }, [api])

  useEffect(() => {
    if (!api) return
    void refreshMax()
    return api.onMaximizedChange((m) => setMaximized(m))
  }, [api, refreshMax])

  if (!api) {
    return null
  }

  return (
    <div className="le-window-chrome" role="group" aria-label="Window">
      <button
        type="button"
        className="le-window-chrome__btn"
        aria-label="Minimize"
        title="Minimize"
        onClick={() => void api.minimize()}
      >
        <IconMinimize />
      </button>
      <button
        type="button"
        className="le-window-chrome__btn"
        aria-label={maximized ? 'Restore' : 'Maximize'}
        title={maximized ? 'Restore' : 'Maximize'}
        onClick={() => void api.maximize().then(() => refreshMax())}
      >
        {maximized ? <IconRestore /> : <IconMaximize />}
      </button>
      <button
        type="button"
        className="le-window-chrome__btn le-window-chrome__btn--close"
        aria-label="Close"
        title="Close"
        onClick={() => void api.close()}
      >
        <IconClose />
      </button>
    </div>
  )
}
