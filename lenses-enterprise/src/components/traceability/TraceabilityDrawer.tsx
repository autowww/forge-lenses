import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { apiGetJson } from '../../api/http'
import { useTraceabilityDrawer } from '../../context/TraceabilityDrawerContext'
import { classifyFetchError } from '../../lib/classifyFetchError'
import { recordPageFailure } from '../../telemetry/studioTelemetry'
import { StatePanel } from '../page/StatePanel'
import './TraceabilityDrawer.css'

type SpineMeta = {
  created_at?: string
  updated_at?: string
  owner?: string
  freshness_at?: string
  trust_level?: string
  workspace_scope?: string
  project_slug?: string
}

type TraceNode = {
  id: string
  kind: string
  display_name: string
  summary?: string
  canonical_kind?: string
  spine_meta?: SpineMeta
  projections?: {
    neutral?: { labels?: { primary?: string; terminology?: unknown } }
    forge?: { labels?: string[]; subtitle?: string; conflict_notes?: string | null }
    sdlc?: { labels?: string[]; subtitle?: string }
    pdlc?: { labels?: string[]; subtitle?: string }
  }
}

type TraceEdge = {
  id: string
  from_id: string
  to_id: string
  kind: string
}

type TracePayload = {
  ok?: boolean
  feature_disabled?: boolean
  error?: string
  root?: TraceNode
  root_id?: string
  nodes?: TraceNode[]
  edges?: TraceEdge[]
  truncated?: boolean
  bridge?: {
    registry_version?: string
    traceability_score?: {
      ok?: boolean
      score?: number
      matched_rules?: number
      total_rules?: number
      canonical_kind?: string
    }
    root_gaps?: Array<{ kind?: string; edge_kind?: string; detail?: string }>
  }
}

type LensTab = 'neutral' | 'forge' | 'sdlc' | 'pdlc'

function groupNodesByKind(nodes: TraceNode[]): Map<string, TraceNode[]> {
  const m = new Map<string, TraceNode[]>()
  for (const n of nodes) {
    const k = n.canonical_kind || n.kind || 'unknown'
    const arr = m.get(k) ?? []
    arr.push(n)
    m.set(k, arr)
  }
  for (const arr of m.values()) {
    arr.sort((a, b) => a.display_name.localeCompare(b.display_name))
  }
  return m
}

function lensLabel(n: TraceNode, lens: LensTab): string {
  const p = n.projections?.[lens]
  if (!p) return n.display_name
  if (lens === 'neutral') {
    const primary = p.labels && typeof p.labels === 'object' && 'primary' in p.labels ? String((p.labels as { primary?: string }).primary || '') : ''
    return primary || n.display_name
  }
  const labels = (p as { labels?: string[] }).labels
  if (Array.isArray(labels) && labels.length) return `${n.display_name} · ${labels[0]}`
  return n.display_name
}

/**
 * Orchestration trace panel: uses Bridge spine API when enabled, else legacy graph trace.
 */
