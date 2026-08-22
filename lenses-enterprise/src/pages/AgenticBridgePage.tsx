import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGetJson } from '../api/http'
import { PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import { StatePanelAssistShortcuts } from '../components/page/StatePanelAssistShortcuts'
import { assistShortcutsForContext, resolveUxFailure, type UxResolvedFailure } from '../lib/uxPageState'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { KNOWLEDGE_PUBLISH_COPILOT, METHODOLOGY_UX_AGENTIC, ROUTE_SUBTITLE, STUDIO_VOCAB } from '../nav/studioVisibleCopy'
import { AgenticStartHere } from '../components/agentic/AgenticStartHere'
import { readFeatureDisabled } from '../lib/apiInternalFields'

type DriftPayload = {
  ok?: boolean
  aligned?: boolean
  active_versona_families?: string[]
  active_disciplines?: string[]
  missing_expected_rules?: { discipline?: string; expected_file?: string }[]
  orphaned_or_unmatched_rules?: { basename?: string; reason?: string }[]
  cursor_rule_count?: number
}

export function AgenticBridgePage() {
  useLensesCopilotPage({ route: 'knowledge', defaultQuery: KNOWLEDGE_PUBLISH_COPILOT.agenticBridge })
  const [versonas, setVersonas] = useState<Record<string, unknown> | null>(null)
  const [recipes, setRecipes] = useState<Record<string, unknown> | null>(null)
  const [tasklets, setTasklets] = useState<Record<string, unknown> | null>(null)
  const [drift, setDrift] = useState<DriftPayload | null>(null)
  const [runs, setRuns] = useState<Record<string, unknown> | null>(null)
  const [approvals, setApprovals] = useState<Record<string, unknown> | null>(null)
  const [policies, setPolicies] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [featureErr, setFeatureErr] = useState<string | null>(null)
  const [fetchFailure, setFetchFailure] = useState<UxResolvedFailure | null>(null)

  useEffect(() => {
    const opt = { headers: { Accept: 'application/json' } }
    void (async () => {
      await Promise.resolve()
      setLoading(true)
      setFeatureErr(null)
      setFetchFailure(null)
      try {
        const [v, r, t, d, rn, ap, po] = await Promise.all([
          apiGetJson<Record<string, unknown>>('/api/agents/versonas', opt),
          apiGetJson<Record<string, unknown>>('/api/agents/recipes', opt),
          apiGetJson<Record<string, unknown>>('/api/agents/tasklets', opt),
          apiGetJson<DriftPayload>('/api/agents/drift', opt),
          apiGetJson<Record<string, unknown>>('/api/agents/runs', opt),
          apiGetJson<Record<string, unknown>>('/api/agents/approvals', opt),
          apiGetJson<Record<string, unknown>>('/api/agents/policies', opt),
        ])
        if (readFeatureDisabled(v as Record<string, unknown>)) {
          setFeatureErr('Agent automation views are turned off for this workspace (or the orchestration graph is disabled).')
          return
        }
        setVersonas(v)
        setRecipes(r)
        setTasklets(t)
        setDrift(d)
        setRuns(rn)
        setApprovals(ap)
        setPolicies(po)
      } catch (e: unknown) {
        setFetchFailure(resolveUxFailure(e))
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const regTasklets = (tasklets?.registry_tasklets as { id?: string; display_name?: string }[]) || []
  const regRecipes = (recipes?.registry_recipes as { id?: string; display_name?: string }[]) || []
  const runRows = (runs?.runs as { id?: string; display_name?: string; payload?: { status?: string } }[]) || []
  const pend = (approvals?.approval_requests as { id?: string; display_name?: string }[]) || []
  const blocked = Boolean(featureErr || fetchFailure)
  const nFam = (versonas?.graph_families as unknown[] | undefined)?.length ?? 0
  const nProf = (versonas?.graph_profiles as unknown[] | undefined)?.length ?? 0
  const driftRows =
    (drift?.missing_expected_rules?.length ?? 0) + (drift?.orphaned_or_unmatched_rules?.length ?? 0)
  const polN = ((policies?.registry_policies as unknown[]) ?? []).length
  const hasLists =
    nFam + nProf + regRecipes.length + regTasklets.length + runRows.length + pend.length + driftRows + polN > 0

  return (
    <>
      <PageHeader
        title={STUDIO_VOCAB.agenticBridge}
        purpose={METHODOLOGY_UX_AGENTIC.bridgePurpose}
        subtitle={ROUTE_SUBTITLE.agenticBridge}
        statusChips={[{ label: 'Read-only catalog', tone: 'muted' }]}
        secondaryMenuItems={[
          { key: 'decisions', label: 'Decision registry', to: '/knowledge/methodology/decisions' },
          { key: 'plan', label: 'Plan summary', to: '/plan' },
        ]}
      />
      <p className="forge-support">{METHODOLOGY_UX_AGENTIC.lead}</p>

      <AgenticStartHere />

      <TechnicalDetails summary="Technical — agent registry HTTP endpoints">
        <p className="forge-support" style={{ margin: 0 }}>
          Read-only discovery uses <code className="le-mono">GET /api/agents/versonas</code>,{' '}
          <code className="le-mono">/api/agents/recipes</code>, <code className="le-mono">/api/agents/tasklets</code>,{' '}
          <code className="le-mono">/api/agents/drift</code>, <code className="le-mono">/api/agents/runs</code>,{' '}
          <code className="le-mono">/api/agents/approvals</code>, <code className="le-mono">/api/agents/policies</code>. No
          autonomous writes; approval-gated modes require explicit human confirmation in the API.
        </p>
      </TechnicalDetails>

      <section className="le-card" style={{ marginTop: '0.75rem', padding: '0.65rem 0.85rem' }} aria-label="Recommended workflow">
        <h2 style={{ fontSize: '0.95rem', margin: '0 0 0.35rem' }}>Recommended workflow</h2>
        <p className="forge-support" style={{ margin: 0 }}>
          On <Link to="/plan?tab=story">Plan → Story</Link>, scope a work item, then use read-only recipes from the catalog
          below. Write or packaging paths stay approval-gated.
        </p>
        <StatePanelAssistShortcuts actions={assistShortcutsForContext({ context: 'Agentic bridge' })} />
      </section>

      {loading ? (
        <StatePanel variant="loading" title="Loading agent registry" description="Fetching Versonas, recipes, drift, runs, and approvals." />
      ) : null}

      {!loading && featureErr ? (
        <StatePanel
          variant="not_configured"
          title="Agent bridge is not available here"
          description={featureErr}
          assistShortcuts={{ context: 'Agentic bridge' }}
          aiRecovery={{
            prompt:
              'Agentic bridge in Lenses is disabled. What enables it (orchestration graph, feature flags) and what is the safest way to turn it on?',
            label: 'Ask Chat about enabling the bridge',
          }}
          telemetryTag="agentic_bridge_feature_off"
        />
      ) : null}

      {!loading && fetchFailure ? (
        <StatePanel
          variant="unavailable"
          title={fetchFailure.title}
          description={fetchFailure.description}
          technicalDetail={fetchFailure.technical}
          assistShortcuts={{ context: 'Agentic bridge' }}
          aiRecovery={{
            prompt:
              'Agentic bridge in Forge Lenses failed to load. What should I verify (server, workspace scan, graph) and what is the next step?',
            label: 'Ask Chat how to recover',
          }}
          actions={
            <button type="button" className="le-btn le-btn--primary" onClick={() => window.location.reload()}>
              Reload page
            </button>
          }
          telemetryTag="agentic_bridge_fetch_failed"
        />
      ) : null}

      {!loading && !blocked && !hasLists ? (
        <StatePanel
          variant="empty"
          title="No agent registry data yet"
          description={METHODOLOGY_UX_AGENTIC.empty}
          assistShortcuts={{ context: 'Agentic bridge' }}
          actions={
            <Link className="le-btn le-btn--primary" to="/plan?tab=story">
              Open Plan → Story
            </Link>
          }
          telemetryTag="agentic_bridge_empty"
        />
      ) : null}

      {!loading && !blocked && versonas ? (
        <>
          <h2 style={{ fontSize: '1.1rem', marginTop: '1.25rem' }}>Active Versonas (configuration summary)</h2>
          <p className="forge-support">
            Graph rows: {(versonas?.graph_families as unknown[] | undefined)?.length ?? 0} families,{' '}
            {(versonas?.graph_profiles as unknown[] | undefined)?.length ?? 0} profiles when demo seed is loaded.
          </p>
          <TechnicalDetails summary="Technical — forge.config excerpt">
            <pre className="le-mono le-card" style={{ overflow: 'auto', fontSize: '0.82rem' }}>
              {JSON.stringify(versonas?.forge_config ?? {}, null, 2)}
            </pre>
          </TechnicalDetails>
        </>
      ) : null}

      {!loading && !blocked && drift ? (
        <>
          <h2 style={{ fontSize: '1.1rem', marginTop: '1.25rem' }}>Rules drift</h2>
          <ul className="le-list forge-support">
            <li>
              Aligned: <strong>{String(drift.aligned)}</strong> — Cursor rules counted:{' '}
              {String(drift.cursor_rule_count ?? '—')}
            </li>
            {(drift.missing_expected_rules || []).map((m, i) => (
              <li key={i} style={{ color: 'var(--le-warning-fg, #b45309)' }}>
                Missing: {m.expected_file} (discipline {m.discipline})
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {!loading && !blocked && regRecipes.length > 0 ? (
        <>
          <h2 style={{ fontSize: '1.1rem', marginTop: '1.25rem' }}>Recipe catalog</h2>
          <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
            {regRecipes.map((x) => (
              <li key={x.id} className="le-card" style={{ marginBottom: '0.35rem' }}>
                <strong>{x.display_name}</strong>
                <details className="forge-support" style={{ marginTop: '0.35rem', fontSize: '0.78rem' }}>
                  <summary style={{ cursor: 'pointer' }}>Recipe id</summary>
                  <code className="le-mono">{x.id}</code>
                </details>
              </li>
            ))}
          </ul>
          <p className="forge-support">
            Discovered files: {(recipes?.discovered_files as unknown[] | undefined)?.length ?? 0}
          </p>
        </>
      ) : null}

      {!loading && !blocked && regTasklets.length > 0 ? (
        <>
          <h2 style={{ fontSize: '1.1rem', marginTop: '1.25rem' }}>Tasklets (registry)</h2>
          <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
            {regTasklets.map((x) => (
              <li key={x.id} className="le-card" style={{ marginBottom: '0.35rem' }}>
                <strong>{x.display_name}</strong>
                <details className="forge-support" style={{ marginTop: '0.35rem', fontSize: '0.78rem' }}>
                  <summary style={{ cursor: 'pointer' }}>Tasklet id</summary>
                  <code className="le-mono">{x.id}</code>
                </details>
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {!loading && !blocked && runRows.length > 0 ? (
        <>
          <h2 style={{ fontSize: '1.1rem', marginTop: '1.25rem' }}>Recent runs</h2>
          <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
            {runRows.map((x) => (
              <li key={x.id} className="le-card" style={{ marginBottom: '0.35rem' }}>
                <Link to={`/knowledge/methodology/record/${encodeURIComponent(x.id || '')}`}>{x.display_name}</Link>
                <span className="le-muted"> — {x.payload?.status ?? 'status unknown'}</span>
                <details className="forge-support" style={{ marginTop: '0.35rem', fontSize: '0.78rem' }}>
                  <summary style={{ cursor: 'pointer' }}>Run id</summary>
                  <code className="le-mono">{x.id}</code>
                </details>
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {!loading && !blocked ? (
        <>
          <h2 style={{ fontSize: '1.1rem', marginTop: '1.25rem' }}>Pending approvals</h2>
          {pend.length === 0 ? (
            <p className="forge-support">None pending.</p>
          ) : (
            <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
              {pend.map((x) => (
                <li key={x.id} className="le-card" style={{ marginBottom: '0.35rem' }}>
                  <Link to={`/knowledge/methodology/record/${encodeURIComponent(x.id || '')}`}>{x.display_name}</Link>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : null}

      {!loading && !blocked && policies ? (
        <>
          <h2 style={{ fontSize: '1.1rem', marginTop: '1.25rem' }}>Policies</h2>
          <TechnicalDetails summary="Technical — policy registry JSON">
            <pre className="le-mono le-card" style={{ overflow: 'auto', fontSize: '0.82rem' }}>
              {JSON.stringify(policies?.registry_policies ?? [], null, 2)}
            </pre>
          </TechnicalDetails>
        </>
      ) : null}

      {!loading && !blocked ? (
        <TechnicalDetails summary="Technical — linking agent outputs">
          <p className="forge-support" style={{ margin: 0 }}>
            Outputs can be linked into the methodology graph with{' '}
            <code className="le-mono">POST /api/agents/outputs/&lt;id&gt;/link</code> and an{' '}
            <code className="le-mono">artifact_id</code> (loopback / allow-actions only).
          </p>
        </TechnicalDetails>
      ) : null}

    </>
  )
}
