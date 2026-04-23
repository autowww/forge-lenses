import { useEffect, type ReactNode } from 'react'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useResilientJsonBlock } from '../../hooks/useResilientJsonBlock'
import { StatePanel } from '../page/StatePanel'
import { recordPageFailure } from '../../telemetry/studioTelemetry'

type DoraPayload = {
  deployment_frequency?: { production_successful_deploys?: number; per_day_approx?: number; computed_from?: string }
  lead_time_for_changes?: { median_hours?: number | null; sample_count?: number; computed_from?: string }
  change_failure_rate?: { ratio?: number; failed_changes_count?: number; deployments_denominator?: number }
  recovery?: { mean_time_to_restore_hours?: number | null; computed_from?: string }
  rework_signals?: { failed_pipeline_runs?: number; blocked_promotions?: number; open_defects?: number }
}

type OpsOverviewPayload = {
  ok?: boolean
  feature_enabled?: boolean
  provider_kind?: string
  resolved_at?: string
  hints?: string[]
  services?: { service_id?: string; display_name?: string; owner_team?: string }[]
  incidents?: {
    incident_id?: string
    title?: string
    status?: string
    severity?: string
    traceability?: { release_version?: string; environment_id?: string; story_ids?: string[] }
  }[]
  rollback_signals?: { message?: string; recommend_rollback_to?: string; severity?: string }[]
  dora_metrics?: DoraPayload
  feature_flag_exposures?: { flag_key?: string; environment_id?: string; variant?: string }[]
  error_budget_events?: { slo_id?: string; burn_percent?: number; reason?: string }[]
}

/**
 * Plan → Today: DORA-style metrics from CI/CD + incidents, service catalog, rollback hints, flags / error budget.
 */
