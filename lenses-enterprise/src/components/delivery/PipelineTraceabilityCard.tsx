import { useEffect, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useResilientJsonBlock } from '../../hooks/useResilientJsonBlock'
import { StatePanel } from '../page/StatePanel'
import {
  API_FEATURE_DISABLED,
  isLocalFixtureProvider,
  isScanOnlyProvider,
  PROVIDER_SCAN_ONLY,
} from '../../lib/apiInternalFields'
import { recordPageFailure } from '../../telemetry/studioTelemetry'
import { TraceabilityLaunchButton } from '../traceability'
import { DEMO_ORCHESTRATION_STORY_ID } from '../../constants/demoOrchestration'

type WorkflowRow = {
  name?: string
  status?: string
  conclusion?: string
  run_url?: string
  head_sha?: string
}

type TraceLink = {
  kind?: string
  label?: string
  url?: string
}

type DeliveryRepoRow = {
  project: string
  is_git?: boolean
  git_head_short?: string
  git_branch?: string
  ci_provider?: string
  workflows?: WorkflowRow[]
  trace_links?: TraceLink[]
  environments?: { name?: string; status?: string; url?: string }[]
  releases?: { tag?: string; url?: string }[]
  data_sources?: string[]
}

export type DeliveryOverviewPayload = {
  ok?: boolean
  schema_version?: number
  feature_enabled?: boolean
  provider_kind?: string
  resolved_at?: string
  workspace_summary?: { child_count?: number; git_repo_count?: number }
  repos?: DeliveryRepoRow[]
  hints?: string[]
}

type QualityMiniPayload = {
  ok?: boolean
  feature_enabled?: boolean
  provider_kind?: string
  gate_evaluations?: { passed?: boolean }[]
}

function workflowStatus(w: WorkflowRow): string {
  const c = (w.conclusion || w.status || '').trim()
  return c || 'unknown'
}

/**
 * Plan → Today: SDLC orchestration slice — CI/traceability overlay from workspace scan + optional
 * `.lenses-local/delivery-signals.json` (and future remote adapters).
 */
