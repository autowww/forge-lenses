import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/http'
import {
  fetchProjectAutonomyMaturity,
  type AutonomyMaturityProject,
} from '../api/autonomyMaturity'
import { PageHeader, StatePanel } from '../components/page'
import { resolveUxFailure, type UxResolvedFailure } from '../lib/uxPageState'
import { ROUTE_SUBTITLE } from '../nav/studioVisibleCopy'

const LADDER: { level: string; label: string }[] = [
  { level: 'L0', label: 'Assisted' },
  { level: 'L1', label: 'Function' },
  { level: 'L2', label: 'Change-set' },
  { level: 'L3', label: 'Use-case slice' },
  { level: 'L4', label: 'Feature/component' },
]

const COMPONENT_LABEL: Record<string, string> = {
  gate_definition: 'Gate definition',
  demonstrated_evidence: 'Demonstrated evidence',
  repeatability: 'Repeatability',
  operational_metrics: 'Operational metrics',
}

const SIGNAL_LABEL: Record<string, string> = {
  forge_config_present: 'forge/forge.config.yaml present',
  forge_config_assay_keys: 'Assay keys declared (tests_pass, acceptance_criteria_met, risks_reviewed)',
  cursor_rules_present: '.cursor/rules synced',
  ci_present: 'CI config present',
  tests_present: 'Test suite present',
}

export function ProjectAutonomyMaturityPage() {
  const { name = '' } = useParams()
  const [data, setData] = useState<AutonomyMaturityProject | null>(null)
  const [err, setErr] = useState<UxResolvedFailure | null>(null)
  const [disabled, setDisabled] = useState(false)
  const [loading, setLoading] = useState(true)
  const [retryNonce, setRetryNonce] = useState(0)

  useEffect(() => {
    if (!name) return
    let cancel = false
    setLoading(true)
    fetchProjectAutonomyMaturity(name)
      .then((d) => {
        if (cancel) return
        setData(d)
        setErr(null)
      })
      .catch((e) => {
        if (cancel) return
        if (e instanceof ApiError && e.status === 404) {
          setDisabled(true)
          setErr(null)
        } else {
          setErr(resolveUxFailure(e))
        }
      })
      .finally(() => {
        if (!cancel) setLoading(false)
      })
    return () => {
      cancel = true
    }
  }, [name, retryNonce])

  const observedIdx = LADDER.findIndex((s) => s.level === data?.observed_level)

  return (
    <>
      <PageHeader
        title={`Autonomy maturity — ${name}`}
        preface={
          <Link to="/autonomy-maturity" className="forge-support">
            ← Workspace autonomy maturity
          </Link>
        }
        subtitle={ROUTE_SUBTITLE.projectAutonomyMaturity}
      />
      {loading ? (
        <StatePanel variant="loading" title="Assessing project" description="Reading gates, run evidence, and repeatability signals." />
      ) : null}
      {err ? (
        <StatePanel
          variant="error"
          title={err.title}
          description={err.description}
          technicalDetail={err.technical}
          actions={
            <button type="button" className="le-btn le-btn--primary" onClick={() => setRetryNonce((n) => n + 1)}>
              Retry
            </button>
          }
        />
      ) : null}
      {disabled ? (
        <StatePanel
          variant="empty"
          title="Autonomy maturity is disabled or project not found"
          description="Enable LENSES_EXPERIMENTAL_AUTONOMY_MATURITY=1 on the server, and check the project name."
        />
      ) : null}
      {!loading && !err && !disabled && data?.ok ? (
        <div style={{ display: 'grid', gap: '1rem' }}>
          <section className="le-card" style={{ padding: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '1rem', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '2.2rem', fontWeight: 700 }}>{data.score ?? 0}/100</span>
              <code className="le-mono" style={{ fontSize: '1.1rem' }}>{data.claim}</code>
            </div>
            <p className="le-muted" style={{ margin: '0.4rem 0 0', fontSize: '0.85rem' }}>{data.note}</p>
          </section>

          <section>
            <h2 style={{ fontSize: '1rem' }}>Ladder position</h2>
            <ol style={{ display: 'flex', gap: '0.5rem', listStyle: 'none', padding: 0, flexWrap: 'wrap' }}>
              {LADDER.map((step, i) => (
                <li
                  key={step.level}
                  className="le-card"
                  style={{
                    padding: '0.45rem 0.7rem',
                    fontSize: '0.82rem',
                    opacity: i <= observedIdx ? 1 : 0.45,
                    borderColor: i === observedIdx ? 'var(--le-accent, #4a7)' : undefined,
                  }}
                >
                  <strong>{step.level}</strong> {step.label}
                  {i === observedIdx ? (
                    <span className="le-muted"> · observed{data.observed_grade ? ` (grade ${data.observed_grade})` : ''}</span>
                  ) : null}
                </li>
              ))}
            </ol>
          </section>

          <section>
            <h2 style={{ fontSize: '1rem' }}>Score components</h2>
            <table className="le-table" style={{ fontSize: '0.85rem' }}>
              <tbody>
                {Object.entries(data.components ?? {}).map(([key, value]) => (
                  <tr key={key}>
                    <td>{COMPONENT_LABEL[key] ?? key}</td>
                    <td style={{ textAlign: 'right' }}>{Math.round((value ?? 0) * 100)}%</td>
                    <td className="le-muted" style={{ textAlign: 'right' }}>weight {data.weights?.[key] ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section>
            <h2 style={{ fontSize: '1rem' }}>Gate signals</h2>
            <ul style={{ listStyle: 'none', padding: 0, fontSize: '0.85rem' }}>
              {Object.entries(data.signals ?? {}).map(([key, value]) => (
                <li key={key}>
                  {value ? '✓' : '✗'} {SIGNAL_LABEL[key] ?? key}
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h2 style={{ fontSize: '1rem' }}>Gap checklist — cheapest next promotion first</h2>
            {data.recommendations?.length ? (
              <ol style={{ fontSize: '0.88rem', paddingLeft: '1.2rem' }}>
                {data.recommendations.map((r) => (
                  <li key={r} style={{ marginBottom: '0.35rem' }}>{r}</li>
                ))}
              </ol>
            ) : (
              <p className="le-muted" style={{ fontSize: '0.85rem' }}>No open recommendations.</p>
            )}
          </section>

          <section>
            <h2 style={{ fontSize: '1rem' }}>Run evidence</h2>
            <p className="le-muted" style={{ fontSize: '0.85rem' }}>
              {data.run_evidence?.green_runs ?? 0} green run(s)
              {data.run_evidence?.levels && Object.keys(data.run_evidence.levels).length > 0
                ? ` — ${Object.entries(data.run_evidence.levels)
                    .map(([lv, n]) => `${lv}: ${n}`)
                    .join(', ')}`
                : ''}
              {typeof data.run_evidence?.escalation_rate === 'number'
                ? ` · escalation rate ${Math.round(data.run_evidence.escalation_rate * 100)}%`
                : ''}
            </p>
          </section>
        </div>
      ) : null}
    </>
  )
}
