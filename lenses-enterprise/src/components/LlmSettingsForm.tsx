import type { CSSProperties, Dispatch, SetStateAction } from 'react'
import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, apiGetJson, apiPostJson } from '../api/http'
import { resolveUxFailure } from '../lib/uxPageState'
import { CustomProviderDrawer } from './ai-setup/CustomProviderDrawer'
import { attentionLineFromRecentUsage } from './ai-setup/llmUsageAttention'
import { ModelIdComboboxField } from './ai-setup/ModelIdComboboxField'
import { OllamaLocalPanel, type OllamaStatusPayload } from './ai-setup/OllamaLocalPanel'
import { mergeModelOptionIds, suggestedModelsForTask } from './ai-setup/taskModelHints'
import { TaskRouteModelStackField } from './ai-setup/TaskRouteModelStackField'
import type { AiSetupSourceLayoutV2, AiSetupTileDensity, CloudCardId } from './ai-setup/aiSetupSourceLayout'
import {
  aiSetupCloudCardStripeCss,
  aiSetupSectionStripeCss,
  loadAiSetupSourceLayout,
  saveAiSetupSourceLayout,
} from './ai-setup/aiSetupSourceLayout'
import { CloudMoreProvidersCard, CloudVendorCard } from './ai-setup/CloudSwimlaneBlocks'
import {
  AiSetupSectionChrome,
  AiSetupSourcePriorityRail,
  AiSetupTileDensityPictograms,
} from './ai-setup/AiSetupSourceLayoutControls'
import { usedForLabels } from './ai-setup/usedFor'
import { useLlmProviderModelCatalog } from './ai-setup/useLlmProviderModelCatalog'
import { LlmTryOutChatModal } from './LlmTryOutChatModal'

export type KeyInfo = {
  set?: boolean
  preview?: string
  /** True if non-empty key in llm-settings.json */
  from_file?: boolean
  /** True if matching env var is set (OPENAI_API_KEY, etc.) */
  from_env?: boolean
  /** Which env var supplies the key when from_env (e.g. OPENAI_API_KEY) */
  env_hint?: string
}

export type TaskRouteEntry = {
  provider?: string
  model?: string
  /** Priority-ordered model ids; only the first is used by routing until failover exists. */
  model_stack?: string[]
  fallback_provider?: string
  fallback_model?: string
  /** ``local_only`` | ``prefer_local`` | ``cloud_allowed`` */
  privacy?: string
}

/** GET /api/llm/settings — ``openai_compatible_endpoint`` (sanitized base URL hint). */
export type EndpointInfo = {
  set?: boolean
  from_file?: boolean
  from_env?: boolean
  preview?: string
  env_hint?: string
}

export type SettingsPayload = {
  version?: number
  provider?: string
  routing_mode?: string
  advanced_ui?: boolean
  auto_model?: boolean
  adaptive_autoselection?: boolean
  tier?: string
  refine_cheaper_steps?: number
  keys?: Record<string, string | KeyInfo>
  main_models?: Record<string, string>
  pools?: Record<string, string[]>
  classifier_models?: Record<string, string>
  task_routes?: Record<string, TaskRouteEntry>
  fallback_route?: TaskRouteEntry
  openai_compatible_endpoint?: EndpointInfo
  /** POST only — persisted base URL (GET omits raw value; use ``openai_compatible_endpoint``). */
  openai_compatible_base_url?: string
  /** UI metadata for the single custom gateway slot (server-side routing is OpenAI-compatible today). */
  custom_provider?: {
    display_name?: string
    transport?: string
    auth?: string
  }
  /** Persisted; when false and no sources connected, Studio may show the first-run wizard. */
  first_run_wizard_dismissed?: boolean
}

/** Masked key shape from GET /api/llm/settings; matches server `sanitize_for_get`. */
const DEFAULT_LLM_SETTINGS: SettingsPayload = {
  version: 2,
  provider: 'openai',
  routing_mode: 'single',
  advanced_ui: false,
  auto_model: false,
  adaptive_autoselection: false,
  tier: 'MED',
  refine_cheaper_steps: 2,
  keys: {
    anthropic: { set: false, from_file: false, from_env: false, preview: '' },
    openai: { set: false, from_file: false, from_env: false, preview: '' },
    gemini: { set: false, from_file: false, from_env: false, preview: '' },
    openai_compatible: { set: false, from_file: false, from_env: false, preview: '' },
  },
  main_models: {},
  pools: {},
  classifier_models: { openai: '', gemini: '' },
  task_routes: {},
  fallback_route: { provider: '', model: '' },
  openai_compatible_endpoint: { set: false, from_file: false, from_env: false, preview: '' },
  custom_provider: { display_name: '', transport: 'openai_compatible', auth: 'bearer' },
  first_run_wizard_dismissed: false,
}

function mergeLoadedSettings(raw: unknown): SettingsPayload {
  if (!raw || typeof raw !== 'object') return { ...DEFAULT_LLM_SETTINGS }
  const r = raw as Record<string, unknown>
  const keysIn = r.keys
  const keysDefault = DEFAULT_LLM_SETTINGS.keys as Record<string, KeyInfo>
  const keysOut =
    keysIn && typeof keysIn === 'object'
      ? { ...keysDefault, ...(keysIn as Record<string, KeyInfo>) }
      : { ...keysDefault }
  const clfIn = r.classifier_models
  const clfDef = DEFAULT_LLM_SETTINGS.classifier_models as Record<string, string>
  const clfOut =
    clfIn && typeof clfIn === 'object'
      ? { ...clfDef, ...(clfIn as Record<string, string>) }
      : { ...clfDef }
  const trIn = r.task_routes
  const taskRoutesOut: Record<string, TaskRouteEntry> = {}
  if (trIn && typeof trIn === 'object') {
    for (const [k, v] of Object.entries(trIn as Record<string, unknown>)) {
      if (v && typeof v === 'object') {
        const o = v as Record<string, unknown>
        const pr = String(o.privacy ?? '').trim().toLowerCase()
        const stackRaw = o.model_stack
        let model_stack: string[] = []
        if (Array.isArray(stackRaw)) {
          model_stack = stackRaw.map((x) => String(x ?? '').trim()).filter(Boolean)
        }
        const modelLegacy = String(o.model ?? '').trim()
        if (model_stack.length === 0 && modelLegacy) model_stack = [modelLegacy]
        const modelOut = model_stack[0] ?? modelLegacy
        taskRoutesOut[k] = {
          provider: String(o.provider ?? ''),
          model: modelOut,
          model_stack,
          fallback_provider: String(o.fallback_provider ?? ''),
          fallback_model: String(o.fallback_model ?? ''),
          privacy:
            pr === 'local_only' || pr === 'prefer_local' || pr === 'cloud_allowed' ? pr : 'cloud_allowed',
        }
      }
    }
  }
  const frIn = r.fallback_route
  let fallbackOut: TaskRouteEntry = { provider: '', model: '' }
  if (frIn && typeof frIn === 'object') {
    const o = frIn as Record<string, unknown>
    fallbackOut = { provider: String(o.provider ?? ''), model: String(o.model ?? '') }
  }
  const rm = typeof r.routing_mode === 'string' ? r.routing_mode : undefined
  const epIn = r.openai_compatible_endpoint
  const endpointDef = DEFAULT_LLM_SETTINGS.openai_compatible_endpoint as EndpointInfo
  const endpointOut: EndpointInfo =
    epIn && typeof epIn === 'object' ? { ...endpointDef, ...(epIn as EndpointInfo) } : { ...endpointDef }
  const cpIn = r.custom_provider
  const cpDef = DEFAULT_LLM_SETTINGS.custom_provider as Record<string, string>
  const cpOut =
    cpIn && typeof cpIn === 'object'
      ? {
          display_name: String((cpIn as Record<string, unknown>).display_name ?? cpDef.display_name ?? ''),
          transport: String((cpIn as Record<string, unknown>).transport ?? cpDef.transport ?? 'openai_compatible'),
          auth: String((cpIn as Record<string, unknown>).auth ?? cpDef.auth ?? 'bearer'),
        }
      : { ...cpDef }
  return {
    ...DEFAULT_LLM_SETTINGS,
    ...r,
    keys: keysOut,
    classifier_models: clfOut,
    task_routes: taskRoutesOut,
    fallback_route: fallbackOut,
    routing_mode: rm ?? inferRoutingModeFromFlags(Boolean(r.advanced_ui), Boolean(r.auto_model)),
    openai_compatible_endpoint: endpointOut,
    custom_provider: cpOut,
    first_run_wizard_dismissed:
      typeof r.first_run_wizard_dismissed === 'boolean'
        ? r.first_run_wizard_dismissed
        : DEFAULT_LLM_SETTINGS.first_run_wizard_dismissed,
  } as SettingsPayload
}

function inferRoutingModeFromFlags(advanced: boolean, auto: boolean): string {
  if (!advanced) return 'single'
  if (auto) return 'smart'
  return 'advanced'
}

function formatDiagnosticTs(iso?: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return iso
  }
}

const TASK_ROWS: Array<{ id: string; label: string }> = [
  { id: 'chat_assistant', label: 'Chat assistant' },
  { id: 'search_knowledge', label: 'Search / knowledge answers' },
  { id: 'plans_generation', label: 'Plans / roadmaps generation' },
  { id: 'site_drafting', label: 'Site / blog drafting' },
  { id: 'code_automation', label: 'Code / automation' },
  { id: 'extraction_classification', label: 'Extraction / classification' },
  { id: 'vision_ocr', label: 'Vision / OCR' },
  { id: 'embeddings_indexing', label: 'Embeddings / indexing' },
]

const TASK_LABEL_BY_ID: Record<string, string> = Object.fromEntries(TASK_ROWS.map((t) => [t.id, t.label]))

const ALL_PROVIDER_IDS = ['anthropic', 'openai', 'gemini', 'ollama', 'openai_compatible'] as const

const PROVIDER_DIAG_LABELS: Record<string, string> = {
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  gemini: 'Google Gemini',
  ollama: 'Ollama (local)',
  openai_compatible: 'Custom gateway',
}

type CloudProviderId = 'openai' | 'anthropic' | 'gemini'
type RevealSecretId = CloudProviderId | 'openai_compatible'

const CLOUD_SOURCES: Array<{ id: CloudProviderId; label: string; outcome: string }> = [
  { id: 'openai', label: 'OpenAI', outcome: 'Hosted GPT models for Chat and copilot.' },
  { id: 'anthropic', label: 'Anthropic', outcome: 'Claude models for Chat and copilot.' },
  { id: 'gemini', label: 'Google', outcome: 'Gemini and Google generative models for Chat and copilot.' },
]

const CUSTOM_SOURCE = {
  id: 'openai_compatible' as const,
  label: 'Custom gateway',
  outcome: 'LM Studio, vLLM, or any OpenAI-compatible server reachable from this Lenses host.',
}

const MIME_CLOUD_CARD = 'application/x-forge-ai-cloud-card'

/** Dark text on amber primary for readability in AI Setup. */
const AI_SETUP_PRIMARY_READABLE: CSSProperties = {
  color: '#141a12',
  fontWeight: 600,
}

function reorderCloudCards(order: CloudCardId[], dragged: CloudCardId, target: CloudCardId): CloudCardId[] {
  if (dragged === target) return order
  const next = [...order]
  const fi = next.indexOf(dragged)
  const ti = next.indexOf(target)
  if (fi < 0 || ti < 0) return order
  next.splice(fi, 1)
  next.splice(ti, 0, dragged)
  return next
}

function moveCloudCard(order: CloudCardId[], id: CloudCardId, dir: -1 | 1): CloudCardId[] {
  const i = order.indexOf(id)
  const j = i + dir
  if (i < 0 || j < 0 || j >= order.length) return order
  const next = [...order]
  const a = next[i]!
  const b = next[j]!
  next[i] = b
  next[j] = a
  return next
}

export type RoutingPreviewRow = {
  task_id: string
  label: string
  provider: string
  model: string
  routing?: string
  routing_mode?: string
  explanation?: string
  privacy?: string
  privacy_warn?: string | null
  fallback_provider?: string | null
  fallback_model?: string | null
}

export type UsageTotals = Record<
  string,
  {
    prompt_tokens?: number
    completion_tokens?: number
    total_tokens?: number
    /** Successful completions with token accounting */
    requests?: number
    /** All chat API attempts (success + failure) */
    attempts?: number
    failures?: number
  }
>

export type UsageSummary = {
  totals: UsageTotals
  last_ok: Record<string, string>
  recent_events: Array<{
    ts: string
    provider: string
    source?: string
    ok?: boolean
    model?: string
    refine?: boolean
    message_chars?: number
    routing_source?: string
    routing_model?: string
    fallback_from?: string | null
    studio_task_id?: string | null
    prompt_tokens?: number
    completion_tokens?: number
    total_tokens?: number
    error?: string | null
    detail?: string | null
  }>
  probe_log?: Array<{
    ts: string
    provider: string
    action?: string
    ok?: boolean
    error?: string | null
    detail?: string | null
  }>
}