export function PipelineTraceabilityCard() {
  const { state } = useWorkspace()
  const refreshKey = state?.resolved_at ?? null

  const block = useResilientJsonBlock<DeliveryOverviewPayload>('/api/delivery/overview', {
    snapshotKey: 'delivery-overview',
    refreshKey,
  })
  const qmini = useResilientJsonBlock<QualityMiniPayload>('/api/quality/overview', {
    snapshotKey: 'quality-overview',
    refreshKey,
  })

  const data = block.data
  const phase = block.phase

  useEffect(() => {
    if (phase === 'error' && block.failure) {
      recordPageFailure('plan_delivery_signals', block.failure.summary)
    }
  }, [phase, block.failure])

  let inner: ReactNode

  if (phase === 'loading' && !data) {
    inner = (
      <StatePanel
        variant="loading"
        density="compact"
        title="Loading pipeline and traceability overlay"
        description="Merges workspace scan with optional local delivery fixtures (no chart bundle required)."
      />
    )
  } else if (phase === 'error' && !data) {
    inner = (
      <StatePanel
        variant="error"
        density="compact"
        title="Could not load delivery overview"
        description="Confirm the Lenses server is running, then retry. This endpoint is read-only and safe to poll."
        technicalDetail={block.failure?.summary ?? null}
        actions={
          <button type="button" className="le-btn le-btn--primary" onClick={() => block.retry()}>
            Retry
          </button>
        }
        telemetryTag="delivery_signals_fetch_error"
      />
    )
  } else if (!data || data.ok === false) {
    inner = (
      <StatePanel
        variant="empty"
        density="compact"
        title="Delivery overview unavailable"
        description="The server returned an unexpected payload."
        actions={
          <button type="button" className="le-btn le-btn--primary" onClick={() => block.retry()}>
            Retry
          </button>
        }
        telemetryTag="delivery_signals_empty_payload"
      />
    )
  } else if (data.feature_enabled === false) {
    inner = (
      <>
        <StatePanel
          variant="empty"
          density="compact"
          title="Pipeline overlay disabled"
          description={
            <>
              Feature flag is off for this server. Adjust{' '}
              <code className="le-mono">LENSES_EXPERIMENTAL_DELIVERY_SIGNALS</code> and restart Lenses to show
              CI fixtures and future remote adapter rows here.
            </>
          }
          telemetryTag={['delivery_signals_', API_FEATURE_DISABLED].join('')}
        />
        {data.workspace_summary ? (
          <p className="forge-support" style={{ marginTop: '0.75rem' }}>
            Workspace scan: {data.workspace_summary.git_repo_count ?? 0} git repo(s) of{' '}
            {data.workspace_summary.child_count ?? 0} children — data still available under{' '}
            <Link to="/projects">Projects</Link>.
          </p>
        ) : null}
        {data.hints?.length ? (
          <ul className="forge-support" style={{ marginTop: '0.5rem' }}>
            {data.hints.map((h) => (
              <li key={h.slice(0, 80)}>{h}</li>
            ))}
          </ul>
        ) : null}
      </>
    )
  } else {
    const repos = data.repos ?? []
    const showScanOnlyCallout = isScanOnlyProvider(data)

    inner = (
      <>
        {block.fromSnapshot ? (
          <StatePanel
            variant="stale"
            density="compact"
            title="Showing cached delivery overview"
            description={`Snapshot: ${block.snapshotTimeLabel ?? 'unknown'}. ${block.snapshotAgeLabel ?? ''}`}
            technicalDetail={block.failure?.summary ?? undefined}
            actions={
              <button type="button" className="le-btn le-btn--primary" onClick={() => block.retry()}>
                Refresh
              </button>
            }
          />
        ) : null}

        {showScanOnlyCallout ? (
          <StatePanel
            variant="empty"
            density="compact"
            title="No local delivery fixture yet"
            description={
              <>
                Repositories below come from the workspace scan only. Add{' '}
                <code className="le-mono">.lenses-local/delivery-signals.json</code> to attach CI runs, PR
                links, environments, and releases — or set{' '}
                <code className="le-mono">LENSES_DELIVERY_SIGNALS_SEED_DEMO=1</code> for the checked-in demo
                overlay.
              </>
            }
            telemetryTag={['delivery_signals_', PROVIDER_SCAN_ONLY].join('')}
          />
        ) : null}

        {data.hints?.length && !showScanOnlyCallout ? (
          <ul className="forge-support" style={{ marginBottom: '1rem' }}>
            {data.hints.map((h) => (
              <li key={h.slice(0, 96)}>{h}</li>
            ))}
          </ul>
        ) : null}

        {repos.length === 0 ? (
          <p className="le-delivery-section__empty">No workspace children in the current scan.</p>
        ) : (
          <div className="le-cc-table-wrap" style={{ overflowX: 'auto' }}>
            <table className="le-cc-table">
              <caption className="forge-support" style={{ textAlign: 'left', marginBottom: '0.35rem' }}>
                Pipeline and traceability by repository
              </caption>
              <thead>
                <tr>
                  <th scope="col">Repository</th>
                  <th scope="col">Git</th>
                  <th scope="col">CI provider</th>
                  <th scope="col">Latest workflow</th>
                  <th scope="col">Quality (workspace)</th>
                  <th scope="col">Trace links</th>
                </tr>
              </thead>
              <tbody>
                {repos.map((r) => {
                  const wf = r.workflows?.[0]
                  const enc = encodeURIComponent(r.project)
                  const trace = r.trace_links?.[0]
                  const qev = qmini.data?.gate_evaluations ?? []
                  const qfail = qev.filter((e) => !e.passed).length
                  const qok =
                    qmini.data?.ok &&
                    qmini.data?.feature_enabled !== false &&
                    isLocalFixtureProvider(qmini.data)
                  return (
                    <tr key={r.project}>
                      <td>
                        <Link to={`/projects/${enc}`}>{r.project}</Link>
                      </td>
                      <td>
                        {r.is_git ? (
                          <>
                            {r.git_branch ? <span className="le-muted">{r.git_branch}</span> : null}
                            {r.git_head_short ? (
                              <code className="le-mono" style={{ marginLeft: '0.35rem' }}>
                                {r.git_head_short}
                              </code>
                            ) : (
                              <span className="forge-support">repo</span>
                            )}
                          </>
                        ) : (
                          <span className="forge-support">non-git</span>
                        )}
                      </td>
                      <td>{r.ci_provider ? <span>{r.ci_provider}</span> : <span className="forge-support">—</span>}</td>
                      <td>
                        {wf ? (
                          <>
                            <strong>{wf.name ?? 'workflow'}</strong>
                            <span className="le-muted"> · {workflowStatus(wf)}</span>
                            {wf.run_url ? (
                              <>
                                {' '}
                                <a className="le-delivery-link" href={wf.run_url} rel="noreferrer" target="_blank">
                                  Open run
                                </a>
                              </>
                            ) : null}
                          </>
                        ) : (
                          <span className="forge-support">No fixture row</span>
                        )}
                      </td>
                      <td>
                        {qok ? (
                          <>
                            {qfail > 0 ? (
                              <strong style={{ color: 'var(--le-danger, #c62828)' }}>{qfail} gate(s) fail</strong>
                            ) : (
                              <span>All gates pass</span>
                            )}
                            <br />
                            <Link className="le-delivery-link" to={`/projects/${enc}`}>
                              Project quality
                            </Link>
                          </>
                        ) : isScanOnlyProvider(qmini.data) ? (
                          <span className="forge-support">No fixture</span>
                        ) : qmini.data?.feature_enabled === false ? (
                          <span className="forge-support">Off</span>
                        ) : (
                          <span className="forge-support">—</span>
                        )}
                      </td>
                      <td>
                        {trace?.url ? (
                          <a className="le-delivery-link" href={trace.url} rel="noreferrer" target="_blank">
                            {trace.label || trace.kind || 'Link'}
                          </a>
                        ) : (
                          <span className="forge-support">—</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        <p className="forge-support" style={{ marginTop: '0.75rem' }}>
          Provider: <code className="le-mono">{data.provider_kind ?? 'unknown'}</code>
          {data.resolved_at ? (
            <>
              {' '}
              · Scan <time dateTime={data.resolved_at}>{data.resolved_at}</time>
            </>
          ) : null}
        </p>
      </>
    )
  }

  return (
    <section className="le-delivery-section" aria-labelledby="le-delivery-pipeline-h">
      <h2 id="le-delivery-pipeline-h" className="le-delivery-section__title">
        Pipeline and traceability
      </h2>
      <p className="le-delivery-section__lead">
        Local-first overlay for CI runs, pull requests, environments, and releases. Data merges workspace scan
        with optional <code className="le-mono">delivery-signals.json</code>; remote systems plug in via
        adapters without changing this table shape.
      </p>
      <p className="forge-support" style={{ marginBottom: '0.75rem' }}>
        <TraceabilityLaunchButton
          rootId={DEMO_ORCHESTRATION_STORY_ID}
          label="Open trace graph (demo story)"
          variant="primary"
          title="Canonical orchestration graph — same drawer as Workspace and Plan"
        />
      </p>
      {inner}
    </section>
  )
}
