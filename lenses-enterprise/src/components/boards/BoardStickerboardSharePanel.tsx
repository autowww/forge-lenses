import { useCallback, useEffect, useState } from 'react'
import { ApiError, apiGetJson, apiPostJson } from '../../api/http'

type ShareMeta = {
  ok?: boolean
  guest_role?: string
  revoked?: boolean
  participants?: { login: string; display_name?: string; joined_at?: number }[]
}

type ShareConfig = {
  ok?: boolean
  public_base?: string
  from_env?: boolean
  public_base_configured?: boolean
}

type StartResult = {
  ok?: boolean
  share_token?: string
  public_url?: string
  guest_role?: string
  error?: string
}

const VITE_PUBLIC_BASE = (
  import.meta.env.VITE_STICKERBOARD_PUBLIC_BASE as string | undefined
)?.replace(/\/$/, '')

function isLoopbackBase(base: string): boolean {
  const b = base.trim().toLowerCase()
  if (!b) return true
  return b.includes('127.0.0.1') || b.includes('://localhost')
}

function pickPublicBase(serverBase: string, fromEnv: boolean, configured?: boolean): string {
  const server = serverBase.trim().replace(/\/$/, '')
  if ((configured ?? (fromEnv && server && !isLoopbackBase(server))) && server) {
    return server
  }
  if (VITE_PUBLIC_BASE && !isLoopbackBase(VITE_PUBLIC_BASE)) {
    return VITE_PUBLIC_BASE
  }
  if (server) return server
  return ''
}

