import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { apiPostJson } from '../../api/http'
import {
  EFFORT_TIERS,
  IMPACT_TIERS,
  impactEffortLabel,
  priorityFromLabels,
} from '../../lib/boardScoringTiers'
import type { WorkshopPhase } from './BoardWorkshopPhaseStrip'

export type WorkshopSticker = {
  id: string
  column_id: string | null
  title?: string
  body?: string
  order?: number
  x?: number
  y?: number
  impact?: number | null
  effort?: number | null
  impact_label?: string | null
  effort_label?: string | null
  scored_by_display_name?: string
  source_node_id?: string
  source_kind?: string
}

export type WorkshopBoardPayload = {
  version?: number
  columns?: { id: string; title: string }[]
  stickers?: WorkshopSticker[]
  template?: string
  board_storage?: string
  session_template?: string
  board_label?: string
  project?: string
  workshop_phase?: string
  prefill_applied?: boolean
  prefill_message?: string
  saved_kanban_columns?: { id: string; title: string }[]
}

function uid(): string {
  return `s-${crypto.randomUUID().slice(0, 10)}`
}

function previewText(body: string | undefined): string {
  const t = (body || '').replace(/\s+/g, ' ').trim()
  if (t.length > 120) return `${t.slice(0, 119)}…`
  return t || '—'
}

function priorityScore(s: WorkshopSticker): number | null {
  if (s.impact_label || s.effort_label) {
    return priorityFromLabels(s.impact_label, s.effort_label)
  }
  const i = s.impact
  const e = s.effort
  if (i == null || e == null || e < 1) return null
  return Math.round((i / e) * 10) / 10
}

export type BoardWorkshopEditorProps = {
  boardId: string
  draft: WorkshopBoardPayload
  setDraft: React.Dispatch<React.SetStateAction<WorkshopBoardPayload | null>>
  phase: WorkshopPhase
  prioritizeMode: boolean
  /** View-only guest share: no edits or saves. */
  readOnly?: boolean
}

