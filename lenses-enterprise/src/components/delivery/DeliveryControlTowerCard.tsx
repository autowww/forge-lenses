import { useEffect, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useResilientJsonBlock } from '../../hooks/useResilientJsonBlock'
import { StatePanel } from '../page/StatePanel'
import { recordPageFailure } from '../../telemetry/studioTelemetry'

type WhatLiveRow = {
  environment_id?: string
  display_name?: string
  tier?: string
  version?: string
  artifact_ref?: string
  last_successful_deploy_at?: string
  last_deploy_status?: string
  project?: string
}

type BlockedRow = {
  promotion_id?: string
  reason?: string
  detail?: string
}

type PipelineRun = {
  pipeline_run_id?: string
  provider?: string
  project?: string
  name?: string
  status?: string
  conclusion?: string
  url?: string
  ref?: string
  head_sha?: string
}

type EnvRow = {
  id?: string
  display_name?: string
  tier?: string
  project?: string
  current_version?: string
  rollback_target_version?: string
  approval_status?: string
  last_successful_deploy_at?: string
  last_deploy_status?: string
}

type ReleaseTrain = {
  name?: string
  track?: string
  current_focus?: string
  candidates?: { version?: string; status?: string; artifact_ref?: string }[]
}

type PromotionRow = {
  id?: string
  from_env?: string
  to_env?: string
  artifact_version?: string
  blocked_reason?: string | null
  checkpoints?: { name?: string; status?: string; required_role?: string }[]
}

type FreezeWindow = {
  id?: string
  name?: string
  active?: boolean
  blocks_promotion_to?: string[]
}

export type SecurityReleaseGate = {
  passed?: boolean
  failed_policy_ids?: string[]
  summary?: string
  risk_score?: {
    value?: number
    scale?: string
    breakdown?: Record<string, number>
    computed_from?: string
  }
}

export type CicdControlTowerPayload = {
  ok?: boolean
  feature_enabled?: boolean
  provider_kind?: string
  resolved_at?: string
  hints?: string[]
  pipeline_runs?: PipelineRun[]
  environments?: EnvRow[]
  release_train?: ReleaseTrain | null
  promotions?: PromotionRow[]
  freeze_windows?: FreezeWindow[]
  blocked_promotions?: BlockedRow[]
  what_is_live?: WhatLiveRow[]
  rollback_targets?: { environment_id?: string; rollback_target_version?: string; approval_status?: string }[]
  security_release_gate?: SecurityReleaseGate | null
}

/**
 * Plan → Today: environments, promotions, freezes, normalized pipeline runs — from
 * `.lenses-local/cicd-orchestration.json` or demo seed (`LENSES_CICD_ORCHESTRATION_SEED_DEMO=1`).
 */
