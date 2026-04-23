import { useEffect, type ReactNode } from 'react'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useResilientJsonBlock } from '../../hooks/useResilientJsonBlock'
import { StatePanel } from '../page/StatePanel'
import { recordPageFailure } from '../../telemetry/studioTelemetry'

type PolicyEval = {
  policy_id?: string
  name?: string
  passed?: boolean
  detail?: string
  applies_to_environments?: string[]
}

type DevsecopsOverviewPayload = {
  ok?: boolean
  feature_enabled?: boolean
  provider_kind?: string
  resolved_at?: string
  hints?: string[]
  risk_score?: {
    value?: number
    scale?: string
    breakdown?: Record<string, number | string>
    computed_from?: string
    exception_count_active?: number
  } | null
  security_release_gate?: {
    passed?: boolean
    failed_policy_ids?: string[]
    summary?: string
  } | null
  policy_check_evaluations?: PolicyEval[]
  rollups?: {
    by_repo?: Record<string, { weighted_open_score?: number; open_security_findings?: number }>
    summary_counts?: Record<string, Record<string, number>>
  }
  exceptions?: {
    id?: string
    title?: string
    status?: string
    owner?: string
    expires_at?: string
    audit_trail?: { at?: string; actor?: string; action?: string; note?: string }[]
  }[]
  controls?: { control_id?: string; name?: string; implementation_status?: string; framework?: string }[]
  sbom_components?: { name?: string; version?: string }[]
  provenance_attestations?: { artifact_ref?: string; valid?: boolean }[]
}

/**
 * Plan → Today: findings, risk (computed), policies, exceptions with audit trail, SBOM/provenance — from
 * ``devsecops-compliance.json`` or ``LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO=1``. Policies can block promotions
 * (see CI/CD control tower).
 */
