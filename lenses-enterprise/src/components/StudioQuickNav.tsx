import { useEffect, useId, useRef, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { STUDIO_VOCAB } from '../nav/studioVisibleCopy'

type QuickLink = { label: string; to: string; end?: boolean }

const LINKS: QuickLink[] = [
  { label: 'Home', to: '/', end: true },
  { label: STUDIO_VOCAB.work, to: '/plan' },
  { label: STUDIO_VOCAB.projects, to: '/projects' },
  { label: STUDIO_VOCAB.knowledge, to: '/tutorials' },
  { label: STUDIO_VOCAB.publish, to: '/websites' },
  { label: STUDIO_VOCAB.search, to: '/search' },
  { label: STUDIO_VOCAB.llmChat, to: '/chat' },
]

/**
 * Compact “Go to” menu — fastest navigation without expanding the primary tabs.
 * Complements Find / Ask / Do in the header utilities.
 */
export function StudioQuickNav() {
  const menuId = useId()
  const [open, setOpen] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onDoc(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  return (
    <div className="le-quick-nav" ref={wrapRef}>
      <button
        type="button"
        className="le-icon-btn le-icon-btn--panel"
        aria-expanded={open}
        aria-haspopup="true"
        aria-controls={menuId}
        title="Go to primary areas or header utilities — advanced admin and automation live under Settings (gear)"
        onClick={() => setOpen((o) => !o)}
      >
        Go
      </button>
      {open ? (
        <div id={menuId} className="le-quick-nav__menu" role="menu">
          <p className="le-quick-nav__head">Quick navigation</p>
          <ul className="le-quick-nav__list">
            {LINKS.map((l) => (
              <li key={l.to}>
                <NavLink
                  role="menuitem"
                  to={l.to}
                  end={l.end}
                  className={({ isActive }) =>
                    `le-quick-nav__link${isActive ? ' le-quick-nav__link--active' : ''}`
                  }
                  onClick={() => setOpen(false)}
                >
                  {l.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