export function DeliveryControlTowerCard() {
  const { state } = useWorkspace()
  const refreshKey = state?.resolved_at ?? null

  const block = useResilientJsonBlock<CicdControlTowerPayload>('/api/cicd/control-tower', {
    snapshotKey: 'cicd-control-tower',
    refreshKey,
  })

  const data = block.data
  const phase = block.phase

  useEffect(() => {
    if (phase === 'error' && block.failure) {
      recordPageFailure('cicd_control_tower', block.failure.summary)
    }
  }, [phase, block.failure])

  let inner: ReactNode

  if (phase === 'loading' && !data) {
    inner = (
      <StatePanel
        variant="loading"
        density="compact"
        title="Loading CI/CD control tower"
        description="Pipelines, environments, release train, and promotion blockers from the local orchestration fixture."
      />
    )
  } else if (phase === 'error' && !data) {
    inner = (
      <StatePanel
        variant="error"
        density="compact"
        title="Could not load CI/CD control tower"
        description="Confirm the Lenses server is running, then retry."
        technicalDetail={block.failure?.summary ?? null}
        actions={
          <button type="button" className="le-btn le-btn--primary" onClick={() => block.retry()}>
            Retry
          </button>
        }
      />
    )
  } else if (!data?.ok) {
    inner = (
      <StatePanel variant="empty" density="compact" title="CI/CD payload unavailable" description="Unexpected response." />
    )
  } else if (data.feature_enabled === false) {
    inner = (
      <StatePanel
        variant="empty"
        density="compact"
        title="CI/CD control tower disabled"
        description={
          <>
            Set <code className="le-mono">LENSES_EXPERIMENTAL_CICD_ORCHESTRATION=1</code> (default) and restart Lenses
            to enable deployment and release views.
          </>
        }
      />
    )
  } else {
    const scanOnly = data.provider_kind === 'scan_only'
    const live = data.what_is_live ?? []
    const blocked = data.blocked_promotions ?? []
    const freezes = (data.freeze_windows ?? []).filter((f) => f.active)
    const rt = data.release_train
    const promos = data.promotions ?? []
    const runs = data.pipeline_runs ?? []
    const envs = data.environments ?? []
    const rollbacks = data.rollback_targets ?? []

    inner = (
      <>
        {data.hints?.length ? (
          <ul className="forge-support" style={{ marginBottom: '0.75rem' }}>
            {data.hints.map((h) => (
              <li key={h.slice(0, 96)}>{h}</li>
            ))}
          </ul>
        ) : null}
        {scanOnly ? (
          <StatePanel
            variant="empty"
            density="compact"
            title="No CI/CD orchestration fixture"
            description={
              <>
                Add <code className="le-mono">.lenses-local/cicd-orchestration.json</code> or{' '}
                <code className="le-mono">LENSES_CICD_ORCHESTRATION_SEED_DEMO=1</code> for environments, promotions,
                pipelines, and freeze windows.
              </>
            }
          />
        ) : null}

        {!scanOnly && rt ? (
          <div className="forge-support" style={{ marginBottom: '0.85rem' }}>
            <p style={{ marginTop: 0, marginBottom: '0.35rem' }}>
              <strong>Release train:</strong> {rt.name ?? '—'} ({rt.track ?? '—'}) · <strong>focus</strong>{' '}
              <code className="le-mono">{rt.current_focus ?? '—'}</code>
            </p>
            {(rt.candidates ?? []).length ? (
              <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
                {(rt.candidates ?? []).slice(0, 6).map((c) => (
                  <li key={String(c.version)}>
                    <code className="le-mono">{c.version}</code>
                    {c.status ? <> · {c.status}</> : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ margin: 0 }}>No release candidates in fixture.</p>
            )}
          </div>
        ) : null}

        {!scanOnly && data.security_release_gate ? (
          <div
            className="le-panel forge-card"
            style={{ marginBottom: '0.85rem', padding: '0.75rem 1rem' }}
            aria-labelledby="le-cicd-sec-gate-h"
          >
            <h3 id="le-cicd-sec-gate-h" className="le-delivery-subtitle" style={{ marginTop: 0 }}>
              Security / compliance release gate
            </h3>
            <p style={{ marginTop: '0.35rem', marginBottom: '0.35rem' }}>
              <strong>Status:</strong>{' '}
              {data.security_release_gate.passed ? (
                <span>Passed</span>
              ) : (
                <strong style={{ color: 'var(--le-danger, #c62828)' }}>Blocked</strong>
              )}
              {data.security_release_gate.risk_score?.value != null ? (
                <>
                  {' '}
                  · <strong>Risk score</strong> {String(data.security_release_gate.risk_score.value)} (
                  {data.security_release_gate.risk_score.scale ?? '0–100, higher worse'})
                </>
              ) : null}
            </p>
            {data.security_release_gate.summary ? (
              <p className="forge-support" style={{ marginTop: 0 }}>
                {data.security_release_gate.summary}
              </p>
            ) : null}
            {(data.security_release_gate.failed_policy_ids ?? []).length > 0 ? (
              <p className="forge-support" style={{ marginBottom: 0 }}>
                Failed policies:{' '}
                <code className="le-mono">{(data.security_release_gate.failed_policy_ids ?? []).join(', ')}</code>
              </p>
            ) : null}
            <p className="forge-support" style={{ marginTop: '0.5rem', marginBottom: 0 }}>
              <Link className="le-delivery-link" to="/plan?tab=today#le-devsecops-h">
                Open DevSecOps detail
              </Link>
              {' · '}
              <Link className="le-delivery-link" to="/plan?tab=today#le-release-manager-h">
                Release manager packet
              </Link>
            </p>
          </div>
        ) : null}

        {!scanOnly && freezes.length > 0 ? (
          <div className="forge-support" style={{ marginBottom: '0.85rem' }}>
            <p style={{ marginTop: 0, marginBottom: '0.35rem' }}>
              <strong>Active freeze windows</strong>
            </p>
            <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
              {freezes.map((f) => (
                <li key={f.id ?? f.name}>
                  {f.name ?? f.id}
                  {(f.blocks_promotion_to ?? []).length ? (
                    <> — blocks promotion to {(f.blocks_promotion_to ?? []).join(', ')}</>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {!scanOnly && blocked.length > 0 ? (
          <div style={{ marginBottom: '0.85rem' }}>
            <h3 className="le-delivery-subtitle">Blocked from promotion</h3>
            <div className="le-cc-table-wrap" style={{ overflowX: 'auto' }}>
              <table className="le-cc-table">
                <thead>
                  <tr>
                    <th scope="col">Promotion</th>
                    <th scope="col">Reason</th>
                    <th scope="col">Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {blocked.map((brow, i) => (
                    <tr key={`${brow.promotion_id ?? i}-${brow.reason ?? ''}`}>
                      <td>
                        <code className="le-mono">{brow.promotion_id ?? '—'}</code>
                      </td>
                      <td>{brow.reason ?? '—'}</td>
                      <td className="forge-support">{brow.detail ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}

        {!scanOnly && live.length > 0 ? (
          <div style={{ marginBottom: '0.85rem' }}>
            <h3 className="le-delivery-subtitle">What is live where</h3>
            <div className="le-cc-table-wrap" style={{ overflowX: 'auto' }}>
              <table className="le-cc-table">
                <caption className="forge-support" style={{ textAlign: 'left', marginBottom: '0.35rem' }}>
                  Current version and last successful deploy per environment
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Environment</th>
                    <th scope="col">Tier</th>
                    <th scope="col">Version</th>
                    <th scope="col">Last success</th>
                    <th scope="col">Status</th>
                    <th scope="col">Project</th>
                  </tr>
                </thead>
                <tbody>
                  {live.map((row) => (
                    <tr key={row.environment_id ?? row.display_name}>
                      <td>{row.display_name || row.environment_id || '—'}</td>
                      <td>{row.tier || '—'}</td>
                      <td>
                        <code className="le-mono">{row.version || '—'}</code>
                      </td>
                      <td>
                        {row.last_successful_deploy_at ? (
                          <time dateTime={row.last_successful_deploy_at}>{row.last_successful_deploy_at}</time>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td>{row.last_deploy_status || '—'}</td>
                      <td>
                        {row.project ? (
                          <Link to={`/projects/${encodeURIComponent(row.project)}`}>{row.project}</Link>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : !scanOnly && envs.length === 0 ? (
          <p className="le-delivery-section__empty">No environments in scope for this workspace scan.</p>
        ) : null}

        {!scanOnly && rollbacks.length > 0 ? (
          <div className="forge-support" style={{ marginBottom: '0.85rem' }}>
            <p style={{ marginTop: 0, marginBottom: '0.35rem' }}>
              <strong>Rollback targets</strong> (from fixture)
            </p>
            <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
              {rollbacks.map((r) => (
                <li key={r.environment_id}>
                  <code className="le-mono">{r.environment_id}</code> →{' '}
                  <code className="le-mono">{r.rollback_target_version}</code>
                  {r.approval_status ? <> · {r.approval_status}</> : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {!scanOnly && promos.length > 0 ? (
          <div style={{ marginBottom: '0.85rem' }}>
            <h3 className="le-delivery-subtitle">Promotions and approvals</h3>
            <div className="le-cc-table-wrap" style={{ overflowX: 'auto' }}>
              <table className="le-cc-table">
                <thead>
                  <tr>
                    <th scope="col">Id</th>
                    <th scope="col">Route</th>
                    <th scope="col">Artifact</th>
                    <th scope="col">Checkpoints</th>
                    <th scope="col">Blocked</th>
                  </tr>
                </thead>
                <tbody>
                  {promos.map((p) => (
                    <tr key={p.id ?? `${p.from_env}-${p.to_env}`}>
                      <td>
                        <code className="le-mono">{p.id ?? '—'}</code>
                      </td>
                      <td>
                        {p.from_env ?? '—'} → {p.to_env ?? '—'}
                      </td>
                      <td>
                        <code className="le-mono">{p.artifact_version ?? '—'}</code>
                      </td>
                      <td className="forge-support">
                        {(p.checkpoints ?? []).map((c) => `${c.name ?? ''} (${c.status ?? ''})`).join('; ') || '—'}
                      </td>
                      <td>{p.blocked_reason ? <span className="forge-support">{String(p.blocked_reason)}</span> : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}

        {!scanOnly && runs.length > 0 ? (
          <div style={{ marginBottom: '0.5rem' }}>
            <h3 className="le-delivery-subtitle">Recent pipeline runs (normalized)</h3>
            <div className="le-cc-table-wrap" style={{ overflowX: 'auto' }}>
              <table className="le-cc-table">
                <thead>
                  <tr>
                    <th scope="col">Provider</th>
                    <th scope="col">Project</th>
                    <th scope="col">Run</th>
                    <th scope="col">Status</th>
                    <th scope="col">Ref / SHA</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.slice(0, 24).map((r) => (
                    <tr key={`${r.provider}-${r.pipeline_run_id}`}>
                      <td>{r.provider ?? '—'}</td>
                      <td>
                        {r.project ? (
                          <Link to={`/projects/${encodeURIComponent(r.project)}`}>{r.project}</Link>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td>
                        {r.url ? (
                          <a className="le-delivery-link" href={r.url} rel="noreferrer" target="_blank">
                            {r.name ?? r.pipeline_run_id ?? 'open'}
                          </a>
                        ) : (
                          (r.name ?? r.pipeline_run_id ?? '—') as ReactNode
                        )}
                      </td>
                      <td>
                        {r.conclusion || r.status || '—'}
                      </td>
                      <td className="forge-support">
                        <code className="le-mono">{(r.ref || '').slice(0, 32)}</code>
                        {r.head_sha ? (
                          <>
                            {' '}
                            <code className="le-mono">{(r.head_sha || '').slice(0, 12)}</code>
                          </>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}

        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          Provider: <code className="le-mono">{data.provider_kind ?? 'unknown'}</code>
          {data.resolved_at ? (
            <>
              {' '}
              · Scan <time dateTime={data.resolved_at}>{data.resolved_at}</time>
            </>
          ) : null}
          {' · '}
          <Link className="le-delivery-link" to="/plan?tab=today#le-release-manager-h">
            Release manager
          </Link>
          {' · '}
          <Link className="le-delivery-link" to="/plan?tab=today#le-ops-delivery-h">
            Ops &amp; DORA
          </Link>
          {' · '}
          <a className="le-delivery-link" href="/api/cicd/control-tower">
            Raw JSON
          </a>
        </p>
      </>
    )
  }

  return (
    <section className="le-delivery-section" aria-labelledby="le-cicd-tower-h" id="le-cicd-tower">
      <h2 id="le-cicd-tower-h" className="le-delivery-section__title">
        CI/CD control tower
      </h2>
      <p className="le-delivery-section__lead">
        Canonical pipeline runs (GitHub Actions, GitLab CI, Azure Pipelines, Jenkins, Argo CD-style sync), environment
        catalog, release train, promotion checkpoints, freeze windows, and rollback hints. Local-first (
        <code className="le-mono">cicd-orchestration.json</code>); adapters normalize provider payloads to one contract.
      </p>
      {inner}
    </section>
  )
}
