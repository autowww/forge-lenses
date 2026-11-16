import type { ReactNode } from 'react'
import type { DocsHealthSessionPayload } from '../../api/docsHealth'
import { TechnicalDetails } from '../page'
import { formatRunStartedShort } from './docsHealthRunRelativeTime'

function humanizeStatus(st: string) {
  const s = st.toLowerCase()
  if (!s) return 'Unknown'
  const map: Record<string, string> = {
    running: 'Running',
    paused: 'Paused',
    completed: 'Completed',
    cancelled: 'Cancelled',
    failed: 'Failed',
    awaiting_input: 'Awaiting your input',
    awaiting_approval: 'Awaiting approval',
  }
  if (map[s]) return map[s]
  const words = s.replace(/_/g, ' ').split(' ')
  return words.map((w) => (w ? w[0].toUpperCase() + w.slice(1) : '')).join(' ')
}

function titleCaseLabel(s: string) {
  const t = s.trim()
  if (!t) return ''
  return t[0].toUpperCase() + t.slice(1)
}

function chipClass(kind: 'status' | 'severity' | 'category'): string {
  if (kind === 'status') return 'le-dh-run-chip le-dh-run-chip--status'
  if (kind === 'severity') return 'le-dh-run-chip le-dh-run-chip--severity'
  return 'le-dh-run-chip le-dh-run-chip--category'
}

function statusToneClass(st: string): string {
  const s = st.toLowerCase()
  if (s === 'completed') return 'le-dh-run-chip--tone-success'
  if (s === 'failed') return 'le-dh-run-chip--tone-danger'
  if (s === 'cancelled') return 'le-dh-run-chip--tone-muted'
  if (s === 'awaiting_approval' || s === 'awaiting_input') return 'le-dh-run-chip--tone-warning'
  if (s === 'running' || s === 'paused') return 'le-dh-run-chip--tone-info'
  return 'le-dh-run-chip--tone-neutral'
}

export type DocsHealthRunSummaryCompactProps = {
  session: DocsHealthSessionPayload | null
  sessionId: string
  /** Display title (short run name). */
  runTitle: string
  /** Optional subtitle when it adds signal the chips do not cover (omit to reduce noise). */
  clusterLabel?: string | null
  severity: string
  category: string
  expectedGainPts: number | null | undefined
  affectedPathCount: number
  streamMode: 'sse' | 'poll' | 'idle'
  affectedPaths: string[]
  cancelErr?: string | null
  /** Collapsed "Advanced pipeline steps" (same behavior as before; moved here for one accordion stack). */
  advancedPipeline?: ReactNode
  /** Primary decision area: sticky action bar + buttons */
  children?: ReactNode
}

/**
 * Decision-first run header: chips + one-line metrics; IDs and telemetry behind disclosure.
 */
