import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { getAuthStatus, postGithubToken, postLogout, type AuthStatus } from '../api/auth'

function githubAvatarUrl(login: string): string {
  const u = encodeURIComponent(login.trim())
  return `https://github.com/${u}.png?size=64`
}

export function HeaderAccount() {
  const menuId = useId()
  const [st, setSt] = useState<AuthStatus | null>(null)
  const [open, setOpen] = useState(false)
  const [token, setToken] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const wrapRef = useRef<HTMLDivElement>(null)

  const load = useCallback(() => {
    void getAuthStatus().then(setSt).catch(() => setSt(null))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!open) return
    function onDoc(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  async function signIn(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setMsg(null)
    try {
      const r = await postGithubToken(token.trim())
      if (r.ok === false && r.error) setMsg(r.error)
      else setOpen(false)
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
      setOpen(false)
    } finally {
      setBusy(false)
    }
  }

  if (!st) {
    return <div className="le-header-account le-header-account--loading" aria-hidden="true" />
  }

  const login = (st.session_login || '').trim()
  const showPatForm = st.expected_configured && !st.session_ok && st.access_policy_enforced
  const showUser = st.session_ok && !!login

  return (
    <div className="le-header-account" ref={wrapRef}>
      {showUser ? (
        <>
          <button
            type="button"
            className="le-header-account__trigger"
            aria-expanded={open}
            aria-haspopup="true"
            aria-controls={menuId}
            onClick={() => setOpen((o) => !o)}
          >
            <img
              className="le-header-account__avatar"
              src={githubAvatarUrl(login)}
              width={28}
              height={28}
              alt=""
              loading="lazy"
              decoding="async"
            />
            <span className="le-header-account__nick">{login}</span>
            <span className="le-header-account__chev" aria-hidden="true" />
          </button>
          {open ? (
            <div id={menuId} className="le-header-account__menu" role="menu">
              <a
                className="le-header-account__menu-link"
                href={`https://github.com/${encodeURIComponent(login)}`}
                target="_blank"
                rel="noreferrer"
              >
                GitHub profile
              </a>
              <button type="button" className="le-header-account__menu-btn" role="menuitem" onClick={() => void signOut()} disabled={busy}>
                Sign out
              </button>
            </div>
          ) : null}
        </>
      ) : showPatForm ? (
        <>
          <button type="button" className="le-header-account__signin-btn" onClick={() => setOpen((o) => !o)}>
            Sign in
          </button>
          {open ? (
            <div className="le-header-account__menu le-header-account__menu--wide" role="dialog" aria-label="Sign in with GitHub token">
              <form className="le-header-account__pat" onSubmit={(e) => void signIn(e)}>
                <label className="le-header-account__pat-label" htmlFor="header-pat">
                  GitHub PAT
                </label>
                <input
                  id="header-pat"
                  className="le-input le-header-account__pat-input"
                  type="password"
                  autoComplete="off"
                  placeholder="Paste token"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                />
                <button className="le-btn le-btn--primary le-header-account__pat-submit" type="submit" disabled={busy}>
                  Sign in
                </button>
              </form>
              {msg ? <p className="le-header-account__err">{msg}</p> : null}
            </div>
          ) : null}
        </>
      ) : (
        <span
          className="le-header-account__signed-out"
          title="No GitHub session yet. The workspace is on your machine; sign in when a feature needs your token."
        >
          Not signed in
        </span>
      )}
    </div>
  )
}