export function BoardWorkshopEditor({
  boardId,
  draft,
  setDraft,
  phase,
  prioritizeMode,
  readOnly = false,
}: BoardWorkshopEditorProps) {
  const [status, setStatus] = useState('')
  const [editing, setEditing] = useState<WorkshopSticker | null>(null)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const isKanban = draft.template === 'kanban'
  const columns = draft.columns ?? []
  const stickers = draft.stickers ?? []

  const showTierPickers =
    !readOnly && (phase === 'score' || phase === 'prioritize' || phase === 'discover')

  const scheduleSave = useCallback(() => {
    if (readOnly) return
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      void (async () => {
        setStatus('Saving…')
        const body = { ...draft }
        delete (body as { board_acl?: unknown }).board_acl
        try {
          const r = await apiPostJson<{ ok?: boolean; error?: string }>(
            `/api/sticker-board?board_id=${encodeURIComponent(boardId)}`,
            body,
          )
          setStatus(r.error ? `Save failed: ${r.error}` : 'Saved')
        } catch (e) {
          setStatus(e instanceof Error ? e.message : String(e))
        }
      })()
    }, 650)
  }, [boardId, draft, readOnly])

  useEffect(
    () => () => {
      if (saveTimer.current) clearTimeout(saveTimer.current)
    },
    [],
  )

  const updateSticker = (sid: string, patch: Partial<WorkshopSticker>) => {
    setDraft((prev) => {
      if (!prev?.stickers) return prev
      return {
        ...prev,
        stickers: prev.stickers.map((s) => (s.id === sid ? { ...s, ...patch } : s)),
      }
    })
    scheduleSave()
  }

  const addSticker = (columnId: string | null) => {
    const col = columnId ?? columns[0]?.id ?? null
    const order =
      stickers.filter((s) => s.column_id === col).length
    const st: WorkshopSticker = {
      id: uid(),
      title: 'New item',
      body: '',
      column_id: col,
      order,
      x: 40,
      y: 40,
    }
    setDraft((prev) =>
      prev ? { ...prev, stickers: [...(prev.stickers ?? []), st] } : prev,
    )
    scheduleSave()
    setEditing(st)
  }

  const deleteSticker = (sid: string) => {
    setDraft((prev) =>
      prev
        ? { ...prev, stickers: (prev.stickers ?? []).filter((s) => s.id !== sid) }
        : prev,
    )
    setEditing(null)
    scheduleSave()
  }

  const stickersInColumn = useCallback(
    (colId: string) => {
      let list = stickers.filter((s) => s.column_id === colId)
      if (prioritizeMode && phase === 'prioritize') {
        list = [...list].sort((a, b) => {
          const pa = priorityScore(a)
          const pb = priorityScore(b)
          if (pa == null && pb == null) return (a.order ?? 0) - (b.order ?? 0)
          if (pa == null) return 1
          if (pb == null) return -1
          return pb - pa
        })
      } else {
        list.sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
      }
      return list
    },
    [stickers, prioritizeMode, phase],
  )

  const onDrop = (colId: string, stickerId: string) => {
    setDraft((prev) => {
      if (!prev?.stickers) return prev
      const siblings = prev.stickers.filter((s) => s.column_id === colId && s.id !== stickerId)
      return {
        ...prev,
        stickers: prev.stickers.map((s) =>
          s.id === stickerId ? { ...s, column_id: colId, order: siblings.length } : s,
        ),
      }
    })
    scheduleSave()
  }

  const cardEl = (st: WorkshopSticker, onOpen: () => void) => {
    const ps = priorityScore(st)
    return (
      <div
        key={st.id}
        className="fs-sticker-card le-sticker"
        draggable={isKanban && !readOnly}
        onDragStart={(e) => {
          e.dataTransfer.setData('text/plain', st.id)
          e.dataTransfer.effectAllowed = 'move'
        }}
        onDoubleClick={readOnly ? undefined : onOpen}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter') onOpen()
        }}
      >
        <p className="fs-sticker-card__title">{st.title || 'Untitled'}</p>
        <p className="fs-sticker-card__preview">{previewText(st.body)}</p>
        <div className="fs-sticker-card__badges">
          {st.impact_label || st.effort_label ? (
            <span className="fs-sticker-badge">{impactEffortLabel(st.impact_label, st.effort_label)}</span>
          ) : null}
          {st.impact != null && !st.impact_label ? (
            <span className="fs-sticker-badge">Impact {st.impact}</span>
          ) : null}
          {st.effort != null && !st.effort_label ? (
            <span className="fs-sticker-badge">Effort {st.effort}</span>
          ) : null}
          {ps != null ? <span className="fs-sticker-badge">Priority {ps}</span> : null}
          {st.source_node_id ? (
            <span className="fs-sticker-badge" title={st.source_node_id}>
              WBS
            </span>
          ) : null}
        </div>
      </div>
    )
  }

  const editorModal = editing ? (
    <div
      className="le-llm-settings-modal-backdrop"
      role="presentation"
      onClick={() => setEditing(null)}
    >
      <div
        className="le-llm-settings-modal"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="le-h2">Edit sticker</h2>
        <label className="forge-support" style={{ display: 'block' }}>
          Title
          <input
            className="le-input"
            style={{ width: '100%', marginTop: '0.25rem' }}
            value={editing.title ?? ''}
            onChange={(e) => setEditing({ ...editing, title: e.target.value })}
          />
        </label>
        <label className="forge-support" style={{ display: 'block', marginTop: '0.5rem' }}>
          Details
          <textarea
            className="le-input"
            style={{ width: '100%', minHeight: '6rem', marginTop: '0.25rem' }}
            value={editing.body ?? ''}
            onChange={(e) => setEditing({ ...editing, body: e.target.value })}
          />
        </label>
        {showTierPickers && (
          <div style={{ marginTop: '0.75rem' }}>
            <label className="forge-support" style={{ display: 'block' }}>
              Impact
              <select
                className="le-input"
                style={{ width: '100%', marginTop: '0.25rem' }}
                value={editing.impact_label ?? ''}
                onChange={(e) =>
                  setEditing({
                    ...editing,
                    impact_label: e.target.value || undefined,
                    impact: undefined,
                  })
                }
              >
                <option value="">—</option>
                {IMPACT_TIERS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
              <span className="forge-support" style={{ display: 'block', marginTop: '0.2rem' }}>
                {IMPACT_TIERS.find((t) => t.value === editing.impact_label)?.hint}
              </span>
            </label>
            <label className="forge-support" style={{ display: 'block', marginTop: '0.5rem' }}>
              Effort
              <select
                className="le-input"
                style={{ width: '100%', marginTop: '0.25rem' }}
                value={editing.effort_label ?? ''}
                onChange={(e) =>
                  setEditing({
                    ...editing,
                    effort_label: e.target.value || undefined,
                    effort: undefined,
                  })
                }
              >
                <option value="">—</option>
                {EFFORT_TIERS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
              <span className="forge-support" style={{ display: 'block', marginTop: '0.2rem' }}>
                {EFFORT_TIERS.find((t) => t.value === editing.effort_label)?.hint}
              </span>
            </label>
          </div>
        )}
        <div className="le-form-row" style={{ marginTop: '1rem' }}>
          <button
            type="button"
            className="le-btn le-btn--primary"
            onClick={() => {
              updateSticker(editing.id, {
                title: editing.title,
                body: editing.body,
                impact_label: editing.impact_label,
                effort_label: editing.effort_label,
                impact: undefined,
                effort: undefined,
              })
              setEditing(null)
            }}
          >
            Done
          </button>
          <button
            type="button"
            className="le-btn"
            onClick={() => {
              deleteSticker(editing.id)
            }}
          >
            Delete
          </button>
          <button type="button" className="le-btn" onClick={() => setEditing(null)}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  ) : null

  const toolbar = (
    <div className="fs-sticker-toolbar">
      {!readOnly ? (
        <button
          type="button"
          className="le-btn le-btn--primary"
          onClick={() => addSticker(columns[0]?.id ?? null)}
        >
          Add sticker
        </button>
      ) : null}
      <span className="forge-support">{status}</span>
      {draft.prefill_message && draft.prefill_message !== 'ok' ? (
        <span className="le-danger">Prefill: {draft.prefill_message}</span>
      ) : null}
    </div>
  )

  const kanban = (
    <div className="fs-sticker-kanban le-board-columns">
      {columns.map((col) => (
        <div key={col.id} className="fs-sticker-column le-board-col">
          <h4 className="fs-sticker-column__title">{col.title}</h4>
          <div
            className="fs-sticker-column__body"
            onDragOver={(e) => {
              e.preventDefault()
              e.currentTarget.classList.add('fs-sticker-column__body--drag-over')
            }}
            onDragLeave={(e) => {
              e.currentTarget.classList.remove('fs-sticker-column__body--drag-over')
            }}
            onDrop={(e) => {
              e.preventDefault()
              e.currentTarget.classList.remove('fs-sticker-column__body--drag-over')
              const sid = e.dataTransfer.getData('text/plain')
              if (sid) onDrop(col.id, sid)
            }}
          >
            {stickersInColumn(col.id).map((st) => cardEl(st, () => setEditing({ ...st })))}
          </div>
          {!readOnly ? (
            <button type="button" className="le-btn" onClick={() => addSticker(col.id)}>
              + Add
            </button>
          ) : null}
        </div>
      ))}
    </div>
  )

  const freeform = useMemo(
    () => (
      <div className="fs-sticker-canvas lenses-sticker-canvas">
        {stickers.map((st) => (
          <FreeformSticker
            key={st.id}
            sticker={st}
            onMove={(x, y) => updateSticker(st.id, { x, y })}
            onOpen={() => setEditing({ ...st })}
            renderCard={() => cardEl(st, () => setEditing({ ...st }))}
          />
        ))}
      </div>
    ),
    [stickers, prioritizeMode, phase],
  )

  return (
    <>
      {toolbar}
      {isKanban ? kanban : freeform}
      {editorModal}
    </>
  )
}

function FreeformSticker({
  sticker,
  onMove,
  onOpen,
  renderCard,
}: {
  sticker: WorkshopSticker
  onMove: (x: number, y: number) => void
  onOpen: () => void
  renderCard: () => React.ReactNode
}) {
  const drag = useRef<{
    active: boolean
    sx: number
    sy: number
    ox: number
    oy: number
  } | null>(null)

  return (
    <div
      className="fs-sticker-float"
      style={{ left: sticker.x ?? 0, top: sticker.y ?? 0 }}
      onPointerDown={(e) => {
        if (e.button !== 0) return
        drag.current = {
          active: true,
          sx: e.clientX,
          sy: e.clientY,
          ox: sticker.x ?? 0,
          oy: sticker.y ?? 0,
        }
        ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
      }}
      onPointerMove={(e) => {
        if (!drag.current?.active) return
        const dx = e.clientX - drag.current.sx
        const dy = e.clientY - drag.current.sy
        onMove(Math.max(0, drag.current.ox + dx), Math.max(0, drag.current.oy + dy))
      }}
      onPointerUp={(e) => {
        if (drag.current) drag.current.active = false
        try {
          ;(e.target as HTMLElement).releasePointerCapture(e.pointerId)
        } catch {
          /* ignore */
        }
      }}
      onDoubleClick={onOpen}
    >
      {renderCard()}
    </div>
  )
}
