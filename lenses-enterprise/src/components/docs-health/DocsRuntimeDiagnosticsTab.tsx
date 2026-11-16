import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { DocsHealthSessionEvent, DocsHealthSessionPayload } from '../../api/docsHealth'
import { formatSessionInstant } from '../../lib/docsHealthSessionFormat'
import {
  getAgentRuntimeOverview,
  getAgentRuntimeSession,
  getAgentRuntimeTokenUsage,
  type AgentRuntimeOverview,
} from '../../api/agentRuntime'
import { ForgeDiagnosticPanel, ForgeKeyValueGrid, type ForgeKeyValueItem } from '../../forgesdlc-kitchensink'
import { TechnicalDetails } from '../page'
import { DocsHealthPlannedModelsTable } from './DocsHealthPlannedModelsTable'

export type DocsRuntimeDiagnosticsTabProps = {
  session: DocsHealthSessionPayload | null
  /** Live feed mode for this session page (informational). */
  streamMode?: 'sse' | 'poll' | 'idle'
}

function tokenStatsRows(events: DocsHealthSessionEvent[] | undefined): DocsHealthSessionEvent[] {
  return (events || []).filter((e) => String(e.type || '') === 'token_stats')
}

/**
 * Diagnostics: models, tokens, routing, policy, and raw ledgers (summary first, detail on demand).
 */
