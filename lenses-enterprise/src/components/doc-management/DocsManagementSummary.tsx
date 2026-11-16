import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listDocManagementSessions, type DocManagementSessionSummary } from '../../api/docManagement'

function lastPromoteLabel(sessions: DocManagementSessionSummary[]): string {
  const promoted = sessions
    .filter((s) => s.status === 'promoted' && s.updated_at)
    .sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)))
  if (!promoted.length) return 'No promotes yet'
  try {
    return new Date(String(promoted[0]!.updated_at)).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  } catch {
    return String(promoted[0]!.updated_at)
  }
}

/**
 * PM-facing Doc Management summary for Home — active sessions and last promote in plain language.
 */
export function DocsManagementSummary() {
  const [sessions, setSessions] = useState<DocManagementSessionSummary[]>([])
  const [err, setErr] = useState(false)

  useEffect(() => {
    let cancelled = false
    void listDocManagementSessions()
      .then((r) => {
        if (!cancelled) {
          setSessions(r.sessions ?? [])
          setErr(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSessions([])
          setErr(true)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const active = sessions.filter((s) => s.status && !['promoted', 'cancelled', 'rolled_back'].includes(s.status))
  const lastPromote = lastPromoteLabel(sessions)

  return (
    <section className="le-card le-docs-mgmt-summary" aria-label="Documentation management summary">
      <h2 className="le-cc-section__title">Documentation management</h2>
      <p className="forge-support le-docs-mgmt-summary__lead">
        For leads: tracks governed doc promotion sessions — how many are in flight and when content last shipped to
        handbooks or product sites.
      </p>
      <dl className="le-docs-mgmt-summary__stats">
        <div>
          <dt>Active sessions</dt>
          <dd>{err ? '—' : active.length}</dd>
        </div>
        <div>
          <dt>Last promote</dt>
          <dd>{err ? 'Unavailable' : lastPromote}</dd>
        </div>
        <div>
          <dt>Total sessions</dt>
          <dd>{err ? '—' : sessions.length}</dd>
        </div>
      </dl>
      <p className="forge-support" style={{ marginTop: '0.65rem' }}>
        <Link className="le-btn le-btn--small" to="/doc-management">
          Open doc management hub
        </Link>
      </p>
    </section>
  )
}
