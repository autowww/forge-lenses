import { useCallback, useEffect, useState } from 'react'
import { getAuthStatus, postGithubToken, postLogout, type AuthStatus } from '../api/auth'

export function AuthBar() {
  const [st, setSt] = useState<AuthStatus | null>(null)
  const [token, setToken] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const load = useCallback(() => {
    void getAuthStatus().then(setSt).catch(() => setSt(null))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function signIn(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setMsg(null)
    try {
      const r = await postGithubToken(token.trim())
      if (r.ok === false && r.error) setMsg(r.error)
      setToken('')
      load()
    } catch (err) {
      setMsg(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function signOut() {
    setBusy(true)
    try {
      await postLogout()
      load()
    } finally {
      setBusy(false)
    }
  }

  if (!st) return <span className="le-muted" style={{ fontSize: '0.75rem' }}>…</span>

  return (
    <div
      className="le-auth-bar"
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '0.5rem',
        fontSize: '0.75rem',
      }}
    >
      {st.access_policy_enforced && (
        <span className="le-muted">
          {st.session_ok ? st.session_login : 'not signed in'}
        </span>
      )}
      {st.expected_configured && !st.session_ok && st.access_policy_enforced && (
        <form onSubmit={signIn} style={{ display: 'flex', gap: '0.35rem' }}>
          <input
            className="le-input"
            type="password"
            autoComplete="off"
            placeholder="GitHub PAT"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            style={{ width: '8rem' }}
          />
          <button className="le-btn le-btn--primary" type="submit" disabled={busy}>
            Sign in
          </button>
        </form>
      )}
      {st.session_ok && (
        <button type="button" className="le-btn" onClick={() => void signOut()} disabled={busy}>
          Sign out
        </button>
      )}
      {msg && <span className="le-danger">{msg}</span>}
    </div>
  )
}
