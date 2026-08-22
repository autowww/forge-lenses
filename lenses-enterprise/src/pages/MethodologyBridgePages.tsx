import { useEffect, useState } from 'react'
import { Link, useLocation, useParams, useSearchParams } from 'react-router-dom'
import { apiGetJson } from '../api/http'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import { StatePanelAssistShortcuts } from '../components/page/StatePanelAssistShortcuts'
import { mergePlanningScopeIntoTo } from '../lib/planningClusterScope'
import { assistShortcutsForContext, resolveUxFailure, type UxResolvedFailure } from '../lib/uxPageState'
import { fetchDiscoveredReleases, type DiscoveredRelease } from '../lib/discoveredReleases'
import { KNOWLEDGE_PUBLISH_COPILOT, METHODOLOGY_UX, METHODOLOGY_UX_RECORD } from '../nav/studioVisibleCopy'
import { KnowledgeEmptyGuidance } from '../components/knowledge/KnowledgeEmptyGuidance'
import { KnowledgeSectionChrome } from '../components/knowledge/KnowledgeSectionChrome'
import { readFeatureDisabled } from '../lib/apiInternalFields'

function OutcomeLearningHint() {
  const [on, setOn] = useState<boolean | null>(null)
  useEffect(() => {
    apiGetJson<{ enabled?: boolean }>('/api/outcomes/enabled')
      .then((r) => setOn(r.enabled !== false))
      .catch(() => setOn(false))
  }, [])
  if (on !== true) return null
  return (
    <section className="le-card" style={{ marginTop: '0.75rem', padding: '0.65rem 0.75rem' }} aria-label="PDLC outcomes">
      <h2 style={{ fontSize: '1rem', margin: 0 }}>PDLC outcomes</h2>
      <p className="forge-support" style={{ marginTop: '0.35rem' }}>
        Post-launch signals connect learning summaries to releases so you can see what shipped and what to learn next.
        When the orchestration graph is on, open{' '}
        <Link to="/orchestration/trace?root=ogs:demo:b6:launch:auth-train&direction=both&max_depth=10&max_nodes=500">
          Orchestration trace
        </Link>{' '}
        to explore links from a demo launch.
      </p>
      <TechnicalDetails summary="Technical — field names and HTTP endpoints">
        <p className="forge-support" style={{ margin: 0 }}>
          Graph fields include <strong>learning_summary</strong> and <code>launch_record</code>. Read-only endpoints:{' '}
          <code className="le-mono">GET /api/outcomes</code>, <code className="le-mono">GET /api/launches/&lt;id&gt;</code>.
        </p>
      </TechnicalDetails>
    </section>
  )
}

type IdRow = { id: string; display_name: string; summary?: string; updated_at?: string }

function RecordListRow({ href, title, summary, id }: { href: string; title: string; summary?: string; id: string }) {
  return (
    <li className="le-card" style={{ marginBottom: '0.35rem' }}>
      <Link to={href}>
        <strong>{title}</strong>
      </Link>
      {summary ? <div className="le-muted">{summary}</div> : null}
      <details className="forge-support" style={{ marginTop: '0.35rem', fontSize: '0.78rem' }}>
        <summary style={{ cursor: 'pointer' }}>Record id</summary>
        <code className="le-mono" style={{ fontSize: '0.72rem', wordBreak: 'break-word' }}>
          {id}
        </code>
      </details>
    </li>
  )
}