export type LlmDiagnosticsPayload = {
  ok?: boolean
  routing_mode?: string
  connected_providers?: number
  connected_provider_ids?: string[]
  providers?: Array<{
    id: string
    connected: boolean
    has_credential: boolean
    last_ok_ts?: string | null
    last_probe?: {
      ts?: string
      action?: string
      ok?: boolean
      detail?: string | null
    } | null
    totals: {
      prompt_tokens?: number
      completion_tokens?: number
      total_tokens?: number
      requests?: number
      attempts?: number
      failures?: number
    }
    recent_failures: Array<{
      ts?: string
      error?: string | null
      detail?: string | null
      model?: string | null
    }>
  }>
  routing_events?: Array<{
    ts?: string
    provider?: string
    ok?: boolean
    model?: string | null
    routing_source?: string | null
    routing_model?: string | null
    fallback_from?: string | null
    studio_task_id?: string | null
    error?: string | null
  }>
  first_run_recommended?: boolean
  next_recommended_step?: string
  cost_note?: string
  usage_path_hint?: string
  settings_path_hint?: string
}

type ProviderProbeState = { loading?: boolean; models?: string[]; error?: string; at?: number }

function svgMiniTokenBar(promptTokens: number, completionTokens: number, w = 260, h = 12) {
  const p = Math.max(0, Math.floor(Number(promptTokens) || 0))
  const c = Math.max(0, Math.floor(Number(completionTokens) || 0))
  const t = p + c || 1
  const pw = (w * p) / t
  const cw = (w * c) / t
  return (
    <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="img" aria-label="Prompt versus completion tokens">
      <rect x="0" y="1" width={pw} height={h - 2} rx="2" fill="var(--le-cyan, #5ec8d4)" opacity="0.9" />
      <rect x={pw} y="1" width={cw} height={h - 2} rx="2" fill="color-mix(in srgb, var(--le-cyan, #5ec8d4) 35%, #889)" opacity="0.85" />
    </svg>
  )
}

function svgAttemptMix(attempts: number, failures: number, w = 260, h = 12) {
  const a = Math.max(0, Math.floor(Number(attempts) || 0))
  const f = Math.max(0, Math.min(Math.floor(Number(failures) || 0), a))
  const ok = a - f
  const denom = Math.max(a, 1)
  const okW = (w * ok) / denom
  const failW = (w * f) / denom
  return (
    <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="img" aria-label="Successful attempts versus logged failures">
      <rect x="0" y="1" width={okW} height={h - 2} rx="2" fill="var(--le-ok, #5a8f5a)" opacity="0.88" />
      <rect x={okW} y="1" width={failW} height={h - 2} rx="2" fill="var(--le-warn, #b86)" opacity="0.9" />
    </svg>
  )
}

