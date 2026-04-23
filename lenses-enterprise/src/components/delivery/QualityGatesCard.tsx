import { useEffect, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useResilientJsonBlock } from '../../hooks/useResilientJsonBlock'
import { StatePanel } from '../page/StatePanel'
import { recordPageFailure } from '../../telemetry/studioTelemetry'

type GateEval = {
  gate_id?: string
  name?: string
  passed?: boolean
  detail?: string
  applies_to_environments?: string[]
  blocks_release_train?: boolean
}

type QualityOverviewPayload = {
  ok?: boolean
  feature_enabled?: boolean
  provider_kind?: string
  resolved_at?: string
  hints?: string[]
  gate_evaluations?: GateEval[]
  release_quality?: {
    ready?: boolean
    failed_gates?: string[]
    blocking_train_gates?: string[]
    summary?: string
  } | null
  test_runs?: { id?: string; suite_id?: string; status?: string; failed?: number; passed?: number }[]
  defects?: { id?: string; status?: string; severity?: string }[]
  run_comparisons?: {
    current_run_id?: string
    previous_run_id?: string
    delta_failed?: number
    delta_passed?: number
  }[]
  release_readiness_checklists?: {
    release_version?: string
    items?: { id?: string; label?: string; status?: string }[]
  }[]
  uat_signoffs?: { story_id?: string; status?: string; by?: string }[]
}

/**
 * Plan → Today: test runs, defects, gate evaluations, UAT, readiness — from
 * `.lenses-local/test-quality.json` or `LENSES_TEST_QUALITY_SEED_DEMO=1`. Failed gates also merge into
 * CI/CD blocked promotions on the server.
 */