export function MethodologyEvidenceRegistryPage() {
  useLensesCopilotPage({ route: 'knowledge', defaultQuery: KNOWLEDGE_PUBLISH_COPILOT.methodologyEvidence })
  const [hits, setHits] = useState<IdRow[]>([])
  const [artifacts, setArtifacts] = useState<IdRow[]>([])
  const [packs, setPacks] = useState<IdRow[]>([])
  const [packets, setPackets] = useState<IdRow[]>([])
  const [loading, setLoading] = useState(true)
  const [featureErr, setFeatureErr] = useState<string | null>(null)
  const [fetchFailure, setFetchFailure] = useState<UxResolvedFailure | null>(null)

  useEffect(() => {
    void (async () => {
      await Promise.resolve()
      setLoading(true)
      setFeatureErr(null)
      setFetchFailure(null)
      try {
        const [ev, art, rp, ap] = await Promise.all([
          apiGetJson<Record<string, unknown>>('/api/evidence/search?q=&limit=80'),
          apiGetJson<Record<string, unknown>>('/api/artifacts?limit=100'),
          apiGetJson<Record<string, unknown>>('/api/review-packs'),
          apiGetJson<Record<string, unknown>>('/api/assay-packets'),
        ])
        if (readFeatureDisabled(ev) || readFeatureDisabled(art)) {
          setFeatureErr('Methodology and evidence views are turned off for this workspace (or the orchestration graph is disabled).')
          setHits([])
          setArtifacts([])
          setPacks([])
          setPackets([])
          return
        }
        setHits((ev.hits as IdRow[] | undefined) ?? [])
        setArtifacts((art.artifacts as IdRow[] | undefined) ?? [])
        setPacks((rp.packs as IdRow[] | undefined) ?? [])
        setPackets((ap.packets as IdRow[] | undefined) ?? [])
      } catch (e: unknown) {
        setFetchFailure(resolveUxFailure(e))
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const totalRows = hits.length + artifacts.length + packs.length + packets.length
  const blocked = Boolean(featureErr || fetchFailure)

  return (
    <>
      <PageHeader
        title="Evidence registry"
        purpose={METHODOLOGY_UX.evidenceRegistryPurpose}
        statusChips={[{ label: 'Methodology-linked', tone: 'muted' }]}
        secondaryMenuItems={[
          { key: 'notes', label: 'Workspace notes', to: '/workspace-md' },
          { key: 'decisions', label: 'Decision registry', to: '/knowledge/methodology/decisions' },
        ]}
      />
      <KnowledgeSectionChrome />
      <p className="forge-support">{METHODOLOGY_UX.evidenceLead}</p>
      <TechnicalDetails summary="Technical — how this page loads">
        <p className="forge-support" style={{ margin: 0 }}>
          Combined registry: recent methodology-linked evidence rows, methodology artifacts, review packs, and assay
          packets. Endpoints: <code className="le-mono">GET /api/evidence/search</code>,{' '}
          <code className="le-mono">GET /api/artifacts</code>, <code className="le-mono">GET /api/review-packs</code>,{' '}
          <code className="le-mono">GET /api/assay-packets</code>.
        </p>
      </TechnicalDetails>

      {loading ? (
        <StatePanel variant="loading" title="Loading evidence" description={METHODOLOGY_UX.evidenceLoading} />
      ) : null}

      {!loading && featureErr ? (
        <StatePanel
          variant="not_configured"
          title="Evidence views are not available here"
          description={featureErr}
          assistShortcuts={{ context: 'Evidence registry' }}
          aiRecovery={{
            prompt:
              'Methodology evidence registry in Lenses says the feature is disabled. What do I enable or install so methodology artifacts appear?',
            label: 'Ask Chat about enabling methodology',
          }}
          actions={
            <Link className="le-btn le-btn--primary" to="/settings/llm">
              Open settings
            </Link>
          }
          telemetryTag="methodology_evidence_feature_off"
        />
      ) : null}

      {!loading && fetchFailure ? (
        <StatePanel
          variant="unavailable"
          title={fetchFailure.title}
          description={fetchFailure.description}
          technicalDetail={fetchFailure.technical}
          assistShortcuts={{ context: 'Evidence registry' }}
          aiRecovery={{
            prompt:
              'Evidence registry in Forge Lenses failed to load. What should I verify (server, workspace scan, orchestration graph) and what is the next step?',
            label: 'Ask Chat how to recover',
          }}
          actions={
            <button type="button" className="le-btn le-btn--primary" onClick={() => window.location.reload()}>
              Reload page
            </button>
          }
          telemetryTag="methodology_evidence_fetch_failed"
        />
      ) : null}

      {!loading && !blocked && totalRows === 0 ? (
        <>
          <KnowledgeEmptyGuidance variant="evidence" />
          <StatePanel
          variant="empty"
          title="No methodology evidence yet"
          description={METHODOLOGY_UX.evidenceEmpty}
          assistShortcuts={{ context: 'Evidence registry' }}
          aiRecovery={{
            prompt:
              'My Lenses Evidence registry is empty. How do I seed demo data or import markdown so methodology-linked rows appear?',
            label: 'Ask Chat how to populate evidence',
          }}
          actions={
            <>
              <Link className="le-btn le-btn--primary" to="/workspace-md">
                Workspace notes
              </Link>
              <Link className="le-btn" to="/plan">
                Plan summary
              </Link>
              <Link className="le-btn" to="/tutorials">
                Tutorials
              </Link>
            </>
          }
          telemetryTag="methodology_evidence_empty"
        />
        </>
      ) : null}

      {!loading && !blocked ? <OutcomeLearningHint /> : null}

      {!loading && !blocked && hits.length > 0 ? (
        <>
          <h2 style={{ fontSize: '1.1rem', marginTop: '1.25rem' }}>Recent methodology-linked rows</h2>
          <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
            {hits.map((h) => (
              <RecordListRow
                key={h.id}
                href={`/knowledge/methodology/record/${encodeURIComponent(h.id)}`}
                title={h.display_name}
                summary={h.summary}
                id={h.id}
              />
            ))}
          </ul>
        </>
      ) : null}

      {!loading && !blocked && artifacts.length > 0 ? (
        <>
          <h2 style={{ fontSize: '1.1rem', marginTop: '1.25rem' }}>Methodology artifacts</h2>
          <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
            {artifacts.map((a) => (
              <RecordListRow
                key={a.id}
                href={`/knowledge/methodology/record/${encodeURIComponent(a.id)}`}
                title={a.display_name}
                id={a.id}
              />
            ))}
          </ul>
        </>
      ) : null}

      {!loading && !blocked && packs.length > 0 ? (
        <>
          <h2 style={{ fontSize: '1.1rem', marginTop: '1.25rem' }}>Review packs</h2>
          <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
            {packs.map((p) => (
              <RecordListKeyRow key={p.id} id={p.id} display_name={p.display_name} />
            ))}
          </ul>
        </>
      ) : null}

      {!loading && !blocked && packets.length > 0 ? (
        <>
          <h2 style={{ fontSize: '1.1rem', marginTop: '1.25rem' }}>Assay packets</h2>
          <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
            {packets.map((p) => (
              <RecordListKeyRow key={p.id} id={p.id} display_name={p.display_name} />
            ))}
          </ul>
        </>
      ) : null}

    </>
  )
}

function RecordListKeyRow({ id, display_name }: { id: string; display_name: string }) {
  return (
    <RecordListRow
      href={`/knowledge/methodology/record/${encodeURIComponent(id)}`}
      title={display_name}
      id={id}
    />
  )
}

export function MethodologyDecisionsRegistryPage() {
  useLensesCopilotPage({ route: 'knowledge', defaultQuery: KNOWLEDGE_PUBLISH_COPILOT.methodologyDecisions })
  const [rows, setRows] = useState<
    { id: string; display_name: string; summary?: string; payload?: { signoff_state?: string; decision_type?: string } }[]
  >([])
  const [loading, setLoading] = useState(true)
  const [featureErr, setFeatureErr] = useState<string | null>(null)
  const [fetchFailure, setFetchFailure] = useState<UxResolvedFailure | null>(null)

  useEffect(() => {
    void (async () => {
      await Promise.resolve()
      setLoading(true)
      setFeatureErr(null)
      setFetchFailure(null)
      try {
        const r = await apiGetJson<Record<string, unknown>>('/api/decisions?limit=200')
        if (readFeatureDisabled(r)) {
          setFeatureErr('Decision registry is turned off for this workspace (or the orchestration graph is disabled).')
          setRows([])
        } else setRows((r.decisions as typeof rows | undefined) ?? [])
      } catch (e: unknown) {
        setFetchFailure(resolveUxFailure(e))
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const blocked = Boolean(featureErr || fetchFailure)

  return (
    <>
      <PageHeader
        title="Decision registry"
        purpose={METHODOLOGY_UX.decisionsRegistryPurpose}
        statusChips={[{ label: 'Sign-off aware', tone: 'muted' }]}
        secondaryMenuItems={[
          { key: 'evidence', label: 'Evidence registry', to: '/knowledge/methodology/evidence' },
          { key: 'notes', label: 'Workspace notes', to: '/workspace-md' },
        ]}
      />
      <p className="forge-support">{METHODOLOGY_UX.decisionsLead}</p>
      <TechnicalDetails summary="Technical — decisions endpoint">
        <p className="forge-support" style={{ margin: 0 }}>
          <code className="le-mono">GET /api/decisions?limit=200</code> — graph-backed decision records with sign-off
          metadata when available.
        </p>
      </TechnicalDetails>

      {loading ? (
        <StatePanel variant="loading" title="Loading decisions" description={METHODOLOGY_UX.decisionsLoading} />
      ) : null}

      {!loading && featureErr ? (
        <StatePanel
          variant="not_configured"
          title="Decision registry is not available here"
          description={featureErr}
          assistShortcuts={{ context: 'Decision registry' }}
          aiRecovery={{
            prompt:
              'Decision registry in Lenses is disabled. How do I turn on the orchestration graph or methodology bridge so ADRs and decisions appear?',
            label: 'Ask Chat about enabling decisions',
          }}
          telemetryTag="methodology_decisions_feature_off"
        />
      ) : null}

      {!loading && fetchFailure ? (
        <StatePanel
          variant="unavailable"
          title={fetchFailure.title}
          description={fetchFailure.description}
          technicalDetail={fetchFailure.technical}
          assistShortcuts={{ context: 'Decision registry' }}
          aiRecovery={{
            prompt:
              'Decision registry in Forge Lenses failed to load. What should I check next (server, scan, graph)?',
            label: 'Ask Chat how to recover',
          }}
          actions={
            <button type="button" className="le-btn le-btn--primary" onClick={() => window.location.reload()}>
              Reload page
            </button>
          }
          telemetryTag="methodology_decisions_fetch_failed"
        />
      ) : null}

      {!loading && !blocked && rows.length === 0 ? (
        <>
          <KnowledgeEmptyGuidance variant="decisions" />
          <StatePanel
          variant="empty"
          title="No decisions in the graph yet"
          description={METHODOLOGY_UX.decisionsEmpty}
          assistShortcuts={{ context: 'Decision registry' }}
          aiRecovery={{
            prompt:
              'My Lenses Decision registry is empty. Where do ADRs and sign-offs live in a typical Forge workspace, and how do they reach this list?',
            label: 'Ask Chat how decisions appear',
          }}
          actions={
            <Link className="le-btn le-btn--primary" to="/knowledge/methodology/evidence">
              Open evidence registry
            </Link>
          }
          telemetryTag="methodology_decisions_empty"
        />
        </>
      ) : null}

      {!loading && !blocked && rows.length > 0 ? (
        <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
          {rows.map((d) => (
            <li key={d.id} className="le-card" style={{ marginBottom: '0.35rem' }}>
              <Link to={`/knowledge/methodology/record/${encodeURIComponent(d.id)}`}>
                <strong>{d.display_name}</strong>
              </Link>
              <div className="le-muted">
                {d.payload?.decision_type ?? 'Type unknown'} · {d.payload?.signoff_state || 'Sign-off: —'}
              </div>
              {d.summary ? <div className="le-muted">{d.summary}</div> : null}
              <details className="forge-support" style={{ marginTop: '0.35rem', fontSize: '0.78rem' }}>
                <summary style={{ cursor: 'pointer' }}>Record id</summary>
                <code className="le-mono" style={{ fontSize: '0.72rem', wordBreak: 'break-word' }}>
                  {d.id}
                </code>
              </details>
            </li>
          ))}
        </ul>
      ) : null}

    </>
  )
}

export function MethodologyGraphRecordPage() {
  useLensesCopilotPage({ route: 'knowledge', defaultQuery: KNOWLEDGE_PUBLISH_COPILOT.methodologyEvidence })
  const { entityId } = useParams<{ entityId: string }>()
  const id = entityId ? decodeURIComponent(entityId) : ''
  const [bundle, setBundle] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(Boolean(id))
  const [fetchFailure, setFetchFailure] = useState<UxResolvedFailure | null>(null)
  const [notFoundMsg, setNotFoundMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    void (async () => {
      await Promise.resolve()
      setLoading(true)
      setFetchFailure(null)
      setNotFoundMsg(null)
      try {
        const b = await apiGetJson<Record<string, unknown>>(`/api/methodology/records/${encodeURIComponent(id)}`)
        if (!b.ok) {
          setNotFoundMsg(String(b.error || 'This record was not found in the methodology graph.'))
          setBundle(null)
        } else {
          setBundle(b)
          setNotFoundMsg(null)
        }
      } catch (e: unknown) {
        setFetchFailure(resolveUxFailure(e))
      } finally {
        setLoading(false)
      }
    })()
  }, [id])

  return (
    <>
      <PageHeader
        title={METHODOLOGY_UX_RECORD.pageTitle}
        purpose={METHODOLOGY_UX_RECORD.pagePurpose}
        secondaryMenuItems={[
          { key: 'evidence', label: 'Evidence registry', to: '/knowledge/methodology/evidence' },
          { key: 'decisions', label: 'Decision registry', to: '/knowledge/methodology/decisions' },
        ]}
      />
      {!id ? (
        <StatePanel
          variant="invalid"
          title="Pick a record from the lists"
          description="Open Evidence or Decisions registry and choose an item. Raw graph ids are optional power-user input."
          assistShortcuts={{ context: 'Methodology graph record' }}
          actions={
            <>
              <Link className="le-btn le-btn--primary" to="/knowledge/methodology/evidence">
                Evidence registry
              </Link>
              <Link className="le-btn" to="/knowledge/methodology/decisions">
                Decision registry
              </Link>
            </>
          }
        />
      ) : null}

      {loading ? (
        <StatePanel variant="loading" title="Loading record" description="Fetching this graph object from your workspace." />
      ) : null}

      {!loading && fetchFailure ? (
        <StatePanel
          variant="unavailable"
          title={fetchFailure.title}
          description={fetchFailure.description}
          technicalDetail={fetchFailure.technical}
          assistShortcuts={{ context: 'Methodology graph record', detail: `Record id: ${id}` }}
          actions={
            <button type="button" className="le-btn le-btn--primary" onClick={() => window.location.reload()}>
              Reload page
            </button>
          }
        />
      ) : null}

      {!loading && notFoundMsg ? (
        <StatePanel
          variant="empty"
          title="Record not found"
          description={notFoundMsg}
          assistShortcuts={{ context: 'Methodology graph record', detail: `Tried id: ${id}` }}
          actions={
            <Link className="le-btn le-btn--primary" to="/knowledge/methodology/evidence">
              Back to evidence registry
            </Link>
          }
          technicalDetail={`Requested id: ${id}`}
        />
      ) : null}

      {bundle?.entity ? (
        <>
          <p className="forge-support">
            <Link to="/knowledge/methodology/evidence">Evidence registry</Link>
            {' · '}
            <Link to="/knowledge/methodology/decisions">Decisions</Link>
          </p>
          <TechnicalDetails summary="Technical — raw graph payload" defaultOpen={false}>
            <pre className="le-mono le-card" style={{ overflow: 'auto', fontSize: '0.85rem' }}>
              {JSON.stringify(bundle, null, 2)}
            </pre>
          </TechnicalDetails>
        </>
      ) : null}
    </>
  )
}

const READINESS_EXAMPLE_IDS = ['ogs:demo:release:v1.4.0', 'ogs:demo:release:v1.5.0']

function ReleaseChecklistPicker({
  releaseId,
  onReleaseIdChange,
  onCheck,
}: {
  releaseId: string
  onReleaseIdChange: (id: string) => void
  onCheck: () => void
}) {
  const [discoveredReleases, setDiscoveredReleases] = useState<DiscoveredRelease[]>([])
  const [loadingReleases, setLoadingReleases] = useState(true)

  useEffect(() => {
    let cancelled = false
    void fetchDiscoveredReleases()
      .then((rows) => {
        if (!cancelled) setDiscoveredReleases(rows)
      })
      .finally(() => {
        if (!cancelled) setLoadingReleases(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const options =
    discoveredReleases.length > 0
      ? discoveredReleases
      : READINESS_EXAMPLE_IDS.map((id) => ({ id, display_name: id.replace(/^ogs:demo:release:/, 'Release ') }))

  return (
    <div className="readinessPicker le-card" style={{ marginBottom: '1rem', padding: '0.65rem 0.85rem' }}>
      <h2 style={{ fontSize: '0.95rem', margin: '0 0 0.35rem' }}>Release checklist</h2>
      <p className="forge-support" style={{ marginTop: 0 }}>
        Pick a release discovered from your orchestration graph — not a free-text graph id.
      </p>
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <label>
          Release
          <select
            className="le-select releasePicker"
            style={{ display: 'block', marginTop: '0.25rem', minWidth: '16rem' }}
            value={releaseId}
            disabled={loadingReleases}
            onChange={(e) => onReleaseIdChange(e.target.value)}
            aria-describedby="readiness-release-hint"
          >
            {options.map((r) => (
              <option key={r.id} value={r.id}>
                {r.display_name}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="le-btn le-btn--primary" onClick={onCheck}>
          Check readiness
        </button>
      </div>
      {discoveredReleases.length > 0 ? (
        <p className="forge-support" style={{ fontSize: '0.82rem', marginBottom: 0 }}>
          {discoveredReleases.length} release(s) discoveredRelease from graph-linked assay packets and trace.
        </p>
      ) : null}
    </div>
  )
}

export function MethodologyReadinessPage() {
  useLensesCopilotPage({ route: 'knowledge', defaultQuery: KNOWLEDGE_PUBLISH_COPILOT.releaseReadiness })
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [releaseId, setReleaseId] = useState(() => searchParams.get('release_id') || 'ogs:demo:release:v1.4.0')
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [featureErr, setFeatureErr] = useState<string | null>(null)
  const [fetchFailure, setFetchFailure] = useState<UxResolvedFailure | null>(null)

  useEffect(() => {
    const rid = searchParams.get('release_id') || 'ogs:demo:release:v1.4.0'
    void (async () => {
      await Promise.resolve()
      setReleaseId(rid)
      setLoading(true)
      setFeatureErr(null)
      setFetchFailure(null)
      try {
        const p = await apiGetJson<Record<string, unknown>>(
          `/api/methodology/readiness?release_id=${encodeURIComponent(rid)}`,
        )
        if (readFeatureDisabled(p)) {
          setFeatureErr('Release readiness checks are turned off for this workspace (or the orchestration graph is disabled).')
          setPayload(null)
          return
        }
        setPayload(p)
      } catch (e: unknown) {
        setFetchFailure(resolveUxFailure(e))
      } finally {
        setLoading(false)
      }
    })()
  }, [searchParams])

  const blocked = Boolean(featureErr || fetchFailure)

  return (
    <>
      <PageHeader
        title="Release readiness"
        purpose={METHODOLOGY_UX.readinessPagePurpose}
        statusChips={[{ label: 'Release check', tone: 'muted' }]}
        secondaryMenuItems={[
          { key: 'evidence', label: 'Evidence registry', to: '/knowledge/methodology/evidence' },
          { key: 'today', label: 'Today', to: '/plan?tab=today' },
        ]}
      />
      <p className="forge-support">{METHODOLOGY_UX.readinessLead}</p>
      <p className="forge-support">
        <Link to={mergePlanningScopeIntoTo('/plan', location.search)}>Open Plan summary with the same Work scope</Link>{' '}
        when you need to adjust backlog or roadmap picks before checking readiness.
      </p>

      <section
        className="le-card"
        style={{ marginBottom: '1rem', padding: '0.65rem 0.85rem' }}
        aria-label="How to run a readiness check"
      >
        <h2 style={{ fontSize: '0.95rem', margin: '0 0 0.35rem' }}>Before you run a check</h2>
        <p className="forge-support" style={{ margin: 0 }}>
          {METHODOLOGY_UX.readinessPrereq}
        </p>
        <StatePanelAssistShortcuts actions={assistShortcutsForContext({ context: 'Release readiness' })} />
      </section>

      <ReleaseChecklistPicker
        releaseId={releaseId}
        onReleaseIdChange={setReleaseId}
        onCheck={() => setSearchParams({ release_id: releaseId })}
      />
      <p id="readiness-release-hint" className="forge-support" style={{ fontSize: '0.82rem' }}>
        Advanced: record id is stored in the URL as <code className="le-mono">release_id</code> when you run a check.
      </p>

      <TechnicalDetails summary="Technical — readiness API">
        <p className="forge-support" style={{ margin: 0 }}>
          Heuristic gaps from <code className="le-mono">GET /api/methodology/readiness?release_id=…</code> — e.g. missing
          assay coverage or unsigned binding directives in the graph.
        </p>
      </TechnicalDetails>

      {loading ? (
        <StatePanel variant="loading" title="Checking readiness" description="Evaluating release coverage signals." />
      ) : null}

      {!loading && featureErr ? (
        <StatePanel
          variant="not_configured"
          title="Readiness is not available here"
          description={featureErr}
          assistShortcuts={{ context: 'Release readiness' }}
          telemetryTag="methodology_readiness_feature_off"
        />
      ) : null}

      {!loading && fetchFailure ? (
        <StatePanel
          variant="unavailable"
          title={fetchFailure.title}
          description={fetchFailure.description}
          technicalDetail={fetchFailure.technical}
          assistShortcuts={{ context: 'Release readiness' }}
          actions={
            <button type="button" className="le-btn le-btn--primary" onClick={() => window.location.reload()}>
              Reload page
            </button>
          }
          telemetryTag="methodology_readiness_fetch_failed"
        />
      ) : null}

      {!loading && !blocked && payload ? (
        <>
          {(payload.gaps as unknown[] | undefined)?.length ? (
            <div className="forge-support" style={{ color: 'var(--le-warning-fg, #b45309)' }}>
              <strong>Missing or required items</strong>
              <ul>
                {((payload.gaps as { kind?: string; detail?: string }[]) || []).map((g, i) => (
                  <li key={i}>
                    {g.kind}: {g.detail}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <StatePanel
              variant="stale"
              density="compact"
              title="No gaps reported"
              description="Heuristics did not flag missing items for this release. Confirm scope and evidence still match your real ship criteria."
            />
          )}
          <TechnicalDetails summary="Technical — full readiness payload">
            <pre className="le-mono le-card" style={{ overflow: 'auto', fontSize: '0.85rem' }}>
              {JSON.stringify(payload, null, 2)}
            </pre>
          </TechnicalDetails>
        </>
      ) : null}

    </>
  )
}