export function DocsRuntimeDiagnosticsTab({ session, streamMode = 'idle' }: DocsRuntimeDiagnosticsTabProps) {
  const hs = session?.header_stats
  const tr = session?.tasklet_run
  const arId = session?.agent_runtime_session_id?.trim()

  const [overview, setOverview] = useState<AgentRuntimeOverview | null>(null)
  const [arSession, setArSession] = useState<Record<string, unknown> | null>(null)
  const [arTokenUsage, setArTokenUsage] = useState<Record<string, unknown> | null>(null)
  const [arErr, setArErr] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void getAgentRuntimeOverview()
      .then((r) => {
        if (!cancelled) setOverview(r.ok ? r : null)
      })
      .catch(() => {
        if (!cancelled) setOverview(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!arId) {
      setArSession(null)
      setArTokenUsage(null)
      setArErr(null)
      return
    }
    let cancelled = false
    setArErr(null)
    void Promise.all([getAgentRuntimeSession(arId), getAgentRuntimeTokenUsage({ session_id: arId })])
      .then(([s, t]) => {
        if (cancelled) return
        const sess =
          s && typeof s === 'object' && 'session' in s
            ? (s as { session?: Record<string, unknown> }).session
            : undefined
        setArSession(sess ?? null)
        setArTokenUsage(t && typeof t === 'object' ? (t as Record<string, unknown>) : null)
      })
      .catch((e) => {
        if (!cancelled) {
          setArSession(null)
          setArTokenUsage(null)
          setArErr(e instanceof Error ? e.message : 'Could not load agent runtime session')
        }
      })
    return () => {
      cancelled = true
    }
  }, [arId])

  const tokenEvents = useMemo(() => tokenStatsRows(session?.events), [session?.events])

  const summaryItems: ForgeKeyValueItem[] = useMemo(() => {
    const feed =
      streamMode === 'sse' ? 'Streaming' : streamMode === 'poll' ? 'Polling' : 'Not connected'
    return [
      {
        label: 'Last model',
        value: hs?.last_model_id || hs?.active_model || 'Not recorded',
        title: 'Latest model identifier recorded for this run',
      },
      {
        label: 'Last provider',
        value: hs?.last_provider || 'Not recorded',
      },
      {
        label: 'Active slot',
        value: hs?.active_slot || 'Not recorded',
      },
      {
        label: 'Tokens in / out',
        value: `${(hs?.prompt_tokens ?? 0).toLocaleString()} / ${(hs?.completion_tokens ?? 0).toLocaleString()}`,
      },
      {
        label: 'Total tokens',
        value: (hs?.total_tokens ?? 0).toLocaleString(),
      },
      {
        label: 'Commands run',
        value: String(hs?.commands_run ?? 0),
      },
      {
        label: 'Files changed',
        value: String(hs?.files_changed ?? 0),
      },
      {
        label: 'Run orchestration',
        value: tr?.state || session?.run_state || 'Not recorded',
        title: tr?.stop_reason || undefined,
      },
      {
        label: 'Live updates',
        value: feed,
      },
      {
        label: 'Linked automation session',
        value: arId ? (
          <code className="le-dh-run-id" title={arId}>
            {arId.length > 28 ? `${arId.slice(0, 14)}…${arId.slice(-8)}` : arId}
          </code>
        ) : (
          'Not linked'
        ),
      },
    ]
  }, [arId, hs, session?.run_state, streamMode, tr?.state, tr?.stop_reason])

  const policySummary =
    overview?.policy && typeof overview.policy === 'object'
      ? String((overview.policy as { summary?: string }).summary ?? '').trim()
      : ''

  const primaryRaw = useMemo(
    () => ({
      usage_session: session?.usage_session,
      step_metrics: session?.step_metrics,
      tasklet_run: session?.tasklet_run,
      execution: session?.execution,
      efficiency_metrics: session?.efficiency_metrics,
      scratch_workspace: session?.scratch_workspace,
      scratch_worktree: session?.scratch_worktree,
      model_routing_preview: session?.model_routing_preview ?? session?.header_stats?.model_routing_preview,
    }),
    [session],
  )

  const dispatchRaw = useMemo(
    () => ({
      header_stats_model_preview: session?.header_stats?.model_routing_preview,
      session_model_routing_preview: session?.model_routing_preview,
    }),
    [session],
  )

  return (
    <div className="le-dh-diag-tab">
      <section className="le-dh-diag-tab__summary" aria-labelledby="le-dh-diag-summary-h">
        <h3 id="le-dh-diag-summary-h" className="le-dh-wf-panel__h4">
          Runtime diagnostics
        </h3>
        <ForgeKeyValueGrid items={summaryItems} aria-label="Runtime diagnostics summary" />
      </section>

      {session?.execution?.step_backend ? (
        <p className="forge-support le-dh-diag-tab__backend">
          <strong>Execution mode:</strong> {session.execution.step_backend}
          {session.execution.resumable === false ? ' · not resumable' : null}
        </p>
      ) : null}

      <section aria-labelledby="le-dh-diag-route-h">
        <h3 id="le-dh-diag-route-h" className="le-dh-wf-panel__h4">
          Provider route and fallback chain
        </h3>
        <p className="forge-support le-dh-diag-tab__micro">
          Provider order follows your AI Setup model map per role. Fallbacks run left to right in each row.
        </p>
        <DocsHealthPlannedModelsTable header={session?.header_stats} />
        {!session?.header_stats?.model_routing_preview?.slots ? (
          <p className="le-dh-diag-tab__empty forge-support">No routing preview is available for this run.</p>
        ) : null}
      </section>

      <section aria-labelledby="le-dh-diag-policy-h">
        <h3 id="le-dh-diag-policy-h" className="le-dh-wf-panel__h4">
          Policy and limits
        </h3>
        {policySummary ? <p className="forge-support">{policySummary}</p> : null}
        {overview?.policy && typeof overview.policy === 'object' ? (
          <dl className="le-dh-diag-tab__policy-dl forge-support">
            <dt>Routing mode</dt>
            <dd>{String((overview.policy as { llm_routing_mode?: string }).llm_routing_mode ?? 'Not recorded')}</dd>
            <dt>Active slots</dt>
            <dd>{((overview.policy as { slots?: string[] }).slots ?? []).join(', ') || 'Not recorded'}</dd>
          </dl>
        ) : (
          <p className="forge-support le-dh-diag-tab__empty">
            Workspace routing policy was not loaded. Open Agent runtime inspect when you need the full policy.
          </p>
        )}
        <ul className="forge-support le-dh-diag-tab__bullets">
          <li>Only markdown paths are accepted for apply.</li>
          <li>Writes require project write access from the server policy.</li>
          <li>Command output is redacted server-side before display.</li>
          <li>Verification runs the same deterministic scanners and updates the score.</li>
        </ul>
        <p className="forge-support" style={{ fontSize: '0.88rem' }}>
          <Link to="/settings/agent-runtime">Open Agent runtime</Link> for endpoints, ledger history, and capabilities.
        </p>
      </section>

      <section aria-labelledby="le-dh-diag-ledger-h">
        <h3 id="le-dh-diag-ledger-h" className="le-dh-wf-panel__h4">
          Per-step token ledger
        </h3>
        <p className="forge-support le-dh-diag-tab__micro">
          Token rows recorded for this run (hidden from Execution to keep the narrative readable).
        </p>
        {tokenEvents.length === 0 ? (
          <p className="le-dh-diag-tab__empty forge-support">No per-step token rows recorded for this run.</p>
        ) : (
          <ul className="le-dh-diag-tab__ledger">
            {tokenEvents.map((ev, i) => {
              const snap = ev.snapshot as Record<string, unknown> | undefined
              const pt = Number(snap?.prompt_tokens) || 0
              const ct = Number(snap?.completion_tokens) || 0
              const tt = Number(snap?.total_tokens) || (pt || ct ? pt + ct : 0)
              const when = formatSessionInstant(ev.ts)
              return (
                <li key={`${ev.ts || i}-tok`} className="le-dh-diag-tab__ledger-item">
                  <div className="le-dh-diag-tab__ledger-line">
                    <span className="le-dh-diag-tab__ledger-ts">
                      {ev.ts ? (
                        <time dateTime={when.dateTime} title={when.utcTitle}>
                          {when.text}
                        </time>
                      ) : (
                        'Not recorded'
                      )}
                    </span>
                    {ev.last_model ? (
                      <code className="le-dh-diag-tab__ledger-model" title={ev.last_model}>
                        {ev.last_model}
                      </code>
                    ) : null}
                    <span className="le-dh-diag-tab__ledger-nums">
                      in {pt.toLocaleString()} · out {ct.toLocaleString()}
                      {tt ? <> · Σ {tt.toLocaleString()}</> : null}
                    </span>
                  </div>
                  {snap && Object.keys(snap).length > 0 ? (
                    <TechnicalDetails summary="Usage detail (JSON)" defaultOpen={false}>
                      <pre className="le-preview le-json" style={{ fontSize: '0.8rem' }}>
                        {JSON.stringify(snap, null, 2)}
                      </pre>
                    </TechnicalDetails>
                  ) : null}
                </li>
              )
            })}
          </ul>
        )}
      </section>

      {arId ? (
        <section aria-labelledby="le-dh-diag-ar-h">
          <h3 id="le-dh-diag-ar-h" className="le-dh-wf-panel__h4">
            Automation session (linked)
          </h3>
          {arErr ? (
            <p className="forge-support" role="status">
              {arErr}
            </p>
          ) : null}
          {!arErr && !arSession && !arTokenUsage ? (
            <p className="forge-support le-dh-diag-tab__empty">Loading linked automation session…</p>
          ) : null}
          {arSession ? (
            <p className="forge-support">
              Linked session <code className="le-dh-run-id">{arId}</code> loaded for diagnostics.
            </p>
          ) : null}
          {arTokenUsage ? (
            <ForgeDiagnosticPanel
              title="Token usage (detail)"
              summary={<p className="forge-support">Server token usage for the linked automation session.</p>}
              raw={arTokenUsage}
              defaultRawOpen={false}
            />
          ) : null}
          {arSession ? (
            <ForgeDiagnosticPanel
              title="Automation session (detail)"
              summary={<p className="forge-support">Full session record from the automation service.</p>}
              raw={arSession}
              defaultRawOpen={false}
            />
          ) : null}
        </section>
      ) : (
        <p className="forge-support le-dh-diag-tab__micro">
          This run is not linked to an automation session. Linked sessions appear when the workspace binds one.
        </p>
      )}

      <ForgeDiagnosticPanel
        title="Raw runtime ledger"
        summary={
          <p className="forge-support" style={{ margin: 0 }}>
            Usage merge, step metrics, sandbox metadata, and routing previews. For troubleshooting only.
          </p>
        }
        raw={primaryRaw}
        defaultRawOpen={false}
      />

      <TechnicalDetails summary="Dispatch routing (detail)" defaultOpen={false}>
        <pre className="le-preview le-json" style={{ fontSize: '0.82rem' }}>
          {JSON.stringify(dispatchRaw, null, 2)}
        </pre>
      </TechnicalDetails>
    </div>
  )
}
