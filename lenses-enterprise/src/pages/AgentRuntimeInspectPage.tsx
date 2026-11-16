import { useEffect, useId, useState } from 'react'
import { getAgentRuntimeOverview, getAgentRuntimeTokenUsage, type AgentRuntimeOverview } from '../api/agentRuntime'
import { PageHeader, StatePanel } from '../components/page'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import {
  ADMIN_INSPECT_COPY,
  ROUTE_SUBTITLE as SUB,
  STUDIO_VOCAB,
} from '../nav/studioVisibleCopy'

export function AgentRuntimeInspectPage() {
  const hProviders = useId()
  const hSlots = useId()
  const hPolicy = useId()
  const hCaps = useId()
  const hLedger = useId()
  const [data, setData] = useState<AgentRuntimeOverview | null>(null)
  const [usage, setUsage] = useState<Record<string, unknown> | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useLensesCopilotPage({
    route: 'agent-runtime-inspect',
    scopeSite: undefined,
  })

  useEffect(() => {
    let cancelled = false
    void Promise.all([getAgentRuntimeOverview(), getAgentRuntimeTokenUsage()])
      .then(([ov, tu]) => {
        if (cancelled) return
        setData(ov)
        setUsage(tu)
        setErr(null)
      })
      .catch((e) => {
        if (!cancelled) {
          setData(null)
          setUsage(null)
          setErr(e instanceof Error ? e.message : 'load failed')
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <>
      <PageHeader
        title={STUDIO_VOCAB.agentRuntimeInspect}
        purpose="Provider adapters, local-first dispatch, token ledger, and agent sessions for docs remediation and future agents."
        secondaryMenuItems={[
          { key: 'llm', to: '/settings/llm', label: STUDIO_VOCAB.llmPreferences },
          { key: 'fleet', to: '/settings/fleet', label: STUDIO_VOCAB.fleetPreferences },
          { key: 'home', to: '/', label: STUDIO_VOCAB.overview },
        ]}
      />
      <p className="forge-support">{ADMIN_INSPECT_COPY.settingsSectionInspect}</p>
      <p className="le-muted">{SUB.agentRuntimeInspect}</p>

      {err ? <StatePanel variant="error" title="Could not load agent runtime" description={err} /> : null}

      {!data?.ok && !err ? (
        <StatePanel variant="loading" title="Loading" description="Reading agent runtime overview from the workspace server." />
      ) : data?.ok ? (
        <>
          <section className="le-panel le-agent-runtime-approval-summary" aria-label="approvalSummary">
            <h2 className="le-panel__title">Automatic vs Needs approval</h2>
            <p className="forge-support">
              Read-only discovery and chat stay automatic. Packaging, exports, and Fleet argv jobs surface as{' '}
              <strong>Needs approval</strong> until you confirm — review the dispatch policy below before delegating
              write paths.
            </p>
          </section>
          <section className="le-panel" aria-labelledby={hPolicy}>
            <h2 id={hPolicy} className="le-panel__title">
              Dispatch policy
            </h2>
            <p className="forge-support" style={{ whiteSpace: 'pre-wrap' }}>
              {String((data.policy as { summary?: string } | undefined)?.summary ?? '—')}
            </p>
            <dl className="le-muted" style={{ display: 'grid', gridTemplateColumns: '12rem 1fr', gap: '0.35rem 1rem' }}>
              <dt>LLM routing mode</dt>
              <dd>{String((data.policy as { llm_routing_mode?: string } | undefined)?.llm_routing_mode ?? '—')}</dd>
              <dt>Active slots</dt>
              <dd>{((data.policy as { slots?: string[] } | undefined)?.slots ?? []).join(', ') || '—'}</dd>
              <dt>Capability ids</dt>
              <dd>{((data.policy as { capability_ids?: string[] } | undefined)?.capability_ids ?? []).join(', ') || '—'}</dd>
            </dl>
          </section>

          {data.capabilities?.length ? (
            <section className="le-panel" aria-labelledby={hCaps}>
              <h2 id={hCaps} className="le-panel__title">
                Semantic capabilities
              </h2>
              <p className="forge-support">
                Tasklets request these ids (not raw model names). Slots map to a capability plus routing profile.
              </p>
              <ul style={{ paddingLeft: '1.2rem' }}>
                {data.capabilities.map((c) => (
                  <li key={String(c.id)} style={{ marginBottom: '0.5rem' }}>
                    <strong>{String(c.id)}</strong>
                    {c.label ? <span className="le-muted"> — {String(c.label)}</span> : null}
                    {c.description ? (
                      <div className="le-muted" style={{ fontSize: '0.9rem' }}>
                        {String(c.description)}
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
              {data.legacy_slot_aliases && Object.keys(data.legacy_slot_aliases).length > 0 ? (
                <p className="le-muted" style={{ fontSize: '0.9rem', marginTop: '0.75rem' }}>
                  Legacy slot names in settings still work:{' '}
                  {Object.entries(data.legacy_slot_aliases)
                    .map(([a, b]) => `${a} → ${b}`)
                    .join('; ')}
                  .
                </p>
              ) : null}
            </section>
          ) : null}

          <section className="le-panel" aria-labelledby={hProviders}>
            <h2 id={hProviders} className="le-panel__title">
              Provider endpoints
            </h2>
            <div className="le-table-wrap" style={{ overflowX: 'auto' }}>
              <table className="le-table" aria-label="Provider capabilities">
                <thead>
                  <tr>
                    <th scope="col">Provider</th>
                    <th scope="col">Adapter</th>
                    <th scope="col">Health</th>
                    <th scope="col">Tokens</th>
                    <th scope="col">Privacy</th>
                    <th scope="col">Streaming</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.providers ?? []).map((p) => (
                    <tr key={String(p.id ?? p.adapter)}>
                      <td>{String(p.display_name ?? p.id ?? '')}</td>
                      <td>{String(p.adapter ?? '')}</td>
                      <td>{String(p.health ?? '')}</td>
                      <td>{String(p.token_counting ?? '')}</td>
                      <td>{String(p.privacy ?? '')}</td>
                      <td>{p.supports_streaming ? 'yes' : 'no'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="le-panel" aria-labelledby={hSlots}>
            <h2 id={hSlots} className="le-panel__title">
              Model slots
            </h2>
            <ul style={{ paddingLeft: '1.2rem' }}>
              {(data.slots ?? []).map((s) => (
                <li key={String(s.id)} style={{ marginBottom: '0.5rem' }}>
                  <strong>{String(s.label ?? s.id)}</strong>
                  {s.capability_id ? (
                    <span className="le-muted"> — capability {String(s.capability_id)}</span>
                  ) : null}
                  <span className="le-muted"> — task {String(s.studio_task_id ?? '')}</span>
                  <div className="le-muted" style={{ fontSize: '0.9rem' }}>
                    Fallback: {(s.fallback_order as string[] | undefined)?.join(' → ') ?? '—'}
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="le-panel" aria-labelledby={hLedger}>
            <h2 id={hLedger} className="le-panel__title">
              Token ledger (recent)
            </h2>
            {usage?.ok ? (
              <p className="forge-support">
                Filtered totals — calls: <strong>{String((usage.totals as { calls?: number })?.calls ?? 0)}</strong>,
                tokens:{' '}
                <strong>{String((usage.totals as { total_tokens?: number })?.total_tokens ?? 0)}</strong>
                {Number((usage.totals as { estimated_rows?: number })?.estimated_rows) > 0
                  ? ' (includes estimated rows)'
                  : null}
              </p>
            ) : (
              <p className="le-muted">No summary yet.</p>
            )}
            {!data.last_ledger_records?.length ? (
              <p className="le-muted">No recent ledger lines on this workspace (run a docs remediation step to populate).</p>
            ) : (
              <ul style={{ paddingLeft: '1.1rem', fontSize: '0.9rem' }}>
                {data.last_ledger_records.map((r, i) => (
                  <li key={String(r.id ?? i)}>
                    {String(r.model_slot ?? '')} · {String(r.provider ?? '')} · in {String(r.input_tokens ?? 0)} / out{' '}
                    {String(r.output_tokens ?? 0)} · {String(r.token_counting_mode ?? '')}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}
    </>
  )
}
