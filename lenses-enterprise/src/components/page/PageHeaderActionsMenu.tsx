import { useEffect, useId, useRef, useState } from 'react'
import { NavLink } from 'react-router-dom'

export type PageHeaderSecondaryItem = {
  key: string
  label: string
  to?: string
  href?: string
  external?: boolean
}

type Props = {
  items: PageHeaderSecondaryItem[]
  /** Button label — keep short for the toolbar. */
  triggerLabel?: string
  menuLabel?: string
}

/**
 * Overflow menu for secondary page actions (keyboard-friendly, closes on outside click).
 */
export function PageHeaderActionsMenu({
  items,
  triggerLabel = 'More',
  menuLabel = 'Additional actions',
}: Props) {
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

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  if (items.length === 0) return null

  return (
    <div className="le-page-header__overflow-wrap" ref={wrapRef}>
      <button
        type="button"
        className="le-btn le-btn--small le-page-header__overflow-trigger"
        aria-expanded={open}
        aria-haspopup="true"
        aria-controls={menuId}
        onClick={() => setOpen((o) => !o)}
      >
        {triggerLabel}
      </button>
      {open ? (
        <div id={menuId} className="le-page-header__overflow-menu" role="menu" aria-label={menuLabel}>
          {items.map((it) => {
            if (it.to) {
              return (
                <NavLink
                  key={it.key}
                  role="menuitem"
                  className={({ isActive }) =>
                    `le-page-header__overflow-item${isActive ? ' le-page-header__overflow-item--active' : ''}`
                  }
                  to={it.to}
                  onClick={() => setOpen(false)}
                >
                  {it.label}
                </NavLink>
              )
            }
            if (it.href) {
              return (
                <a
                  key={it.key}
                  role="menuitem"
                  className="le-page-header__overflow-item"
                  href={it.href}
                  {...(it.external ? { target: '_blank', rel: 'noreferrer' } : {})}
                  onClick={() => setOpen(false)}
                >
                  {it.label}
                  {it.external ? <span aria-hidden="true"> ↗</span> : null}
                </a>
              )
            }
            return null
          })}
        </div>
      ) : null}
    </div>
  )
}
