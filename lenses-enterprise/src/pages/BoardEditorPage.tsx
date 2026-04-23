import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiGetJson, apiPostJson } from '../api/http'
import { BoardPlanningShortcutStrip } from '../components/boards'
import { ObjectMetaBar, PageHeader, StatePanel } from '../components/page'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { DELIVERY_LENS, FULL_WORKSPACE_UI, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

type Sticker = {
  id: string
  column_id: string
  title?: string
  body?: string
}

type BoardPayload = {
  version?: number
  columns?: { id: string; title: string }[]
  stickers?: Sticker[]
  template?: string
  board_storage?: string
  board_acl?: unknown
}

function stripForPost(b: BoardPayload): BoardPayload {
  const { board_acl, ...rest } = b
  void board_acl
  return rest
}

export function BoardEditorPage() {
  const { id = '' } = useParams()
  const boardId = decodeURIComponent(id)
  useLensesCopilotPage({ route: 'board', entityId: boardId.trim() || undefined })
  const displayTitle = useMemo(() => {
    const t = boardId.trim()
    if (!t) return STUDIO_VOCAB.boardEditor
    return t.length > 42 ? `${t.slice(0, 18)}…${t.slice(-12)}` : t
  }, [boardId])
  const [draft, setDraft] = useState<BoardPayload | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    if (!boardId) return
    // eslint-disable-next-line react-hooks/set-state-in-effect -- begin load before network
    setLoading(true)
    setLoadError(null)
    apiGetJson<BoardPayload>(`/api/sticker-board?board_id=${encodeURIComponent(boardId)}`)
      .then((b) => {
        setDraft(b)
        setLoadError(null)
      })
      .catch((e) => {
        setDraft(null)
        setLoadError(e instanceof Error ? e.message : String(e))
      })
      .finally(() => setLoading(false))
  }, [boardId])

  function updateSticker(sid: string, patch: Partial<Sticker>) {
    setDraft((prev) => {
      if (!prev?.stickers) return prev
      return {
        ...prev,
        stickers: prev.stickers.map((s) => (s.id === sid ? { ...s, ...patch } : s)),
      }
    })
  }

  async function save() {
    if (!draft) return
    setMsg(null)
    try {
      const body = stripForPost(draft)
      const r = await apiPostJson<{ ok?: boolean; error?: string }>(
        `/api/sticker-board?board_id=${encodeURIComponent(boardId)}`,
        body,
      )
      setMsg(r.error ? String(r.error) : 'Saved.')
      const b = await apiGetJson<BoardPayload>(
        `/api/sticker-board?board_id=${encodeURIComponent(boardId)}`,
      )
      setDraft(b)
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e))
    }
  }

  if (!boardId) {
    return (
      <StatePanel
        variant="invalid"
        title="Missing board id"
        description="Open a board from the boards hub, or use a link that includes the board identifier."
        actions={<Link to="/board">All boards</Link>}
      />
    )
  }

  if (loading) {
    return (
      <>
        <PageHeader title={displayTitle} subtitle={STUDIO_VOCAB.boardEditor} />
        <StatePanel
          variant="loading"
          title="Loading board"
          description="Fetching columns and stickers from the Lenses server."
        />
      </>
    )
  }

  if (!draft?.columns) {
    return (
      <>
        <PageHeader title={displayTitle} subtitle={STUDIO_VOCAB.boardEditor} />
        <StatePanel
          variant="error"
          title="Could not load board"
          description="The server returned no column layout. The board may have been removed, the id may be wrong, or you may lack access."
          technicalDetail={loadError}
          actions={
            <>
              <button type="button" className="le-btn le-btn--primary" onClick={() => window.location.reload()}>
                Retry
              </button>
              <Link className="le-btn" to="/board">
                Board hub
              </Link>
              <Link className="le-btn" to="/board?filter=attention">
                Hub: needs attention
              </Link>
              <a className="le-btn" href={`/board/${encodeURIComponent(boardId)}`}>
                {FULL_WORKSPACE_UI.openFullBoardEditor}
              </a>
            </>
          }
        />
      </>
    )
  }

  return (
    <>
      <PageHeader
        title={displayTitle}
        subtitle={`${STUDIO_VOCAB.boardEditor} · ${DELIVERY_LENS.boardEditorExecutionLead}`}
        preface={
          <Link to="/board" className="forge-support">
            ← {STUDIO_VOCAB.boards} hub
          </Link>
        }
        actions={
          <>
            <button type="button" className="le-btn le-btn--primary" onClick={() => void save()}>
              Save changes
            </button>
            <Link className="le-btn" to="/board?filter=attention">
              Review portfolio
            </Link>
            <a className="le-btn" href={`/board/${encodeURIComponent(boardId)}`}>
              {FULL_WORKSPACE_UI.openFullBoardEditor}{' '}
              <span className="le-shortcut-pill">Full UI</span>
            </a>
          </>
        }
      />
      <BoardPlanningShortcutStrip />
      <ObjectMetaBar
        label="Board metadata"
        items={[
          { label: 'Board id', value: boardId },
          { label: 'Storage', value: draft.board_storage ?? '—' },
          { label: 'Template', value: draft.template ?? '—' },
          {
            label: 'Freshness',
            value: 'See hub for preview mtime / stale flags',
          },
        ]}
      />
      {msg ? (
        <p className={msg === 'Saved.' ? 'forge-support' : 'le-danger'} style={{ marginBottom: '0.75rem' }}>
          {msg}
        </p>
      ) : null}
      <div className="le-board-columns">
        {draft.columns.map((col) => (
          <div key={col.id} className="le-board-col">
            <h4>{col.title}</h4>
            {(draft.stickers ?? [])
              .filter((s) => s.column_id === col.id)
              .map((s) => (
                <div key={s.id} className="le-sticker">
                  <label className="forge-support" style={{ display: 'block', fontSize: '0.7rem' }}>
                    {s.id}
                  </label>
                  <input
                    className="le-input"
                    style={{ width: '100%', marginBottom: '0.35rem' }}
                    value={s.title ?? ''}
                    onChange={(e) => updateSticker(s.id, { title: e.target.value })}
                    placeholder="Title"
                  />
                  <textarea
                    className="le-input"
                    style={{ width: '100%', minHeight: '4rem', fontFamily: 'inherit' }}
                    value={s.body ?? ''}
                    onChange={(e) => updateSticker(s.id, { body: e.target.value })}
                    placeholder="Body"
                  />
                </div>
              ))}
          </div>
        ))}
      </div>
      <details className="le-raw-wrap">
        <summary>Raw JSON (advanced)</summary>
        <pre className="le-preview le-json" style={{ maxHeight: '16rem' }}>
          {JSON.stringify(draft, null, 2)}
        </pre>
      </details>
    </>
  )
}
