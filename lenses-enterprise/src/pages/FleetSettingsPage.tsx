import { Fragment, useCallback, useEffect, useId, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiGetJson, apiPostJson, ApiError } from '../api/http'
import { PageHeader, StatePanel } from '../components/page'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { ROUTE_SUBTITLE, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

type FleetNodePayload = {
  id: string
  base_url: string
  /** Present only on newly added rows before first Save (server stores separately). */
  bearer_token?: string
  bearer_token_configured?: boolean
  enabled?: boolean
  priority?: number
  max_cpu_percent?: number | null
  max_memory_percent?: number | null
}

type FleetSettingsPayload = {
  version?: number
  nodes?: FleetNodePayload[]
}

type StudioFleetStatus = 'connected' | 'online' | 'needs_token' | 'offline'

type ProbeNodeRow = {
  id?: string
  base_url?: string
  skipped?: boolean
  reason?: string
  studio_status?: StudioFleetStatus
  version?: Record<string, unknown>
  health?: Record<string, unknown>
  health_anonymous?: { http_status?: number; ok?: boolean }
  eligible?: boolean
  priority?: number
}

type RollupPayload = {
  connected_count?: number
  configured_count?: number
  weight_sum?: number
  cpu_usage_pct?: number | null
  memory_used_pct?: number | null
  loadavg_1m?: number | null
  cpus_logical_sum?: number | null
  avg_ghz?: number | null
  memory_total_gb_sum?: number | null
}

type DiscoveryCandidate = {
  host: string
  port: number
  base_url: string
  reachable?: boolean
  is_fleet?: boolean
  auth_required?: boolean
  version?: Record<string, unknown> | null
  error?: string | null
}

function newNodeId(): string {
  return `n-${Date.now().toString(36)}-${Math.random().toString(16).slice(2, 10)}`
}

function defaultLocalRow(): FleetNodePayload {
  return {
    id: newNodeId(),
    base_url: 'http://127.0.0.1:18765',
    enabled: true,
    priority: 10,
    max_cpu_percent: null,
    max_memory_percent: null,
  }
}

function normalizeLoadedNodes(nodes: FleetNodePayload[] | undefined): FleetNodePayload[] {
  if (!nodes || nodes.length === 0) {
    return [defaultLocalRow()]
  }
  return nodes.map((n) => ({
    id: String(n.id || newNodeId()),
    base_url: String(n.base_url ?? '').trim(),
    enabled: n.enabled !== false,
    priority: typeof n.priority === 'number' ? n.priority : Number(n.priority) || 100,
    max_cpu_percent: n.max_cpu_percent === undefined || n.max_cpu_percent === null ? null : Number(n.max_cpu_percent),
    max_memory_percent:
      n.max_memory_percent === undefined || n.max_memory_percent === null ? null : Number(n.max_memory_percent),
    bearer_token_configured: Boolean(n.bearer_token_configured),
  }))
}

function statusLabel(s: StudioFleetStatus | undefined): string {
  switch (s) {
    case 'connected':
      return 'Connected'
    case 'online':
      return 'Online'
    case 'needs_token':
      return 'Auth required'
    case 'offline':
      return 'Offline'
    default:
      return '—'
  }
}

function fleetHostTabDotClass(s: StudioFleetStatus | undefined): string {
  const base = 'le-fleet-host-tabs__dot'
  switch (s) {
    case 'connected':
      return `${base} ${base}--ok`
    case 'online':
      return `${base} ${base}--warn`
    case 'needs_token':
      return `${base} ${base}--token`
    case 'offline':
      return `${base} ${base}--off`
    default:
      return base
  }
}

function statusClass(s: StudioFleetStatus | undefined): string {
  switch (s) {
    case 'connected':
      return 'le-fleet-status le-fleet-status--ok'
    case 'online':
      return 'le-fleet-status le-fleet-status--warn'
    case 'needs_token':
      return 'le-fleet-status le-fleet-status--token'
    case 'offline':
      return 'le-fleet-status le-fleet-status--off'
    default:
      return 'le-fleet-status'
  }
}

function formatSemver(v: Record<string, unknown> | null | undefined): string {
  if (!v) return ''
  const p = typeof v.package_semver === 'string' ? v.package_semver : ''
  const sv = typeof v.server_version === 'string' ? v.server_version : ''
  return p || sv || ''
}

function fleetHostTabLabel(n: FleetNodePayload): string {
  const url = n.base_url.trim()
  if (!url) return 'New host'
  if (/127\.0\.0\.1|localhost/i.test(url)) return 'Localhost'
  try {
    const u = new URL(url)
    const host = u.hostname
    const port = u.port
    if (port) return `${host}:${port}`
    return host
  } catch {
    return url.length > 22 ? `${url.slice(0, 20)}…` : url
  }
}

function gpuChipsFromSnapshot(snapshot: Record<string, unknown> | null | undefined): string[] {
  if (!snapshot) return []
  const host = snapshot.host as Record<string, unknown> | undefined
  if (!host || typeof host !== 'object') return []
  const gpu = host.gpu as Record<string, unknown> | undefined
  if (!gpu || typeof gpu !== 'object') return []
  const labels: string[] = []
  const pushIf = (key: string, label: string) => {
    const block = gpu[key] as Record<string, unknown> | undefined
    if (!block || typeof block !== 'object') return
    if (block.available === true) labels.push(label)
    const dev = block.devices
    if (Array.isArray(dev) && dev.length > 0) labels.push(label)
  }
  pushIf('nvidia', 'NVIDIA')
  pushIf('rocm', 'AMD ROCm')
  pushIf('amdgpu_sysfs', 'AMDGPU')
  pushIf('intel_drm_est', 'Intel')
  return labels
}

export function FleetSettingsPage() {
  const navigate = useNavigate()
  const hForm = useId()
  const hDiscover = useId()
  const hTestFleet = useId()
  useLensesCopilotPage({ route: 'fleet-settings' })

  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [nodes, setNodes] = useState<FleetNodePayload[]>([])
  const [bearerDrafts, setBearerDrafts] = useState<Record<string, string>>({})
  const [clearedBearerIds, setClearedBearerIds] = useState<Record<string, boolean>>({})
  const [probe, setProbe] = useState<Record<string, unknown> | null>(null)
  const [probeErr, setProbeErr] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveOk, setSaveOk] = useState<string | null>(null)
  const [tfBusy, setTfBusy] = useState(false)
  const [tfErr, setTfErr] = useState<string | null>(null)
  const [tfResult, setTfResult] = useState<Record<string, unknown> | null>(null)

  const [discMode, setDiscMode] = useState<'quick' | 'subnet'>('quick')
  const [discGlobalTok, setDiscGlobalTok] = useState('')
  const [discExtraHosts, setDiscExtraHosts] = useState('')
  const [discBusy, setDiscBusy] = useState(false)
  const [discRes, setDiscRes] = useState<Record<string, unknown> | null>(null)
  const [discErr, setDiscErr] = useState<string | null>(null)
  const [discPick, setDiscPick] = useState<Record<string, boolean>>({})
  const [discRowTok, setDiscRowTok] = useState<Record<string, string>>({})

  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [detailById, setDetailById] = useState<Record<string, Record<string, unknown>>>({})
  const [detailBusy, setDetailBusy] = useState<string | null>(null)
  const [detailErr, setDetailErr] = useState<string | null>(null)
  const [connectBusy, setConnectBusy] = useState<string | null>(null)
  const [connectMsg, setConnectMsg] = useState<string | null>(null)
  /** Which Fleet host row is focused in the browser-style tab strip (one node per tab). */
  const [activeHostTabId, setActiveHostTabId] = useState<string | null>(null)

  const emptyFallback = useMemo(() => [defaultLocalRow()], [])

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    setSaveOk(null)
    try {
      const res = await apiGetJson<{ ok?: boolean; settings?: FleetSettingsPayload }>('/api/fleet/settings')
      if (!res.ok) {
        setErr('Could not load Fleet settings')
        return
      }
      const st = res.settings ?? {}
      const raw = st.nodes
      if (raw && raw.length > 0) {
        setNodes(normalizeLoadedNodes(raw))
      } else {
        setNodes(emptyFallback)
      }
      setBearerDrafts({})
      setClearedBearerIds({})
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : 'Could not load Fleet settings')
    } finally {
      setLoading(false)
    }
  }, [emptyFallback])

  useEffect(() => {
    void load()
  }, [load])

  const onSave = useCallback(async () => {
    setSaving(true)
    setSaveOk(null)
    setErr(null)
    try {
      const payloadNodes = nodes.map((n) => {
        const base: Record<string, unknown> = {
          id: n.id,
          base_url: n.base_url.trim().replace(/\/+$/, ''),
          enabled: n.enabled !== false,
          priority: Number.isFinite(Number(n.priority)) ? Number(n.priority) : 100,
          max_cpu_percent:
            n.max_cpu_percent === null || n.max_cpu_percent === undefined || String(n.max_cpu_percent) === ''
              ? null
              : Number(n.max_cpu_percent),
          max_memory_percent:
            n.max_memory_percent === null || n.max_memory_percent === undefined || String(n.max_memory_percent) === ''
              ? null
              : Number(n.max_memory_percent),
        }
        const draft = (bearerDrafts[n.id] ?? '').trim()
        if (clearedBearerIds[n.id]) {
          base.bearer_token = ''
        } else if (draft !== '') {
          base.bearer_token = draft
        } else if (!n.bearer_token_configured) {
          base.bearer_token = ''
        }
        return base
      })
      await apiPostJson('/api/fleet/settings', { settings: { nodes: payloadNodes } })
      setSaveOk('Saved on the Lenses host (same trust boundary as AI Setup).')
      setBearerDrafts({})
      setClearedBearerIds({})
      await load()
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }, [nodes, bearerDrafts, clearedBearerIds, load])

  const onProbe = useCallback(async () => {
    setProbe(null)
    setProbeErr(null)
    try {
      const res = await apiPostJson<Record<string, unknown>>('/api/fleet/probe', {})
      setProbe(res)
    } catch (e) {
      setProbeErr(e instanceof ApiError ? e.message : 'Probe failed')
    }
  }, [])

  const onTestFleet = useCallback(async () => {
    setTfBusy(true)
    setTfErr(null)
    setTfResult(null)
    try {
      const res = await apiPostJson<Record<string, unknown>>('/api/fleet/test-fleet', { count: 5 })
      if (res.ok !== true) {
        const code = typeof res.error === 'string' ? res.error : 'fleet_test_failed'
        const det = res.detail
        setTfErr(det != null ? `${code} · ${typeof det === 'string' ? det : JSON.stringify(det)}` : code)
        setTfResult(res)
        return
      }
      setTfResult(res)
    } catch (e) {
      setTfErr(e instanceof ApiError ? e.message : 'Test Fleet failed')
    } finally {
      setTfBusy(false)
    }
  }, [])

  const onDiscover = useCallback(async () => {
    setDiscBusy(true)
    setDiscErr(null)
    setDiscRes(null)
    setDiscPick({})
    try {
      const extra = discExtraHosts
        .split(/[\s,]+/)
        .map((s) => s.trim())
        .filter(Boolean)
      const res = await apiPostJson<Record<string, unknown>>('/api/fleet/discover', {
        mode: discMode,
        global_token: discGlobalTok.trim(),
        hosts: extra.length ? extra : undefined,
      })
      setDiscRes(res)
    } catch (e) {
      setDiscErr(e instanceof ApiError ? e.message : 'Discovery failed')
    } finally {
      setDiscBusy(false)
    }
  }, [discMode, discGlobalTok, discExtraHosts])

  const toggleDiscPick = useCallback((key: string) => {
    setDiscPick((p) => ({ ...p, [key]: !p[key] }))
  }, [])

  const addSelectedDiscovery = useCallback(() => {
    if (!discRes?.candidates || !Array.isArray(discRes.candidates)) return
    const cands = discRes.candidates as DiscoveryCandidate[]
    const next: FleetNodePayload[] = [...nodes]
    const draftAdds: Record<string, string> = {}
    let pri = Math.max(0, ...next.map((n) => Number(n.priority) || 0)) + 10
    for (const c of cands) {
      const key = `${c.host}:${c.port}`
      if (!discPick[key] || !c.is_fleet) continue
      const tok = (discRowTok[key] ?? '').trim() || discGlobalTok.trim()
      pri += 10
      const nid = newNodeId()
      next.push({
        id: nid,
        base_url: c.base_url.replace(/\/+$/, ''),
        enabled: true,
        priority: pri,
        max_cpu_percent: null,
        max_memory_percent: null,
        bearer_token_configured: Boolean(tok),
      })
      if (tok) {
        draftAdds[nid] = tok
      }
    }
    if (Object.keys(draftAdds).length) {
      setBearerDrafts((d) => ({ ...d, ...draftAdds }))
    }
    setNodes(next.length ? next : nodes)
    setDiscPick({})
    setConnectMsg('Added hosts — pick each tab to review, then click Save to persist.')
  }, [discRes, discPick, discRowTok, discGlobalTok, nodes])

  const fetchNodeDetail = useCallback(async (nodeId: string) => {
    setDetailBusy(nodeId)
    setDetailErr(null)
    try {
      const res = await apiPostJson<Record<string, unknown>>('/api/fleet/node-detail', {
        node_id: nodeId,
        include_snapshot: true,
      })
      setDetailById((m) => ({ ...m, [nodeId]: res }))
    } catch (e) {
      setDetailErr(e instanceof ApiError ? e.message : 'Detail request failed')
    } finally {
      setDetailBusy(null)
    }
  }, [])

  const onConnectForgeLlm = useCallback(
    async (nodeId: string, openaiBaseUrl?: string, forgeBearer?: string) => {
      setConnectBusy(nodeId)
      setConnectMsg(null)
      try {
        const body: Record<string, unknown> = { fleet_node_id: nodeId }
        if (openaiBaseUrl?.trim()) body.openai_base_url = openaiBaseUrl.trim()
        if (forgeBearer?.trim()) body.bearer_token = forgeBearer.trim()
        const res = await apiPostJson<Record<string, unknown>>('/api/fleet/connect-forge-llm', body)
        if (res.ok !== true) {
          const er = typeof res.error === 'string' ? res.error : 'connect_failed'
          setConnectMsg(`${er}${res.detail ? ` · ${JSON.stringify(res.detail).slice(0, 200)}` : ''}`)
          return
        }
        if (res.unchanged) {
          setConnectMsg('LLM gateway URL already matches this Fleet host.')
        } else {
          setConnectMsg('OpenAI-compatible base URL saved. Opening LLM settings.')
          navigate('/settings/llm')
        }
      } catch (e) {
        setConnectMsg(e instanceof ApiError ? e.message : 'Connect failed')
      } finally {
        setConnectBusy(null)
      }
    },
    [navigate],
  )

  const addRow = useCallback(() => {
    const nid = newNodeId()
    setNodes((prev) => [
      ...prev,
      {
        id: nid,
        base_url: '',
        enabled: true,
        priority: (prev[prev.length - 1]?.priority ?? 100) + 10,
        max_cpu_percent: null,
        max_memory_percent: null,
        bearer_token_configured: false,
      },
    ])
    setActiveHostTabId(nid)
  }, [])

  const removeRow = useCallback((id: string) => {
    setNodes((prev) => (prev.length <= 1 ? prev : prev.filter((r) => r.id !== id)))
    setBearerDrafts((d) => {
      const next = { ...d }
      delete next[id]
      return next
    })
    setClearedBearerIds((c) => {
      const next = { ...c }
      delete next[id]
      return next
    })
    setDetailById((m) => {
      const next = { ...m }
      delete next[id]
      return next
    })
    if (expandedId === id) setExpandedId(null)
  }, [expandedId])

  const probeRows = useMemo(() => {
    const raw = probe?.nodes
    if (!Array.isArray(raw)) return [] as ProbeNodeRow[]
    return raw as ProbeNodeRow[]
  }, [probe])

  const rollup = useMemo(() => {
    const r = probe?.rollup as RollupPayload | undefined
    return r && typeof r === 'object' ? r : null
  }, [probe])

  /** Fleet runner subprocess could not exec ``docker`` (systemd --user often ships a tiny PATH). */
  const testFleetDockerMissingFromPath = useMemo(() => {
    if (!tfResult || tfResult.ok !== true) return false
    const samples = tfResult.samples as unknown[] | undefined
    if (!Array.isArray(samples)) return false
    return samples.some((row) => {
      const e = String((row as Record<string, unknown>).stderr_preview || '')
      return e.includes("No such file or directory: 'docker'") || /\[Errno 2\][^\n]*docker/i.test(e)
    })
  }, [tfResult])

  const resolvedHostTabId = useMemo(() => {
    if (!nodes.length) return null
    if (activeHostTabId && nodes.some((n) => n.id === activeHostTabId)) return activeHostTabId
    return nodes[0].id
  }, [nodes, activeHostTabId])

  const activeHostNode = useMemo(
    () => (resolvedHostTabId ? nodes.find((x) => x.id === resolvedHostTabId) ?? null : null),
    [nodes, resolvedHostTabId],
  )

  const fleetHostPanelId = `${hForm}-fleet-host-panel`

  return (
    <>
      <style>{`
        .le-fleet-status { font-size: 0.75rem; font-weight: 600; padding: 0.15rem 0.45rem; border-radius: 4px; display: inline-block; }
        .le-fleet-status--ok { background: color-mix(in srgb, #0a6 18%, transparent); color: #bfe8d4; }
        .le-fleet-status--warn { background: color-mix(in srgb, #c90 20%, transparent); color: #f5e6b0; }
        .le-fleet-status--token { background: color-mix(in srgb, #08c 18%, transparent); color: #c8e8ff; }
        .le-fleet-status--off { background: color-mix(in srgb, #888 16%, transparent); color: #ccc; }
        .le-fleet-rollup { margin: 0.75rem 0 1rem; padding: 0.65rem 0.85rem; border-radius: 8px; border: 1px solid var(--le-border, rgba(255,255,255,0.12)); background: color-mix(in srgb, var(--le-panel, #1a1a1f) 92%, transparent); }
        .le-fleet-rollup__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr)); gap: 0.35rem 0.75rem; font-size: 0.85rem; margin-top: 0.35rem; }
        .le-gpu-chip { display: inline-flex; align-items: center; gap: 0.25rem; margin-right: 0.35rem; font-size: 0.72rem; padding: 0.1rem 0.35rem; border-radius: 4px; border: 1px solid var(--le-border, rgba(255,255,255,0.15)); }
        .le-fleet-host-tabs { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 0.15rem; margin: 1rem 0 0.65rem; padding: 0 0.15rem; border-bottom: 1px solid var(--le-border-muted, rgba(148, 163, 184, 0.22)); }
        .le-fleet-host-tabs__cluster { display: inline-flex; align-items: stretch; margin-bottom: -1px; }
        .le-fleet-host-tabs__tab {
          display: inline-flex; align-items: center; gap: 0.35rem;
          border: 1px solid transparent; border-bottom: none;
          border-radius: 6px 6px 0 0;
          background: color-mix(in srgb, var(--le-panel, #1a1a1f) 88%, transparent);
          color: var(--le-fg-muted, #cbd5e1);
          padding: 0.4rem 0.65rem 0.45rem; font-size: 0.86rem; font-weight: 600; cursor: pointer;
        }
        .le-fleet-host-tabs__tab:hover { border-color: var(--le-border-muted, rgba(148, 163, 184, 0.35)); color: var(--le-fg, #f1f5f9); }
        .le-fleet-host-tabs__tab--active {
          border-color: var(--le-border-muted, rgba(148, 163, 184, 0.35));
          border-bottom-color: var(--le-panel, #1a1a1f);
          color: var(--le-fg, #f1f5f9);
          background: var(--le-panel, #1a1a1f);
        }
        .le-fleet-host-tabs__dot { width: 0.45rem; height: 0.45rem; border-radius: 999px; flex-shrink: 0; opacity: 0.85; }
        .le-fleet-host-tabs__dot--ok { background: #16a34a; }
        .le-fleet-host-tabs__dot--warn { background: #ca8a04; }
        .le-fleet-host-tabs__dot--token { background: #0284c7; }
        .le-fleet-host-tabs__dot--off { background: #737373; }
        .le-fleet-host-tabs__close {
          border: 1px solid transparent; border-bottom: none; border-left: 1px solid var(--le-border-muted, rgba(148, 163, 184, 0.18));
          border-radius: 0 6px 0 0;
          background: color-mix(in srgb, var(--le-panel, #1a1a1f) 88%, transparent);
          color: var(--le-fg-muted, #94a3b8); padding: 0 0.4rem; font-size: 1rem; line-height: 1; cursor: pointer;
        }
        .le-fleet-host-tabs__close:hover { color: var(--le-danger, #f87171); }
        .le-fleet-host-tabs__cluster--active .le-fleet-host-tabs__close { background: var(--le-panel, #1a1a1f); border-bottom-color: var(--le-panel, #1a1a1f); }
        .le-fleet-host-tabs__add {
          border: 1px dashed var(--le-border-muted, rgba(148, 163, 184, 0.35));
          border-bottom: none; border-radius: 6px 6px 0 0;
          background: transparent; color: var(--le-fg-muted, #94a3b8);
          padding: 0.4rem 0.65rem 0.45rem; font-size: 1.05rem; font-weight: 600; line-height: 1; cursor: pointer; margin-bottom: -1px;
        }
        .le-fleet-host-tabs__add:hover { color: var(--le-fg, #f1f5f9); border-color: var(--le-cyan, #06b6d4); }
        .le-fleet-host-tab-panel {
          border: 1px solid var(--le-border-muted, rgba(148, 163, 184, 0.22));
          border-top: none;
          border-radius: 0 0 8px 8px;
          padding: 1rem 1rem 0.85rem;
          background: var(--le-panel, #1a1a1f);
        }
      `}</style>
      <PageHeader
        title={STUDIO_VOCAB.fleetPreferences}
        purpose="Multiple Fleet servers: lower priority number is tried first; disabled or overloaded nodes are skipped when another healthy node is available."
        subtitle={ROUTE_SUBTITLE.fleetPreferencesUtility}
        secondaryMenuItems={[
          { key: 'llm', to: '/settings/llm', label: STUDIO_VOCAB.llmPreferences },
          { key: 'agent', to: '/settings/agent-runtime', label: STUDIO_VOCAB.agentRuntimeInspect },
        ]}
      />

      {probe && rollup ? (
        <div className="le-fleet-rollup" aria-live="polite">
          <strong>Connected fleet summary</strong>
          <span className="le-muted" style={{ marginLeft: '0.5rem', fontWeight: 400, fontSize: '0.8rem' }}>
            (weighted by 1 ÷ priority; refresh via &quot;Refresh status&quot;)
          </span>
          <div className="le-fleet-rollup__grid">
            <span>
              Nodes: <strong>{rollup.connected_count ?? 0}</strong> connected /{' '}
              <strong>{rollup.configured_count ?? 0}</strong> configured
            </span>
            {rollup.cpu_usage_pct != null ? (
              <span>
                CPU % (w.avg): <strong>{rollup.cpu_usage_pct}</strong>
              </span>
            ) : null}
            {rollup.memory_used_pct != null ? (
              <span>
                RAM % (w.avg): <strong>{rollup.memory_used_pct}</strong>
              </span>
            ) : null}
            {rollup.loadavg_1m != null ? (
              <span>
                Load 1m (w.avg): <strong>{rollup.loadavg_1m}</strong>
              </span>
            ) : null}
            {rollup.cpus_logical_sum != null ? (
              <span>
                Logical cores (sum): <strong>{rollup.cpus_logical_sum}</strong>
              </span>
            ) : null}
            {rollup.avg_ghz != null ? (
              <span>
                Avg GHz (w.avg): <strong>{rollup.avg_ghz}</strong>
              </span>
            ) : null}
            {rollup.memory_total_gb_sum != null ? (
              <span>
                RAM total GB (sum): <strong>{rollup.memory_total_gb_sum}</strong>
              </span>
            ) : null}
          </div>
        </div>
      ) : null}

      {err ? <StatePanel variant="error" title="Fleet settings" description={err} /> : null}
      {saveOk ? <p className="forge-support">{saveOk}</p> : null}
      {connectMsg ? <p className="forge-support">{connectMsg}</p> : null}

      {loading ? (
        <StatePanel variant="loading" title="Loading" description="Reading Fleet settings from the workspace server." />
      ) : (
        <>
          <section className="le-panel" style={{ marginBottom: '1.25rem' }} aria-labelledby={hDiscover}>
            <h2 id={hDiscover} className="le-panel__title">
              LAN discovery (ports 18765 / 18766 / 18767)
            </h2>
            <p className="le-muted" style={{ marginTop: 0 }}>
              Scan runs on the Lenses workspace server. Ranges follow each interface&apos;s IPv4 address and prefix (same
              as <code className="le-code">ip -json addr</code>). Each candidate is probed on{' '}
              <strong>18765</strong>, <strong>18766</strong>, and <strong>18767</strong> (Caddy often exposes Fleet on{' '}
              <code className="le-code">*:18767</code> while Fleet itself stays on loopback). Detection uses{' '}
              <code className="le-code">GET /v1/health</code> (<code className="le-code">service: forge-fleet</code>).
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.65rem', alignItems: 'flex-end', marginTop: '0.75rem' }}>
              <label className="le-muted" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <span>Mode</span>
                <select
                  className="le-input"
                  value={discMode}
                  onChange={(e) => setDiscMode(e.target.value === 'subnet' ? 'subnet' : 'quick')}
                >
                  <option value="quick">Quick (from local IF prefixes)</option>
                  <option value="subnet">Full subnet (per interface prefix)</option>
                </select>
              </label>
              <label className="le-muted" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', minWidth: '12rem' }}>
                <span>Shared discovery token (optional)</span>
                <input
                  className="le-input"
                  type="password"
                  autoComplete="off"
                  placeholder="Bearer for all hosts"
                  value={discGlobalTok}
                  onChange={(e) => setDiscGlobalTok(e.target.value)}
                />
              </label>
              <label className="le-muted" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', flex: '1 1 14rem' }}>
                <span>Extra IPv4 hosts (optional, space/comma)</span>
                <input
                  className="le-input le-mono"
                  autoComplete="off"
                  placeholder="192.168.1.40 192.168.1.41"
                  value={discExtraHosts}
                  onChange={(e) => setDiscExtraHosts(e.target.value)}
                />
              </label>
              <button type="button" className="le-btn le-btn--primary" disabled={discBusy} onClick={() => void onDiscover()}>
                {discBusy ? 'Scanning…' : 'Scan LAN'}
              </button>
            </div>
            {discErr ? <p className="le-muted" style={{ color: 'var(--le-danger, #a40000)' }}>{discErr}</p> : null}
            {discRes?.candidates && Array.isArray(discRes.candidates) ? (
              <>
                <p className="le-muted" style={{ marginTop: '0.75rem' }}>
                  Scanned {(discRes.targets_scanned as number) ?? 0} targets · Fleet found:{' '}
                  <strong>{(discRes.fleet_found as number) ?? 0}</strong>
                </p>
                {Array.isArray(discRes.local_networks) && (discRes.local_networks as Record<string, unknown>[]).length ? (
                  <ul className="le-muted" style={{ marginTop: '0.35rem', fontSize: '0.82rem', paddingLeft: '1.2rem' }}>
                    {(discRes.local_networks as Record<string, unknown>[]).map((nw, i) => (
                      <li key={`${String(nw.interface)}-${String(nw.network)}-${i}`}>
                        <span className="le-mono">{String(nw.interface || '')}</span> — {String(nw.address || '')}/
                        {String(nw.prefixlen ?? '')} (<span className="le-mono">{String(nw.network || '')}</span>
                        {nw.source ? ` · ${String(nw.source)}` : ''})
                      </li>
                    ))}
                  </ul>
                ) : null}
                <div className="le-table-wrap" style={{ overflowX: 'auto', marginTop: '0.5rem' }}>
                  <table className="le-table" aria-label="Discovery results">
                    <thead>
                      <tr>
                        <th scope="col">Add</th>
                        <th scope="col">Fleet</th>
                        <th scope="col">Base URL</th>
                        <th scope="col">Version</th>
                        <th scope="col">Token (row)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(discRes.candidates as DiscoveryCandidate[])
                        .filter((c) => c.is_fleet || c.reachable)
                        .map((c) => {
                          const key = `${c.host}:${c.port}`
                          return (
                            <tr key={key}>
                              <td>
                                {c.is_fleet ? (
                                  <input
                                    type="checkbox"
                                    checked={Boolean(discPick[key])}
                                    onChange={() => toggleDiscPick(key)}
                                    aria-label={`Select ${c.base_url}`}
                                  />
                                ) : null}
                              </td>
                              <td>{c.is_fleet ? 'yes' : '—'}</td>
                              <td className="le-mono">{c.base_url}</td>
                              <td className="le-mono" style={{ fontSize: '0.8rem' }}>
                                {formatSemver(c.version ?? undefined) || (c.auth_required ? '(needs token)' : '—')}
                              </td>
                              <td>
                                <input
                                  className="le-input"
                                  type="password"
                                  autoComplete="off"
                                  placeholder="Override shared token"
                                  value={discRowTok[key] ?? ''}
                                  onChange={(e) => setDiscRowTok((m) => ({ ...m, [key]: e.target.value }))}
                                />
                              </td>
                            </tr>
                          )
                        })}
                    </tbody>
                  </table>
                </div>
                <button type="button" className="le-btn" style={{ marginTop: '0.65rem' }} onClick={addSelectedDiscovery}>
                  Add selected to table
                </button>
              </>
            ) : null}
          </section>

          <section className="le-panel" aria-labelledby={hForm}>
            <h2 id={hForm} className="le-panel__title">
              Fleet servers
            </h2>
            <p className="le-muted" style={{ marginTop: 0 }}>
              Jobs are sent to the first <strong>enabled</strong> server that responds healthy and is within optional{' '}
              <strong>max CPU %</strong> and <strong>max memory %</strong> (from Fleet <code className="le-code">/v1/health</code>
              ). Set ceilings empty to ignore that metric.
            </p>
            <p className="le-muted">
              <code className="le-code">LENSES_FLEET_URL</code> / <code className="le-code">LENSES_FLEET_TOKEN</code> override
              this list with a single node (priority 0).
            </p>
            <p className="le-muted" style={{ marginTop: '0.5rem' }}>
              Each <strong>tab</strong> is one Fleet base URL (and optional bearer). Use <strong>+</strong> like a browser tab to add
              another host; later the same pattern can host other service UIs that talk through the API.
            </p>

            {activeHostNode ? (
              <>
                <div className="le-fleet-host-tabs" role="tablist" aria-label="Forge Fleet hosts">
                  {nodes.map((n) => {
                    const pr = probeRows.find((r) => r.id === n.id && !r.skipped)
                    const st = pr?.studio_status
                    const selected = resolvedHostTabId === n.id
                    const tabId = `${hForm}-tab-${n.id}`
                    return (
                      <div
                        key={n.id}
                        className={`le-fleet-host-tabs__cluster${selected ? ' le-fleet-host-tabs__cluster--active' : ''}`}
                      >
                        <button
                          type="button"
                          role="tab"
                          aria-selected={selected}
                          id={tabId}
                          aria-controls={fleetHostPanelId}
                          className={`le-fleet-host-tabs__tab${selected ? ' le-fleet-host-tabs__tab--active' : ''}`}
                          onClick={() => setActiveHostTabId(n.id)}
                        >
                          <span
                            className={fleetHostTabDotClass(st)}
                            style={pr ? undefined : { opacity: 0.22 }}
                            title={pr ? `${statusLabel(st)}${pr?.health_anonymous?.http_status != null ? ` · HTTP ${pr.health_anonymous.http_status}` : ''}` : 'Refresh status to probe'}
                            aria-hidden
                          />
                          {fleetHostTabLabel(n)}
                        </button>
                        {nodes.length > 1 ? (
                          <button
                            type="button"
                            className="le-fleet-host-tabs__close"
                            aria-label={`Close tab ${fleetHostTabLabel(n)}`}
                            onClick={() => removeRow(n.id)}
                          >
                            ×
                          </button>
                        ) : null}
                      </div>
                    )
                  })}
                  <button
                    type="button"
                    className="le-fleet-host-tabs__add"
                    aria-label="Add Fleet host tab"
                    title="New host tab"
                    onClick={addRow}
                  >
                    +
                  </button>
                </div>

                <div
                  role="tabpanel"
                  id={fleetHostPanelId}
                  aria-labelledby={`${hForm}-tab-${activeHostNode.id}`}
                  className="le-fleet-host-tab-panel"
                >
                  {(() => {
                    const n = activeHostNode
                    const pr = probeRows.find((r) => r.id === n.id && !r.skipped)
                    const st = pr?.studio_status
                    const open = expandedId === n.id
                    const det = detailById[n.id]
                    const snapWrap = det?.snapshot as { ok?: boolean; snapshot?: Record<string, unknown> } | undefined
                    const snapBody =
                      snapWrap?.ok === true && snapWrap.snapshot && typeof snapWrap.snapshot === 'object'
                        ? snapWrap.snapshot
                        : null
                    const services =
                      snapBody &&
                      typeof snapBody.meta === 'object' &&
                      (snapBody.meta as Record<string, unknown>).integrations
                        ? (((snapBody.meta as Record<string, unknown>).integrations as Record<string, unknown>)
                            .forge_llm_services as unknown[])
                        : null
                    const gpus = gpuChipsFromSnapshot(snapBody)
                    return (
                      <Fragment key={n.id}>
                        <div
                          style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fill, minmax(12rem, 1fr))',
                            gap: '0.75rem 1rem',
                            alignItems: 'start',
                          }}
                        >
                          <label className="le-muted" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <span>Status</span>
                            <span className={statusClass(st)} title={String(pr?.health_anonymous?.http_status ?? '')}>
                              {pr ? statusLabel(st) : '—'}
                            </span>
                            {pr?.version && formatSemver(pr.version as Record<string, unknown>) ? (
                              <span className="le-muted" style={{ fontSize: '0.72rem' }}>
                                {formatSemver(pr.version as Record<string, unknown>)}
                              </span>
                            ) : null}
                          </label>
                          <label className="le-muted" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <span>Enabled</span>
                            <input
                              type="checkbox"
                              checked={n.enabled !== false}
                              aria-label={`Enable ${n.base_url || 'server'}`}
                              style={{ width: '1.1rem', height: '1.1rem', marginTop: '0.15rem' }}
                              onChange={(e) =>
                                setNodes((prev) => prev.map((r) => (r.id === n.id ? { ...r, enabled: e.target.checked } : r)))
                              }
                            />
                          </label>
                          <label className="le-muted" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <span>Priority (lower first)</span>
                            <input
                              className="le-input"
                              type="number"
                              inputMode="numeric"
                              aria-label="Priority (lower = tried first)"
                              value={n.priority ?? 100}
                              onChange={(e) =>
                                setNodes((prev) =>
                                  prev.map((r) => (r.id === n.id ? { ...r, priority: Number(e.target.value) } : r)),
                                )
                              }
                            />
                          </label>
                          <label className="le-muted" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', gridColumn: 'span 2' }}>
                            <span>Base URL</span>
                            <input
                              className="le-input le-mono"
                              type="url"
                              autoComplete="off"
                              placeholder="http://127.0.0.1:18765"
                              value={n.base_url}
                              onChange={(e) =>
                                setNodes((prev) => prev.map((r) => (r.id === n.id ? { ...r, base_url: e.target.value } : r)))
                              }
                            />
                          </label>
                          <label className="le-muted" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', gridColumn: 'span 2' }}>
                            <span>Bearer token</span>
                            <input
                              className="le-input"
                              type="password"
                              autoComplete="off"
                              placeholder={n.bearer_token_configured ? 'Leave blank to keep' : 'Optional'}
                              value={bearerDrafts[n.id] ?? ''}
                              onChange={(e) => {
                                setClearedBearerIds((c) => {
                                  const next = { ...c }
                                  delete next[n.id]
                                  return next
                                })
                                setBearerDrafts((d) => ({ ...d, [n.id]: e.target.value }))
                              }}
                            />
                            {n.bearer_token_configured ? (
                              <button
                                type="button"
                                className="le-btn le-btn--ghost le-btn--small"
                                style={{ alignSelf: 'flex-start', marginTop: '0.15rem' }}
                                onClick={() => {
                                  setBearerDrafts((d) => ({ ...d, [n.id]: '' }))
                                  setClearedBearerIds((c) => ({ ...c, [n.id]: true }))
                                }}
                              >
                                Clear stored token
                              </button>
                            ) : null}
                          </label>
                          <label className="le-muted" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <span>Max CPU %</span>
                            <input
                              className="le-input"
                              type="number"
                              inputMode="decimal"
                              placeholder="—"
                              value={n.max_cpu_percent ?? ''}
                              onChange={(e) => {
                                const v = e.target.value
                                setNodes((prev) =>
                                  prev.map((r) =>
                                    r.id === n.id
                                      ? { ...r, max_cpu_percent: v === '' ? null : Math.min(100, Math.max(0, Number(v))) }
                                      : r,
                                  ),
                                )
                              }}
                            />
                          </label>
                          <label className="le-muted" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <span>Max memory %</span>
                            <input
                              className="le-input"
                              type="number"
                              inputMode="decimal"
                              placeholder="—"
                              value={n.max_memory_percent ?? ''}
                              onChange={(e) => {
                                const v = e.target.value
                                setNodes((prev) =>
                                  prev.map((r) =>
                                    r.id === n.id
                                      ? { ...r, max_memory_percent: v === '' ? null : Math.min(100, Math.max(0, Number(v))) }
                                      : r,
                                  ),
                                )
                              }}
                            />
                          </label>
                          <div className="le-muted" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', justifyContent: 'flex-end' }}>
                            <span>Host detail</span>
                            <button
                              type="button"
                              className="le-btn le-btn--ghost le-btn--small"
                              style={{ alignSelf: 'flex-start' }}
                              disabled={detailBusy === n.id}
                              onClick={() => {
                                if (open) {
                                  setExpandedId(null)
                                } else {
                                  setExpandedId(n.id)
                                  void fetchNodeDetail(n.id)
                                }
                              }}
                            >
                              {open ? 'Hide snapshot' : 'Load snapshot'}
                            </button>
                          </div>
                        </div>
                        {open ? (
                          <div
                            style={{
                              marginTop: '0.85rem',
                              padding: '0.75rem',
                              borderRadius: '6px',
                              background: 'color-mix(in srgb, var(--le-panel) 85%, transparent)',
                            }}
                          >
                            {detailBusy === n.id ? <p className="le-muted">Loading snapshot…</p> : null}
                            {detailErr && open ? <p className="le-muted">{detailErr}</p> : null}
                            {det?.studio_status && det.studio_status !== 'connected' ? (
                              <p className="le-muted">Connect a saved bearer token and save, then use Load for host load / GPU / services.</p>
                            ) : null}
                            {gpus.length ? (
                              <div style={{ margin: '0.35rem 0' }}>
                                <span className="le-muted" style={{ fontSize: '0.8rem' }}>
                                  GPU:{' '}
                                </span>
                                {gpus.map((g) => (
                                  <span key={g} className="le-gpu-chip" title={g}>
                                    {g}
                                  </span>
                                ))}
                              </div>
                            ) : null}
                            {Array.isArray(services) && services.length ? (
                              <div style={{ margin: '0.35rem 0' }}>
                                <div className="le-muted" style={{ fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                                  forge-llm services (from Fleet)
                                </div>
                                <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.85rem' }}>
                                  {services.map((s, i) => {
                                    const row = s as Record<string, unknown>
                                    const sid = String(row.id ?? i)
                                    const label = String(row.label ?? row.id ?? 'service')
                                    const run = `${row.services_running ?? '?'}/${row.services_total ?? '?'}`
                                    return (
                                      <li key={sid} style={{ marginBottom: '0.35rem' }}>
                                        <strong>{label}</strong> — running {run}
                                        <button
                                          type="button"
                                          className="le-btn le-btn--ghost le-btn--small"
                                          style={{ marginLeft: '0.5rem' }}
                                          disabled={connectBusy === n.id}
                                          onClick={() => void onConnectForgeLlm(n.id)}
                                        >
                                          Connect to LLM settings
                                        </button>
                                      </li>
                                    )
                                  })}
                                </ul>
                              </div>
                            ) : null}
                            {det && open && snapBody ? (
                              <details style={{ marginTop: '0.5rem' }}>
                                <summary className="le-muted" style={{ cursor: 'pointer' }}>
                                  Raw snapshot (JSON)
                                </summary>
                                <pre className="le-pre le-muted" style={{ marginTop: '0.35rem', maxHeight: '14rem', overflow: 'auto' }}>
                                  {JSON.stringify(det, null, 2)}
                                </pre>
                              </details>
                            ) : null}
                          </div>
                        ) : null}
                      </Fragment>
                    )
                  })()}
                </div>
              </>
            ) : null}

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
              <button type="button" className="le-btn le-btn--primary" disabled={saving} onClick={() => void onSave()}>
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button type="button" className="le-btn" onClick={() => void onProbe()}>
                Refresh status
              </button>
              <button type="button" className="le-btn le-btn--ghost" onClick={() => void load()}>
                Reload
              </button>
            </div>
            {probeErr ? <p className="le-muted">{probeErr}</p> : null}
            {probe ? (
              <details style={{ marginTop: '0.75rem' }}>
                <summary className="le-muted" style={{ cursor: 'pointer' }}>
                  Full probe JSON
                </summary>
                <pre className="le-pre le-muted" style={{ marginTop: '0.5rem', maxHeight: '18rem', overflow: 'auto' }}>
                  {JSON.stringify(probe, null, 2)}
                </pre>
              </details>
            ) : null}
          </section>

          <section className="le-panel" style={{ marginTop: '1.25rem' }} aria-labelledby={hTestFleet}>
            <h2 id={hTestFleet} className="le-panel__title">
              Test Fleet (host CPU)
            </h2>
            <p className="le-muted" style={{ marginTop: 0 }}>
              Enqueue <strong>five</strong> short Docker jobs (class <code className="le-code">host_cpu_probe</code>) that mount the host{' '}
              <code className="le-code">/proc</code> tree and print one JSON line with approximate <strong>host CPU busy %</strong> per job.
              The Lenses server picks an eligible Fleet node and calls Fleet with the stored bearer (never from this browser). The Fleet host must run Docker and allow bind-mounting host <code className="le-code">/proc</code> (rootless setups sometimes block this).
            </p>
            <p className="le-muted">
              To surface the rolled-up summary in <strong>Lenses Studio</strong> (Attention bell), run Fleet with{' '}
              <code className="le-code">FLEET_LENSES_WORKSPACE_ROOT</code> set to the same absolute path Lenses uses as its workspace root; Fleet writes{' '}
              <code className="le-code">.lenses-local/fleet-test-attention.json</code> when the batch finalizer runs. For the user install, put that line in{' '}
              <code className="le-code">~/.config/forge-fleet/forge-fleet.env</code> and run{' '}
              <code className="le-code">systemctl --user restart forge-fleet.service</code>.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
              <button type="button" className="le-btn le-btn--primary" disabled={tfBusy} onClick={() => void onTestFleet()}>
                {tfBusy ? 'Running…' : 'Test Fleet (5 probes)'}
              </button>
            </div>
            {tfErr ? <p className="le-muted" style={{ color: 'var(--le-danger, #a40000)' }}>{tfErr}</p> : null}
            {testFleetDockerMissingFromPath ? (
              <p className="le-muted" style={{ marginTop: '0.75rem', color: 'var(--le-danger, #a40000)' }}>
                The Fleet host could not run the <code className="le-code">docker</code> CLI (not found for the{' '}
                <code className="le-code">forge-fleet</code> process — common with <code className="le-code">systemd --user</code> or Docker installed via{' '}
                <strong>Snap</strong>). Update Forge Fleet and restart the service: newer releases resolve <code className="le-code">docker</code> using a
                widened search path and optional <code className="le-code">FLEET_DOCKER_BIN</code>. Until then: re-run{' '}
                <code className="le-code">./update-user.sh</code> from your forge-fleet checkout (unit <code className="le-code">PATH</code> includes{' '}
                <code className="le-code">/snap/bin</code>), or set <code className="le-code">FLEET_DOCKER_BIN=/absolute/path/to/docker</code> in{' '}
                <code className="le-code">~/.config/forge-fleet/forge-fleet.env</code> and{' '}
                <code className="le-code">systemctl --user restart forge-fleet.service</code>.
              </p>
            ) : null}
            {tfResult?.ok === true && tfResult.lenses_attention_expected !== true ? (
              <p className="le-muted" style={{ marginTop: '0.75rem' }}>
                Fleet did not report Attention publishing for this batch. If you want the bell item, set{' '}
                <code className="le-code">FLEET_LENSES_WORKSPACE_ROOT</code> on the Fleet host to this workspace root and retry.
              </p>
            ) : null}
            {tfResult ? (
              <pre className="le-pre le-muted" style={{ marginTop: '1rem', maxHeight: '18rem', overflow: 'auto' }}>
                {JSON.stringify(tfResult, null, 2)}
              </pre>
            ) : null}
          </section>
        </>
      )}
    </>
  )
}