export function TraceabilityDrawer() {
  const { isOpen, rootId, headline, close } = useTraceabilityDrawer()
  const [phase, setPhase] = useState<'idle' | 'loading' | 'ok' | 'err'>('idle')
  const [data, setData] = useState<TracePayload | null>(null)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const [traceSource, setTraceSource] = useState<'bridge' | 'legacy' | null>(null)
  const [lensTab, setLensTab] = useState<LensTab>('forge')

  const load = useCallback(async () => {
    if (!rootId) return
    setPhase('loading')
    setErrMsg(null)
    setTraceSource(null)

    const legacyUrl = `/api/orchestration/trace?${new URLSearchParams({
      root: rootId,
      direction: 'both',
      max_depth: '8',
      max_nodes: '500',
    }).toString()}`

    try {
      const en = await apiGetJson<{ ok?: boolean; enabled?: boolean }>('/api/bridge/enabled')
      const bridgeOn = !!(en.ok !== false && en.enabled)

      if (bridgeOn) {
        try {
          const enc = encodeURIComponent(rootId)
          const bp = await apiGetJson<TracePayload>(
            `/api/bridge/trace/${enc}?max_depth=8&max_nodes=500`,
          )
          if (bp.feature_disabled) {
            /* fall through to legacy */
          } else if (bp.ok === false && bp.error === 'entity_not_found') {
            setData(bp)
            setPhase('err')
            setErrMsg('This entity is not in the local orchestration graph yet.')
            recordPageFailure('bridge_trace', 'entity_not_found')
            setTraceSource('bridge')
            return
          } else if (bp.ok === true) {
            setData(bp)
            setPhase('ok')
            setTraceSource('bridge')
            return
          }
        } catch {
          /* fallback */
        }
      }

      const payload = await apiGetJson<TracePayload>(legacyUrl)
      setData(payload)
      setTraceSource('legacy')
      if (payload.feature_disabled) {
        setPhase('ok')
        return
      }
      if (payload.ok === false && payload.error === 'entity_not_found') {
        setPhase('err')
        setErrMsg('This entity is not in the local orchestration graph yet.')
        recordPageFailure('orchestration_trace', 'entity_not_found')
        return
      }
      if (payload.ok !== true) {
        setPhase('err')
        setErrMsg(payload.error || 'Trace failed')
        recordPageFailure('orchestration_trace', payload.error || 'unknown')
        return
      }
      setPhase('ok')
    } catch (e) {
      const c = classifyFetchError(e)
      setPhase('err')
      setErrMsg(c.summary)
      recordPageFailure('traceability_drawer', c.summary)
    }
  }, [rootId])

  useEffect(() => {
    if (!isOpen || !rootId) {
      setPhase('idle')
      setData(null)
      setErrMsg(null)
      setTraceSource(null)
      return
    }
    void load()
  }, [isOpen, rootId, load])

  useEffect(() => {
    if (!isOpen) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [isOpen, close])

  if (!isOpen || typeof document === 'undefined') return null

  const nodes = data?.nodes ?? []
  const edges = data?.edges ?? []
  const grouped =
    phase === 'ok' && data?.ok && traceSource === 'bridge'
      ? groupNodesByKind(nodes)
      : phase === 'ok' && data?.ok
        ? (() => {
            const m = new Map<string, TraceNode[]>()
            for (const n of nodes) {
              const k = n.kind || 'unknown'
              const arr = m.get(k) ?? []
              arr.push(n)
              m.set(k, arr)
            }
            for (const arr of m.values()) {
              arr.sort((a, b) => a.display_name.localeCompare(b.display_name))
            }
            return m
          })()
        : null

  const bridgeScore = data?.bridge?.traceability_score
  const rootGaps = data?.bridge?.root_gaps ?? []
  const rootMeta = traceSource === 'bridge' && data?.root && 'spine_meta' in data.root ? data.root.spine_meta : null

  const panel = (
    <>
      <div
        className="le-trace-drawer-backdrop"
        role="presentation"
        aria-hidden="true"
        onClick={close}
      />
      <aside
        className="le-trace-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="le-trace-drawer-title"
      >
        <div className="le-trace-drawer__head">
          <div>
            <h2 className="le-trace-drawer__title" id="le-trace-drawer-title">
              Traceability
            </h2>
            <p className="le-trace-drawer__sub forge-support">
              {headline ?? 'Planning through delivery — methodology-neutral spine with optional Forge / SDLC / PDLC labels.'}
            </p>
          </div>
          <button type="button" className="le-trace-drawer__close" onClick={close} autoFocus>
            Close
          </button>
        </div>
        <div className="le-trace-drawer__body">
          {rootId ? (
            <div className="le-trace-drawer__root-pill">
              <span className="forge-support">Root · </span>
              <code className="le-trace-drawer__mono">{rootId}</code>
              {traceSource ? (
                <span className="forge-support" style={{ marginLeft: '0.5rem' }}>
                  ({traceSource === 'bridge' ? 'Bridge spine' : 'Graph trace'})
                </span>
              ) : null}
              {data?.root && traceSource === 'bridge' && data.root.canonical_kind ? (
                <div className="forge-support" style={{ marginTop: '0.35rem' }}>
                  Canonical: <code className="le-mono">{data.root.canonical_kind}</code>
                  {rootMeta?.updated_at ? (
                    <>
                      {' '}
                      · updated <time dateTime={rootMeta.updated_at}>{rootMeta.updated_at}</time>
                    </>
                  ) : null}
                  {rootMeta?.freshness_at ? (
                    <>
                      {' '}
                      · freshness <time dateTime={rootMeta.freshness_at}>{rootMeta.freshness_at}</time>
                    </>
                  ) : null}
                  {rootMeta?.trust_level ? (
                    <>
                      {' '}
                      · trust <code className="le-mono">{rootMeta.trust_level}</code>
                    </>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}

          {traceSource === 'bridge' && phase === 'ok' && data?.ok ? (
            <div className="le-trace-drawer__lens-tabs" role="tablist" aria-label="Methodology lens">
              {(['forge', 'sdlc', 'pdlc', 'neutral'] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  aria-selected={lensTab === tab}
                  className={`le-trace-drawer__lens-tab${lensTab === tab ? ' is-active' : ''}`}
                  onClick={() => setLensTab(tab)}
                >
                  {tab === 'neutral' ? 'Neutral' : tab.toUpperCase()}
                </button>
              ))}
            </div>
          ) : null}

          {phase === 'loading' ? <p className="forge-support">Loading trace…</p> : null}

          {data?.feature_disabled ? (
            <p className="forge-support">
              Orchestration graph is disabled on this server (
              <code className="le-mono">LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH=0</code>).
            </p>
          ) : null}

          {phase === 'err' ? (
            <StatePanel
              variant="error"
              density="compact"
              title="Could not load trace"
              description={errMsg}
              actions={
                <button type="button" className="le-btn le-btn--primary le-btn--small" onClick={() => void load()}>
                  Retry
                </button>
              }
              telemetryTag="orchestration_trace_error"
            />
          ) : null}

          {traceSource === 'bridge' && bridgeScore?.ok === true ? (
            <div className="le-trace-drawer__score" role="status">
              <strong>Graph completeness (registry rules)</strong>
              <span className="forge-support" style={{ marginLeft: '0.35rem' }}>
                {(bridgeScore.score != null ? Math.round(bridgeScore.score * 100) : 0)}% ·{' '}
                {bridgeScore.matched_rules ?? 0}/{bridgeScore.total_rules ?? 0} edge patterns matched for{' '}
                <code className="le-mono">{bridgeScore.canonical_kind ?? '?'}</code>
              </span>
              {data?.bridge?.registry_version ? (
                <div className="forge-support" style={{ marginTop: '0.25rem' }}>
                  Registry <code className="le-mono">{data.bridge.registry_version}</code>
                </div>
              ) : null}
            </div>
          ) : null}

          {traceSource === 'bridge' && rootGaps.length > 0 ? (
            <div className="le-trace-drawer__gaps">
              <h3 className="le-trace-drawer__section-title">Possible chain gaps</h3>
              <ul className="le-trace-drawer__list">
                {rootGaps.map((g, i) => (
                  <li key={`${g.edge_kind ?? i}`} className="le-trace-drawer__li forge-support">
                    {g.detail ?? g.kind ?? 'gap'}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {traceSource === 'bridge' && phase === 'ok' && data?.ok && !rootGaps.length && bridgeScore?.ok === true && (bridgeScore.total_rules ?? 0) > 0 && (bridgeScore.score ?? 0) >= 1 ? (
            <p className="forge-support" style={{ marginBottom: '0.75rem' }}>
              No registry-reported gaps for this root under current rules.
            </p>
          ) : null}

          {phase === 'ok' && data?.ok && grouped ? (
            <>
              {data.truncated ? (
                <p className="forge-support" style={{ marginBottom: '0.75rem' }}>
                  Graph truncated for safety — increase limits in the API later if needed.
                </p>
              ) : null}
              <p className="forge-support" style={{ marginBottom: '0.75rem' }}>
                <strong>{nodes.length}</strong> entities · <strong>{edges.length}</strong> relationships
                {nodes.length === 0 ? (
                  <span> — nothing linked in this neighborhood yet.</span>
                ) : null}
              </p>
              {[...grouped.entries()]
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([kind, list]) => (
                  <div key={kind}>
                    <h3 className="le-trace-drawer__section-title">
                      {traceSource === 'bridge' ? kind.replace(/_/g, ' ') : kind.replace(/_/g, ' ')}
                      {traceSource === 'bridge' ? (
                        <span className="forge-support" style={{ fontWeight: 400 }}>
                          {' '}
                          (canonical)
                        </span>
                      ) : null}
                    </h3>
                    <ul className="le-trace-drawer__list">
                      {list.map((n) => (
                        <li key={n.id} className="le-trace-drawer__li">
                          <strong>
                            {traceSource === 'bridge' ? lensLabel(n, lensTab) : n.display_name}
                          </strong>
                          {n.summary ? <span className="forge-support"> — {n.summary}</span> : null}
                          <div className="le-trace-drawer__mono">{n.id}</div>
                          {traceSource === 'bridge' && n.projections?.forge?.conflict_notes ? (
                            <div className="forge-support" style={{ marginTop: '0.25rem' }}>
                              Note: {n.projections.forge.conflict_notes}
                            </div>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              <h3 className="le-trace-drawer__section-title">Relationships</h3>
              {edges.length === 0 ? (
                <p className="forge-support">No edges in this neighborhood — seed the orchestration graph or link work in-repo.</p>
              ) : (
                <ul className="le-trace-drawer__list">
                  {edges.map((e) => (
                    <li key={e.id} className="le-trace-drawer__li">
                      <div className="le-trace-drawer__edge">
                        <code className="le-trace-drawer__mono">{e.from_id}</code>
                        <span className="forge-support"> —{e.kind}→ </span>
                        <code className="le-trace-drawer__mono">{e.to_id}</code>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : null}
        </div>
      </aside>
    </>
  )

  return createPortal(panel, document.body)
}
