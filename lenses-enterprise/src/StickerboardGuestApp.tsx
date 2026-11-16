import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiGetJson, apiPath, apiPostJson } from './api/http'
import {
  BoardWorkshopEditor,
  BoardWorkshopPhaseStrip,
  type WorkshopBoardPayload,
  type WorkshopPhase,
} from './components/boards'
import { StatePanel } from './components/page'

type ShareMeta = {
  ok?: boolean
  board_id?: string
  board_label?: string
  guest_role?: 'view' | 'edit'
  revoked?: boolean
  participants?: { login: string; display_name?: string }[]
}

type AuthStatus = {
  session_ok?: boolean
  session_login?: string
  oidc_configured?: boolean
  stickerboard_loopback_dev_auth?: boolean
}

type OidcStatus = {
  ok?: boolean
  configured?: boolean
  hint?: string
  discovery_ok?: boolean
  loopback_dev_auth?: boolean
}

function isLocalStickerboardHost(): boolean {
  if (typeof window === 'undefined') return false
  const h = window.location.hostname
  return h === '127.0.0.1' || h === 'localhost'
}

function parsePhase(raw: string | undefined): WorkshopPhase {
  if (raw === 'score' || raw === 'prioritize' || raw === 'capture') return raw
  return 'discover'
}

export function StickerboardGuestApp() {
  const { shareToken = '' } = useParams()
  const token = decodeURIComponent(shareToken).trim()

  const [meta, setMeta] = useState<ShareMeta | null>(null)
  const [auth, setAuth] = useState<AuthStatus | null>(null)
  const [oidcStatus, setOidcStatus] = useState<OidcStatus | null>(null)
  const [joined, setJoined] = useState(false)
  const [draft, setDraft] = useState<WorkshopBoardPayload | null>(null)
  const [phase, setPhase] = useState<WorkshopPhase>('discover')
  const [prioritizeMode, setPrioritizeMode] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const boardId = meta?.board_id ?? ''
  const guestRole = meta?.guest_role ?? 'view'
  const readOnly = guestRole === 'view'

  const refreshAuth = useCallback(async () => {
    try {
      const [a, oidc] = await Promise.all([
        apiGetJson<AuthStatus>('/api/auth/status'),
        apiGetJson<OidcStatus>('/api/auth/oidc/status'),
      ])
      setAuth(a)
      setOidcStatus(oidc)
      return a
    } catch (e) {
      setAuth(null)
      setOidcStatus(null)
      throw e
    }
  }, [])

  const oidcReady =
    oidcStatus?.configured !== false && auth?.oidc_configured !== false

  const refreshMeta = useCallback(async () => {
    if (!token) return
    const m = await apiGetJson<ShareMeta>(
      `/api/sticker-board-share?token=${encodeURIComponent(token)}`,
    )
    setMeta(m)
    if (m.revoked) {
      setErr('This share link was revoked by the facilitator.')
    }
  }, [token])

  const tryJoin = useCallback(async () => {
    if (!token) return
    await apiPostJson('/api/sticker-board-share/join', { share_token: token })
    setJoined(true)
  }, [token])

  const loopbackDevAuth =
    auth?.stickerboard_loopback_dev_auth === true || oidcStatus?.loopback_dev_auth === true

  const tryLoopbackLoginAndJoin = useCallback(async () => {
    await apiPostJson('/api/auth/loopback-dev-login', {})
    await tryJoin()
  }, [tryJoin])

  const loadBoard = useCallback(async () => {
    if (!boardId) return
    const b = await apiGetJson<WorkshopBoardPayload>(
      `/api/sticker-board?board_id=${encodeURIComponent(boardId)}`,
    )
    setDraft(b)
    setPhase(parsePhase(b.workshop_phase))
    setPrioritizeMode(parsePhase(b.workshop_phase) === 'prioritize')
  }, [boardId])

  useEffect(() => {
    if (!token) {
      setErr('Missing share token in URL.')
      setLoading(false)
      return
    }
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setErr(null)
      try {
        await refreshMeta()
        const a = await refreshAuth()
        if (!cancelled && a.session_ok) {
          await tryJoin()
        } else if (
          !cancelled &&
          !a.session_ok &&
          isLocalStickerboardHost() &&
          a.stickerboard_loopback_dev_auth
        ) {
          await tryLoopbackLoginAndJoin()
        }
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token, refreshMeta, refreshAuth, tryJoin, tryLoopbackLoginAndJoin])

  useEffect(() => {
    if (!joined || !boardId || meta?.revoked) return
    loadBoard().catch((e) => setErr(e instanceof Error ? e.message : String(e)))
  }, [joined, boardId, meta?.revoked, loadBoard])

  const loginHref = useMemo(() => {
    const prefix =
      typeof window !== 'undefined' && window.location.pathname.startsWith('/stickerboard')
        ? '/stickerboard'
        : ''
    const returnTo = `${prefix}/#/${encodeURIComponent(token)}`
    return `${apiPath('/api/auth/oidc/login')}?return_to=${encodeURIComponent(returnTo)}`
  }, [token])

  const setWorkshopPhase = (p: WorkshopPhase) => {
    setPhase(p)
    setPrioritizeMode(p === 'prioritize')
    setDraft((prev) => (prev ? { ...prev, workshop_phase: p } : prev))
  }

  if (!token) {
    return (
      <div className="fl-stickerboard-guest-shell">
        <StatePanel variant="error" title="Invalid link" description="No share token in the URL." />
      </div>
    )
  }

  return (
    <div className="fl-stickerboard-guest-shell">
      <header className="fl-stickerboard-guest-shell__header">
        <h1 className="le-h1">{meta?.board_label?.trim() || 'Forge Lenses Stickerboard'}</h1>
        <p className="forge-support">
          {meta?.board_label?.trim() ? 'Forge Lenses Stickerboard · ' : ''}
          sign in to participate
        </p>
      </header>

      {loading ? (
        <StatePanel variant="loading" title="Loading session" description="Checking share link and sign-in." />
      ) : null}

      {err ? (
        <StatePanel variant="error" title="Cannot open board" description={err} />
      ) : null}

      {!loading && !err && meta?.revoked ? null : null}

      {!loading && !err && !meta?.revoked && !auth?.session_ok && !joined ? (
        <div className="le-card" style={{ maxWidth: '28rem', margin: '1rem auto' }}>
          <p className="forge-support" style={{ marginBottom: '1rem' }}>
            Sign in with Google to join this board as{' '}
            <strong>{guestRole === 'edit' ? 'editor' : 'viewer'}</strong>.
          </p>
          {oidcReady ? (
            <a className="le-btn le-btn--primary" href={loginHref}>
              Sign in with Google
            </a>
          ) : (
            <StatePanel
              variant="error"
              density="compact"
              title="Sign-in not configured"
              description={
                oidcStatus?.hint ??
                'Add Google OAuth credentials to Code/.lenses-local/lenses-oidc.env (see forge-lenses/docs/examples/lenses-oidc.env.example), then restart Lenses.'
              }
            />
          )}
          {isLocalStickerboardHost() && loopbackDevAuth ? (
            <button
              type="button"
              className="le-btn le-btn--secondary"
              style={{ marginTop: '0.75rem', width: '100%' }}
              onClick={() => {
                tryLoopbackLoginAndJoin().catch((e) =>
                  setErr(e instanceof Error ? e.message : String(e)),
                )
              }}
            >
              Continue as local developer
            </button>
          ) : null}
        </div>
      ) : null}

      {!loading && !err && joined && draft ? (
        <>
          <BoardWorkshopPhaseStrip phase={phase} onPhaseChange={setWorkshopPhase} />
          <BoardWorkshopEditor
            boardId={boardId}
            draft={draft}
            setDraft={setDraft}
            phase={phase}
            prioritizeMode={prioritizeMode}
            readOnly={readOnly}
          />
          {meta?.participants && meta.participants.length > 0 ? (
            <p className="forge-support" style={{ margin: '1rem' }}>
              Participants:{' '}
              {meta.participants.map((p) => p.display_name || p.login).join(', ')}
            </p>
          ) : null}
        </>
      ) : null}
    </div>
  )
}
