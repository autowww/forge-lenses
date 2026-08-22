import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { apiGetJson } from '../api/http'
import { useWorkspace } from '../context/WorkspaceContext'
import { buildAttentionItems, type AttentionItem } from './shell/attentionFromWorkspace'
import { AttentionItemsList } from './shell/AttentionItemsList'

type CatalogNotificationsRes = {
  ok?: boolean
  notifications?: Array<{
    id?: string
    headline?: string
    scope_label?: string
    action_hint?: string
    try_chat_to?: string
  }>
}

function IconBell() {
  return (
    <svg className="le-header-icon-svg" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"
      />
    </svg>
  )
}

export function AttentionNotifications() {
  const { state, loading } = useWorkspace()
  const [catalogItems, setCatalogItems] = useState<AttentionItem[]>([])

  useEffect(() => {
    if (loading || !state) return
    let cancelled = false
    apiGetJson<CatalogNotificationsRes>('/api/llm/model-catalog-notifications')
      .then((r) => {
        if (cancelled || r.ok !== true || !Array.isArray(r.notifications)) return
        setCatalogItems(
          r.notifications.map((n) => ({
            id: String(n.id ?? `llm-catalog-${Math.random()}`),
            category: 'catalog',
            headline: String(n.headline ?? 'New models available'),
            scopeLabel: String(n.scope_label ?? ''),
            actionHint: String(n.action_hint ?? 'Open Chat to try a model.'),
            to: n.try_chat_to ? String(n.try_chat_to) : '/chat',
          })),
        )
      })
      .catch(() => {
        if (!cancelled) setCatalogItems([])
      })
    return () => {
      cancelled = true
    }
  }, [loading, state])

  const items = useMemo(() => {
    const merged = [...catalogItems, ...buildAttentionItems(state)]
    return merged.slice(0, 12)
  }, [catalogItems, state])
  const n = items.length
  const [open, setOpen] = useState(false)
  const btnRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const [panelPos, setPanelPos] = useState({ top: 0, right: 0 })

  useLayoutEffect(() => {
    if (!open || !btnRef.current) return
    const r = btnRef.current.getBoundingClientRect()
    setPanelPos({ top: r.bottom + 8, right: Math.max(8, window.innerWidth - r.right) })
  }, [open])

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    function onPointerDown(e: MouseEvent | PointerEvent) {
      const t = e.target as Node
      if (btnRef.current?.contains(t)) return
      if (panelRef.current?.contains(t)) return
      setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    window.addEventListener('pointerdown', onPointerDown, true)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('pointerdown', onPointerDown, true)
    }
  }, [open])

  const panel = open ? (
    <>
      <div
        className="le-attention-popover__backdrop"
        aria-hidden
        onClick={() => setOpen(false)}
      />
      <div
        ref={panelRef}
        className="le-attention-popover"
        role="dialog"
        aria-modal="true"
        aria-labelledby="le-attention-popover-title"
        style={{ top: panelPos.top, right: panelPos.right }}
      >
        <div className="le-attention-popover__head">
          <h2 id="le-attention-popover-title" className="le-attention-popover__title">
            Attention
          </h2>
          <p className="le-attention-popover__sub">
            Workspace scan exceptions, Forge Fleet &quot;Test Fleet&quot; CPU summaries when the Fleet server writes
            attention into this workspace, and new model notices when URL-backed LLM catalogs change.
          </p>
        </div>
        {n === 0 ? (
          <p className="le-attention-popover__empty">No attention items.</p>
        ) : (
          <div className="le-attention-popover__scroll">
            <AttentionItemsList items={items} />
          </div>
        )}
      </div>
    </>
  ) : null

  return (
    <div className="le-header-notifications">
      <button
        ref={btnRef}
        type="button"
        className="le-icon-btn le-icon-btn--panel"
        title="Workspace attention"
        aria-label={n > 0 ? `Attention: ${n} item${n === 1 ? '' : 's'}` : 'Attention (no items)'}
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => setOpen((v) => !v)}
      >
        <IconBell />
        {n > 0 ? (
          <span className="le-header-notifications__badge" aria-hidden>
            {n > 99 ? '99+' : n}
          </span>
        ) : null}
      </button>
      {panel && typeof document !== 'undefined' ? createPortal(panel, document.body) : null}
    </div>
  )
}
