import { Link } from 'react-router-dom'
import type { DocsHealthRunSummary } from '../../api/docsHealth'
import type { RecentSessionRow, TaskletRunRow } from '../../lib/docsHealthProjectRunBuckets'
import type { DocsHealthProjectView } from './DocsHealthProjectSubNav'
import './docs-health-project-page.css'

function formatWhen(iso: string | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return iso
  }
}

type Props = {
  view: DocsHealthProjectView
  encProject: string
  projectSlug: string
  queueRuns: TaskletRunRow[]
  runningRuns: TaskletRunRow[]
  runningSessions: RecentSessionRow[]
  completedRuns: TaskletRunRow[]
  completedSessions: RecentSessionRow[]
  failedRuns: TaskletRunRow[]
  failedSessions: RecentSessionRow[]
  runHistory: DocsHealthRunSummary[] | undefined
  scanning: boolean
}

export function DocsHealthRunLifecyclePanels({
  view,
  encProject,
  projectSlug,
  queueRuns,
  runningRuns,
  runningSessions,
  completedRuns,
  completedSessions,
  failedRuns,
  failedSessions,
  runHistory,
  scanning,
}: Props) {
  if (view === 'dashboard') return null

  const sessionHref = (sid: string) =>
    `/projects/${encProject}/docs-health/session/${encodeURIComponent(sid)}`

  if (view === 'queue') {
    return (
      <section className="le-panel" aria-labelledby="le-dh-queue-h">
        <h2 id="le-dh-queue-h" className="le-panel__title">
          Run queue
        </h2>
        <p className="forge-support">
          Tasklet runs waiting to start (<code>created</code> / <code>preparing</code>). Deterministic markdown scans run
          synchronously when you press <strong>Run markdown scan</strong>, so they do not appear here.
        </p>
        {!queueRuns.length ? (
          <p className="le-muted">Nothing queued for this repository.</p>
        ) : (
          <table className="le-dh-lifecycle-table">
            <thead>
              <tr>
                <th>Run id</th>
                <th>State</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {queueRuns.map((r, i) => (
                <tr key={r.id || `queue-${i}`}>
                  <td>
                    <code>{r.id || '—'}</code>
                  </td>
                  <td>{r.state || '—'}</td>
                  <td>{formatWhen(r.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    )
  }

  if (view === 'running') {
    return (
      <section className="le-panel" aria-labelledby="le-dh-running-h">
        <h2 id="le-dh-running-h" className="le-panel__title">
          Running now
        </h2>
        {scanning ? (
          <p className="forge-support" role="status">
            Deterministic markdown scan in progress in this browser session…
          </p>
        ) : null}
        <p className="forge-support">Active remediation tasklets and in-flight sessions for this repository.</p>
        {!runningRuns.length && !runningSessions.length && !scanning ? (
          <p className="le-muted">No active runs or sessions.</p>
        ) : null}
        {runningRuns.length ? (
          <>
            <h3 className="le-muted" style={{ fontSize: '0.85rem', margin: '0.75rem 0 0.25rem' }}>
              Tasklet runs
            </h3>
            <table className="le-dh-lifecycle-table">
              <thead>
                <tr>
                  <th>Run id</th>
                  <th>State</th>
                  <th>Session</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {runningRuns.map((r) => (
                  <tr key={r.id || String(r.updated_at)}>
                    <td>
                      <code>{r.id || '—'}</code>
                    </td>
                    <td>{r.state || '—'}</td>
                    <td>
                      {r.docs_health_session_id ? (
                        <Link to={sessionHref(r.docs_health_session_id)}>Open session</Link>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>{formatWhen(r.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : null}
        {runningSessions.length ? (
          <>
            <h3 className="le-muted" style={{ fontSize: '0.85rem', margin: '0.75rem 0 0.25rem' }}>
              Sessions
            </h3>
            <table className="le-dh-lifecycle-table">
              <thead>
                <tr>
                  <th>Session</th>
                  <th>Status</th>
                  <th>Tokens</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {runningSessions.map((s) => (
                  <tr key={s.session_id || String(s.updated_at)}>
                    <td>
                      {s.href_session ? (
                        <Link to={s.href_session}>{s.display_name || s.cluster_label || s.session_id || 'Session'}</Link>
                      ) : (
                        s.display_name || s.cluster_label || s.session_id
                      )}
                    </td>
                    <td>{s.status || '—'}</td>
                    <td>{typeof s.total_tokens === 'number' && s.total_tokens > 0 ? s.total_tokens.toLocaleString() : '—'}</td>
                    <td>{formatWhen(s.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : null}
      </section>
    )
  }

  if (view === 'completed') {
    const scans = runHistory ?? []
    return (
      <section className="le-panel" aria-labelledby="le-dh-done-h">
        <h2 id="le-dh-done-h" className="le-panel__title">
          Completed
        </h2>
        <p className="forge-support">Finished tasklets, closed remediation sessions, and recent markdown scan runs.</p>
        {completedRuns.length ? (
          <>
            <h3 className="le-muted" style={{ fontSize: '0.85rem', margin: '0.5rem 0 0.25rem' }}>
              Tasklet runs
            </h3>
            <table className="le-dh-lifecycle-table">
              <thead>
                <tr>
                  <th>Run id</th>
                  <th>Session</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {completedRuns.map((r) => (
                  <tr key={r.id || String(r.updated_at)}>
                    <td>
                      <code>{r.id || '—'}</code>
                    </td>
                    <td>
                      {r.docs_health_session_id ? (
                        <Link to={sessionHref(r.docs_health_session_id)}>Open session</Link>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>{formatWhen(r.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : null}
        {completedSessions.length ? (
          <>
            <h3 className="le-muted" style={{ fontSize: '0.85rem', margin: '0.75rem 0 0.25rem' }}>
              Sessions
            </h3>
            <table className="le-dh-lifecycle-table">
              <thead>
                <tr>
                  <th>Session</th>
                  <th>Tokens</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {completedSessions.map((s) => (
                  <tr key={s.session_id || String(s.updated_at)}>
                    <td>
                      {s.href_session ? (
                        <Link to={s.href_session}>{s.display_name || s.cluster_label || s.session_id}</Link>
                      ) : (
                        s.display_name || s.cluster_label || s.session_id
                      )}
                    </td>
                    <td>{typeof s.total_tokens === 'number' && s.total_tokens > 0 ? s.total_tokens.toLocaleString() : '—'}</td>
                    <td>{formatWhen(s.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : null}
        {scans.length ? (
          <>
            <h3 className="le-muted" style={{ fontSize: '0.85rem', margin: '0.75rem 0 0.25rem' }}>
              Markdown scans
            </h3>
            <table className="le-dh-lifecycle-table">
              <thead>
                <tr>
                  <th>Run id</th>
                  <th>Finished</th>
                  <th>Score</th>
                  <th>Findings</th>
                </tr>
              </thead>
              <tbody>
                {scans.map((row) => (
                  <tr key={row.id || String(row.finished_at)}>
                    <td>
                      <code>{row.id ? `${row.id.slice(0, 14)}…` : '—'}</code>
                    </td>
                    <td>{formatWhen(row.finished_at)}</td>
                    <td>{row.score ?? '—'}</td>
                    <td>{row.finding_count ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : null}
        {!completedRuns.length && !completedSessions.length && !scans.length ? (
          <p className="le-muted">No completed runs recorded yet for {projectSlug}.</p>
        ) : null}
      </section>
    )
  }

  if (view === 'failed') {
    return (
      <section className="le-panel" aria-labelledby="le-dh-fail-h">
        <h2 id="le-dh-fail-h" className="le-panel__title">
          Failed
        </h2>
        <p className="forge-support">Stopped or failed tasklets and sessions that need follow-up.</p>
        {!failedRuns.length && !failedSessions.length ? (
          <p className="le-muted">No failed runs in the recent window.</p>
        ) : null}
        {failedRuns.length ? (
          <>
            <h3 className="le-muted" style={{ fontSize: '0.85rem', margin: '0.5rem 0 0.25rem' }}>
              Tasklet runs
            </h3>
            <table className="le-dh-lifecycle-table">
              <thead>
                <tr>
                  <th>Run id</th>
                  <th>State</th>
                  <th>Stop / error</th>
                  <th>Session</th>
                </tr>
              </thead>
              <tbody>
                {failedRuns.map((r) => (
                  <tr key={r.id || String(r.updated_at)}>
                    <td>
                      <code>{r.id || '—'}</code>
                    </td>
                    <td>{r.state || '—'}</td>
                    <td>
                      {[r.stop_reason, r.last_error].filter(Boolean).join(' · ') || '—'}
                    </td>
                    <td>
                      {r.docs_health_session_id ? (
                        <Link to={sessionHref(r.docs_health_session_id)}>Open session</Link>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : null}
        {failedSessions.length ? (
          <>
            <h3 className="le-muted" style={{ fontSize: '0.85rem', margin: '0.75rem 0 0.25rem' }}>
              Sessions
            </h3>
            <table className="le-dh-lifecycle-table">
              <thead>
                <tr>
                  <th>Session</th>
                  <th>Status</th>
                  <th>Tokens</th>
                </tr>
              </thead>
              <tbody>
                {failedSessions.map((s) => (
                  <tr key={s.session_id || String(s.updated_at)}>
                    <td>
                      {s.href_session ? (
                        <Link to={s.href_session}>{s.display_name || s.cluster_label || s.session_id}</Link>
                      ) : (
                        s.display_name || s.cluster_label || s.session_id
                      )}
                    </td>
                    <td>{s.status || '—'}</td>
                    <td>{typeof s.total_tokens === 'number' && s.total_tokens > 0 ? s.total_tokens.toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : null}
      </section>
    )
  }

  return null
}