export function DevSecOpsCard() {
  const { state } = useWorkspace()
  const refreshKey = state?.resolved_at ?? null

  const block = useResilientJsonBlock<DevsecopsOverviewPayload>('/api/devsecops/overview', {
    snapshotKey: 'devsecops-overview',
    refreshKey,
  })

  const data = block.data
  const phase = block.phase

  useEffect(() => {
    if (phase === 'error' && block.failure) {
      recordPageFailure('devsecops_overview', block.failure.summary)
    }
  }, [phase, block.failure])

  let inner: ReactNode

  if (phase === 'loading' && !data) {
    inner = (
      <StatePanel
        variant="loading"
        density="compact"
        title="Loading DevSecOps overview"
        description="Security findings, compliance controls, policy checks, and risk score from the local fixture."
      />
    )
  } else if (phase === 'error' && !data) {
    inner = (
      <StatePanel
        variant="error"
        density="compact"
        title="Could not load DevSecOps overview"
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
      <StatePanel variant="empty" density="compact" title="DevSecOps payload unavailable" description="Unexpected response." />
    )
  } else if (data.feature_enabled === false) {
    inner = (
      <StatePanel
        variant="empty"
        density="compact"
        title="DevSecOps / compliance orchestration disabled"
        description={
          <>
            Set <code className="le-mono">LENSES_EXPERIMENTAL_DEVSECOPS_COMPLIANCE=1</code> (default) and restart Lenses.
          </>
        }
      />
    )
  } else if (data.provider_kind === 'scan_only') {
    inner = (
      <StatePanel
        variant="empty"
        density="compact"
        title="No devsecops-compliance fixture"
        description={
          <>
            Add <code className="le-mono">.lenses-local/devsecops-compliance.json</code> or{' '}
            <code className="le-mono">LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO=1</code> for scanners, SBOM, provenance,
            controls, exceptions, and policy-as-code checks.
          </>
        }
      />
    )
  } else {
    const rs = data.risk_score
    const gate = data.security_release_gate
    const ev = data.policy_check_evaluations ?? []
    const failed = ev.filter((e) => !e.passed)

    inner = (
      <>
        {data.hints?.length ? (
          <ul className="forge-support" style={{ marginBottom: '0.75rem' }}>
            {data.hints.map((h) => (
              <li key={h.slice(0, 96)}>{h}</li>
            ))}
          </ul>
        ) : null}

        <div className="le-stats" style={{ marginBottom: '1rem' }}>
          <div className="le-stat">
            <span className="le-stat__value">{rs?.value ?? '—'}</span>
            <span className="le-stat__label">Risk score (computed)</span>
          </div>
          <div className="le-stat">
            <span className="le-stat__value">{gate?.passed === true ? 'Pass' : gate?.passed === false ? 'Fail' : '—'}</span>
            <span className="le-stat__label">Release gate</span>
          </div>
          <div className="le-stat">
            <span className="le-stat__value">{failed.length}/{ev.length}</span>
            <span className="le-stat__label">Policies failed</span>
          </div>
          <div className="le-stat">
            <span className="le-stat__value">{data.exceptions?.length ?? 0}</span>
            <span className="le-stat__label">Exceptions (fixture)</span>
          </div>
        </div>

        {rs?.breakdown ? (
          <p className="forge-support">
            <strong>Score inputs:</strong> findings {String(rs.breakdown.from_findings ?? 0)}, vulns{' '}
            {String(rs.breakdown.from_vulnerabilities ?? 0)}, secrets {String(rs.breakdown.from_secrets ?? 0)}, deps{' '}
            {String(rs.breakdown.from_dependency_risks ?? 0)}, control mitigation −{String(rs.breakdown.mitigation_controls ?? 0)}.
            {rs.computed_from ? <> {rs.computed_from.slice(0, 120)}…</> : null}
          </p>
        ) : null}

        {gate?.summary ? <p className="forge-support">{gate.summary}</p> : null}

        {ev.length > 0 ? (
          <div className="le-cc-table-wrap" style={{ overflowX: 'auto', marginBottom: '1rem' }}>
            <table className="le-cc-table">
              <caption className="forge-support" style={{ textAlign: 'left', marginBottom: '0.35rem' }}>
                Policy-as-code checks (release readiness)
              </caption>
              <thead>
                <tr>
                  <th scope="col">Policy</th>
                  <th scope="col">Result</th>
                  <th scope="col">Detail</th>
                </tr>
              </thead>
              <tbody>
                {ev.map((p) => (
                  <tr key={p.policy_id ?? p.name}>
                    <td>{p.name ?? p.policy_id ?? '—'}</td>
                    <td>{p.passed ? 'Passed' : <strong>Failed</strong>}</td>
                    <td className="forge-support">{p.detail ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        {(data.exceptions ?? []).length > 0 ? (
          <div style={{ marginBottom: '1rem' }}>
            <h3 className="le-delivery-subtitle">Risk acceptance &amp; exceptions (auditable)</h3>
            {(data.exceptions ?? []).map((ex) => (
              <div key={ex.id} className="forge-support" style={{ marginBottom: '0.75rem' }}>
                <strong>{ex.title ?? ex.id}</strong> — {ex.status ?? '—'} · owner {ex.owner ?? '—'} · expires{' '}
                <time dateTime={ex.expires_at}>{ex.expires_at ?? '—'}</time>
                {(ex.audit_trail ?? []).length ? (
                  <ul style={{ margin: '0.35rem 0', paddingLeft: '1.1rem' }}>
                    {(ex.audit_trail ?? []).map((a, i) => (
                      <li key={`${a.at}-${i}`}>
                        {a.at} · <code className="le-mono">{a.actor}</code> · {a.action}
                        {a.note ? <> — {a.note}</> : null}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}

        {(data.controls ?? []).length > 0 ? (
          <div style={{ marginBottom: '0.75rem' }}>
            <h3 className="le-delivery-subtitle">Controls (evidence mapping)</h3>
            <ul className="forge-support" style={{ marginTop: 0 }}>
              {(data.controls ?? []).map((c) => (
                <li key={c.control_id}>
                  <code className="le-mono">{c.control_id}</code> — {c.name ?? '—'} ({c.framework ?? '—'}) ·{' '}
                  {c.implementation_status ?? '—'}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <p className="forge-support">
          SBOM rows: {data.sbom_components?.length ?? 0} · Provenance: {data.provenance_attestations?.length ?? 0}
        </p>

        <p className="forge-support" style={{ marginTop: '0.5rem' }}>
          Provider: <code className="le-mono">{data.provider_kind ?? 'unknown'}</code>
          {data.resolved_at ? (
            <>
              {' '}
              · Scan <time dateTime={data.resolved_at}>{data.resolved_at}</time>
            </>
          ) : null}
          {' · '}
          <a className="le-delivery-link" href="/api/devsecops/overview">
            Raw JSON
          </a>
        </p>
      </>
    )
  }

  return (
    <section className="le-delivery-section" aria-labelledby="le-devsecops-h" id="le-devsecops">
      <h2 id="le-devsecops-h" className="le-delivery-section__title">
        DevSecOps &amp; compliance
      </h2>
      <p className="le-delivery-section__lead">
        Canonical security and compliance objects (findings, vulnerabilities, secrets, dependency risk, SBOM,
        provenance, controls, exceptions, policy decisions) with ingestion adapters for common scanners. Posture
        rollups and computed risk drive the release gate shown in the CI/CD control tower.
      </p>
      {inner}
    </section>
  )
}
