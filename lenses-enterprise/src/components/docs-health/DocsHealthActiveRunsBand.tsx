import { Link } from 'react-router-dom'
import { useDocsHealthLive } from '../../context/DocsHealthLiveContext'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'
import './docs-health-session.css'

export function DocsHealthActiveRunsBand() {
  const live = useDocsHealthLive()
  const sessions = live?.globalSessions ?? []
  if (!sessions.length) return null

  return (
    <section
      className="le-panel"
      aria-label="Active documentation sessions"
      role="status"
      aria-live="polite"
      aria-relevant="additions text"
    >
      <h2 className="le-panel__title">Active documentation sessions</h2>
      <p className="forge-support">
        {STUDIO_VOCAB.docsHealth} runs that are still in progress across the workspace. Token totals update while
        sessions are open.
      </p>
      <ul className="forge-support" style={{ listStyle: 'none', padding: 0, marginTop: '0.65rem' }}>
        {sessions.map((s) => {
          const proj = String(s.project || '')
          const sid = String(s.session_id || '')
          if (!proj || !sid) return null
          const href = `/projects/${encodeURIComponent(proj)}/docs-health/session/${encodeURIComponent(sid)}`
          const tt = Number(s.total_tokens) || 0
          return (
            <li
              key={`${proj}-${sid}`}
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'baseline',
                gap: '0.35rem 0.75rem',
                padding: '0.45rem 0',
                borderBottom: '1px solid var(--le-border-muted, #e5e5e5)',
              }}
            >
              <Link to={href} className="le-dh-live-chip" style={{ marginRight: 0 }}>
                Resume
              </Link>
              <span>
                <strong>{proj}</strong>
                {s.cluster_label ? <span className="le-muted"> · {s.cluster_label}</span> : null}
              </span>
              <span className="le-muted">
                {s.tasklet_state ? `${s.tasklet_state}` : s.status}
                {s.status && s.tasklet_state && s.status !== s.tasklet_state ? ` (session ${s.status})` : ''} ·{' '}
                {tt.toLocaleString()} tokens
                {s.last_model ? ` · ${s.last_model}` : null}
              </span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
