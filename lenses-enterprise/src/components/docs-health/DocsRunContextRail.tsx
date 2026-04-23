import { Link } from 'react-router-dom'
import type { DocsHealthCluster, DocsHealthFinding, DocsHealthProjectPayload, DocsHealthSessionPayload } from '../../api/docsHealth'
import { TechnicalDetails } from '../page'

type LatestRunShape = {
  clusters?: DocsHealthCluster[]
  findings?: DocsHealthFinding[]
}

export type DocsRunContextRailProps = {
  projectSlug: string
  encProject: string
  session: DocsHealthSessionPayload | null
  projectSnapshot: DocsHealthProjectPayload | null
  /** Live transport label for audit (mirrors Technical details). */
  streamMode?: 'sse' | 'poll' | 'idle'
}

/**
 * Slim rail: cluster focus + links. Telemetry and paths mirror the main run summary (disclosure by default).
 */
export function DocsRunContextRail({
  projectSlug,
  encProject,
  session,
  projectSnapshot,
  streamMode = 'idle',
}: DocsRunContextRailProps) {
  const latest = projectSnapshot?.latest_run as LatestRunShape | null | undefined
  const clusterId = session?.cluster_id || session?.cluster?.id
  const cluster =
    latest?.clusters?.find((c) => (clusterId ? c.id === clusterId : false)) ??
    latest?.clusters?.find((c) => c.label && c.label === session?.cluster?.label)

  const findingIds = new Set(cluster?.finding_ids ?? [])
  const affected = (latest?.findings ?? [])
    .filter((f) => f.id && findingIds.has(f.id))
    .flatMap((f) => f.affected_paths ?? [])
  const uniqAffected = Array.from(new Set(affected))

  const knowledge =
    session?.knowledge_links && Object.keys(session.knowledge_links).length > 0 ? session.knowledge_links : null

  const policyNotes: string[] = []
  if (session?.execution?.step_backend && session.execution.step_backend !== 'inline') {
    policyNotes.push(`Step backend: ${session.execution.step_backend}`)
  }
  if (session?.execution?.resumable === false) policyNotes.push('This run may not be resumable under current policy.')
  if (session?.scratch_workspace?.worktree_path) policyNotes.push('Drafts use an isolated scratch worktree.')

  return (
    <aside className="le-dh-session-layout__rail" aria-label="Remediation context">
      <section className="le-panel le-dh-rail-panel le-dh-rail-panel--compact">
        <h2 className="le-panel__title">This run</h2>
        <p className="le-dh-rail-lead forge-support">
          Cluster <strong>{cluster?.label || session?.cluster?.label || '—'}</strong>
        </p>
        <p className="le-dh-rail-micro le-muted">
          <code className="le-dh-rail-repo">{projectSlug}</code>
        </p>
        <p className="le-dh-rail-links">
          <Link className="le-btn le-btn--small le-btn--ghost" to={`/projects/${encProject}/docs-health`}>
            Project Docs health
          </Link>
        </p>
      </section>

      <TechnicalDetails summary="Paths & audit ids" defaultOpen={false} className="le-dh-rail-details">
        <dl className="le-dh-run-summary__dl le-dh-run-summary__dl--tight">
          <div>
            <dt>Documentation scan id</dt>
            <dd>
              {session?.run_id ? (
                <code className="le-dh-run-id le-dh-run-id--secondary" title={session.run_id}>
                  {String(session.run_id)}
                </code>
              ) : (
                <span className="le-muted">Not linked</span>
              )}
            </dd>
          </div>
          <div>
            <dt>Live transport</dt>
            <dd>{streamMode === 'sse' ? 'SSE' : streamMode === 'poll' ? 'HTTP polling' : 'Idle'}</dd>
          </div>
        </dl>
        {uniqAffected.length > 0 ? (
          <ul className="forge-support le-dh-rail-paths">
            {uniqAffected.map((p) => (
              <li key={p}>
                <code>{p}</code>
              </li>
            ))}
          </ul>
        ) : (
          <p className="le-muted le-dh-rail-micro">No paths linked from the latest scan for this cluster.</p>
        )}
      </TechnicalDetails>

      {knowledge ? (
        <section className="le-panel le-dh-rail-panel">
          <h2 className="le-panel__title">Knowledge</h2>
          <ul className="forge-support le-dh-rail-knowledge">
            {Object.entries(knowledge).map(([k, href]) => (
              <li key={k}>
                <Link to={href}>{k.replace(/_/g, ' ')}</Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {policyNotes.length > 0 ? (
        <section className="le-panel le-dh-rail-panel">
          <h2 className="le-panel__title">Execution notes</h2>
          <ul className="forge-support le-dh-rail-policy">
            {policyNotes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </aside>
  )
}