function OpenAiCompatGatewayPanel(props: {
  settings: SettingsPayload
  setSettings: Dispatch<SetStateAction<SettingsPayload | null>>
  providersMap: Record<string, boolean> | null
  usageSummary: UsageSummary | null
  diagnostics: LlmDiagnosticsPayload | null
  probes: Record<string, ProviderProbeState>
  setCustomDrawerOpen: (v: boolean) => void
  openTryOutChat: (providerId: string, modelId: string) => void
  runModelDiscovery: (providerId: string) => Promise<void>
  runProviderHealth: (providerId: string) => Promise<void>
  density?: AiSetupTileDensity
  /** Refresh usage + diagnostics after embedded try-out turns (graphs / summaries). */
  onRefreshMetrics?: () => void | Promise<void>
}) {
  const {
    settings,
    setSettings,
    providersMap,
    usageSummary,
    diagnostics,
    probes,
    setCustomDrawerOpen,
    openTryOutChat,
    runModelDiscovery,
    runProviderHealth,
    density = 'hero',
    onRefreshMetrics,
  } = props
  const cid = CUSTOM_SOURCE.id
  const on = Boolean(providersMap?.[cid])
  const k = (settings.keys as Record<string, KeyInfo>)?.[cid]
  const modelId = (settings.main_models?.[cid] ?? '').trim()
  const lastOk = usageSummary?.last_ok?.[cid]
  const displayName = (settings.custom_provider?.display_name ?? '').trim()
  const pr = probes[cid]
  const chips = usedForLabels(cid, settings.task_routes, TASK_ROWS)
  const failLine = attentionLineFromRecentUsage(usageSummary?.recent_events, cid)
  const statusLabel = !on ? 'Not set up' : pr?.error || failLine ? 'Needs attention' : 'Ready'
  const statusColor =
    !on
      ? 'color-mix(in srgb, var(--le-fg, #fff) 55%, transparent)'
      : pr?.error || failLine
        ? 'var(--le-warn, #d96)'
        : 'var(--le-ok, #8d8)'

  const autoCatalog = useLlmProviderModelCatalog(providersMap, cid)
  const probeStrip = useMemo(
    () => (pr?.models || []).filter((m) => m && !String(m).startsWith('Healthy ·')),
    [pr?.models],
  )
  const optionIds = useMemo(
    () =>
      mergeModelOptionIds(
        '',
        suggestedModelsForTask('openai_compatible', 'chat_assistant'),
        [...new Set([...autoCatalog.models, ...probeStrip])].sort((a, b) => a.localeCompare(b)),
        [modelId],
      ),
    [autoCatalog.models, probeStrip, modelId],
  )

  const baseId = useId()
  const inputId = `${baseId}-compat-model`
  const listId = `${baseId}-compat-model-list`

  const catalogHint =
    autoCatalog.state === 'loading'
      ? 'Loading model catalog…'
      : autoCatalog.state === 'error' && autoCatalog.models.length === 0 && probeStrip.length === 0
        ? 'Catalog unavailable — type a model id or leave empty for the server default.'
        : null

  const compact = density === 'compact'
  const advanced = density === 'advanced'

  const gatewayDiagRow = diagnostics?.providers?.find((p) => p.id === cid)

  const gatewayActivityStats = useMemo(() => {
    const ev = usageSummary?.recent_events?.filter((row) => row.provider === cid || row.source === cid) ?? []
    const pl = usageSummary?.probe_log?.filter((p) => p.provider === cid) ?? []
    const evOk = ev.filter((e) => e.ok !== false).length
    const evFail = ev.filter((e) => e.ok === false).length
    const plOk = pl.filter((p) => p.ok !== false).length
    const plFail = pl.filter((p) => p.ok === false).length
    let latestTs: string | null = null
    for (const e of ev) {
      const ts = e.ts
      if (ts && (!latestTs || ts > latestTs)) latestTs = ts
    }
    for (const p of pl) {
      const ts = p.ts
      if (ts && (!latestTs || ts > latestTs)) latestTs = ts
    }
    return { evOk, evFail, plOk, plFail, evTotal: ev.length, plTotal: pl.length, latestTs }
  }, [usageSummary?.recent_events, usageSummary?.probe_log, cid])

  return (
    <div
      style={{
        padding: compact ? '0.55rem 0.65rem' : '0.75rem 0.85rem',
        borderRadius: '10px',
        border: '1px solid var(--le-border, rgba(255,255,255,0.12))',
        background: 'color-mix(in srgb, var(--le-panel, #1a1a1f) 92%, transparent)',
        marginBottom: '1.15rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
        <div>
          <strong style={{ fontSize: compact ? '0.9rem' : '0.98rem' }}>{displayName || CUSTOM_SOURCE.label}</strong>
          {!compact ? (
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', opacity: 0.86, lineHeight: 1.35 }}>
              {CUSTOM_SOURCE.outcome}
            </p>
          ) : null}
        </div>
        <span
          className="le-mono"
          style={{
            fontSize: '0.72rem',
            fontWeight: 600,
            padding: '0.15rem 0.4rem',
            borderRadius: '999px',
            border: '1px solid var(--le-border, rgba(255,255,255,0.15))',
            color: statusColor,
            whiteSpace: 'nowrap',
          }}
        >
          {statusLabel}
        </span>
      </div>
      {k?.set ? (
        <p className="forge-support" style={{ fontSize: '0.74rem', margin: '0.4rem 0 0', opacity: 0.84 }}>
          Token: {k.from_file ? 'saved on this host' : k.from_env ? 'from environment' : 'configured'} ·{' '}
          <span className="le-mono">{k.preview || '••••'}</span>
        </p>
      ) : null}
      <p className="forge-support" style={{ fontSize: '0.78rem', margin: '0.45rem 0 0.15rem', opacity: 0.88 }}>
        <strong>Endpoint</strong>:{' '}
        <span className="le-mono">
          {settings.openai_compatible_endpoint?.set
            ? settings.openai_compatible_endpoint.preview || '(set)'
            : '(none)'}
        </span>
      </p>
      {on && !compact ? (
        <ModelIdComboboxField
          inputId={inputId}
          listId={listId}
          label={
            <span style={{ opacity: 0.88 }}>
              <strong>Default model id</strong> for this gateway (optional)
            </span>
          }
          hint={catalogHint}
          value={settings.main_models?.openai_compatible ?? ''}
          onChange={(v) =>
            setSettings({
              ...settings,
              main_models: { ...(settings.main_models || {}), openai_compatible: v },
            })
          }
          optionIds={optionIds}
          disabled={!on}
          catalogBusy={autoCatalog.state === 'loading'}
          style={{ margin: '0.35rem 0 0.15rem' }}
        />
      ) : (
        <p className="forge-support" style={{ fontSize: '0.78rem', margin: '0 0 0.15rem', opacity: 0.88 }}>
          <strong>Model id</strong>: <span className="le-mono">{modelId || '(server default)'}</span>
        </p>
      )}
      {on && !compact ? (
        <p className="forge-support" style={{ fontSize: '0.72rem', margin: '0.15rem 0 0', opacity: 0.78, lineHeight: 1.35 }}>
          Leave the field empty to use the server default. Suggestions merge the live catalog (auto-refreshed) with
          ids from <strong>Discover models</strong> on this card. Persist with <strong>Save changes</strong>.
        </p>
      ) : null}
      <p className="forge-support" style={{ fontSize: '0.78rem', margin: '0 0 0.35rem', opacity: 0.82 }}>
        <strong>Try result</strong>:{' '}
        {lastOk?.trim() ? (
          <>
            Last OK chat · <span className="le-mono">{lastOk.trim()}</span>
          </>
        ) : (
          'No successful Studio chat logged for this gateway yet.'
        )}
      </p>
      {!compact ? (
        <div style={{ marginBottom: '0.35rem' }}>
          <span style={{ fontSize: '0.72rem', fontWeight: 600, opacity: 0.88 }}>Used for</span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', marginTop: '0.25rem' }}>
            {chips.length ? (
              chips.map((label) => (
                <span
                  key={label}
                  className="le-mono"
                  style={{
                    fontSize: '0.68rem',
                    padding: '0.12rem 0.4rem',
                    borderRadius: '999px',
                    border: '1px solid var(--le-border, rgba(255,255,255,0.14))',
                    background: 'color-mix(in srgb, var(--le-cyan, #5ec8d4) 10%, transparent)',
                  }}
                >
                  {label}
                </span>
              ))
            ) : (
              <span style={{ fontSize: '0.72rem', opacity: 0.75 }}>All tasks — follows primary source</span>
            )}
          </div>
        </div>
      ) : chips.length ? (
        <p className="forge-support" style={{ fontSize: '0.72rem', margin: '0.25rem 0 0.35rem', opacity: 0.82 }}>
          <strong>Used for</strong>: {chips.join(', ')}
        </p>
      ) : null}
      {pr?.loading ? (
        <p style={{ fontSize: '0.74rem', opacity: 0.85, margin: '0 0 0.35rem' }}>Checking catalog…</p>
      ) : null}
      {pr?.models && pr.models.length > 0 && !compact ? (
        <p
          className="le-mono"
          style={{ fontSize: '0.68rem', opacity: 0.82, margin: '0 0 0.35rem', wordBreak: 'break-word' }}
        >
          {pr.models.slice(0, advanced ? 14 : 8).join(', ')}
          {pr.models.length > (advanced ? 14 : 8) ? ` · +${pr.models.length - (advanced ? 14 : 8)} more` : ''}
        </p>
      ) : null}
      {pr?.error ? (
        <p style={{ fontSize: '0.74rem', color: 'var(--le-warn, #d96)', margin: '0 0 0.35rem' }}>{pr.error}</p>
      ) : null}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', alignItems: 'center' }}>
        <button
          type="button"
          className="le-btn le-btn--primary"
          style={{
            ...AI_SETUP_PRIMARY_READABLE,
            fontSize: compact ? '0.74rem' : '0.78rem',
            padding: compact ? '0.18rem 0.48rem' : '0.2rem 0.55rem',
          }}
          onClick={() => setCustomDrawerOpen(true)}
        >
          {on ? 'Edit custom provider' : 'Add custom provider'}
        </button>
        {on && !compact ? (
          <button
            type="button"
            className="le-btn le-btn--secondary"
            style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem' }}
            onClick={() => openTryOutChat(cid, modelId)}
          >
            Test connection
          </button>
        ) : null}
        {!compact ? (
          <button
            type="button"
            className="le-btn le-btn--secondary"
            style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem' }}
            disabled={Boolean(pr?.loading) || !on}
            onClick={() => void runModelDiscovery(cid)}
          >
            Discover models
          </button>
        ) : null}
        {!compact ? (
          <button
            type="button"
            className="le-btn le-btn--secondary"
            style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem' }}
            disabled={Boolean(pr?.loading) || !on}
            onClick={() => void runProviderHealth(cid)}
          >
            Health check
          </button>
        ) : null}
      </div>
      {advanced ? (
        <>
          <div
            style={{
              margin: '0.55rem 0 0',
              padding: '0.5rem 0.65rem',
              borderRadius: '10px',
              border: '1px solid var(--le-border, rgba(255,255,255,0.12))',
              background: 'color-mix(in srgb, var(--le-panel, #1a1a1f) 96%, transparent)',
            }}
          >
            <div style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.06em', opacity: 0.82, marginBottom: '0.45rem' }}>
              Activity summary (this host)
            </div>
            {gatewayDiagRow ? (
              <>
                <p className="forge-support" style={{ fontSize: '0.72rem', margin: '0 0 0.35rem', opacity: 0.88, lineHeight: 1.45 }}>
                  Tokens recorded: <strong>{gatewayDiagRow.totals?.total_tokens ?? 0}</strong> total ·{' '}
                  <span className="le-mono">
                    {gatewayDiagRow.totals?.prompt_tokens ?? 0} prompt / {gatewayDiagRow.totals?.completion_tokens ?? 0} completion
                  </span>
                  {' · '}
                  Chats with usage: <strong>{gatewayDiagRow.totals?.requests ?? 0}</strong> · attempts{' '}
                  <strong>{gatewayDiagRow.totals?.attempts ?? 0}</strong>
                  {(gatewayDiagRow.totals?.failures ?? 0) > 0 ? (
                    <span style={{ color: 'var(--le-warn, #e8b86a)' }}> · failures {gatewayDiagRow.totals?.failures}</span>
                  ) : null}
                </p>
                <div style={{ fontSize: '0.7rem', opacity: 0.8, marginBottom: '0.2rem' }}>Prompt vs completion (share)</div>
                {svgMiniTokenBar(gatewayDiagRow.totals?.prompt_tokens ?? 0, gatewayDiagRow.totals?.completion_tokens ?? 0)}
                <div style={{ fontSize: '0.7rem', opacity: 0.8, margin: '0.5rem 0 0.2rem' }}>Attempts — success vs logged failures</div>
                {svgAttemptMix(
                  gatewayDiagRow.totals?.attempts ?? gatewayDiagRow.totals?.requests ?? 0,
                  gatewayDiagRow.totals?.failures ?? 0,
                )}
              </>
            ) : (
              <p className="forge-support" style={{ fontSize: '0.72rem', margin: 0, opacity: 0.82 }}>
                Connect this gateway to see token charts from diagnostics.
              </p>
            )}
            <p className="forge-support" style={{ fontSize: '0.72rem', margin: '0.5rem 0 0', opacity: 0.86, lineHeight: 1.45 }}>
              Recent Studio events (this source): <strong>{gatewayActivityStats.evOk}</strong> ok,{' '}
              <strong>{gatewayActivityStats.evFail}</strong> failed
              {gatewayActivityStats.evTotal ? ` · ${gatewayActivityStats.evTotal} in rolling history` : ''}. Probes:{' '}
              <strong>{gatewayActivityStats.plOk}</strong> ok, <strong>{gatewayActivityStats.plFail}</strong> failed
              {gatewayActivityStats.plTotal ? ` · ${gatewayActivityStats.plTotal} logged` : ''}.
              {gatewayActivityStats.latestTs ? (
                <>
                  {' '}
                  Latest: <span className="le-mono">{formatDiagnosticTs(gatewayActivityStats.latestTs)}</span>.
                </>
              ) : null}
            </p>
            {gatewayDiagRow?.last_probe?.ts ? (
              <p className="forge-support" style={{ fontSize: '0.72rem', margin: '0.35rem 0 0', opacity: 0.84 }}>
                Last health probe: <span className="le-mono">{formatDiagnosticTs(gatewayDiagRow.last_probe.ts)}</span> ·{' '}
                {gatewayDiagRow.last_probe.ok === false ? 'needs attention' : 'ok'}
              </p>
            ) : null}
          </div>

          {on && onRefreshMetrics ? (
            <LlmTryOutChatModal
              layout="embedded"
              open
              onClose={() => {}}
              providerId={cid}
              defaultModelId={modelId}
              onAfterExchange={() => void Promise.resolve(onRefreshMetrics()).catch(() => {})}
              onOpenPopout={() => openTryOutChat(cid, modelId)}
            />
          ) : null}

          <p className="forge-support" style={{ fontSize: '0.72rem', margin: '0.55rem 0 0', opacity: 0.82, lineHeight: 1.45 }}>
            Line-by-line probe and chat logs live under <strong>Usage & diagnostics</strong> below. Charts and counts refresh after each Test
            chat send (and when Discover / Health runs). Persist model defaults with <strong>Save changes</strong>.
          </p>
        </>
      ) : null}
    </div>
  )
}

const TIERS = ['TOP', 'HIGHEST', 'HIGH', 'MED', 'LOW', 'EXTRA_LOW']

/** Four UX stops for Smart multi-model — map to internal ``tier`` values. */
const SMART_QUALITY_STOPS = [
  { tier: 'EXTRA_LOW', label: 'Speed' },
  { tier: 'MED', label: 'Balanced' },
  { tier: 'HIGH', label: 'Quality' },
  { tier: 'TOP', label: 'Max' },
] as const

function smartStopIndexForTier(tier: string | undefined): number {
  const t = (tier ?? 'MED').toUpperCase()
  const i = SMART_QUALITY_STOPS.findIndex((s) => s.tier === t)
  if (i >= 0) return i
  if (['LOW', 'EXTRA_LOW', 'NONE'].includes(t)) return 0
  if (t === 'MED') return 1
  if (t === 'HIGH' || t === 'HIGHEST') return 2
  return 3
}

/** Slider position 0 = left (cheapest tier), 5 = right (strongest). Maps to TIERS[5 - pos]. */
function tierToSliderPos(tier: string | undefined): number {
  const idx = TIERS.indexOf(tier ?? 'MED')
  if (idx < 0) return 3
  return 5 - idx
}

type Props = {
  compactIntro?: boolean
}

export function LlmSettingsForm({ compactIntro = false }: Props) {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [banner, setBanner] = useState<string | null>(null)
  const [bannerTechnical, setBannerTechnical] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [settings, setSettings] = useState<SettingsPayload | null>(null)
  const [keysOpenai, setKeysOpenai] = useState('')
  const [keysAnthropic, setKeysAnthropic] = useState('')
  const [keysGemini, setKeysGemini] = useState('')
  const [keysCompat, setKeysCompat] = useState('')
  const [usageSummary, setUsageSummary] = useState<UsageSummary | null>(null)
  const [diagnostics, setDiagnostics] = useState<LlmDiagnosticsPayload | null>(null)
  const [wizardDismissing, setWizardDismissing] = useState(false)
  const [providersMap, setProvidersMap] = useState<Record<string, boolean> | null>(null)
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatusPayload | null>(null)
  const [routingPreview, setRoutingPreview] = useState<{
    rows: RoutingPreviewRow[]
    connected_providers: number
  } | null>(null)
  /** Draft for ``openai_compatible_base_url`` (saved on submit; GET omits raw URL). */
  const [compatBaseUrl, setCompatBaseUrl] = useState('')
  const [compatUrlTouched, setCompatUrlTouched] = useState(false)
  /** When false, cloud credential fields stay hidden (no blank password wall). */
  const [revealSecrets, setRevealSecrets] = useState<Partial<Record<RevealSecretId, boolean>>>({})
  const [customDrawerOpen, setCustomDrawerOpen] = useState(false)
  const [moreProvidersOpen, setMoreProvidersOpen] = useState(false)
  const [probes, setProbes] = useState<
    Record<string, { loading?: boolean; models?: string[]; error?: string; at?: number }>
  >({})
  const cloudGroupRef = useRef<HTMLDivElement>(null)
  const customGroupRef = useRef<HTMLDivElement>(null)
  const localGroupRef = useRef<HTMLDivElement>(null)
  const [tryOut, setTryOut] = useState<{ providerId: string; defaultModelId: string } | null>(null)
  const [sourceLayout, setSourceLayout] = useState<AiSetupSourceLayoutV2>(() => loadAiSetupSourceLayout())

  useEffect(() => {
    saveAiSetupSourceLayout(sourceLayout)
  }, [sourceLayout])

  const primaryPidForCatalog = (settings?.provider ?? 'openai').trim()
  const primaryCatalog = useLlmProviderModelCatalog(providersMap, primaryPidForCatalog)
  const primaryModelFieldBaseId = useId()

  function openTryOutChat(providerId: string, modelId: string) {
    setTryOut({ providerId, defaultModelId: modelId })
  }

  /** GET /api/llm/settings strips raw ``openai_compatible_base_url``; preview holds the effective origin for the UI. */
  useEffect(() => {
    if (!settings || compatUrlTouched) return
    const ep = settings.openai_compatible_endpoint
    if (ep?.set && (ep.preview || '').trim()) {
      let p = String(ep.preview).trim()
      if (p.endsWith('…')) p = p.slice(0, -1).trim()
      setCompatBaseUrl(p)
    } else {
      setCompatBaseUrl('')
    }
  }, [settings, compatUrlTouched])

  useEffect(() => {
    let cancelled = false
    Promise.all([
      apiGetJson<{ ok?: boolean; settings?: SettingsPayload }>('/api/llm/settings'),
      apiGetJson<{ ok?: boolean; usage?: UsageSummary }>('/api/llm/usage').catch(() => null),
      apiGetJson<LlmDiagnosticsPayload>('/api/llm/diagnostics').catch(() => null),
      apiGetJson<{ ok?: boolean; providers?: Record<string, boolean> }>('/api/llm/providers').catch(() => null),
      apiGetJson<OllamaStatusPayload>('/api/llm/ollama-status').catch(() => null),
      apiGetJson<{ ok?: boolean; rows?: RoutingPreviewRow[]; connected_providers?: number }>(
        '/api/llm/routing-preview',
      ).catch(() => null),
    ])
      .then(([st, us, dg, pv, oll, rp]) => {
        if (cancelled) return
        setSettings(mergeLoadedSettings(st.settings))
        if (us && us.usage) setUsageSummary(us.usage)
        if (dg && dg.ok !== false) setDiagnostics(dg)
        if (pv?.providers) setProvidersMap(pv.providers)
        if (oll) setOllamaStatus(oll)
        if (rp?.rows) setRoutingPreview({ rows: rp.rows, connected_providers: Number(rp.connected_providers) || 0 })
      })
      .catch((err) => {
        if (cancelled) return
        setSettings({ ...DEFAULT_LLM_SETTINGS })
        if (err instanceof ApiError && err.status === 403) {
          setBanner(
            'AI Setup can’t be loaded from this browser address. Open Studio the same way you open Lenses locally (loopback), or ask an admin about remote access.',
          )
          setBannerTechnical(err.technicalNote)
        } else {
          const ux = resolveUxFailure(err)
          setBanner(ux.description)
          setBannerTechnical(ux.technical)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function refreshOllama() {
    const oll = await apiGetJson<OllamaStatusPayload>('/api/llm/ollama-status').catch(() => null)
    if (oll) setOllamaStatus(oll)
  }

  const taskRoutesRevision = useMemo(
    () => JSON.stringify(settings?.task_routes ?? {}),
    [settings?.task_routes],
  )
  const mainModelsRevision = useMemo(
    () => JSON.stringify(settings?.main_models ?? {}),
    [settings?.main_models],
  )
  const poolsRevision = useMemo(() => JSON.stringify(settings?.pools ?? {}), [settings?.pools])

  useEffect(() => {
    if (!settings || import.meta.env.VITE_STATIC_MUSEUM === 'true') return
    const h = window.setTimeout(() => {
      void (async () => {
        try {
          const draft = {
            routing_mode: settings.routing_mode,
            tier: settings.tier,
            provider: settings.provider,
            advanced_ui: settings.advanced_ui,
            auto_model: settings.auto_model,
            adaptive_autoselection: settings.adaptive_autoselection,
            refine_cheaper_steps: settings.refine_cheaper_steps,
            main_models: settings.main_models,
            pools: settings.pools,
            classifier_models: settings.classifier_models,
            task_routes: settings.task_routes,
          }
          const rp = await apiPostJson<{
            ok?: boolean
            rows?: RoutingPreviewRow[]
            connected_providers?: number
            routing_mode?: string
          }>('/api/llm/routing-preview-draft', { settings: draft })
          if (rp?.rows) {
            setRoutingPreview({ rows: rp.rows, connected_providers: Number(rp.connected_providers) || 0 })
          }
        } catch {
          /* static museum or offline */
        }
      })()
    }, 280)
    return () => window.clearTimeout(h)
  }, [
    settings?.routing_mode,
    settings?.tier,
    settings?.provider,
    settings?.advanced_ui,
    settings?.auto_model,
    settings?.adaptive_autoselection,
    settings?.refine_cheaper_steps,
    settings?.classifier_models,
    taskRoutesRevision,
    mainModelsRevision,
    poolsRevision,
  ])

  async function reloadLlmPanels() {
    const [st, us, dg, pv, oll, rp] = await Promise.all([
      apiGetJson<{ ok?: boolean; settings?: SettingsPayload }>('/api/llm/settings'),
      apiGetJson<{ ok?: boolean; usage?: UsageSummary }>('/api/llm/usage').catch(() => null),
      apiGetJson<LlmDiagnosticsPayload>('/api/llm/diagnostics').catch(() => null),
      apiGetJson<{ ok?: boolean; providers?: Record<string, boolean> }>('/api/llm/providers').catch(() => null),
      apiGetJson<OllamaStatusPayload>('/api/llm/ollama-status').catch(() => null),
      apiGetJson<{ ok?: boolean; rows?: RoutingPreviewRow[]; connected_providers?: number }>(
        '/api/llm/routing-preview',
      ).catch(() => null),
    ])
    if (st.settings) setSettings(mergeLoadedSettings(st.settings))
    if (us && us.usage) setUsageSummary(us.usage)
    if (dg && dg.ok !== false) setDiagnostics(dg)
    if (pv?.providers) setProvidersMap(pv.providers)
    if (oll) setOllamaStatus(oll)
    if (rp?.rows) setRoutingPreview({ rows: rp.rows, connected_providers: Number(rp.connected_providers) || 0 })
  }

  async function refreshUsageAndDiagnostics() {
    const [us, dg] = await Promise.all([
      apiGetJson<{ ok?: boolean; usage?: UsageSummary }>('/api/llm/usage').catch(() => null),
      apiGetJson<LlmDiagnosticsPayload>('/api/llm/diagnostics').catch(() => null),
    ])
    if (us && us.usage) setUsageSummary(us.usage)
    if (dg && dg.ok !== false) setDiagnostics(dg)
  }

  async function dismissFirstRunWizard() {
    setWizardDismissing(true)
    try {
      await apiPostJson<{ ok?: boolean }>('/api/llm/settings', {
        settings: { first_run_wizard_dismissed: true },
      })
      await reloadLlmPanels()
    } catch {
      /* ignore */
    } finally {
      setWizardDismissing(false)
    }
  }

  async function runModelDiscovery(providerId: string) {
    setProbes((p) => ({ ...p, [providerId]: { ...p[providerId], loading: true, error: undefined } }))
    try {
      const out = await apiPostJson<{ ok?: boolean; models?: string[]; error?: string; detail?: string }>(
        '/api/llm/provider-probe',
        { provider: providerId, action: 'models' },
      )
      if (out.ok && Array.isArray(out.models)) {
        setProbes((p) => ({
          ...p,
          [providerId]: { models: out.models, loading: false, at: Date.now() },
        }))
      } else {
        setProbes((p) => ({
          ...p,
          [providerId]: {
            loading: false,
            error: [out.error, out.detail].filter(Boolean).join(' · ') || 'Unavailable',
            at: Date.now(),
          },
        }))
      }
    } catch (err) {
      const ux = resolveUxFailure(err)
      setProbes((p) => ({
        ...p,
        [providerId]: { loading: false, error: ux.description, at: Date.now() },
      }))
    } finally {
      void refreshUsageAndDiagnostics()
    }
  }

  async function runProviderHealth(providerId: string) {
    setProbes((p) => ({ ...p, [providerId]: { ...p[providerId], loading: true, error: undefined } }))
    try {
      const out = await apiPostJson<{
        ok?: boolean
        healthy?: boolean
        model_count?: number
        detail?: string
        error?: string
      }>('/api/llm/provider-probe', { provider: providerId, action: 'health' })
      if (out.healthy) {
        setProbes((p) => ({
          ...p,
          [providerId]: {
            models: [`Healthy · ${out.model_count ?? 0} models in catalog`],
            loading: false,
            error: undefined,
            at: Date.now(),
          },
        }))
      } else {
        setProbes((p) => ({
          ...p,
          [providerId]: {
            loading: false,
            error: [out.error, out.detail].filter(Boolean).join(' · ') || 'Not reachable',
            at: Date.now(),
          },
        }))
      }
    } catch (err) {
      const ux = resolveUxFailure(err)
      setProbes((p) => ({
        ...p,
        [providerId]: { loading: false, error: ux.description, at: Date.now() },
      }))
    } finally {
      void refreshUsageAndDiagnostics()
    }
  }

  async function save(e: React.FormEvent) {
    e.preventDefault()
    if (!settings) return
    setSaving(true)
    setSaveSuccess(false)
    setBanner(null)
    setBannerTechnical(null)
    const payload: SettingsPayload = {
      version: settings.version ?? 2,
      provider: settings.provider,
      routing_mode: settings.routing_mode,
      advanced_ui: settings.advanced_ui,
      auto_model: settings.auto_model,
      adaptive_autoselection: settings.adaptive_autoselection,
      tier: settings.tier,
      refine_cheaper_steps: settings.refine_cheaper_steps,
      main_models: settings.main_models,
      pools: settings.pools,
      classifier_models: settings.classifier_models,
      task_routes: settings.task_routes,
      fallback_route: settings.fallback_route,
      custom_provider: settings.custom_provider,
    }
    if (compatUrlTouched) {
      payload.openai_compatible_base_url = compatBaseUrl.trim()
    }
    const keys: Record<string, string> = {}
    if (keysAnthropic.trim()) keys.anthropic = keysAnthropic.trim()
    if (keysOpenai.trim()) keys.openai = keysOpenai.trim()
    if (keysGemini.trim()) keys.gemini = keysGemini.trim()
    if (keysCompat.trim()) keys.openai_compatible = keysCompat.trim()
    if (Object.keys(keys).length) payload.keys = keys

    try {
      await apiPostJson('/api/llm/settings', { settings: payload })
      setSaveSuccess(true)
      setBanner('Settings saved.')
      setBannerTechnical(null)
      setKeysOpenai('')
      setKeysAnthropic('')
      setKeysGemini('')
      setKeysCompat('')
      setCompatBaseUrl('')
      setCompatUrlTouched(false)
      await reloadLlmPanels()
    } catch (err) {
      setSaveSuccess(false)
      if (err instanceof ApiError && err.status === 403) {
        setBanner(
          'Saving isn’t allowed from this browser address for your Lenses security settings. Use the local Studio URL or ask an admin.',
        )
        setBannerTechnical(err.technicalNote)
      } else {
        const ux = resolveUxFailure(err)
        setBanner(ux.description)
        setBannerTechnical(ux.technical)
      }
    } finally {
      setSaving(false)
    }
  }

  const sliderPos = tierToSliderPos(settings?.tier)
  const prov = (settings?.provider ?? 'openai').trim()
  const mainModelVal = (settings?.main_models?.[prov] ?? '').trim()
  const primaryModelOptionIds = useMemo(
    () =>
      mergeModelOptionIds(
        '',
        suggestedModelsForTask(prov, 'chat_assistant'),
        primaryCatalog.models,
        [mainModelVal].filter(Boolean),
      ),
    [prov, primaryCatalog.models, mainModelVal],
  )
  const primaryModelHint =
    primaryCatalog.state === 'loading'
      ? 'Loading model catalog…'
      : primaryCatalog.state === 'error' && primaryCatalog.models.length === 0
        ? 'Catalog unavailable — type a model id or pick a suggestion when listed.'
        : null
  const adv = Boolean(settings?.advanced_ui)
  const auto = Boolean(settings?.auto_model)
  const adapt = Boolean(settings?.adaptive_autoselection)

  function setMainModel(v: string) {
    if (!settings) return
    setSettings({
      ...settings,
      main_models: { ...(settings.main_models || {}), [prov]: v },
    })
  }

  function setClassifierModel(which: 'openai' | 'gemini', v: string) {
    if (!settings) return
    setSettings({
      ...settings,
      classifier_models: { ...(settings.classifier_models || {}), [which]: v },
    })
  }

  function updateTaskRoute(taskId: string, patch: Partial<TaskRouteEntry>) {
    if (!settings) return
    const cur: TaskRouteEntry = settings.task_routes?.[taskId] ?? {
      provider: '',
      model: '',
      model_stack: [],
    }
    let merged: TaskRouteEntry = { ...cur, ...patch }
    if (Array.isArray(patch.model_stack)) {
      const ms = patch.model_stack.map((x) => String(x ?? '').trim()).filter(Boolean)
      merged.model_stack = ms
      merged.model = ms[0] ?? ''
    } else if (patch.model !== undefined && patch.model_stack === undefined) {
      const m = String(patch.model ?? '').trim()
      merged.model = m
      merged.model_stack = m ? [m] : []
    }
    setSettings({
      ...settings,
      task_routes: {
        ...(settings.task_routes || {}),
        [taskId]: merged,
      },
    })
  }

  function applyRoutingMode(mode: 'single' | 'smart' | 'advanced') {
    if (!settings) return
    if (mode === 'single') {
      setSettings({
        ...settings,
        routing_mode: 'single',
        advanced_ui: false,
        auto_model: false,
        adaptive_autoselection: false,
      })
    } else if (mode === 'smart') {
      setSettings({
        ...settings,
        routing_mode: 'smart',
        advanced_ui: true,
        auto_model: true,
      })
    } else {
      setSettings({
        ...settings,
        routing_mode: 'advanced',
        advanced_ui: true,
      })
    }
  }

  if (loading) {
    return <p className="forge-support">Loading settings…</p>
  }
  if (!settings) {
    return <p className="forge-support">No settings available.</p>
  }

  const connectedCount = ALL_PROVIDER_IDS.filter((id) => providersMap?.[id]).length
  const allowSmartRouting = connectedCount >= 2
  const routingLabel =
    settings.routing_mode === 'smart'
      ? 'Smart routing'
      : settings.routing_mode === 'advanced'
        ? 'Advanced routing'
        : 'Single model'
  const ollChip =
    ollamaStatus?.configured === false
      ? 'Ollama: not configured'
      : ollamaStatus?.reachable
        ? `Ollama: running @ ${ollamaStatus.base || ''}`
        : `Ollama: unreachable @ ${ollamaStatus?.base || ''}`
  const previewRows: RoutingPreviewRow[] =
    routingPreview?.rows?.length
      ? routingPreview.rows
      : TASK_ROWS.map((t) => ({ task_id: t.id, label: t.label, provider: '—', model: '—' }))

  const cloudConnected = CLOUD_SOURCES.filter((s) => providersMap?.[s.id]).length
  const ollamaReady = Boolean(providersMap?.ollama)

  return (
    <>
      {compactIntro ? (
        <p className="forge-support" style={{ fontSize: '0.88rem', marginBottom: '0.75rem' }}>
          Same dashboard as <strong>AI Setup</strong> under Workspace — credentials live on the Lenses host, not in
          the browser. Open the full page for guided setup.
        </p>
      ) : null}
      <div
        className="forge-support"
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.5rem',
          alignItems: 'center',
          marginBottom: '0.85rem',
          padding: '0.65rem 0.75rem',
          borderRadius: '10px',
          border: '1px solid var(--le-border, rgba(255,255,255,0.12))',
          background: 'color-mix(in srgb, var(--le-panel, #1a1a1f) 88%, transparent)',
        }}
      >
        <span style={{ fontWeight: 700, marginRight: '0.15rem' }}>Status</span>
        <span style={{ fontSize: '0.84rem', opacity: 0.92 }}>
          {connectedCount === 0
            ? 'No model sources detected yet'
            : `${connectedCount} source${connectedCount === 1 ? '' : 's'} ready`}
          {cloudConnected > 0 ? ` · ${cloudConnected} cloud` : ''}
          {providersMap?.openai_compatible ? ' · custom gateway' : ''}
          {ollamaReady ? ' · Ollama' : ''}
        </span>
        <span style={{ opacity: 0.35 }} aria-hidden>
          |
        </span>
        <span className="le-mono" style={{ fontSize: '0.8rem', opacity: 0.9 }} title="How requests pick a model when several sources exist">
          {allowSmartRouting ? routingLabel : 'Primary source only'}
        </span>
        <span style={{ opacity: 0.35 }} aria-hidden>
          |
        </span>
        <span className="le-mono" style={{ fontSize: '0.8rem', opacity: 0.88 }} title="Native Ollama integration">
          {ollChip}
        </span>
        <span style={{ flex: '1 1 4rem' }} />
        <button
          className="le-btn le-btn--primary"
          type="submit"
          form="le-ai-setup-form"
          disabled={saving}
          style={AI_SETUP_PRIMARY_READABLE}
        >
          {saving ? 'Saving…' : 'Save changes'}
        </button>
        <Link className="le-btn le-btn--secondary" to="/chat">
          Try Chat
        </Link>
      </div>
      {!compactIntro && diagnostics?.first_run_recommended ? (
        <div
          className="forge-support"
          style={{
            marginBottom: '1rem',
            padding: '1rem 1.1rem',
            borderRadius: '12px',
            border: '1px solid color-mix(in srgb, var(--le-amber, #e8b86a) 40%, var(--le-border, rgba(255,255,255,0.12)))',
            background: 'color-mix(in srgb, var(--le-amber, #e8b86a) 8%, var(--le-panel, #1a1a1f))',
          }}
          role="region"
          aria-label="First-time AI setup"
        >
          <h2 style={{ margin: '0 0 0.35rem', fontSize: '1.05rem', fontWeight: 700 }}>Welcome — wire your first model</h2>
          <ol style={{ margin: '0 0 0.85rem', paddingLeft: '1.2rem', fontSize: '0.9rem', opacity: 0.93, maxWidth: '42rem' }}>
            <li>Pick one path: a cloud API key, a custom OpenAI-compatible gateway, or local Ollama on this host.</li>
            <li>Use <strong>Discover models</strong> / <strong>Health check</strong> on the card — failures show error codes here and in the diagnostics table below.</li>
            <li>Open <strong>Try Chat</strong> and send a short message to confirm routing.</li>
          </ol>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
            <button
              type="button"
              className="le-btn le-btn--secondary"
              onClick={() => {
                setRevealSecrets((s) => ({ ...s, openai: true }))
                cloudGroupRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }}
            >
              Add a cloud API key
            </button>
            <button
              type="button"
              className="le-btn le-btn--secondary"
              onClick={() => {
                setCustomDrawerOpen(true)
                customGroupRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }}
            >
              Add a custom gateway
            </button>
            <button
              type="button"
              className="le-btn le-btn--secondary"
              onClick={() => {
                localGroupRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }}
            >
              Set up local Ollama
            </button>
            <span style={{ flex: '1 1 2rem' }} />
            <button
              type="button"
              className="le-btn le-btn--ghost"
              disabled={wizardDismissing}
              onClick={() => void dismissFirstRunWizard()}
            >
              {wizardDismissing ? 'Saving…' : 'Dismiss wizard'}
            </button>
          </div>
        </div>
      ) : null}
      {!compactIntro && !diagnostics?.first_run_recommended && connectedCount === 0 ? (
        <div
          className="forge-support"
          style={{
            marginBottom: '1.15rem',
            padding: '1rem 1.1rem',
            borderRadius: '12px',
            border: '1px solid color-mix(in srgb, var(--le-cyan, #5ec8d4) 35%, var(--le-border, rgba(255,255,255,0.12)))',
            background: 'color-mix(in srgb, var(--le-cyan, #5ec8d4) 6%, var(--le-panel, #1a1a1f))',
          }}
        >
          <h2 style={{ margin: '0 0 0.35rem', fontSize: '1.05rem', fontWeight: 700 }}>Get answers in this workspace</h2>
          <p style={{ margin: '0 0 0.85rem', fontSize: '0.9rem', opacity: 0.92, maxWidth: '40rem' }}>
            You have not wired a model yet. Pick <strong>one</strong> path below—hosted APIs, your own gateway, or
            local Ollama—then use <strong>Try Chat</strong> to confirm it responds.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            <button
              type="button"
              className="le-btn le-btn--secondary"
              onClick={() => {
                setRevealSecrets((s) => ({ ...s, openai: true }))
                cloudGroupRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }}
            >
              Add a cloud API key
            </button>
            <button
              type="button"
              className="le-btn le-btn--secondary"
              onClick={() => {
                setCustomDrawerOpen(true)
                customGroupRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }}
            >
              Add a custom gateway
            </button>
            <button
              type="button"
              className="le-btn le-btn--secondary"
              onClick={() => {
                localGroupRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }}
            >
              Set up local Ollama
            </button>
          </div>
        </div>
      ) : null}
      {banner ? (
        <p
          role="status"
          className="forge-support"
          style={
            saveSuccess
              ? {
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.45rem',
                  color: 'var(--le-ok, #7d7)',
                  fontWeight: 600,
                }
              : undefined
          }
        >
          {saveSuccess ? (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '1.25rem',
                height: '1.25rem',
                borderRadius: '4px',
                border: '1px solid color-mix(in srgb, var(--le-ok, #7d7) 55%, transparent)',
                background: 'color-mix(in srgb, var(--le-ok, #7d7) 12%, transparent)',
                fontSize: '0.85rem',
                lineHeight: 1,
              }}
              aria-hidden
            >
              ✓
            </span>
          ) : null}
          {banner}
        </p>
      ) : null}
      {bannerTechnical ? (
        <details className="forge-support" style={{ margin: '0 0 0.75rem', fontSize: '0.8rem' }}>
          <summary style={{ cursor: 'pointer' }}>Show error detail</summary>
          <pre
            className="le-preview"
            style={{ marginTop: '0.4rem', fontSize: '0.72rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
          >
            {bannerTechnical}
          </pre>
        </details>
      ) : null}
      <form id="le-ai-setup-form" onSubmit={save}>
        <h2 className="forge-support" style={{ fontSize: '1.05rem', margin: '0 0 0.35rem', fontWeight: 700 }}>
          Model sources
        </h2>
        <p className="forge-support" style={{ fontSize: '0.88rem', marginBottom: '1rem', opacity: 0.9, maxWidth: '44rem' }}>
          Each card is optional. Connect only what you use—Studio picks up keys and URLs from this host (saved file or
          environment). <strong>Cloud</strong> tiles each have Tile / Hero / Advanced: Tile is a compact summary (use{' '}
          <strong>Expand to configure</strong> or the pictograms); Hero keeps the main row light and tucks catalog probes
          under a fold; Advanced inlines the full catalog strip, diagnostics, and all probe actions. Custom and Ollama use
          one density per section. Names and paths stay under <strong>Technical details</strong> at the bottom.
        </p>

        <AiSetupSourcePriorityRail
          layout={sourceLayout}
          onReorder={(nextOrder) => setSourceLayout((prev) => ({ ...prev, order: nextOrder }))}
        />
        <p
          className="forge-support"
          style={{ fontSize: '0.76rem', margin: '-0.2rem 0 0.9rem', opacity: 0.82, maxWidth: '48rem' }}
        >
          Section rail: <strong>blue</strong> = hosted cloud, <strong>pale green</strong> = custom gateway, <strong>gray</strong>{' '}
          = local Ollama. Stronger tint = higher on the page. Drag section cards or use their arrows.           Each <strong>cloud</strong>{' '}
          vendor tile has its own Tile / Hero / Advanced control (saved in this browser); Hero vs Advanced changes layout on
          that tile, not just a label. Custom and Ollama sections keep one density each. Reorder cloud tiles with the
          arrows at the bottom-right of each tile.
        </p>

        {sourceLayout.order.map((sectionId) => {
          const priorityIdx = sourceLayout.order.indexOf(sectionId)
          const sectionStripe = aiSetupSectionStripeCss(sectionId, priorityIdx)

          if (sectionId === 'cloud') {
            const nCloudSlots = sourceLayout.cloudCardOrder.length
            const cloudGridStyle = {
              display: 'grid' as const,
              gridTemplateColumns: 'repeat(auto-fill, minmax(15rem, 1fr))',
              gap: '0.6rem',
              alignItems: 'stretch' as const,
              marginBottom: '1.15rem',
            }

            return (
              <AiSetupSectionChrome key={sectionId} stripeColor={sectionStripe}>
                <div ref={cloudGroupRef}>
                  <h3
                    className="forge-support"
                    style={{ fontSize: '0.95rem', margin: '0 0 0.5rem', fontWeight: 700, letterSpacing: '0.02em' }}
                  >
                    Cloud providers
                  </h3>
                  <p className="forge-support" style={{ fontSize: '0.82rem', margin: '-0.15rem 0 0.55rem', opacity: 0.85 }}>
                    Hosted vendors—best when you want turnkey quality without running a server.
                  </p>
                  <div style={cloudGridStyle}>
                    {sourceLayout.cloudCardOrder.map((slotId, slotIndex) => {
                      if (slotId === 'more_providers') {
                        const stripe = aiSetupCloudCardStripeCss(slotIndex, nCloudSlots)
                        return (
                          <CloudMoreProvidersCard
                            key="more_providers"
                            density={sourceLayout.cloudTileDensity.more_providers}
                            onDensityChange={(next) =>
                              setSourceLayout((prev) => ({
                                ...prev,
                                cloudTileDensity: { ...prev.cloudTileDensity, more_providers: next },
                              }))
                            }
                            stripe={stripe}
                            slotIndex={slotIndex}
                            nCloudSlots={nCloudSlots}
                            mimeType={MIME_CLOUD_CARD}
                            onReorderCloud={(dragged, target) =>
                              setSourceLayout((prev) => ({
                                ...prev,
                                cloudCardOrder: reorderCloudCards(prev.cloudCardOrder, dragged, target),
                              }))
                            }
                            onMoveCloud={(dir) =>
                              setSourceLayout((p) => ({
                                ...p,
                                cloudCardOrder: moveCloudCard(p.cloudCardOrder, 'more_providers', dir),
                              }))
                            }
                            moreProvidersOpen={moreProvidersOpen}
                            setMoreProvidersOpen={setMoreProvidersOpen}
                            onOpenCustom={() => {
                              setCustomDrawerOpen(true)
                              customGroupRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                            }}
                            onJumpOllama={() =>
                              localGroupRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                            }
                          />
                        )
                      }
                      const c = CLOUD_SOURCES.find((s) => s.id === slotId)
                      if (!c || !settings) return null
                      const stripe = aiSetupCloudCardStripeCss(slotIndex, nCloudSlots)
                      return (
                        <CloudVendorCard
                          key={c.id}
                          source={c}
                          density={sourceLayout.cloudTileDensity[c.id]}
                          onDensityChange={(next) =>
                            setSourceLayout((prev) => ({
                              ...prev,
                              cloudTileDensity: { ...prev.cloudTileDensity, [c.id]: next },
                            }))
                          }
                          stripe={stripe}
                          slotIndex={slotIndex}
                          nCloudSlots={nCloudSlots}
                          slotId={c.id}
                          mimeType={MIME_CLOUD_CARD}
                          onReorderCloud={(dragged, target) =>
                            setSourceLayout((prev) => ({
                              ...prev,
                              cloudCardOrder: reorderCloudCards(prev.cloudCardOrder, dragged, target),
                            }))
                          }
                          onMoveCloud={(dir) =>
                            setSourceLayout((p) => ({
                              ...p,
                              cloudCardOrder: moveCloudCard(p.cloudCardOrder, c.id, dir),
                            }))
                          }
                          providersMap={providersMap}
                          settings={settings}
                          keysOpenai={keysOpenai}
                          keysAnthropic={keysAnthropic}
                          keysGemini={keysGemini}
                          setKeysOpenai={setKeysOpenai}
                          setKeysAnthropic={setKeysAnthropic}
                          setKeysGemini={setKeysGemini}
                          usageSummary={usageSummary}
                          probes={probes}
                          revealSecrets={revealSecrets}
                          setRevealSecrets={setRevealSecrets}
                          openTryOutChat={openTryOutChat}
                          runModelDiscovery={runModelDiscovery}
                          runProviderHealth={runProviderHealth}
                        />
                      )
                    })}
                  </div>
                </div>
              </AiSetupSectionChrome>
            )
          }

          if (sectionId === 'custom') {
            return (
              <AiSetupSectionChrome
                key={sectionId}
                stripeColor={sectionStripe}
                headerRight={
                  <AiSetupTileDensityPictograms
                    value={sourceLayout.customTileDensity}
                    onChange={(next) => setSourceLayout((prev) => ({ ...prev, customTileDensity: next }))}
                    ariaGroupLabel="Custom gateway card density"
                  />
                }
              >
                <div ref={customGroupRef}>
                  <h3
                    className="forge-support"
                    style={{ fontSize: '0.95rem', margin: '0 0 0.5rem', fontWeight: 700, letterSpacing: '0.02em' }}
                  >
                    Custom providers
                  </h3>
                  <p className="forge-support" style={{ fontSize: '0.82rem', margin: '-0.15rem 0 0.55rem', opacity: 0.85 }}>
                    Anything that exposes OpenAI-style HTTP on your network or localhost.
                  </p>
                  <OpenAiCompatGatewayPanel
                    settings={settings}
                    setSettings={setSettings}
                    providersMap={providersMap}
                    usageSummary={usageSummary}
                    diagnostics={diagnostics}
                    probes={probes}
                    setCustomDrawerOpen={setCustomDrawerOpen}
                    openTryOutChat={openTryOutChat}
                    runModelDiscovery={runModelDiscovery}
                    runProviderHealth={runProviderHealth}
                    density={sourceLayout.customTileDensity}
                    onRefreshMetrics={refreshUsageAndDiagnostics}
                  />
                </div>
              </AiSetupSectionChrome>
            )
          }

          return (
            <AiSetupSectionChrome
              key={sectionId}
              stripeColor={sectionStripe}
              headerRight={
                <AiSetupTileDensityPictograms
                  value={sourceLayout.ollamaTileDensity}
                  onChange={(next) => setSourceLayout((prev) => ({ ...prev, ollamaTileDensity: next }))}
                  ariaGroupLabel="Ollama panel density"
                />
              }
            >
              <div ref={localGroupRef}>
                <OllamaLocalPanel
                  ollamaStatus={ollamaStatus}
                  settings={settings}
                  updateTaskRoute={updateTaskRoute}
                  usageSummary={usageSummary}
                  providersMap={providersMap}
                  probes={probes.ollama}
                  ollamaReady={ollamaReady}
                  onRefreshCatalog={refreshOllama}
                  runModelDiscovery={runModelDiscovery}
                  runProviderHealth={runProviderHealth}
                  openTryOutChat={openTryOutChat}
                  density={sourceLayout.ollamaTileDensity}
                />
              </div>
            </AiSetupSectionChrome>
          )
        })}

        <h2 className="forge-support" style={{ fontSize: '1.05rem', margin: '0.25rem 0 0.35rem', fontWeight: 700 }}>
          Workspace defaults
        </h2>
        <p className="forge-support" style={{ fontSize: '0.82rem', marginBottom: '0.55rem', opacity: 0.88, maxWidth: '42rem' }}>
          Choose which connected source answers first when a feature does not override it.
        </p>

        <label className="forge-support" style={{ display: 'block', marginBottom: '0.75rem' }}>
          Primary source
          <select
            className="le-input"
            style={{ display: 'block', marginTop: '0.25rem', maxWidth: '20rem' }}
            value={settings.provider ?? 'openai'}
            onChange={(e) => setSettings({ ...settings, provider: e.target.value })}
          >
            <option value="anthropic">anthropic</option>
            <option value="openai">openai</option>
            <option value="gemini">gemini</option>
            <option value="openai_compatible">openai_compatible</option>
            <option value="ollama">ollama</option>
          </select>
          <span className="forge-support" style={{ display: 'block', fontSize: '0.8rem', marginTop: '0.3rem', opacity: 0.85 }}>
            Studio uses this source when a feature does not pick something more specific. Internal ids match the cards
            above.
          </span>
        </label>

        <h2 className="forge-support" style={{ fontSize: '1.05rem', margin: '1rem 0 0.35rem', fontWeight: 700 }}>
          Multi-source routing
        </h2>
        {allowSmartRouting ? (
          <>
            <fieldset className="forge-support" style={{ border: 'none', margin: '0 0 0.75rem', padding: 0 }}>
              <legend className="forge-support" style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '0.35rem' }}>
                How should Studio choose when several sources are ready?
              </legend>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', fontSize: '0.9rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <input
                    type="radio"
                    name="routing-mode"
                    checked={settings.routing_mode === 'single'}
                    onChange={() => applyRoutingMode('single')}
                  />
                  Single model — one primary source for every Studio surface (optional per-task overrides below).
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <input
                    type="radio"
                    name="routing-mode"
                    checked={settings.routing_mode === 'smart'}
                    onChange={() => applyRoutingMode('smart')}
                  />
                  Smart multi-model — Studio picks a provider per task category from who is connected; quality preset
                  steers depth vs speed.
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <input
                    type="radio"
                    name="routing-mode"
                    checked={settings.routing_mode === 'advanced'}
                    onChange={() => applyRoutingMode('advanced')}
                  />
                  Advanced routing — explicit primary + fallback per task, privacy hints, and full pool / classifier
                  controls.
                </label>
              </div>
            </fieldset>
            {settings.routing_mode === 'smart' ? (
              <div
                className="forge-support"
                style={{
                  marginBottom: '0.85rem',
                  padding: '0.65rem 0.75rem',
                  borderRadius: '10px',
                  border: '1px solid var(--le-border, rgba(255,255,255,0.12))',
                  background: 'color-mix(in srgb, var(--le-panel, #1a1a1f) 90%, transparent)',
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: '0.35rem' }}>Smart quality preset</div>
                <p style={{ fontSize: '0.82rem', margin: '0 0 0.5rem', opacity: 0.88, lineHeight: 1.4 }}>
                  Four stops map to the routing ladder. The preview table updates live as you change this (nothing is
                  written to disk until you save).
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                  {SMART_QUALITY_STOPS.map((stop, idx) => (
                    <button
                      key={stop.tier}
                      type="button"
                      className={smartStopIndexForTier(settings.tier) === idx ? 'le-btn le-btn--primary' : 'le-btn le-btn--secondary'}
                      style={{ fontSize: '0.8rem', padding: '0.25rem 0.55rem' }}
                      onClick={() => setSettings({ ...settings, tier: stop.tier })}
                    >
                      {stop.label}
                    </button>
                  ))}
                </div>
                <p className="le-mono" style={{ fontSize: '0.72rem', margin: '0.45rem 0 0', opacity: 0.75 }}>
                  Tier: {settings.tier ?? 'MED'}
                </p>
              </div>
            ) : null}
          </>
        ) : (
          <p
            className="forge-support"
            style={{ fontSize: '0.86rem', margin: '0 0 0.85rem', opacity: 0.9, maxWidth: '42rem', lineHeight: 1.45 }}
          >
            With a single connected source, Studio routes everything there automatically. Wire <strong>two or more</strong>{' '}
            cards above to unlock smart routing, per-surface overrides, and the quality ladder.
          </p>
        )}

        {connectedCount >= 1 ? (
          <>
        <div
          className="forge-support"
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            gap: '1rem',
            marginBottom: '0.75rem',
            padding: '0.65rem 0',
            borderTop: '1px solid var(--le-border, rgba(255,255,255,0.12))',
            borderBottom: '1px solid var(--le-border, rgba(255,255,255,0.12))',
          }}
        >
          <div>
            <div style={{ fontWeight: 600 }}>Deeper model controls</div>
            <p style={{ fontSize: '0.85rem', margin: '0.25rem 0 0', opacity: 0.9 }}>
              Tiers, pools, and optional classifiers when you care about cost vs depth—not needed for a quick smoke test.
            </p>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexShrink: 0 }}>
            <input
              type="checkbox"
              checked={adv}
              onChange={(e) => {
                const on = e.target.checked
                setSettings({
                  ...settings,
                  advanced_ui: on,
                  routing_mode: on ? (settings.routing_mode === 'single' ? 'advanced' : settings.routing_mode) : 'single',
                  ...(!on ? { auto_model: false, adaptive_autoselection: false, routing_mode: 'single' } : {}),
                })
              }}
            />
            <span className="le-mono" style={{ fontSize: '0.8rem' }}>
              On
            </span>
          </label>
        </div>

        {!adv ? (
          <div style={{ marginBottom: '1rem' }}>
            <ModelIdComboboxField
              inputId={`${primaryModelFieldBaseId}-main-simple`}
              listId={`${primaryModelFieldBaseId}-main-simple-list`}
              label={
                <>
                  Model for requests (primary source: <span className="le-mono">{prov}</span>)
                </>
              }
              hint={primaryModelHint}
              value={settings.main_models?.[prov] ?? ''}
              onChange={setMainModel}
              optionIds={primaryModelOptionIds}
              catalogBusy={primaryCatalog.state === 'loading'}
              style={{ maxWidth: '28rem' }}
            />
            <p className="forge-support" style={{ fontSize: '0.82rem', marginTop: '0.35rem', opacity: 0.85 }}>
              Empty = provider default. The custom gateway has its own field on that card. Turn on{' '}
              <strong>Deeper model controls</strong> for auto-selection, tier sliders, and adaptive routing.
            </p>
          </div>
        ) : (
          <>
            <div
              className="forge-support"
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                gap: '1rem',
                marginBottom: '0.65rem',
              }}
            >
              <div>
                <div style={{ fontWeight: 600 }}>Advanced model autoselection</div>
                <p style={{ fontSize: '0.85rem', margin: '0.25rem 0 0', opacity: 0.9 }}>
                  Pick from tier on the quality ladder instead of a single fixed model
                </p>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexShrink: 0 }}>
                <input
                  type="checkbox"
                  checked={auto}
                  onChange={(e) => {
                    const on = e.target.checked
                    setSettings({
                      ...settings,
                      auto_model: on,
                      ...(!on ? { adaptive_autoselection: false } : {}),
                    })
                  }}
                />
                <span className="le-mono" style={{ fontSize: '0.8rem' }}>
                  Auto
                </span>
              </label>
            </div>

            {!auto ? (
              <div style={{ marginBottom: '1rem' }}>
                <ModelIdComboboxField
                  inputId={`${primaryModelFieldBaseId}-main-adv`}
                  listId={`${primaryModelFieldBaseId}-main-adv-list`}
                  label={
                    <>
                      Default model id (primary source: <span className="le-mono">{prov}</span>)
                    </>
                  }
                  hint={primaryModelHint}
                  value={settings.main_models?.[prov] ?? ''}
                  onChange={setMainModel}
                  optionIds={primaryModelOptionIds}
                  catalogBusy={primaryCatalog.state === 'loading'}
                  style={{ maxWidth: '28rem' }}
                />
              </div>
            ) : settings.routing_mode === 'smart' ? (
              <p
                className="forge-support"
                style={{ fontSize: '0.82rem', marginBottom: '0.75rem', opacity: 0.88, lineHeight: 1.4 }}
              >
                Smart multi-model keeps <strong>Auto</strong> on so each provider can use its pool when you configure
                pools. Use the <strong>four quality stops</strong> in Multi-source routing to steer providers across task
                categories — the preview table updates live.
              </p>
            ) : (
              <>
                <div style={{ margin: '0.75rem 0' }}>
                  <label className="forge-support" style={{ display: 'block' }}>
                    Quality / cost tier: <strong>{settings.tier ?? 'MED'}</strong>
                    <input
                      type="range"
                      min={0}
                      max={5}
                      step={1}
                      value={sliderPos}
                      onChange={(e) => {
                        const pos = parseInt(e.target.value, 10)
                        setSettings({ ...settings, tier: TIERS[5 - pos] ?? 'MED' })
                      }}
                      style={{ width: '100%', maxWidth: '24rem', display: 'block', marginTop: '0.35rem' }}
                    />
                    <div className="forge-support" style={{ fontSize: '0.8rem', marginTop: '0.25rem', opacity: 0.88 }}>
                      <span style={{ display: 'flex', justifyContent: 'space-between', maxWidth: '24rem' }}>
                        <span>Speed</span>
                        <span>Balanced</span>
                        <span>Quality</span>
                        <span>Max</span>
                      </span>
                      <span style={{ display: 'block', marginTop: '0.2rem' }}>
                        Six discrete tier slots — relative to your pool, not dollar cost. The routing preview updates
                        live while you edit (save to persist).
                      </span>
                    </div>
                  </label>
                </div>
                <label className="forge-support" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <input
                    type="checkbox"
                    checked={adapt}
                    onChange={(e) => setSettings({ ...settings, adaptive_autoselection: e.target.checked })}
                  />
                  Adaptive autoselection (classifier call — extra latency and tokens)
                </label>
                {adapt ? (
                  <div
                    style={{
                      marginBottom: '0.85rem',
                      paddingLeft: '0.5rem',
                      borderLeft: '2px solid var(--le-cyan, #5ec8d4)',
                    }}
                  >
                    <p className="forge-support" style={{ fontSize: '0.82rem', marginBottom: '0.5rem' }}>
                      Optional classifier model overrides (empty = built-in defaults: OpenAI{' '}
                      <code className="le-mono">gpt-4o-mini</code>, Gemini <code className="le-mono">gemini-2.0-flash</code>
                      ). Anthropic adaptive routing uses the OpenAI classifier when an OpenAI key is set.
                    </p>
                    <label className="forge-support" style={{ display: 'block', marginBottom: '0.45rem' }}>
                      Classifier model (OpenAI API id)
                      <input
                        type="text"
                        className="le-input"
                        style={{ display: 'block', width: '100%', maxWidth: '28rem', marginTop: '0.2rem' }}
                        value={settings.classifier_models?.openai ?? ''}
                        onChange={(e) => setClassifierModel('openai', e.target.value)}
                        placeholder="gpt-4o-mini"
                        autoComplete="off"
                      />
                    </label>
                    <label className="forge-support" style={{ display: 'block' }}>
                      Classifier model (Gemini API id)
                      <input
                        type="text"
                        className="le-input"
                        style={{ display: 'block', width: '100%', maxWidth: '28rem', marginTop: '0.2rem' }}
                        value={settings.classifier_models?.gemini ?? ''}
                        onChange={(e) => setClassifierModel('gemini', e.target.value)}
                        placeholder="gemini-2.0-flash"
                        autoComplete="off"
                      />
                    </label>
                  </div>
                ) : null}
                <label className="forge-support" style={{ display: 'block', marginBottom: '0.75rem' }}>
                  Refinement downshift (steps toward cheaper model on refine requests)
                  <input
                    type="number"
                    className="le-input"
                    min={0}
                    max={20}
                    value={settings.refine_cheaper_steps ?? 2}
                    onChange={(e) =>
                      setSettings({ ...settings, refine_cheaper_steps: parseInt(e.target.value, 10) || 0 })
                    }
                    style={{ display: 'block', marginTop: '0.25rem', maxWidth: '8rem' }}
                  />
                </label>
              </>
            )}
          </>
        )}
          </>
        ) : (
          <div style={{ marginBottom: '1rem' }}>
            <ModelIdComboboxField
              inputId={`${primaryModelFieldBaseId}-main-pref`}
              listId={`${primaryModelFieldBaseId}-main-pref-list`}
              label={
                <>
                  Preferred model id for primary source <span className="le-mono">{prov}</span> (optional)
                </>
              }
              hint={primaryModelHint}
              value={settings.main_models?.[prov] ?? ''}
              onChange={setMainModel}
              optionIds={primaryModelOptionIds}
              catalogBusy={primaryCatalog.state === 'loading'}
              style={{ maxWidth: '28rem' }}
            />
          </div>
        )}

        <h2 className="forge-support" style={{ fontSize: '1.05rem', marginTop: '1.15rem', fontWeight: 700 }}>
          Routing preview
        </h2>
        <p className="forge-support" style={{ fontSize: '0.82rem', marginBottom: '0.45rem', opacity: 0.88 }}>
          Effective provider and model per Studio task on this host (merged with your draft below). Save to persist;
          refresh if credentials changed outside Studio.
        </p>
        <p className="forge-support" style={{ fontSize: '0.8rem', marginBottom: '0.45rem', opacity: 0.86 }}>
          The right-hand <strong>Lenses Copilot</strong> rail and header <strong>Ask</strong> use the{' '}
          <strong>Search / knowledge answers</strong> task for routing. Pin that row in Advanced mode, or leave it empty
          so your <strong>primary source</strong> and <strong>main model</strong> apply. With <strong>Smart</strong>{' '}
          routing, that task prefers your primary source first (including a custom OpenAI-compatible gateway), then
          falls back to other connected sources. The quality <strong>tier</strong> slider and provider <strong>model
          pools</strong> (when Advanced + auto model are on) pick among listed model ids for the active provider—they do
          not add separate “tier-only” model fields.
        </p>
        <div style={{ overflowX: 'auto', marginBottom: allowSmartRouting ? '0.5rem' : '1rem' }}>
          <table className="forge-support" style={{ fontSize: '0.82rem', borderCollapse: 'collapse', minWidth: '28rem' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '0.3rem 0.5rem', borderBottom: '1px solid var(--le-border)' }}>
                  Task
                </th>
                <th style={{ textAlign: 'left', padding: '0.3rem 0.5rem', borderBottom: '1px solid var(--le-border)' }}>
                  Provider
                </th>
                <th style={{ textAlign: 'left', padding: '0.3rem 0.5rem', borderBottom: '1px solid var(--le-border)' }}>
                  Model
                </th>
                {allowSmartRouting ? (
                  <th style={{ textAlign: 'left', padding: '0.3rem 0.5rem', borderBottom: '1px solid var(--le-border)' }}>
                    How routed
                  </th>
                ) : null}
                {settings.routing_mode === 'advanced' && allowSmartRouting ? (
                  <>
                    <th style={{ textAlign: 'left', padding: '0.3rem 0.5rem', borderBottom: '1px solid var(--le-border)' }}>
                      Fallback
                    </th>
                    <th style={{ textAlign: 'left', padding: '0.3rem 0.5rem', borderBottom: '1px solid var(--le-border)' }}>
                      Privacy
                    </th>
                  </>
                ) : null}
              </tr>
            </thead>
            <tbody>
              {previewRows.map((row) => (
                <tr key={row.task_id}>
                  <td style={{ padding: '0.3rem 0.5rem', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                    {row.label}
                  </td>
                  <td
                    className="le-mono"
                    style={{ padding: '0.3rem 0.5rem', borderBottom: '1px solid rgba(255,255,255,0.08)' }}
                  >
                    {row.provider}
                  </td>
                  <td
                    className="le-mono"
                    style={{ padding: '0.3rem 0.5rem', borderBottom: '1px solid rgba(255,255,255,0.08)' }}
                  >
                    {row.model}
                  </td>
                  {allowSmartRouting ? (
                    <td style={{ padding: '0.3rem 0.5rem', borderBottom: '1px solid rgba(255,255,255,0.08)', maxWidth: '14rem' }}>
                      <span style={{ fontSize: '0.76rem', lineHeight: 1.35 }}>
                        {row.explanation?.startsWith('smart:')
                          ? row.explanation.includes('→')
                            ? `Auto-pick · ${row.explanation.split('→').pop()?.trim() ?? row.explanation}`
                            : row.explanation
                          : row.explanation?.replace(/^advanced:/, '').replace(/_/g, ' ') ?? row.routing ?? '—'}
                      </span>
                      {row.privacy_warn === 'local_unsatisfied' ? (
                        <span style={{ display: 'block', fontSize: '0.7rem', color: 'var(--le-warn, #d96)', marginTop: '0.15rem' }}>
                          Local-only requested but no local gateway is connected.
                        </span>
                      ) : null}
                    </td>
                  ) : null}
                  {settings.routing_mode === 'advanced' && allowSmartRouting ? (
                    <>
                      <td
                        className="le-mono"
                        style={{ padding: '0.3rem 0.5rem', borderBottom: '1px solid rgba(255,255,255,0.08)', fontSize: '0.76rem' }}
                      >
                        {row.fallback_provider
                          ? `${row.fallback_provider}${row.fallback_model ? ` · ${row.fallback_model}` : ''}`
                          : '—'}
                      </td>
                      <td style={{ padding: '0.3rem 0.5rem', borderBottom: '1px solid rgba(255,255,255,0.08)', fontSize: '0.76rem' }}>
                        {row.privacy === 'local_only'
                          ? 'Local only'
                          : row.privacy === 'prefer_local'
                            ? 'Prefer local'
                            : 'Cloud allowed'}
                      </td>
                    </>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {allowSmartRouting && settings.routing_mode === 'single' ? (
          <>
            <h2 className="forge-support" style={{ fontSize: '1.05rem', marginTop: '0.5rem', fontWeight: 700 }}>
              Per-task overrides (optional)
            </h2>
            <p className="forge-support" style={{ fontSize: '0.82rem', marginBottom: '0.5rem', opacity: 0.88 }}>
              Single-model mode follows the primary source unless you pin a provider and/or model stack for a task.
              Extra models in the stack are saved for later routing; only the first is used today. Privacy applies when
              set.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
              {TASK_ROWS.map((t) => {
                const workspacePrimary = (settings.provider ?? 'openai').trim()
                const tr = settings.task_routes?.[t.id] ?? {
                  provider: '',
                  model: '',
                  model_stack: [],
                  privacy: 'cloud_allowed',
                }
                const pr = (tr.privacy as string) || 'cloud_allowed'
                const effProv = (tr.provider || settings.provider || 'openai').trim()
                const stack =
                  Array.isArray(tr.model_stack) && tr.model_stack.length > 0
                    ? tr.model_stack.map((x) => String(x ?? '').trim()).filter(Boolean)
                    : tr.model
                      ? [String(tr.model).trim()].filter(Boolean)
                      : []
                return (
                  <div
                    key={t.id}
                    style={{
                      display: 'grid',
                      gridTemplateColumns:
                        'minmax(9rem, 1fr) minmax(7rem, 0.85fr) minmax(11rem, 1.35fr) minmax(8rem, 0.9fr)',
                      gap: '0.45rem',
                      alignItems: 'start',
                      fontSize: '0.86rem',
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>{t.label}</span>
                    <label className="forge-support" style={{ display: 'block' }}>
                      Provider
                      <select
                        className="le-input"
                        style={{ display: 'block', width: '100%', marginTop: '0.2rem' }}
                        value={tr.provider || ''}
                        onChange={(e) => updateTaskRoute(t.id, { provider: e.target.value })}
                      >
                        <option value="">(primary: {workspacePrimary})</option>
                        <option value="anthropic" disabled={providersMap != null && !providersMap.anthropic}>
                          anthropic
                        </option>
                        <option value="openai" disabled={providersMap != null && !providersMap.openai}>
                          openai
                        </option>
                        <option value="gemini" disabled={providersMap != null && !providersMap.gemini}>
                          gemini
                        </option>
                        <option
                          value="openai_compatible"
                          disabled={providersMap != null && !providersMap.openai_compatible}
                        >
                          openai_compatible
                        </option>
                        <option value="ollama" disabled={providersMap != null && !providersMap.ollama}>
                          ollama
                        </option>
                      </select>
                    </label>
                    <TaskRouteModelStackField
                      taskId={t.id}
                      probeProvider={effProv}
                      providersMap={providersMap}
                      mainModelHint={(settings.main_models?.[effProv] ?? '').trim()}
                      modelStack={stack}
                      onStackChange={(next) => updateTaskRoute(t.id, { model_stack: next })}
                      resolvedRouting={{
                        providerId: effProv,
                        modelSummary: (settings.main_models?.[effProv] ?? '').trim() || 'server default',
                      }}
                    />
                    <label className="forge-support" style={{ display: 'block' }}>
                      Privacy
                      <select
                        className="le-input"
                        style={{ display: 'block', width: '100%', marginTop: '0.2rem' }}
                        value={pr}
                        onChange={(e) => updateTaskRoute(t.id, { privacy: e.target.value })}
                      >
                        <option value="cloud_allowed">Cloud allowed</option>
                        <option value="prefer_local">Prefer local</option>
                        <option value="local_only">Local only</option>
                      </select>
                    </label>
                  </div>
                )
              })}
            </div>
          </>
        ) : null}

        {allowSmartRouting && settings.routing_mode === 'advanced' ? (
          <>
            <h2 className="forge-support" style={{ fontSize: '1.05rem', marginTop: '0.5rem', fontWeight: 700 }}>
              Advanced routing matrix
            </h2>
            <p className="forge-support" style={{ fontSize: '0.82rem', marginBottom: '0.5rem', opacity: 0.88 }}>
              Primary route is used first; on failure Studio tries the fallback once. Privacy steers off cloud when
              local gateways are available.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', marginBottom: '1rem' }}>
              {TASK_ROWS.map((t) => {
                const workspacePrimaryAdv = (settings.provider ?? 'openai').trim()
                const tr = settings.task_routes?.[t.id] ?? {
                  provider: '',
                  model: '',
                  model_stack: [],
                  fallback_provider: '',
                  fallback_model: '',
                  privacy: 'cloud_allowed',
                }
                const pr = (tr.privacy as string) || 'cloud_allowed'
                const effProvAdv = (tr.provider || settings.provider || 'openai').trim()
                const stackAdv =
                  Array.isArray(tr.model_stack) && tr.model_stack.length > 0
                    ? tr.model_stack.map((x) => String(x ?? '').trim()).filter(Boolean)
                    : tr.model
                      ? [String(tr.model).trim()].filter(Boolean)
                      : []
                return (
                  <div
                    key={t.id}
                    style={{
                      border: '1px solid var(--le-border, rgba(255,255,255,0.1))',
                      borderRadius: '8px',
                      padding: '0.55rem 0.65rem',
                      background: 'color-mix(in srgb, var(--le-panel, #1a1a1f) 92%, transparent)',
                    }}
                  >
                    <div style={{ fontWeight: 600, marginBottom: '0.4rem' }}>{t.label}</div>
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(8.5rem, 1fr))',
                        gap: '0.45rem',
                        alignItems: 'end',
                        fontSize: '0.82rem',
                      }}
                    >
                      <label className="forge-support" style={{ display: 'block' }}>
                        Primary provider
                        <select
                          className="le-input"
                          style={{ display: 'block', width: '100%', marginTop: '0.2rem' }}
                          value={tr.provider || ''}
                          onChange={(e) => updateTaskRoute(t.id, { provider: e.target.value })}
                        >
                          <option value="">(workspace primary: {workspacePrimaryAdv})</option>
                          <option value="anthropic" disabled={providersMap != null && !providersMap.anthropic}>
                            anthropic
                          </option>
                          <option value="openai" disabled={providersMap != null && !providersMap.openai}>
                            openai
                          </option>
                          <option value="gemini" disabled={providersMap != null && !providersMap.gemini}>
                            gemini
                          </option>
                          <option
                            value="openai_compatible"
                            disabled={providersMap != null && !providersMap.openai_compatible}
                          >
                            openai_compatible
                          </option>
                          <option value="ollama" disabled={providersMap != null && !providersMap.ollama}>
                            ollama
                          </option>
                        </select>
                      </label>
                      <TaskRouteModelStackField
                        variant="embedded"
                        taskId={t.id}
                        probeProvider={effProvAdv}
                        providersMap={providersMap}
                        mainModelHint={(settings.main_models?.[effProvAdv] ?? '').trim()}
                        modelStack={stackAdv}
                        onStackChange={(next) => updateTaskRoute(t.id, { model_stack: next })}
                        resolvedRouting={{
                          providerId: effProvAdv,
                          modelSummary: (settings.main_models?.[effProvAdv] ?? '').trim() || 'server default',
                        }}
                      />
                      <label className="forge-support" style={{ display: 'block' }}>
                        Fallback provider
                        <select
                          className="le-input"
                          style={{ display: 'block', width: '100%', marginTop: '0.2rem' }}
                          value={tr.fallback_provider || ''}
                          onChange={(e) => updateTaskRoute(t.id, { fallback_provider: e.target.value })}
                        >
                          <option value="">(none)</option>
                          <option value="anthropic" disabled={providersMap != null && !providersMap.anthropic}>
                            anthropic
                          </option>
                          <option value="openai" disabled={providersMap != null && !providersMap.openai}>
                            openai
                          </option>
                          <option value="gemini" disabled={providersMap != null && !providersMap.gemini}>
                            gemini
                          </option>
                          <option
                            value="openai_compatible"
                            disabled={providersMap != null && !providersMap.openai_compatible}
                          >
                            openai_compatible
                          </option>
                          <option value="ollama" disabled={providersMap != null && !providersMap.ollama}>
                            ollama
                          </option>
                        </select>
                      </label>
                      <label className="forge-support" style={{ display: 'block' }}>
                        Fallback model
                        <input
                          type="text"
                          className="le-input"
                          style={{ display: 'block', width: '100%', marginTop: '0.2rem' }}
                          value={tr.fallback_model || ''}
                          onChange={(e) => updateTaskRoute(t.id, { fallback_model: e.target.value })}
                          placeholder="optional id"
                          autoComplete="off"
                        />
                      </label>
                      <label className="forge-support" style={{ display: 'block' }}>
                        Privacy
                        <select
                          className="le-input"
                          style={{ display: 'block', width: '100%', marginTop: '0.2rem' }}
                          value={pr}
                          onChange={(e) => updateTaskRoute(t.id, { privacy: e.target.value })}
                        >
                          <option value="cloud_allowed">Cloud allowed</option>
                          <option value="prefer_local">Prefer local</option>
                          <option value="local_only">Local only</option>
                        </select>
                      </label>
                    </div>
                  </div>
                )
              })}
            </div>
          </>
        ) : null}

        <details
          id="ai-setup-diagnostics"
          className="forge-support"
          style={{ marginTop: '1.25rem', fontSize: '0.88rem' }}
        >
          <summary style={{ cursor: 'pointer', fontWeight: 700 }}>Usage & diagnostics</summary>
          <p style={{ margin: '0.5rem 0 0.45rem', opacity: 0.9 }}>
            Provider health, token totals, chat failures, routing/fallback events, and probe history stay on this host.
            Dollar cost is not inferred locally — see each vendor’s dashboard for billing.
          </p>
          {diagnostics?.cost_note ? (
            <p style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', opacity: 0.85 }}>
              {diagnostics.cost_note}
            </p>
          ) : null}
          <p style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', opacity: 0.85 }}>
            Files:{' '}
            <code className="le-mono">{diagnostics?.usage_path_hint || '.lenses-local/llm-usage.json'}</code>,{' '}
            <code className="le-mono">{diagnostics?.settings_path_hint || '.lenses-local/llm-settings.json'}</code>{' '}
            (gitignored).
          </p>
          {diagnostics?.providers && diagnostics.providers.length > 0 ? (
            <div style={{ overflowX: 'auto', marginBottom: '0.65rem' }}>
              <table className="forge-support" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                <caption style={{ textAlign: 'left', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Provider health & usage
                </caption>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '0.25rem 0.35rem', borderBottom: '1px solid var(--le-border, rgba(255,255,255,0.12))' }}>
                      Source
                    </th>
                    <th style={{ textAlign: 'left', padding: '0.25rem 0.35rem', borderBottom: '1px solid var(--le-border, rgba(255,255,255,0.12))' }}>
                      Config
                    </th>
                    <th style={{ textAlign: 'left', padding: '0.25rem 0.35rem', borderBottom: '1px solid var(--le-border, rgba(255,255,255,0.12))' }}>
                      Last chat OK
                    </th>
                    <th style={{ textAlign: 'left', padding: '0.25rem 0.35rem', borderBottom: '1px solid var(--le-border, rgba(255,255,255,0.12))' }}>
                      Last probe
                    </th>
                    <th style={{ textAlign: 'right', padding: '0.25rem 0.35rem', borderBottom: '1px solid var(--le-border, rgba(255,255,255,0.12))' }}>
                      Tokens (prompt / comp / total)
                    </th>
                    <th style={{ textAlign: 'right', padding: '0.25rem 0.35rem', borderBottom: '1px solid var(--le-border, rgba(255,255,255,0.12))' }}>
                      Ok / attempts
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {diagnostics.providers.map((row) => {
                    const t = row.totals || {}
                    const lp = row.last_probe
                    const probeLine =
                      lp && lp.ts
                        ? `${formatDiagnosticTs(lp.ts)} · ${String(lp.action || '')} · ${lp.ok === false ? 'failed' : 'ok'}`
                        : '—'
                    const cfgParts: string[] = []
                    if (row.connected) cfgParts.push('reachable')
                    else cfgParts.push('not reachable')
                    if (row.has_credential) cfgParts.push('credential/base')
                    else cfgParts.push('no key/base')
                    return (
                      <tr key={row.id}>
                        <td style={{ padding: '0.3rem 0.35rem', verticalAlign: 'top' }}>
                          <strong>{PROVIDER_DIAG_LABELS[row.id] || row.id}</strong>
                        </td>
                        <td style={{ padding: '0.3rem 0.35rem', verticalAlign: 'top' }}>{cfgParts.join(' · ')}</td>
                        <td style={{ padding: '0.3rem 0.35rem', verticalAlign: 'top' }}>
                          {formatDiagnosticTs(row.last_ok_ts ?? null)}
                        </td>
                        <td style={{ padding: '0.3rem 0.35rem', verticalAlign: 'top', maxWidth: '14rem' }}>
                          {probeLine}
                          {lp?.detail ? (
                            <span style={{ display: 'block', opacity: 0.85, fontSize: '0.78rem' }}>{lp.detail}</span>
                          ) : null}
                        </td>
                        <td style={{ padding: '0.3rem 0.35rem', textAlign: 'right', verticalAlign: 'top' }}>
                          {t.prompt_tokens ?? 0} / {t.completion_tokens ?? 0} / {t.total_tokens ?? 0}
                        </td>
                        <td style={{ padding: '0.3rem 0.35rem', textAlign: 'right', verticalAlign: 'top' }}>
                          {t.requests ?? 0} / {t.attempts ?? t.requests ?? 0}
                          {(t.failures ?? 0) > 0 ? (
                            <span style={{ color: 'var(--le-warn, #e8b86a)' }}> ({t.failures} failed)</span>
                          ) : null}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : null}
          {diagnostics?.providers?.some((p) => (p.recent_failures?.length ?? 0) > 0) ? (
            <div style={{ marginBottom: '0.65rem' }}>
              <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Recent chat / API errors</div>
              <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.82rem' }}>
                {diagnostics.providers.flatMap((p) =>
                  (p.recent_failures || []).map((f, i) => (
                    <li key={`${p.id}-${f.ts}-${i}`}>
                      <strong>{PROVIDER_DIAG_LABELS[p.id] || p.id}</strong> · {formatDiagnosticTs(f.ts ?? null)} —{' '}
                      <code className="le-mono">{f.error || 'error'}</code>
                      {f.model ? (
                        <>
                          {' '}
                          · model <code className="le-mono">{f.model}</code>
                        </>
                      ) : null}
                      {f.detail ? <span style={{ opacity: 0.9 }}> — {f.detail}</span> : null}
                    </li>
                  )),
                )}
              </ul>
            </div>
          ) : null}
          {diagnostics?.routing_events && diagnostics.routing_events.length > 0 ? (
            <div style={{ marginBottom: '0.65rem' }}>
              <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Routing & fallback log (recent)</div>
              <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.82rem' }}>
                {diagnostics.routing_events.map((ev, idx) => (
                  <li key={`${ev.ts}-${idx}`}>
                    {formatDiagnosticTs(ev.ts ?? null)} · <strong>{ev.provider}</strong>
                    {ev.ok === false ? ' · failed' : ' · ok'}
                    {ev.routing_source ? (
                      <>
                        {' '}
                        · route <code className="le-mono">{ev.routing_source}</code>
                      </>
                    ) : null}
                    {ev.model ? (
                      <>
                        {' '}
                        · <code className="le-mono">{ev.model}</code>
                      </>
                    ) : null}
                    {ev.fallback_from ? (
                      <>
                        {' '}
                        · fallback from <code className="le-mono">{ev.fallback_from}</code>
                      </>
                    ) : null}
                    {ev.studio_task_id ? (
                      <>
                        {' '}
                        · task {TASK_LABEL_BY_ID[ev.studio_task_id] || ev.studio_task_id}
                      </>
                    ) : null}
                    {ev.error ? (
                      <>
                        {' '}
                        · <code className="le-mono">{ev.error}</code>
                      </>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p style={{ fontSize: '0.8rem', opacity: 0.82, margin: '0 0 0.5rem' }}>
              No routing or fallback events recorded yet (appears after Studio chat with routing metadata).
            </p>
          )}
          {usageSummary && Object.keys(usageSummary.totals || {}).length > 0 ? (
            <ul className="forge-support" style={{ fontSize: '0.86rem', margin: '0.35rem 0 0.5rem', paddingLeft: '1.2rem' }}>
              {Object.entries(usageSummary.totals).map(([pid, t]) => (
                <li key={pid}>
                  <strong>{pid}</strong>: {t.total_tokens ?? 0} total tokens — prompt {t.prompt_tokens ?? 0}, completion{' '}
                  {t.completion_tokens ?? 0} — {t.requests ?? 0} ok / {t.attempts ?? t.requests ?? 0} attempts
                  {(t.failures ?? 0) > 0 ? ` (${t.failures} failed)` : ''}
                </li>
              ))}
            </ul>
          ) : (
            <p className="forge-support" style={{ fontSize: '0.84rem', opacity: 0.88, margin: '0.35rem 0 0.5rem' }}>
              No chat usage yet. After a source responds in <strong>Try Chat</strong>, token totals appear here.
            </p>
          )}
          {usageSummary?.probe_log && usageSummary.probe_log.length > 0 ? (
            <div style={{ marginTop: '0.35rem' }}>
              <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Recent Discover / Health probes</div>
              <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.8rem' }}>
                {usageSummary.probe_log.slice(-12).map((pl, i) => (
                  <li key={`${pl.ts}-${i}`}>
                    {formatDiagnosticTs(pl.ts)} · <strong>{pl.provider}</strong> · {pl.action || 'models'} ·{' '}
                    {pl.ok === false ? 'failed' : 'ok'}
                    {[pl.error, pl.detail].filter(Boolean).length ? (
                      <span style={{ opacity: 0.88 }}> — {[pl.error, pl.detail].filter(Boolean).join(' · ')}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </details>

        <details className="forge-support" style={{ marginTop: '0.85rem', marginBottom: '0.5rem', fontSize: '0.88rem' }}>
          <summary style={{ cursor: 'pointer', fontWeight: 700 }}>Technical details — files, env vars, and URLs</summary>
          <p style={{ margin: '0.5rem 0 0.35rem', opacity: 0.92 }}>
            Settings file (this host): <code className="le-mono">.lenses-local/llm-settings.json</code> — non-empty keys
            in the file override matching environment variables.
          </p>
          <p style={{ margin: '0.35rem 0', fontWeight: 600 }}>Custom / OpenAI-compatible gateway</p>
          <p style={{ margin: '0.35rem 0', opacity: 0.9 }}>
            <code className="le-mono">LENSES_OPENAI_COMPAT_BASE_URL</code> — HTTP(S) origin without{' '}
            <code className="le-mono">/v1</code>; server calls <code className="le-mono">{'{origin}/v1/chat/completions'}</code>.
            Optional <code className="le-mono">LENSES_OPENAI_COMPAT_KEY</code>. You can also save base URL in the JSON from
            this page.
          </p>
          <p style={{ margin: '0.35rem 0', fontWeight: 600 }}>Native Ollama</p>
          <p style={{ margin: '0.35rem 0', opacity: 0.9 }}>
            <code className="le-mono">OLLAMA_BASE_URL</code> — origin for the Ollama daemon (e.g.{' '}
            <code className="le-mono">http://127.0.0.1:11434</code>). Copilot and Chat use the same provider list as this
            page.
          </p>
          <p style={{ margin: '0.35rem 0', fontWeight: 600 }}>Cloud keys (env)</p>
          <p style={{ margin: '0.35rem 0', opacity: 0.9 }}>
            <code className="le-mono">OPENAI_API_KEY</code>, <code className="le-mono">ANTHROPIC_API_KEY</code>,{' '}
            <code className="le-mono">GOOGLE_API_KEY</code> or <code className="le-mono">GEMINI_API_KEY</code>.
          </p>
          <p style={{ margin: '0.35rem 0 0.5rem', fontSize: '0.8rem', opacity: 0.85 }}>
            Example env file: <code className="le-mono">scripts/lenses-openai-compat.env.example</code>
          </p>
        </details>

        <button
          className="le-btn le-btn--primary"
          type="submit"
          disabled={saving}
          style={{ marginTop: '1rem', ...AI_SETUP_PRIMARY_READABLE }}
        >
          {saving ? 'Saving…' : 'Save changes'}
        </button>
      </form>
      {tryOut ? (
        <LlmTryOutChatModal
          open
          onClose={() => setTryOut(null)}
          providerId={tryOut.providerId}
          defaultModelId={tryOut.defaultModelId}
        />
      ) : null}
      <CustomProviderDrawer
        open={customDrawerOpen}
        onClose={() => setCustomDrawerOpen(false)}
        settings={settings}
        compatBaseUrl={compatBaseUrl}
        setCompatBaseUrl={setCompatBaseUrl}
        setCompatUrlTouched={setCompatUrlTouched}
        keysCompat={keysCompat}
        setKeysCompat={setKeysCompat}
        compatKeyInfo={(settings.keys as Record<string, KeyInfo> | undefined)?.openai_compatible}
        onApplied={reloadLlmPanels}
      />
    </>
  )
}
