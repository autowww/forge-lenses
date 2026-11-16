import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  createDocManagementSession,
  getDocManagementCatalog,
  listDocManagementSessions,
  type DocManagementSessionSummary,
  type DocManagementSurface,
} from '../api/docManagement'
import { PageHeader, StatePanel } from '../components/page'
import { docManagementFeatureEnabled } from '../util/experimentalFlags'

export function DocManagementHubPage() {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<DocManagementSessionSummary[]>([])
  const [surfaces, setSurfaces] = useState<DocManagementSurface[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [sessRes, catRes] = await Promise.all([
        listDocManagementSessions(),
        getDocManagementCatalog(),
      ])
      setSessions(sessRes.sessions || [])
      setSurfaces(catRes.surfaces || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'load_failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!docManagementFeatureEnabled()) return
    void refresh()
  }, [refresh])

  const onNew = async () => {
    setCreating(true)
    try {
      const res = await createDocManagementSession('New doc management session')
      const sid = String((res.session as { id?: string })?.id || '')
      if (sid) navigate(`/doc-management/session/${encodeURIComponent(sid)}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'create_failed')
    } finally {
      setCreating(false)
    }
  }

  if (!docManagementFeatureEnabled()) {
    return (
      <StatePanel
        variant="not_configured"
        title="Doc Management is disabled"
        description="Set VITE_EXPERIMENTAL_DOC_MANAGEMENT=1 to enable governed hydration sessions."
      />
    )
  }

  return (
    <div className="studio-page doc-management-hub">
      <PageHeader
        title="Doc management"
        subtitle="Governed hydration sessions — intake seeds, run agents, approve, and promote to sites."
        actions={
          <button type="button" className="ks-btn ks-btn-primary" disabled={creating} onClick={() => void onNew()}>
            {creating ? 'Creating…' : 'New session'}
          </button>
        }
      />
      {error ? <StatePanel variant="error" title="Error" description={error} /> : null}
      {loading ? <p>Loading sessions…</p> : null}
      {!loading && sessions.length === 0 ? (
        <StatePanel
          variant="empty"
          title="No sessions yet"
          description="Start a session to paste Markdown, upload a zip of seeds, fetch a URL, or hydrate from a blog post."
        />
      ) : null}
      <ul className="doc-management-session-list">
        {sessions.map((s) => (
          <li key={s.session_id}>
            <Link to={`/doc-management/session/${encodeURIComponent(s.session_id)}`}>
              <strong>{s.display_name}</strong>
              <span className="dm-meta">
                {s.status} · {s.workflow_stage || 'draft'}
                {s.target_surfaces?.length ? ` · ${s.target_surfaces.join(', ')}` : ''}
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <section className="dm-surfaces-preview">
        <h2>Target surfaces</h2>
        <ul>
          {surfaces.map((s) => (
            <li key={s.surface_id}>
              {s.label} <code>{s.surface_id}</code>
            </li>
          ))}
        </ul>
      </section>
      <p>
        <Link to="/blog">Browse blog posts</Link> to start hydration from cached forgesdlc.com content.
      </p>
    </div>
  )
}