export function OpsDeliveryCard() {
  const { state } = useWorkspace()
  const refreshKey = state?.resolved_at ?? null

  const block = useResilientJsonBlock<OpsOverviewPayload>('/api/ops-delivery/overview', {
    snapshotKey: 'ops-delivery-overview',
    refreshKey,
  })

  const data = block.data
  const phase = block.phase

  useEffect(() => {
    if (phase === 'error' && block.failure) {
      recordPageFailure('ops_delivery_overview', block.failure.summary)
    }
  }, [phase, block.failure])

  let inner: ReactNode

  if (phase === 'loading' && !data) {
    inner = (
      <StatePanel
        variant="loading"
        density="compact"
        title="Loading ops & delivery metrics"
        description="DORA signals, incidents, rollback recommendations, and service catalog."
      />
    )
  } else if (phase === 'error' && !data) {
    inner = (
      <StatePanel
        variant="error"
        density="compact"
        title="Could not load ops delivery overview"
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
      <StatePanel variant="error" density="compact" title="Unexpected payload" description="Try again or check the API." />
    )
  } else if (data.feature_enabled === false) {
    inner = (
      <StatePanel
        variant="empty"
        density="compact"
        title="Ops delivery metrics disabled"
        description="Set LENSES_EXPERIMENTAL_OPS_DELIVERY=1 (default on) to enable this card."
      />
    )
  } else if (data.provider_kind === 'scan_only') {
    inner = (
      <StatePanel
        variant="empty"
        density="compact"
        title="No ops-delivery fixture"
        description={
          <>
            Add <code className="le-mono">.lenses-local/ops-delivery.json</code> or set{' '}
            <code className="le-mono">LENSES_OPS_DELIVERY_SEED_DEMO=1</code> for services, incidents, SLOs, and DORA
            rollups merged with CI/CD.
          </>
        }
      />
    )
  } else {
    const d = data.dora_metrics || {}
    const df = d.deployment_frequency || {}
    const lt = d.lead_time_for_changes || {}
    const cfr = d.change_failure_rate || {}
    const rec = d.recovery || {}
    const rw = d.rework_signals || {}
    const rbs = data.rollback_signals || []
    const svcs = data.services || []
    const incs = data.incidents || []

    inner = (
      <>
        <p className="forge-support" style={{ marginTop: 0 }}>
          Deploy frequency, lead time, change-failure rate, recovery, and rework are computed from{' '}
          <strong>live pipeline and environment history</strong> plus your ops fixture (incidents, SLOs, flags). Production
          incidents list <strong>release / environment / story</strong> trace fields.
        </p>

        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginTop: '0.85rem', marginBottom: '0.35rem' }}>
          DORA-style signals (rolling window)
        </h3>
        <div className="le-stats">
          <div className="le-stat">
            <span className="le-stat__value">{df.production_successful_deploys ?? '—'}</span>
            <span className="le-stat__label">Prod deploys</span>
          </div>
          <div className="le-stat">
            <span className="le-stat__value">{lt.median_hours != null ? `${lt.median_hours}h` : '—'}</span>
            <span className="le-stat__label">Lead time (median)</span>
          </div>
          <div className="le-stat">
            <span className="le-stat__value">{cfr.ratio != null ? `${(cfr.ratio * 100).toFixed(1)}%` : '—'}</span>
            <span className="le-stat__label">Change fail rate</span>
          </div>
          <div className="le-stat">
            <span className="le-stat__value">
              {rec.mean_time_to_restore_hours != null ? `${rec.mean_time_to_restore_hours}h` : '—'}
            </span>
            <span className="le-stat__label">MTTR (mean)</span>
          </div>
        </div>
        <p className="forge-support" style={{ fontSize: '0.8rem', marginTop: '0.35rem' }}>
          Rework: {rw.failed_pipeline_runs ?? 0} failed pipeline runs · {rw.blocked_promotions ?? 0} blocked promotions ·{' '}
          {rw.open_defects ?? 0} open defects (when quality fixture present).
        </p>

        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginTop: '0.85rem', marginBottom: '0.35rem' }}>
          Service catalog
        </h3>
        <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem', fontSize: '0.9rem' }}>
          {svcs.slice(0, 8).map((s) => (
            <li key={s.service_id}>
              <code className="le-mono">{s.service_id}</code>
              {s.display_name ? <> — {s.display_name}</> : null}
              {s.owner_team ? <span className="forge-support"> ({s.owner_team})</span> : null}
            </li>
          ))}
        </ul>

        {rbs.length > 0 ? (
          <>
            <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginTop: '0.85rem', marginBottom: '0.35rem' }}>
              Rollback signals
            </h3>
            <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem', fontSize: '0.9rem' }}>
              {rbs.map((r, i) => (
                <li key={i}>
                  {r.message}
                  {r.recommend_rollback_to ? (
                    <>
                      {' '}
                      <span className="forge-support">
                        Suggested target: <code className="le-mono">{r.recommend_rollback_to}</code>
                      </span>
                    </>
                  ) : null}
                </li>
              ))}
            </ul>
          </>
        ) : null}

        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginTop: '0.85rem', marginBottom: '0.35rem' }}>
          Incidents (traceability)
        </h3>
        <div className="le-table-wrap" style={{ maxHeight: '10rem', overflow: 'auto' }}>
          <table className="le-table" style={{ fontSize: '0.8rem' }}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Status</th>
                <th>Release</th>
                <th>Env</th>
              </tr>
            </thead>
            <tbody>
              {incs.slice(0, 12).map((x) => (
                <tr key={x.incident_id}>
                  <td>
                    <code className="le-mono">{x.incident_id}</code>
                  </td>
                  <td>{x.status}</td>
                  <td>{x.traceability?.release_version || '—'}</td>
                  <td>{x.traceability?.environment_id || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {(data.feature_flag_exposures || []).length > 0 ? (
          <p className="forge-support" style={{ marginTop: '0.65rem' }}>
            <strong>Feature flags:</strong>{' '}
            {(data.feature_flag_exposures || [])
              .slice(0, 4)
              .map((f) => `${f.flag_key}@${f.environment_id}=${f.variant}`)
              .join('; ')}
          </p>
        ) : null}

        {(data.error_budget_events || []).length > 0 ? (
          <p className="forge-support" style={{ marginTop: '0.35rem' }}>
            <strong>Error budget:</strong>{' '}
            {(data.error_budget_events || [])
              .slice(0, 3)
              .map((e) => `${e.slo_id} burn ${e.burn_percent}%`)
              .join('; ')}
          </p>
        ) : null}

        {data.hints?.length ? (
          <ul className="le-list forge-support" style={{ marginTop: '0.65rem', fontSize: '0.85rem' }}>
            {data.hints.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        ) : null}

        <p style={{ marginTop: '0.65rem', marginBottom: 0 }}>
          <a className="le-btn le-btn--small" href="/api/ops-delivery/overview">
            Raw JSON
          </a>
        </p>
      </>
    )
  }

  return (
    <section className="le-delivery-section" aria-labelledby="le-ops-delivery-h" id="le-ops-delivery">
      <h2 id="le-ops-delivery-h" className="le-delivery-section__title">
        Ops feedback &amp; delivery metrics
      </h2>
      {inner}
    </section>
  )
}
