import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { apiGetJson, apiPostJson } from '../api/http'
import {
  BoardPlanningShortcutStrip,
  BoardWorkshopEditor,
  BoardStickerboardSharePanel,
  BoardWorkshopPhaseStrip,
  type WorkshopBoardPayload,
  type WorkshopPhase,
} from '../components/boards'
import { ObjectMetaBar, PageHeader, StatePanel } from '../components/page'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { DELIVERY_LENS, FULL_WORKSPACE_UI, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

function stripForPost(b: WorkshopBoardPayload): WorkshopBoardPayload {
  const { board_acl, ...rest } = b as WorkshopBoardPayload & { board_acl?: unknown }
  void board_acl
  return rest
}

function parsePhase(raw: string | null): WorkshopPhase {
  if (raw === 'score' || raw === 'prioritize' || raw === 'capture') return raw
  return 'discover'
}

export function BoardEditorPage() {
  const { id = '' } = useParams()
  const boardId = decodeURIComponent(id)
  const [searchParams, setSearchParams] = useSearchParams()
  const phase = parsePhase(searchParams.get('phase'))
  const [prioritizeMode, setPrioritizeMode] = useState(phase === 'prioritize')

  useLensesCopilotPage({ route: 'board', entityId: boardId.trim() || undefined })

  const [draft, setDraft] = useState<WorkshopBoardPayload | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const displayTitle = useMemo(() => {
    const label = draft?.board_label?.trim()
    if (label) return label
    if (!boardId.trim()) return STUDIO_VOCAB.boardEditor
    return STUDIO_VOCAB.boardEditor
  }, [boardId, draft?.board_label])

  useEffect(() => {
    if (!boardId) return
    setLoading(true)
    setLoadError(null)
    apiGetJson<WorkshopBoardPayload>(`/api/sticker-board?board_id=${encodeURIComponent(boardId)}`)
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

  const setPhase = (p: WorkshopPhase) => {
    const next = new URLSearchParams(searchParams)
    next.set('phase', p)
    setSearchParams(next, { replace: true })
    setPrioritizeMode(p === 'prioritize')
    setDraft((prev) => (prev ? { ...prev, workshop_phase: p } : prev))
  }

  useEffect(() => {
    setPrioritizeMode(phase === 'prioritize')
  }, [phase])

  useEffect(() => {
    if (!draft || !boardId) return
    const wp = draft.workshop_phase
    if (wp && wp !== phase) {
      const next = new URLSearchParams(searchParams)
      next.set('phase', wp)
      setSearchParams(next, { replace: true })
    }
  }, [draft?.workshop_phase, boardId, phase, searchParams, setSearchParams])

  async function save() {
    if (!draft) return
    setMsg(null)
    try {
      const body = stripForPost({ ...draft, workshop_phase: phase })
      const r = await apiPostJson<{ ok?: boolean; error?: string }>(
        `/api/sticker-board?board_id=${encodeURIComponent(boardId)}`,
        body,
      )
      setMsg(r.error ? String(r.error) : 'Saved.')
      const b = await apiGetJson<WorkshopBoardPayload>(
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
            </>
          }
        />
      </>
    )
  }

  const prefillWarn =
    draft.session_template === 'product_map_workshop' &&
    draft.prefill_message &&
    draft.prefill_message !== 'ok' &&
    !(draft.stickers?.length)

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
            {phase === 'prioritize' ? (
              <button
                type="button"
                className={`le-btn${prioritizeMode ? ' le-btn--primary' : ''}`}
                onClick={() => setPrioritizeMode((v) => !v)}
              >
                Sort by priority
              </button>
            ) : null}
            <a className="le-btn" href={`/board/${encodeURIComponent(boardId)}`}>
              {FULL_WORKSPACE_UI.openFullBoardEditor}{' '}
              <span className="le-shortcut-pill">Classic</span>
            </a>
          </>
        }
      />
      <BoardPlanningShortcutStrip />
      {prefillWarn ? (
        <StatePanel
          variant="invalid"
          density="compact"
          title="No WBS data for this project"
          description="Add docs/requirements/WBS.md under the project, or pick another project when creating the board."
          technicalDetail={draft.prefill_message}
        />
      ) : null}
      <BoardStickerboardSharePanel boardId={boardId} boardLabel={draft.board_label} />
      <BoardWorkshopPhaseStrip boardId={boardId} phase={phase} onPhaseChange={setPhase} />
      <ObjectMetaBar
        label="Board metadata"
        items={[
          { label: 'Name', value: draft.board_label ?? displayTitle },
          { label: 'Board id', value: boardId },
          { label: 'Project', value: draft.project ?? '—' },
          { label: 'Session', value: draft.session_template ?? '—' },
          { label: 'Layout', value: draft.template ?? '—' },
          { label: 'Storage', value: draft.board_storage ?? '—' },
        ]}
      />
      {msg ? (
        <p className={msg === 'Saved.' ? 'forge-support' : 'le-danger'} style={{ marginBottom: '0.75rem' }}>
          {msg}
        </p>
      ) : null}
      <BoardWorkshopEditor
        boardId={boardId}
        draft={draft}
        setDraft={setDraft}
        phase={phase}
        prioritizeMode={prioritizeMode}
      />
      <details className="le-raw-wrap">
        <summary>Raw JSON (advanced)</summary>
        <pre className="le-preview le-json" style={{ maxHeight: '16rem' }}>
          {JSON.stringify(draft, null, 2)}
        </pre>
      </details>
    </>
  )
}
