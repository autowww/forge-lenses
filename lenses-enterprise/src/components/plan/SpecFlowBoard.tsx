import { useCallback, useState } from 'react'
import { apiPostJson } from '../../api/http'

export type SpecFlowCard = {
  epic_id: string
  title?: string
  column: string
  change_slug?: string
  charge_status?: string
  actor?: string
  validate_ok?: boolean
  overlays?: string[]
  plan_href?: string
}

export type SpecFlowColumn = { id: string; label: string }

type Props = {
  columns: SpecFlowColumn[]
  cards: SpecFlowCard[]
  wbsP: string
  repo: string
  selectedId?: string
  onSelect: (epicId: string) => void
  onTransitionComplete?: () => void
  dragEnabled?: boolean
}

const COLUMN_ORDER = ['intent', 'specify', 'ready', 'charged', 'apply', 'verify', 'archived']

/** Canon labels — must match Blueprints SPEC-FLOW-BOARD.md */
export const SPEC_FLOW_COLUMN_LABELS = [
  'Intent',
  'Specify',
  'Ready',
  'Charged',
  'Apply',
  'Verify',
  'Archived',
] as const

export function SpecFlowBoard({
  columns,
  cards,
  wbsP,
  repo,
  selectedId,
  onSelect,
  onTransitionComplete,
  dragEnabled = true,
}: Props) {
  const [dragEpic, setDragEpic] = useState<SpecFlowCard | null>(null)
  const [error, setError] = useState<string | null>(null)

  const labelById = Object.fromEntries(columns.map((c) => [c.id, c.label]))
  const orderedCols =
    COLUMN_ORDER.filter((id) => labelById[id]).map((id) => ({ id, label: labelById[id]! })) ||
    columns

  const cardsByCol = orderedCols.reduce<Record<string, SpecFlowCard[]>>((acc, col) => {
    acc[col.id] = cards.filter((c) => c.column === col.id)
    return acc
  }, {})

  const postTransition = useCallback(
    async (card: SpecFlowCard, toColumn: string) => {
      setError(null)
      try {
        const res = await apiPostJson<Record<string, unknown>>('/api/epic-spec-board/transition', {
          epic_id: card.epic_id,
          to_column: toColumn,
          change_slug: card.change_slug || undefined,
          wbs_p: wbsP,
          repo: repo || undefined,
        })
        if (!res.ok) {
          setError(String(res.detail || res.error || 'Transition failed'))
          return
        }
        onTransitionComplete?.()
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e))
      }
    },
    [wbsP, repo, onTransitionComplete],
  )

  const onDrop = (toColumn: string) => {
    if (!dragEnabled || !dragEpic) return
    if (dragEpic.column === toColumn) return
    if (toColumn === 'ready' && !dragEpic.validate_ok && dragEpic.column === 'specify') {
      setError('Ready requires OpenSpec validate --strict green.')
      return
    }
    void postTransition(dragEpic, toColumn)
    setDragEpic(null)
  }

  return (
    <section className="le-spec-flow-board" aria-label="Spec Flow board">
      <p className="forge-support le-spec-flow-board__lead">
        OpenSpec Kanban derived from WBS Epics, Charge, and openspec/changes/. Drag updates Charge
        and OpenSpec phase (loopback write).
      </p>
      {error ? (
        <p className="forge-support" role="alert" style={{ color: 'var(--le-danger, #f87171)' }}>
          {error}
        </p>
      ) : null}
      <div className="le-spec-flow-board__grid">
        {orderedCols.map((col) => (
          <div
            key={col.id}
            className="le-spec-flow-board__col"
            onDragOver={(e) => {
              if (dragEnabled) e.preventDefault()
            }}
            onDrop={() => onDrop(col.id)}
          >
            <h3 className="le-spec-flow-board__col-title">{col.label}</h3>
            <ul className="le-list le-spec-flow-board__cards">
              {(cardsByCol[col.id] ?? []).length === 0 ? (
                <li className="le-muted" style={{ fontSize: '0.85rem', listStyle: 'none' }}>
                  —
                </li>
              ) : (
                (cardsByCol[col.id] ?? []).map((card) => (
                  <li key={card.epic_id} style={{ listStyle: 'none', marginBottom: '0.35rem' }}>
                    <button
                      type="button"
                      className={`le-card le-spec-flow-card${selectedId === card.epic_id ? ' le-spec-flow-card--selected' : ''}`}
                      draggable={dragEnabled}
                      onDragStart={() => setDragEpic(card)}
                      onDragEnd={() => setDragEpic(null)}
                      onClick={() => onSelect(card.epic_id)}
                      style={{ width: '100%', textAlign: 'left', cursor: dragEnabled ? 'grab' : 'pointer' }}
                    >
                      <strong>{card.epic_id}</strong>
                      {card.title && card.title !== card.epic_id ? (
                        <span className="forge-support"> — {card.title}</span>
                      ) : null}
                      {card.change_slug ? (
                        <div className="le-mono forge-support" style={{ fontSize: '0.75rem' }}>
                          {card.change_slug}
                        </div>
                      ) : null}
                      {(card.overlays ?? []).length > 0 ? (
                        <div style={{ marginTop: '0.25rem' }}>
                          {(card.overlays ?? []).map((o) => (
                            <span
                              key={o}
                              className="le-muted"
                              style={{
                                fontSize: '0.7rem',
                                marginRight: '0.35rem',
                                border: '1px solid var(--le-border, #94a3b840)',
                                borderRadius: 4,
                                padding: '0.05rem 0.3rem',
                              }}
                            >
                              {o}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </button>
                  </li>
                ))
              )}
            </ul>
          </div>
        ))}
      </div>
      <style>{`
        .le-spec-flow-board__grid {
          display: grid;
          grid-template-columns: repeat(7, minmax(8rem, 1fr));
          gap: 0.5rem;
          overflow-x: auto;
          padding-bottom: 0.5rem;
        }
        .le-spec-flow-board__col {
          min-width: 8rem;
          border: 1px solid var(--le-border, #94a3b840);
          border-radius: 6px;
          padding: 0.5rem;
          background: var(--le-surface-1, rgba(255,255,255,0.03));
        }
        .le-spec-flow-board__col-title {
          font-size: 0.8rem;
          font-weight: 650;
          margin: 0 0 0.5rem;
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }
        .le-spec-flow-card--selected {
          outline: 2px solid var(--le-accent, #3b82f6);
        }
      `}</style>
    </section>
  )
}
