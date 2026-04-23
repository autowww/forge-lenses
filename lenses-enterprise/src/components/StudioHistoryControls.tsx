import { useEffect, useId, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useNavigationMode } from '../nav/useNavigationMode'
import { getBackTarget } from '../nav/routeMeta'
import { useStudioNavigationTrail } from '../context/StudioNavigationTrailContext'
import type { StudioTrailEntry } from '../context/StudioNavigationTrailContext'

/**
 * Browser-style back/forward plus a recent-pages menu (session trail).
 * Complements breadcrumbs; back/forward use the real history stack.
 */
export function StudioHistoryControls() {
  const navigate = useNavigate()
  const location = useLocation()
  const { mode } = useNavigationMode()
  const { recent, goBack, goForward, goToEntry, currentKey } = useStudioNavigationTrail()
  const menuId = useId()
  const [menuOpen, setMenuOpen] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)

  const explicit = getBackTarget(location.pathname, location.search, mode)
  const isHome = location.pathname === '/' || location.pathname === ''

  useEffect(() => {
    if (!menuOpen) return
    function onDoc(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [menuOpen])

  const handleBackClick = () => {
    if (explicit) {
      navigate(explicit)
      return
    }
    goBack()
  }

  /** Newest-first for the menu */
  const menuEntries: StudioTrailEntry[] = [...recent].reverse()

  return (
    <div className="le-history-controls" ref={wrapRef}>
      {!isHome || explicit ? (
        <button
          type="button"
          className="le-back-btn"
          onClick={handleBackClick}
          aria-label="Go back"
          title={explicit ? 'Back to parent section' : 'Back'}
        >
          <span className="le-back-btn__icon" aria-hidden="true">
            ←
          </span>
          <span className="le-back-btn__text">Back</span>
        </button>
      ) : null}
      <button
        type="button"
        className="le-history-controls__fwd le-icon-btn le-icon-btn--panel"
        onClick={() => goForward()}
        aria-label="Go forward"
        title="Forward"
      >
        →
      </button>
      <div className="le-history-controls__menu-wrap">
        <button
          type="button"
          className="le-history-controls__menu-btn le-icon-btn le-icon-btn--panel"
          aria-expanded={menuOpen}
          aria-haspopup="true"
          aria-controls={menuId}
          title="Recent pages"
          aria-label="Open recent pages menu"
          onClick={() => setMenuOpen((o) => !o)}
        >
          <span aria-hidden="true">▾</span>
        </button>
        {menuOpen ? (
          <div id={menuId} className="le-history-controls__dropdown" role="menu">
            <p className="le-history-controls__dropdown-h">Recent in this session</p>
            {menuEntries.length === 0 ? (
              <p className="le-history-controls__dropdown-empty forge-support">No history yet</p>
            ) : (
              <ul className="le-history-controls__list">
                {menuEntries.map((e) => (
                  <li key={e.key}>
                    <button
                      type="button"
                      role="menuitem"
                      className={`le-history-controls__item${e.key === currentKey ? ' le-history-controls__item--current' : ''}`}
                      onClick={() => {
                        goToEntry(e)
                        setMenuOpen(false)
                      }}
                    >
                      {e.title}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}
      </div>
    </div>
  )
}