export function QualityGatesCard() {
  const { state } = useWorkspace()
  const refreshKey = state?.resolved_at ?? null

  const block = useResilientJsonBlock<QualityOverviewPayload>('/api/quality/overview', {
    snapshotKey: 'quality-overview',
    refreshKey,
  })

  const data = block.data
  const phase = block.phase

  useEffect(() => {
    if (phase === 'error' && block.failure) {
      recordPageFailure('quality_overview', block.failure.summary)
    }
  }, [phase, block.failure])

  let inner: ReactNode

  if (phase === 'loading' && !data) {
    inner = (
      <StatePanel
        variant="loading"
        density="compact"
        title="Loading quality overview"
        description="Test plans, runs, defects, gate evaluations, and release readiness from the local fixture."
      />
    )
  } else if (phase === 'error' && !data) {
    inner = (
      <StatePanel
        variant="error"
        density="compact"
        title="Could not load quality overview"
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
      <StatePanel variant="empty" density="compact" title="Quality payload unavailable" description="Unexpected response." />
    )
  } else if (data.feature_enabled === false) {
    inner = (
      <StatePanel
        variant="empty"
        density="compact"
        title="Test management and quality gates disabled"
        description={
          <>
            Set <code className="le-mono">LENSES_EXPERIMENTAL_TEST_QUALITY=1</code> (default) and restart Lenses.
          </>
        }
      />
    )
  } else if (data.provider_kind === 'scan_only') {
    inner = (
      <StatePanel
        variant="empty"
        density="compact"
        title="No test-quality fixture"
        description={
          <>
            Add <code className="le-mono">.lenses-local/test-quality.json</code> or{' '}
            <code className="le-mono">LENSES_TEST_QUALITY_SEED_DEMO=1</code> for gates, runs, defects, UAT, and
            readiness checklists.
          </>
        }
      />
    )
  } else {
    const ev = data.gate_evaluations ?? []
    const failed = ev.filter((e) => !e.passed)
    const rq = data.release_quality
    const openDefects = (data.defects ?? []).filter(
      (d) => !['closed', 'done', 'resolved'].includes(String(d.status || '').toLowerCase()),
    )

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
            <span className="le-stat__value" style={{ color: failed.length ? 'var(--le-danger, #c62828)' : undefined }}>
              {failed.length}/{ev.length}
            </span>
            <span className="le-stat__label">Gates failed / total</span>
          </div>
          <div className="le-stat">
            <span className="le-stat__value">{openDefects.length}</span>
            <span className="le-stat__label">Open defects</span>
          </div>
          <div className="le-stat">
            <span className="le-stat__value">{rq?.ready === true ? 'Yes' : rq?.ready === false ? 'No' : '—'}</span>
            <span className="le-stat__label">Release train ready</span>
          </div>
        </div>

        {rq?.summary ? <p className="forge-support">{rq.summary}</p> : null}

        {ev.length > 0 ? (
          <div className="le-cc-table-wrap" style={{ overflowX: 'auto', marginBottom: '1rem' }}>
            <table className="le-cc-table">
              <caption className="forge-support" style={{ textAlign: 'left', marginBottom: '0.35rem' }}>
                Quality gates (manual + automated evidence)
              </caption>
              <thead>
                <tr>
                  <th scope="col">Gate</th>
                  <th scope="col">Result</th>
                  <th scope="col">Detail</th>
                  <th scope="col">Environments</th>
                </tr>
              </thead>
              <tbody>
                {ev.map((g) => (
                  <tr key={g.gate_id ?? g.name}>
                    <td>{g.name ?? g.gate_id ?? '—'}</td>
                    <td>{g.passed ? <span>Passed</span> : <strong>Failed</strong>}</td>
                    <td className="forge-support">{g.detail ?? '—'}</td>
                    <td className="forge-support">{(g.applies_to_environments ?? []).join(', ') || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="le-delivery-section__empty">No gate definitions in fixture.</p>
        )}

        {(data.run_comparisons ?? []).length > 0 ? (
          <div style={{ marginBottom: '1rem' }}>
            <h3 className="le-delivery-subtitle">Run vs prior (evidence trend)</h3>
            <ul className="forge-support" style={{ marginTop: 0 }}>
              {(data.run_comparisons ?? []).map((c) => (
                <li key={c.current_run_id}>
                  Run <code className="le-mono">{c.current_run_id}</code> vs{' '}
                  <code className="le-mono">{c.previous_run_id}</code>
                  {c.delta_failed != null ? (
                    <>
                      {' '}
                      — failed delta <strong>{c.delta_failed > 0 ? '+' : ''}{c.delta_failed}</strong>, passed delta{' '}
                      <strong>{c.delta_passed != null && c.delta_passed > 0 ? '+' : ''}{c.delta_passed ?? 0}</strong>
                    </>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {(data.release_readiness_checklists ?? []).map((cl) => (
          <div key={cl.release_version} style={{ marginBottom: '1rem' }}>
            <h3 className="le-delivery-subtitle">Release readiness — {cl.release_version ?? '—'}</h3>
            <ul className="le-list" style={{ marginTop: 0 }}>
              {(cl.items ?? []).map((it) => (
                <li key={it.id ?? it.label}>
                  {it.label ?? it.id} — <span className="forge-support">{it.status ?? '—'}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}

        {(data.uat_signoffs ?? []).length > 0 ? (
          <div style={{ marginBottom: '0.5rem' }}>
            <h3 className="le-delivery-subtitle">UAT sign-off (sample)</h3>
            <ul className="forge-support" style={{ marginTop: 0 }}>
              {(data.uat_signoffs ?? []).map((u) => (
                <li key={u.story_id}>
                  Story <code className="le-mono">{u.story_id}</code> — {u.status ?? '—'}
                  {u.by ? <> by {u.by}</> : null}
                </li>
              ))}
            </ul>
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
          <a className="le-delivery-link" href="/api/quality/overview">
            Raw JSON
          </a>
          {' · '}
          <Link className="le-delivery-link" to="/plan?tab=today#le-quality-gates-h">
            Anchor link
          </Link>
        </p>
      </>
    )
  }

  return (
    <section className="le-delivery-section" aria-labelledby="le-quality-gates-h" id="le-quality-gates">
      <h2 id="le-quality-gates-h" className="le-delivery-section__title">
        Quality gates and test evidence
      </h2>
      <p className="le-delivery-section__lead">
        Canonical test entities (plans, suites, cases, runs, defects, coverage, flaky signals) with gate rules that
        can block promotions and the release train. Complements pipeline rows above; evidence also appears on work
        items when the graph and fixture are loaded.
      </p>
      {inner}
    </section>
  )
}