export function BoardStickerboardSharePanel({
  boardId,
  boardLabel,
}: {
  boardId: string
  boardLabel?: string
}) {
  const [guestRole, setGuestRole] = useState<'view' | 'edit'>('view')
  const [activeToken, setActiveToken] = useState<string | null>(null)
  const [publicBase, setPublicBase] = useState(VITE_PUBLIC_BASE || '')
  const [publicUrl, setPublicUrl] = useState<string | null>(null)
  const [participants, setParticipants] = useState<ShareMeta['participants']>([])
  const [status, setStatus] = useState('')
  const [revoked, setRevoked] = useState(false)

  const guestUrl = useCallback(
    (token: string) => {
      const base = (publicBase || VITE_PUBLIC_BASE || 'http://127.0.0.1:9999').replace(/\/$/, '')
      return `${base}/#/${token}`
    },
    [publicBase],
  )

  useEffect(() => {
    apiGetJson<ShareConfig>('/api/sticker-board-share/config')
      .then((c) => {
        const picked = pickPublicBase(
          c.public_base || '',
          Boolean(c.from_env),
          c.public_base_configured,
        )
        if (picked) setPublicBase(picked)
      })
      .catch(() => {
        if (VITE_PUBLIC_BASE) setPublicBase(VITE_PUBLIC_BASE)
      })
  }, [])

  const refreshMeta = useCallback(
    async (token: string) => {
      const m = await apiGetJson<ShareMeta>(
        `/api/sticker-board-share?token=${encodeURIComponent(token)}`,
      )
      setParticipants(m.participants ?? [])
      setRevoked(Boolean(m.revoked))
    },
    [],
  )

  useEffect(() => {
    if (!activeToken) return
    void refreshMeta(activeToken).catch(() => {})
  }, [activeToken, refreshMeta])

  async function startSharing() {
    setStatus('Starting…')
    try {
      const r = await apiPostJson<StartResult>('/api/sticker-board-share', {
        action: 'start',
        board_id: boardId,
        guest_role: guestRole,
      })
      if (!r.ok || !r.share_token) {
        setStatus(r.error ?? 'Failed to start sharing')
        return
      }
      setActiveToken(r.share_token)
      const fromServer = (r.public_url || '').trim()
      const url =
        fromServer && !isLoopbackBase(fromServer.split('#')[0] || fromServer)
          ? fromServer
          : guestUrl(r.share_token)
      setPublicUrl(url)
      const hashIdx = url.indexOf('#')
      if (hashIdx > 0) {
        setPublicBase(url.slice(0, hashIdx).replace(/\/$/, ''))
      }
      setRevoked(false)
      setStatus('Sharing active')
      await refreshMeta(r.share_token)
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setStatus(
          'Sign in with Google (Forge Studio header) to start sharing, or use Lenses on loopback with access policy disabled.',
        )
      } else {
        setStatus(e instanceof Error ? e.message : String(e))
      }
    }
  }

  async function revokeSharing() {
    if (!activeToken) return
    setStatus('Revoking…')
    try {
      await apiPostJson('/api/sticker-board-share', {
        action: 'revoke',
        share_token: activeToken,
      })
      setRevoked(true)
      setStatus('Sharing revoked')
    } catch (e) {
      setStatus(e instanceof Error ? e.message : String(e))
    }
  }

  async function copyLink() {
    const url = publicUrl ?? (activeToken ? guestUrl(activeToken) : '')
    if (!url) return
    try {
      await navigator.clipboard.writeText(url)
      setStatus('Link copied')
    } catch {
      setStatus(url)
    }
  }

  const displayBase =
    (publicBase && !isLoopbackBase(publicBase) ? publicBase : '') ||
    (VITE_PUBLIC_BASE && !isLoopbackBase(VITE_PUBLIC_BASE) ? VITE_PUBLIC_BASE : '') ||
    'http://127.0.0.1:9999'
  const hasPublic = !isLoopbackBase(displayBase)
  const baseHint =
    (hasPublic ? displayBase : 'http://127.0.0.1:9999') +
    (hasPublic
      ? ''
      : ' — add Code/.lenses-local/stickerboard-public.env or LENSES_STICKERBOARD_PUBLIC_BASE')

  return (
    <section className="le-card le-board-share-panel" aria-labelledby="stickerboard-share-heading">
      <h2 id="stickerboard-share-heading" className="le-h2">
        {boardLabel?.trim()
          ? `${boardLabel.trim()} — Stickerboard sharing`
          : 'Forge Lenses Stickerboard — sharing'}
      </h2>
      <p className="forge-support">
        Guests open <strong>{baseHint}</strong>
        <code>#/share-token</code>. Google sign-in required. Set{' '}
        <code>LENSES_STICKERBOARD_PUBLIC_BASE</code> on the Lenses process (e.g.{' '}
        <code>https://leo.forgedc.net/stickerboard</code>) or{' '}
        <code>VITE_STICKERBOARD_PUBLIC_BASE</code> in Studio.
      </p>
      <fieldset className="le-form-row" style={{ marginTop: '0.75rem' }}>
        <legend className="forge-support">Guest access</legend>
        <label style={{ marginRight: '1rem' }}>
          <input
            type="radio"
            name="guest_role"
            checked={guestRole === 'view'}
            onChange={() => setGuestRole('view')}
          />{' '}
          Guests can view
        </label>
        <label>
          <input
            type="radio"
            name="guest_role"
            checked={guestRole === 'edit'}
            onChange={() => setGuestRole('edit')}
          />{' '}
          Guests can edit
        </label>
      </fieldset>
      <div className="le-form-row" style={{ marginTop: '0.75rem', gap: '0.5rem' }}>
        <button type="button" className="le-btn le-btn--primary" onClick={() => void startSharing()}>
          Start sharing
        </button>
        {activeToken && !revoked ? (
          <button type="button" className="le-btn" onClick={() => void revokeSharing()}>
            Revoke sharing
          </button>
        ) : null}
        {publicUrl && !revoked ? (
          <button type="button" className="le-btn" onClick={() => void copyLink()}>
            Copy Forge Lenses Stickerboard URL
          </button>
        ) : null}
      </div>
      {publicUrl && !revoked ? (
        <p className="forge-support" style={{ marginTop: '0.5rem', wordBreak: 'break-all' }}>
          {publicUrl}
        </p>
      ) : null}
      {status ? <p className="forge-support">{status}</p> : null}
      {participants && participants.length > 0 ? (
        <ul className="forge-support" style={{ marginTop: '0.5rem' }}>
          {participants.map((p) => (
            <li key={p.login}>
              {p.display_name || p.login}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