export function DocsHealthRunSummaryCompact({
  session,
  sessionId,
  runTitle,
  clusterLabel,
  severity,
  category,
  expectedGainPts,
  affectedPathCount,
  streamMode,
  affectedPaths,
  cancelErr,
  advancedPipeline,
  children,
}: DocsHealthRunSummaryCompactProps) {
  const st = String(session?.status || '').toLowerCase()
  const hs = session?.header_stats
  const rid = session?.id ?? sessionId
  const scanId = session?.run_id
  const branch = session?.suggested_git_branch?.trim()
  const ex = session?.execution
  const scratch = session?.scratch_workspace
  const agentSid = session?.agent_runtime_session_id

  const metaParts: string[] = []
  if (typeof expectedGainPts === 'number' && !Number.isNaN(expectedGainPts)) {
    metaParts.push(`+${expectedGainPts.toFixed(1)} pts expected gain`)
  }
  metaParts.push(`${affectedPathCount} file${affectedPathCount === 1 ? '' : 's'}`)
  const rel = formatRunStartedShort(session?.started_at)
  if (rel) metaParts.push(`started ${rel}`)

  return (
    <section className="le-dh-run-summary" aria-labelledby="le-dh-run-summary-title">
      <div className="le-dh-run-summary__row1">
        <div className="le-dh-run-summary__title-block">
          <h2 id="le-dh-run-summary-title" className="le-dh-run-summary__title">
            {runTitle}
          </h2>
          {clusterLabel ? (
            <p className="le-dh-run-summary__cluster">{clusterLabel}</p>
          ) : null}
        </div>
        <div className="le-dh-run-summary__row1-tail">
          <div className="le-dh-run-summary__chips" role="list">
            <span className={`${chipClass('status')} ${statusToneClass(st)}`} role="listitem">
              {humanizeStatus(st)}
            </span>
            {severity ? (
              <span className={chipClass('severity')} role="listitem">
                {titleCaseLabel(severity)}
              </span>
            ) : null}
            {category ? (
              <span className={chipClass('category')} role="listitem">
                {titleCaseLabel(category)}
              </span>
            ) : null}
          </div>
          {children ? <div className="le-dh-run-summary__cta">{children}</div> : null}
        </div>
      </div>

      <div className="le-dh-run-summary__meta-row">
        <p className="le-dh-run-summary__meta-line">{metaParts.join(' · ')}</p>
        {branch ? (
          <span
            className="le-dh-run-summary__branch-hint"
            title={branch}
            aria-label={`Branch-first apply: ${branch}`}
          >
            Branch-first
          </span>
        ) : null}
      </div>

      {cancelErr ? (
        <p className="le-dh-run-summary__err forge-support" role="alert">
          {cancelErr}
        </p>
      ) : null}

      <div className="le-dh-run-summary__expanders">
        <TechnicalDetails
          summary={affectedPathCount ? `Affected paths (${affectedPathCount})` : 'Affected paths'}
          defaultOpen={false}
        >
          {affectedPaths.length > 0 ? (
            <ul className="le-dh-run-summary__path-list">
              {affectedPaths.map((p) => (
                <li key={p}>
                  <code>{p}</code>
                </li>
              ))}
            </ul>
          ) : (
            <p className="le-muted le-dh-run-summary__empty">
              No paths linked from the latest scan for this cluster yet.
            </p>
          )}
        </TechnicalDetails>

        <TechnicalDetails summary="Technical details" defaultOpen={false}>
          <dl className="le-dh-run-summary__dl">
            <div>
              <dt>Remediation run id</dt>
              <dd>
                <code className="le-dh-run-id le-dh-run-id--secondary">{rid}</code>
              </dd>
            </div>
            <div>
              <dt>Docs scan id</dt>
              <dd>
                {scanId ? (
                  <code className="le-dh-run-id le-dh-run-id--secondary" title={scanId}>
                    {String(scanId)}
                  </code>
                ) : (
                  <span className="le-muted">Not linked</span>
                )}
              </dd>
            </div>
            {branch ? (
              <div>
                <dt>Suggested branch</dt>
                <dd>
                  <code className="le-dh-run-id le-dh-run-id--secondary">{branch}</code>
                </dd>
              </div>
            ) : null}
            {session?.started_at ? (
              <div>
                <dt>Started (ISO)</dt>
                <dd>{session.started_at}</dd>
              </div>
            ) : null}
            {session?.updated_at ? (
              <div>
                <dt>Last updated (ISO)</dt>
                <dd>{session.updated_at}</dd>
              </div>
            ) : null}
            <div>
              <dt>Live transport</dt>
              <dd>{streamMode === 'sse' ? 'SSE' : streamMode === 'poll' ? 'HTTP polling' : 'Idle'}</dd>
            </div>
            {typeof hs?.total_tokens === 'number' ? (
              <div>
                <dt>Session tokens</dt>
                <dd>
                  {hs.total_tokens.toLocaleString()}
                  {typeof hs.prompt_tokens === 'number' && typeof hs.completion_tokens === 'number'
                    ? ` (${hs.prompt_tokens} in + ${hs.completion_tokens} out)`
                    : ''}
                </dd>
              </div>
            ) : null}
            {(hs?.last_model_id || hs?.active_model) ? (
              <div>
                <dt>Last model</dt>
                <dd>{hs?.last_model_id || hs?.active_model}</dd>
              </div>
            ) : null}
            {session?.tasklet_run?.state ? (
              <div>
                <dt>Tasklet</dt>
                <dd>{String(session.tasklet_run.state)}</dd>
              </div>
            ) : null}
            {session?.run_state ? (
              <div>
                <dt>Run state</dt>
                <dd>{String(session.run_state)}</dd>
              </div>
            ) : null}
            {agentSid ? (
              <div>
                <dt>Agent runtime session</dt>
                <dd>
                  <code className="le-dh-run-id le-dh-run-id--secondary">{agentSid}</code>
                </dd>
              </div>
            ) : null}
            {ex?.step_backend ? (
              <div>
                <dt>Step backend</dt>
                <dd>{ex.step_backend}</dd>
              </div>
            ) : null}
            {typeof ex?.resumable === 'boolean' ? (
              <div>
                <dt>Resumable</dt>
                <dd>{ex.resumable ? 'Yes' : 'No'}</dd>
              </div>
            ) : null}
            {scratch?.worktree_path ? (
              <div>
                <dt>Scratch / worktree</dt>
                <dd>
                  <code className="le-dh-run-id le-dh-run-id--secondary">{scratch.worktree_path}</code>
                </dd>
              </div>
            ) : null}
            {session?.scratch_worktree?.path ? (
              <div>
                <dt>Scratch worktree</dt>
                <dd>
                  <code className="le-dh-run-id le-dh-run-id--secondary">{session.scratch_worktree.path}</code>
                </dd>
              </div>
            ) : null}
          </dl>
        </TechnicalDetails>

        {advancedPipeline ? <div className="le-dh-run-summary__advanced-slot">{advancedPipeline}</div> : null}
      </div>
    </section>
  )
}
