import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ApiError, apiGetJson, apiPostJson, lensesJsonApiOrigin, qs } from '../api/http'
import {
  CopilotAttemptFailure,
  copilotAttemptFailureFromUnknown,
  formatCopilotExhaustedAttemptsMessage,
  isRetriableCopilotFailure,
} from '../lib/classifyFetchError'
import { resolveUxFailure } from '../lib/uxPageState'
import { useWorkspace } from '../context/WorkspaceContext'
import { useLensesCopilotPageScope } from '../context/LensesCopilotPageScopeContext'
import {
  formatCopilotFailureMessage,
  pickOpenAiCompatFallbackModel,
  readStudioLlmPrefsForHydration,
  sanitizeStudioModelOverride,
  writeMirroredLlmSessionPrefs,
} from '../lib/copilotSessionPrefs'
import { compactRelatedMdPathsForApi } from '../lib/copilotPageEvidence'
import { readCopilotRailMessages, writeCopilotRailMessages } from '../lib/copilotRailHistory'
import { ChatRequestPendingRow } from './chat/ChatRequestPendingRow'
import { CopilotModelSelect } from './copilot/CopilotModelSelect'

type Citation = {
  id?: number
  kind?: string
  title?: string
  ref?: string
  snippet?: string
  source?: string
}

type WriteProposal = {
  id?: string
  tool_id?: string
  title?: string
  payload?: unknown
  created_at?: string
}

type LlmSettingsBrief = {
  ok?: boolean
  settings?: { provider?: string; main_models?: Record<string, string> }
}

const EMPTY_MAIN_MODELS: Record<string, string> = {}

type TurnReflection = {
  answered?: string
  confidence?: number
  /** When present, `confidence` is a satisfaction estimate (API tag name unchanged). */
  confidence_semantic?: string
  agent_note?: string
  suggested_follow_up?: string
  adjust_context?: boolean
  source?: string
}

type CopilotChatRes = {
  ok?: boolean
  text?: string
  error?: string
  detail?: string
  model?: string
  model_fallback_from?: string
  usage?: {
    prompt_tokens?: number
    completion_tokens?: number
    total_tokens?: number
  }
  citations?: Citation[]
  audit_id?: string
  grounding_truncated?: boolean
  write_proposals?: WriteProposal[]
  tool_mode?: string
  turn_reflection?: TurnReflection
  copilot_trace?: {
    strategy?: string
    stopped_reason?: string
    map_results_count?: number
    subtask_count?: number
    truncated?: boolean
  }
}

type CopilotRailMessage = {
  role: 'user' | 'assistant'
  text: string
  citations?: Citation[]
  proposals?: WriteProposal[]
  auditId?: string
  truncated?: boolean
  failed?: boolean
  retryPrompt?: string
  usage?: CopilotChatRes['usage']
  reflection?: TurnReflection
  copilotTrace?: CopilotChatRes['copilot_trace']
}

const STATIC_MUSEUM = import.meta.env.VITE_STATIC_MUSEUM === 'true'

/** Set sessionStorage `lenses.copilot.sse` to `'0'` to force legacy sync POST (no SSE) if proxies block streams. */
function copilotUseSseTransport(): boolean {
  if (typeof window === 'undefined') return true
  try {
    return window.sessionStorage.getItem('lenses.copilot.sse') !== '0'
  } catch {
    return true
  }
}

const PROVIDER_IDS = [
  'anthropic',
  'openai',
  'gemini',
  'openai_compatible',
  'ollama',
] as const

const COPILOT_THINKING_MESSAGES = [
  'Scanning workspace context for your question…',
  'Grounding citations and Studio page context…',
  'Calling the model (token totals update when this turn completes)…',
] as const

/** Transient / model failures; same prompt is retried automatically before showing an error. */
const MAX_TRANSIENT_COPILOT_ATTEMPTS = 3

const COPILOT_RETRY_BACKOFF_MS = (attempt: number) => 400 + attempt * 350

/** SSE wait budget — must exceed slow custom gateways and multi-step Copilot (see LENSES_COPILOT_SSE_MAX_WAIT_SEC). */
const COPILOT_SSE_TIMEOUT_MS = 600_000

function effectiveModelOverride(raw: string): string | undefined {
  const t = raw.trim()
  if (!t) return undefined
  const lower = t.toLowerCase()
  if (lower === 'optional' || lower === 'n/a' || lower === '—' || lower === '-') return undefined
  return t
}

function GearIcon() {
  return (
    <svg
      className="le-copilot-rail__gear-icon"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </svg>
  )
}

/** Full-height grounded copilot column: thread + composer; model/mode in gears popover (Kitchen Sink–aligned panel chrome). */
export function LensesCopilotRail() {
  const pageScope = useLensesCopilotPageScope()
  const ws = useWorkspace()
  const location = useLocation()
  const studioChatMode = useMemo((): 'threads' | 'linear' | undefined => {
    const p = location.pathname || ''
    if (p !== '/chat' && !p.endsWith('/chat')) return undefined
    const q = new URLSearchParams(location.search || '')
    return q.get('chatMode') === 'threads' ? 'threads' : 'linear'
  }, [location.pathname, location.search])

  const topicStartedIso = useRef<string>(new Date().toISOString())
  const topicAnchorMs = useRef<number>(Date.now())
  const [copilotOn, setCopilotOn] = useState<boolean | null>(null)
  const [providers, setProviders] = useState<Record<string, boolean> | null>(null)
  const [provider, setProvider] = useState<string>('ollama')
  const [modelOverride, setModelOverride] = useState('')
  const [toolMode, setToolMode] = useState<'read_only' | 'propose_writes'>('read_only')
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<CopilotRailMessage[]>([])
  const [railHydrated, setRailHydrated] = useState(false)
  const [llmSessionHydrated, setLlmSessionHydrated] = useState(false)
  const [loading, setLoading] = useState(false)
  /** Cumulative token totals from multi-step Copilot SSE (per completed LLM round). */
  const [streamUsage, setStreamUsage] = useState<{
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  } | null>(null)
  const [thinkingIdx, setThinkingIdx] = useState(0)
  const [streamProgress, setStreamProgress] = useState<string | null>(null)
  const [pendingSince, setPendingSince] = useState<number | null>(null)
  const [banner, setBanner] = useState<string | null>(null)
  const [proposalReadyId, setProposalReadyId] = useState<string | null>(null)
  const [mainModelsHint, setMainModelsHint] = useState<Record<string, string>>(EMPTY_MAIN_MODELS)
  const [settingsOpen, setSettingsOpen] = useState(false)
  /** Latest Copilot turn usage when the provider returned token fields (shown above composer). */
  const [lastReplyUsage, setLastReplyUsage] = useState<CopilotChatRes['usage'] | null>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const gearBtnRef = useRef<HTMLButtonElement>(null)
  const copilotEsRef = useRef<EventSource | null>(null)

  const threadEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (pageScope.defaultQuery !== undefined && pageScope.defaultQuery !== '') {
      setInput(pageScope.defaultQuery)
    }
  }, [pageScope.defaultQuery])

  useEffect(() => {
    const root = ws.state?.workspace_root?.trim() || ''
    const route = (pageScope.route || 'default').trim() || 'default'
    setRailHydrated(false)
    const loaded = readCopilotRailMessages(root || undefined, route) as CopilotRailMessage[]
    setMessages(loaded)
    setRailHydrated(true)
  }, [ws.state?.workspace_root, pageScope.route])

  useEffect(() => {
    if (!railHydrated) return
    const root = ws.state?.workspace_root?.trim() || ''
    const route = (pageScope.route || 'default').trim() || 'default'
    writeCopilotRailMessages(root || undefined, route, messages)
  }, [messages, railHydrated, ws.state?.workspace_root, pageScope.route])

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  useEffect(() => {
    if (!loading) return
    const id = window.setInterval(() => {
      setThinkingIdx((i) => (i + 1) % COPILOT_THINKING_MESSAGES.length)
    }, 2400)
    return () => window.clearInterval(id)
  }, [loading])

  useEffect(() => {
    let cancel = false
    const ac = new AbortController()
    setLlmSessionHydrated(false)
    const workspaceRoot = ws.state?.workspace_root?.trim() || ''
    Promise.all([
      apiGetJson<{ ok?: boolean; enabled?: boolean }>('/api/sdlc-copilot/enabled', { signal: ac.signal }).catch(
        () => ({
          ok: false,
          enabled: false,
        }),
      ),
      apiGetJson<{ providers?: Record<string, boolean> }>('/api/llm/providers', { signal: ac.signal }).catch(
        () => ({}) as { providers?: Record<string, boolean> },
      ),
      apiGetJson<LlmSettingsBrief>('/api/llm/settings', { signal: ac.signal }).catch(
        () => ({}) as LlmSettingsBrief,
      ),
    ])
      .then(([en, prov, st]) => {
        if (cancel) return
        setCopilotOn(en.enabled === true && en.ok === true)
        const mainModels =
          st.settings?.main_models && typeof st.settings.main_models === 'object'
            ? (st.settings.main_models as Record<string, string>)
            : {}
        const saved = readStudioLlmPrefsForHydration(workspaceRoot || undefined)
        if (saved && typeof saved.model === 'string') {
          const preferredProvider = (
            saved.provider ||
            (st.settings?.provider || '').trim().toLowerCase() ||
            'openai_compatible'
          ).trim().toLowerCase()
          const cleaned = sanitizeStudioModelOverride(saved.model, mainModels[preferredProvider])
          setModelOverride(cleaned)
          if (cleaned !== saved.model.trim()) {
            writeMirroredLlmSessionPrefs(workspaceRoot || undefined, { model: cleaned })
          }
        }
        if (saved?.toolMode === 'propose_writes' || saved?.toolMode === 'read_only') setToolMode(saved.toolMode)

        const pmap = prov.providers
        if (pmap) {
          setProviders(pmap)
          const preferred = (st.settings?.provider || '').trim().toLowerCase()
          const fromServer =
            preferred && pmap[preferred]
              ? preferred
              : (PROVIDER_IDS.find((id) => pmap[id]) as string | undefined) || 'ollama'
          const sp = (saved?.provider || '').trim().toLowerCase()
          const savedIsKnown =
            Boolean(sp) && (PROVIDER_IDS as readonly string[]).includes(sp)
          // Prefer session choice even when that provider is temporarily "off" (e.g. Ollama not up yet);
          // otherwise we snap to AI Setup (often openai) and overwrite prefs on the next save effect.
          if (savedIsKnown) setProvider(sp)
          else setProvider(fromServer)
        }
        if (st.settings?.main_models && typeof st.settings.main_models === 'object') {
          setMainModelsHint(st.settings.main_models as Record<string, string>)
        }
        if (!cancel) setLlmSessionHydrated(true)
      })
      .catch(() => {
        if (!cancel) {
          setCopilotOn(false)
          setLlmSessionHydrated(true)
        }
      })
    return () => {
      cancel = true
      ac.abort()
    }
  }, [ws.state?.workspace_root])

  useEffect(() => {
    if (!settingsOpen) return
    function onKey(ev: KeyboardEvent) {
      if (ev.key === 'Escape') setSettingsOpen(false)
    }
    function onPointerDown(ev: PointerEvent) {
      const t = ev.target as Node
      if (popoverRef.current?.contains(t)) return
      if (gearBtnRef.current?.contains(t)) return
      setSettingsOpen(false)
    }
    window.addEventListener('keydown', onKey)
    window.addEventListener('pointerdown', onPointerDown, true)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('pointerdown', onPointerDown, true)
    }
  }, [settingsOpen])

  useEffect(() => {
    if (!providers || !llmSessionHydrated) return
    const root = ws.state?.workspace_root?.trim() || ''
    writeMirroredLlmSessionPrefs(root || undefined, {
      provider,
      model: modelOverride,
      toolMode,
    })
  }, [provider, modelOverride, toolMode, providers, ws.state?.workspace_root, llmSessionHydrated])

  /** When AI Setup has a main model, keep override empty so the server uses that default. */
  useEffect(() => {
    if (!llmSessionHydrated) return
    if (provider !== 'openai_compatible' || !providers?.['openai_compatible']) return
    if (modelOverride.trim()) return
    const hint = (mainModelsHint['openai_compatible'] || '').trim()
    if (hint) return
    let cancelled = false
    void apiPostJson<{ ok?: boolean; models?: string[] }>('/api/llm/provider-probe', {
      provider: 'openai_compatible',
      action: 'models',
    }).then((out) => {
      if (cancelled || !out.ok || !Array.isArray(out.models) || out.models.length === 0) return
      const pick = pickOpenAiCompatFallbackModel(out.models.map((x) => String(x)))
      if (pick) setModelOverride(pick)
    })
    return () => {
      cancelled = true
    }
  }, [provider, providers, modelOverride, mainModelsHint, llmSessionHydrated])

  const startNewTopic = useCallback(async () => {
    if (messages.length === 0) {
      topicStartedIso.current = new Date().toISOString()
      topicAnchorMs.current = Date.now()
      setBanner(null)
      return
    }
    const ended = new Date().toISOString()
    const dwellApprox = Math.max(0, Math.round((Date.now() - topicAnchorMs.current) / 1000))
    let sumPrompt = 0
    let sumCompletion = 0
    let sumTotal = 0
    for (const m of messages) {
      const u = m.usage
      if (u) {
        sumPrompt += Number(u.prompt_tokens) || 0
        sumCompletion += Number(u.completion_tokens) || 0
        sumTotal += Number(u.total_tokens) || 0
      }
    }
    const turns = messages.map((m) => ({
      role: m.role,
      text_excerpt: m.text.slice(0, 2000),
      usage: m.usage,
    }))
    const tags: string[] = [
      pageScope.route ? `route:${pageScope.route}` : 'route:unknown',
      studioChatMode ? `studio_chat:${studioChatMode}` : 'studio_chat:off',
    ]
    const ps0 = (pageScope.projectSlug || '').trim()
    if (ps0) tags.push(`project:${ps0}`)
    const topicId =
      typeof globalThis.crypto !== 'undefined' && 'randomUUID' in globalThis.crypto
        ? globalThis.crypto.randomUUID()
        : `topic-${Date.now()}`
    try {
      await apiPostJson<{ ok?: boolean; markdown?: string | null }>('/api/sdlc-copilot/topic-archive', {
        topic_id: topicId,
        started_at_iso: topicStartedIso.current,
        ended_at_iso: ended,
        route: pageScope.route,
        project_slug: pageScope.projectSlug || undefined,
        turns,
        totals: {
          prompt_tokens: sumPrompt,
          completion_tokens: sumCompletion,
          total_tokens: sumTotal || sumPrompt + sumCompletion,
          dwell_approx_sec: dwellApprox,
        },
        tags,
        title: 'Copilot topic',
        summary: `Wrapped ${messages.length} turns (route ${pageScope.route || 'unknown'}).`,
      })
    } catch {
      /* offline */
    }
    topicStartedIso.current = new Date().toISOString()
    topicAnchorMs.current = Date.now()
    setMessages([])
    setLastReplyUsage(null)
    setBanner(
      'New topic started. A snapshot was appended to .lenses-local/copilot-topics.jsonl (and a Markdown file under copilot-discussions/ when possible).',
    )
  }, [messages, pageScope.projectSlug, pageScope.route, studioChatMode])

  const runSend = useCallback(
    async (textRaw: string, opts?: { skipUserAppend?: boolean }) => {
      const text = textRaw.trim()
      if (!text || loading || copilotOn !== true) return
      setBanner(null)
      if (!opts?.skipUserAppend) {
        setMessages((m) => [...m, { role: 'user', text }])
      }
      setThinkingIdx(0)
      setStreamProgress(null)
      setStreamUsage(null)
      setPendingSince(Date.now())
      setLoading(true)
      const failBody =
        'Something blocked that response. Retry with a shorter question or confirm your provider is configured.'

      const body: Record<string, unknown> = {
        provider,
        message: text,
        refine: false,
        tool_mode: toolMode,
        route: pageScope.route,
        studio_task_id: 'search_knowledge',
        project_slug: pageScope.projectSlug || undefined,
        entity_id: pageScope.entityId || undefined,
        scope_site: pageScope.scopeSite || undefined,
      }
      const pcs = pageScope.pageContextSummary?.trim()
      if (pcs) body.page_context_summary = pcs
      const mdApi = compactRelatedMdPathsForApi(pageScope.relatedMdRelPaths)
      if (mdApi) body.related_md_rel_paths = mdApi
      if (studioChatMode === 'threads' || studioChatMode === 'linear') {
        body.studio_chat_mode = studioChatMode
      }
      const mo = effectiveModelOverride(modelOverride)
      if (mo) body.model = mo
      body.stream = copilotUseSseTransport()

      try {
        let lastFailureMessage = failBody
        attemptLoop: for (let attempt = 1; attempt <= MAX_TRANSIENT_COPILOT_ATTEMPTS; attempt++) {
          if (attempt > 1) {
            setStreamUsage(null)
            setStreamProgress(`Retrying (${attempt}/${MAX_TRANSIENT_COPILOT_ATTEMPTS})…`)
            await new Promise<void>((r) => window.setTimeout(r, COPILOT_RETRY_BACKOFF_MS(attempt - 1)))
          }
          try {
            const applyRes = (res: CopilotChatRes) => {
              if (res.ok && res.text?.trim()) {
                const fbFrom = (res.model_fallback_from || '').trim()
                if (fbFrom) {
                  setModelOverride('')
                  const root = ws.state?.workspace_root?.trim() || ''
                  writeMirroredLlmSessionPrefs(root || undefined, { model: '' })
                  setBanner(
                    `Model ${fbFrom} crashed on the gateway; used AI Setup default${res.model ? ` (${res.model})` : ''} instead.`,
                  )
                }
                const u = res.usage
                if (
                  u &&
                  (typeof u.total_tokens === 'number' ||
                    typeof u.prompt_tokens === 'number' ||
                    typeof u.completion_tokens === 'number')
                ) {
                  setLastReplyUsage(u)
                }
                setMessages((m) => [
                  ...m,
                  {
                    role: 'assistant',
                    text: res.text!,
                    citations: res.citations,
                    proposals: res.write_proposals,
                    auditId: res.audit_id,
                    truncated: res.grounding_truncated,
                    usage: res.usage,
                    reflection: res.turn_reflection,
                    copilotTrace: res.copilot_trace,
                  },
                ])
                return
              }
              const msg = formatCopilotFailureMessage(res, failBody)
              throw new CopilotAttemptFailure(msg, isRetriableCopilotFailure(res))
            }

            if (STATIC_MUSEUM) {
              const res = await apiPostJson<CopilotChatRes>('/api/sdlc-copilot/chat', body)
              applyRes(res)
              return
            }
            if (body.stream === false) {
              const res = await apiPostJson<CopilotChatRes>('/api/sdlc-copilot/chat', body)
              applyRes(res)
              return
            }
            const start = await apiPostJson<{ ok?: boolean; session_id?: string }>(
              '/api/sdlc-copilot/chat-async',
              body,
            )
            if (!start.ok || !start.session_id) {
              throw new CopilotAttemptFailure(failBody, true)
            }
            const origin = lensesJsonApiOrigin()
            const streamPath = `/api/sdlc-copilot/chat-stream${qs({ session_id: start.session_id })}`
            const streamUrl = origin ? `${origin.replace(/\/$/, '')}${streamPath}` : streamPath
            await new Promise<void>((resolve, reject) => {
              let settled = false
              const settle = () => {
                if (settled) return
                settled = true
                resolve()
              }
              const fail = (msg: string, retriable = true) => {
                if (settled) return
                settled = true
                reject(new CopilotAttemptFailure(msg, retriable))
              }
              const to = window.setTimeout(
                () =>
                  fail(
                    'Copilot stream timed out — slow models may need up to a few minutes.',
                    true,
                  ),
                COPILOT_SSE_TIMEOUT_MS,
              )
              const es = new EventSource(streamUrl, { withCredentials: true } as EventSourceInit)
              copilotEsRef.current = es
              es.onmessage = (ev) => {
                try {
                  const row = JSON.parse(ev.data) as Record<string, unknown>
                  if (row.done === true) {
                    window.clearTimeout(to)
                    es.close()
                    copilotEsRef.current = null
                    settle()
                    return
                  }
                  if (row.ok === false && !row.event) {
                    window.clearTimeout(to)
                    es.close()
                    copilotEsRef.current = null
                    const errPayload = {
                      ok: false,
                      error: String(row.error || 'stream_error'),
                      detail: typeof row.detail === 'string' ? row.detail : undefined,
                    }
                    fail(
                      formatCopilotFailureMessage(errPayload, failBody),
                      isRetriableCopilotFailure(errPayload),
                    )
                    return
                  }
                  const event = row.event as Record<string, unknown> | undefined
                  if (!event || typeof event !== 'object') return
                  const typ = String(event.type || '')
                  const payload = (event.payload || {}) as Record<string, unknown>
                  if (typ === 'usage') {
                    const cum = payload.cumulative as Record<string, unknown> | undefined
                    if (cum && typeof cum === 'object') {
                      setStreamUsage({
                        prompt_tokens: Number(cum.prompt_tokens) || 0,
                        completion_tokens: Number(cum.completion_tokens) || 0,
                        total_tokens: Number(cum.total_tokens) || 0,
                      })
                    }
                    return
                  }
                  if (typ === 'plan') {
                    const n = Number(payload.subtask_count) || 0
                    setStreamProgress(
                      n > 0
                        ? `Planning ${n} scoped lookups (${String(payload.strategy || 'map-reduce')})…`
                        : 'Planning scoped lookups…',
                    )
                    return
                  }
                  if (typ === 'subtask_start') {
                    setStreamProgress(
                      `Summarizing ${payload.index}/${payload.total}: ${String(payload.label || 'entry')}…`,
                    )
                    return
                  }
                  if (typ === 'subtask_end') {
                    return
                  }
                  if (typ === 'thought') {
                    const msg = String(payload.message || '').trim()
                    if (msg) setStreamProgress(msg)
                    return
                  }
                  if (typ === 'final') {
                    window.clearTimeout(to)
                    es.close()
                    copilotEsRef.current = null
                    const res = payload.result as CopilotChatRes
                    try {
                      applyRes(res)
                      settle()
                    } catch (e) {
                      fail(
                        e instanceof CopilotAttemptFailure
                          ? e.userMessage
                          : formatCopilotFailureMessage(res, failBody),
                        e instanceof CopilotAttemptFailure
                          ? e.retriable
                          : isRetriableCopilotFailure(res),
                      )
                    }
                    return
                  }
                  if (typ === 'error') {
                    window.clearTimeout(to)
                    es.close()
                    copilotEsRef.current = null
                    const errPayload = {
                      ok: false,
                      error: 'llm_provider_error',
                      detail: String(payload.message || 'Copilot error'),
                    }
                    fail(
                      formatCopilotFailureMessage(errPayload, failBody),
                      isRetriableCopilotFailure(errPayload),
                    )
                  }
                } catch {
                  /* ignore malformed chunk */
                }
              }
              es.onerror = () => {
                window.clearTimeout(to)
                es.close()
                copilotEsRef.current = null
                if (!settled) {
                  fail('SSE connection lost', true)
                }
              }
            })
            return
          } catch (err) {
            const failure = copilotAttemptFailureFromUnknown(err, failBody)
            lastFailureMessage = failure.userMessage
            if (failure.retriable && attempt < MAX_TRANSIENT_COPILOT_ATTEMPTS) {
              continue attemptLoop
            }
            let assistantText = failure.userMessage
            if (err instanceof ApiError && err.status === 403) {
              assistantText =
                toolMode === 'propose_writes'
                  ? 'Write proposals need a signed-in session with project access. Try read-only or open a project dashboard.'
                  : 'This endpoint is not available from how you opened Lenses.'
            } else if (failure.retriable && attempt >= MAX_TRANSIENT_COPILOT_ATTEMPTS) {
              assistantText = formatCopilotExhaustedAttemptsMessage(
                lastFailureMessage,
                MAX_TRANSIENT_COPILOT_ATTEMPTS,
              )
            }
            setBanner(assistantText)
            setMessages((m) => [
              ...m,
              { role: 'assistant', text: assistantText, failed: true, retryPrompt: text },
            ])
            return
          }
        }
      } finally {
        copilotEsRef.current?.close()
        copilotEsRef.current = null
        setStreamUsage(null)
        setStreamProgress(null)
        setLoading(false)
        setPendingSince(null)
      }
    },
    [
      copilotOn,
      loading,
      modelOverride,
      pageScope.entityId,
      pageScope.pageContextSummary,
      pageScope.projectSlug,
      pageScope.route,
      pageScope.scopeSite,
      (pageScope.relatedMdRelPaths ?? [])
        .map((s) => s.trim())
        .filter(Boolean)
        .sort()
        .join('\n'),
      provider,
      toolMode,
      studioChatMode,
    ],
  )

  const submitFromComposer = useCallback(() => {
    const text = input.trim()
    if (!text || loading || copilotOn !== true) return
    setInput('')
    void runSend(text)
  }, [copilotOn, input, loading, runSend])

  const handleRetry = useCallback(
    (retryPrompt: string) => {
      setBanner(null)
      setMessages((m) => {
        if (m.length === 0) return m
        const last = m[m.length - 1]
        if (last.role === 'assistant' && last.failed) return m.slice(0, -1)
        return m
      })
      void runSend(retryPrompt, { skipUserAppend: true })
    },
    [runSend],
  )

  const onComposerSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      submitFromComposer()
    },
    [submitFromComposer],
  )

  const commitProposal = useCallback(async (proposalId: string) => {
    setBanner(null)
    try {
      const r = await apiPostJson<{ ok?: boolean; error?: string; export_path?: string }>(
        '/api/sdlc-copilot/commit-proposal',
        { proposal_id: proposalId, confirm: true },
      )
      if (r.ok) {
        setBanner('Draft exported to your local Lenses workspace data.')
        setProposalReadyId(null)
      } else {
        setBanner('That export could not be completed. Confirm permissions and try again.')
      }
    } catch (err) {
      const ux = resolveUxFailure(err)
      setBanner(ux.description)
    }
  }, [])

  if (copilotOn === null) {
    return (
      <aside className="le-copilot-rail" aria-label="Lenses Copilot">
        <div className="le-copilot-rail__header">
          <h2 className="le-copilot-rail__title">Lenses Copilot</h2>
        </div>
        <p className="le-copilot-rail__muted">Checking availability…</p>
      </aside>
    )
  }

  if (!copilotOn) {
    return null
  }

  /** defaultOpen: sources panel expanded on Ask */
  const sourcesExpanded = true

  return (
    <aside className="le-copilot-rail" aria-label="Lenses Copilot">
      <div className="le-copilot-rail__header">
        <div className="le-copilot-rail__head-text">
          <h2 className="le-copilot-rail__title" id="le-copilot-rail-h">
            Lenses Copilot
          </h2>
          <p className="le-copilot-rail__subtitle">
            Grounded on your workspace scan. Citations point to workspace <strong>context</strong> (docs and
            links); exports stay drafts until you confirm.
          </p>
          <p className="le-copilot-rail__full-chat-links">
            <Link to="/chat">Chat</Link>
            <span aria-hidden="true"> · </span>
            <Link to="/chat?chatMode=threads">Threads</Link>
            <span className="le-copilot-rail__full-chat-links-note">
              {' '}
              — multi-turn on the Chat page (Threads = one conversation per Studio page)
            </span>
          </p>
          <p className="le-copilot-rail__topic-row">
            <button
              type="button"
              className="le-btn le-btn--small"
              onClick={() => void startNewTopic()}
              disabled={loading}
            >
              New topic
            </button>
            <span className="le-copilot-rail__full-chat-links-note">
              {' '}
              Wrap this rail thread, save a snapshot, and clear messages.
            </span>
          </p>
          {(pageScope.projectSlug || '').trim() ? (
            <div className="le-copilot-rail__project-scope" role="status">
              <span className="le-copilot-rail__project-scope-label">Project scope</span>
              <code className="le-copilot-rail__project-scope-code">{pageScope.projectSlug}</code>
              {pageScope.projectScopeConfirmed ? (
                <span className="le-copilot-rail__project-scope-note">Listed in workspace scan</span>
              ) : (
                <span className="le-copilot-rail__project-scope-note le-copilot-rail__project-scope-note--muted">
                  Confirm folder under workspace if needed
                </span>
              )}
            </div>
          ) : null}
        </div>
        <div className="le-copilot-rail__header-actions">
          <button
            ref={gearBtnRef}
            type="button"
            className={`le-copilot-rail__icon-btn${settingsOpen ? ' le-copilot-rail__icon-btn--active' : ''}`}
            aria-expanded={settingsOpen}
            aria-controls="le-copilot-rail-settings"
            aria-label="Model and mode settings"
            onClick={() => setSettingsOpen((o) => !o)}
          >
            <GearIcon />
          </button>
          {settingsOpen ? (
            <div
              ref={popoverRef}
              id="le-copilot-rail-settings"
              className="le-copilot-rail__popover"
              role="dialog"
              aria-labelledby="le-copilot-rail-settings-h"
            >
              <h3 className="le-copilot-rail__popover-title" id="le-copilot-rail-settings-h">
                Model &amp; mode
              </h3>
              <p className="le-copilot-rail__popover-hint">
                Defaults follow{' '}
                <Link to="/settings/llm" onClick={() => setSettingsOpen(false)}>
                  AI Setup
                </Link>
                . Keep the model on the first option unless you need a different id for this session (dropdown only).
              </p>
              <label className="le-copilot-rail__field">
                <span className="le-copilot-rail__label">Provider</span>
                <select
                  className="le-select le-copilot-rail__control"
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  disabled={loading}
                >
                  {PROVIDER_IDS.map((id) => (
                    <option key={id} value={id} disabled={Boolean(providers && !providers[id])}>
                      {id}
                      {providers && !providers[id] ? ' (off)' : ''}
                    </option>
                  ))}
                </select>
              </label>
              <label className="le-copilot-rail__field">
                <span className="le-copilot-rail__label">Model (optional)</span>
                <CopilotModelSelect
                  className="le-select le-input le-copilot-rail__control"
                  provider={provider}
                  providers={providers}
                  modelOverride={modelOverride}
                  onModelOverride={setModelOverride}
                  setupDefaultModelId={(mainModelsHint[provider] || '').trim()}
                  disabled={loading}
                />
              </label>
              <p className="le-copilot-rail__popover-hint" style={{ marginTop: '0.35rem' }}>
                Page-scoped <strong>Threads</strong> live on{' '}
                <Link to="/chat?chatMode=threads" onClick={() => setSettingsOpen(false)}>
                  Chat → Threads
                </Link>
                .
              </p>
              <label className="le-copilot-rail__field">
                <span className="le-copilot-rail__label">Copilot mode</span>
                <select
                  className="le-select le-copilot-rail__control"
                  value={toolMode}
                  onChange={(e) =>
                    setToolMode(e.target.value === 'propose_writes' ? 'propose_writes' : 'read_only')
                  }
                  disabled={loading}
                >
                  <option value="read_only">Answers only</option>
                  <option value="propose_writes">Propose write drafts</option>
                </select>
              </label>
              {toolMode === 'propose_writes' && !(pageScope.projectSlug || '').trim() ? (
                <p className="le-copilot-rail__warn">
                  Open a project-scoped page for write proposals when RBAC is on.
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      {banner ? <p className="le-copilot-rail__banner">{banner}</p> : null}

      <div className="le-copilot-rail__usage-strip" aria-live="polite">
        {lastReplyUsage &&
        (typeof lastReplyUsage.total_tokens === 'number' ||
          typeof lastReplyUsage.prompt_tokens === 'number' ||
          typeof lastReplyUsage.completion_tokens === 'number') ? (
          <div className="le-copilot-rail__usage-strip-body">
            <strong className="le-copilot-rail__usage-strip-strong">Token usage (last reply)</strong>
            {': '}
            {typeof lastReplyUsage.total_tokens === 'number' ? (
              <span>{lastReplyUsage.total_tokens.toLocaleString()} total</span>
            ) : null}
            {typeof lastReplyUsage.prompt_tokens === 'number' &&
            typeof lastReplyUsage.completion_tokens === 'number' ? (
              <span className="le-muted">
                {' '}
                ({lastReplyUsage.prompt_tokens.toLocaleString()} in +{' '}
                {lastReplyUsage.completion_tokens.toLocaleString()} out)
              </span>
            ) : null}
          </div>
        ) : (
          <>
            <strong className="le-copilot-rail__usage-strip-strong">Token usage</strong>
            <p className="le-copilot-rail__usage-strip-detail">
              None yet. Totals appear when the provider returns usage on the last reply (separate from context
              citations below).
            </p>
          </>
        )}
      </div>

      <div className="le-copilot-rail__thread" role="log" aria-live="polite" aria-relevant="additions">
        {messages.length === 0 ? (
          <p className="le-copilot-rail__empty">
            Ask about delivery, quality, release readiness, or risks. Use{' '}
            <span className="le-copilot-rail__kbd">Ask</span> in the header for a quick one-off question.
          </p>
        ) : (
          <ul className="le-copilot-rail__messages">
            {messages.map((m, i) => (
              <li
                key={i}
                className={`le-copilot-rail__bubble${m.role === 'user' ? ' le-copilot-rail__bubble--user' : ' le-copilot-rail__bubble--assistant'}${m.role === 'assistant' && m.failed ? ' le-copilot-rail__bubble--failed' : ''}`}
              >
                <div className="le-copilot-rail__bubble-role">{m.role === 'user' ? 'You' : 'Lenses'}</div>
                <div className="le-copilot-rail__bubble-body">{m.text}</div>
                {m.role === 'assistant' && m.reflection ? (
                  <details className="le-copilot-rail__reflection">
                    <summary>
                      Agent note
                      {m.reflection.answered ? ` · answered: ${m.reflection.answered}` : ''}
                      {typeof m.reflection.confidence === 'number'
                        ? ` · satisfaction ${Math.round(m.reflection.confidence * 100)}%`
                        : ''}
                    </summary>
                    <p className="le-copilot-rail__reflection-hint forge-support">
                      Satisfaction is an estimate of whether your request was met (same{' '}
                      <code className="le-mono">confidence</code> field in the API)—not a score of factual
                      correctness.
                    </p>
                    <p className="le-copilot-rail__reflection-note">{m.reflection.agent_note}</p>
                    {m.reflection.suggested_follow_up ? (
                      <p className="le-copilot-rail__reflection-follow">
                        <strong>Next:</strong> {m.reflection.suggested_follow_up}
                      </p>
                    ) : null}
                    {m.reflection.adjust_context ? (
                      <div className="le-copilot-rail__reflection-actions">
                        <button
                          type="button"
                          className="le-btn le-btn--small le-btn--primary"
                          onClick={() =>
                            setInput(
                              'What additional workspace files or Studio pages should we add to the context so you can answer?',
                            )
                          }
                        >
                          Ask to widen context
                        </button>
                        <button
                          type="button"
                          className="le-btn le-btn--small"
                          onClick={() =>
                            setInput(
                              'What single clarifying question would most improve your next answer about this topic?',
                            )
                          }
                        >
                          Ask for a clarifying question
                        </button>
                      </div>
                    ) : null}
                  </details>
                ) : null}
                {m.role === 'assistant' && m.failed && m.retryPrompt ? (
                  <div className="le-copilot-rail__retry-row">
                    <button
                      type="button"
                      className="le-btn le-btn--small le-btn--primary"
                      onClick={() => handleRetry(m.retryPrompt!)}
                      disabled={loading}
                    >
                      Retry
                    </button>
                  </div>
                ) : null}
                {m.role === 'assistant' && m.auditId ? (
                  <p className="le-copilot-rail__bubble-meta">
                    Audit <code className="le-mono">{m.auditId}</code>
                    {m.truncated ? ' · grounding trimmed' : null}
                    {m.copilotTrace?.strategy ? (
                      <>
                        {' '}
                        · {m.copilotTrace.strategy}
                        {typeof m.copilotTrace.subtask_count === 'number'
                          ? ` (${m.copilotTrace.subtask_count} slices)`
                          : ''}
                      </>
                    ) : null}
                  </p>
                ) : null}
                {m.role === 'assistant' &&
                m.usage &&
                (typeof m.usage.total_tokens === 'number' ||
                  typeof m.usage.prompt_tokens === 'number' ||
                  typeof m.usage.completion_tokens === 'number') ? (
                  <p className="le-copilot-rail__bubble-meta le-copilot-rail__bubble-meta--tokens">
                    Tokens (this reply)
                    {typeof m.usage.total_tokens === 'number' ? `: ${m.usage.total_tokens} total` : ''}
                    {typeof m.usage.prompt_tokens === 'number' &&
                    typeof m.usage.completion_tokens === 'number'
                      ? ` — ${m.usage.prompt_tokens} prompt + ${m.usage.completion_tokens} completion`
                      : ''}
                  </p>
                ) : null}
                {m.role === 'assistant' && m.citations && m.citations.length > 0 ? (
                  <details className="le-copilot-rail__citations" open={sourcesExpanded}>
                    <summary>Sources ({m.citations.length})</summary>
                    <ol>
                      {m.citations.map((c) => (
                        <li key={c.id ?? `${c.ref}-${c.title}`}>
                          <span className="le-mono">[{c.id}]</span> {c.kind}:{' '}
                          {c.ref && c.ref.startsWith('/') ? (
                            <Link to={c.ref}>{c.title || c.ref}</Link>
                          ) : c.ref && /^https?:\/\//i.test(c.ref) ? (
                            <a href={c.ref} target="_blank" rel="noreferrer">
                              {c.title || c.ref}
                            </a>
                          ) : (
                            <>
                              {c.title}
                              {c.ref ? (
                                <>
                                  {' '}
                                  <span className="le-muted">({c.ref})</span>
                                </>
                              ) : null}
                            </>
                          )}
                          {c.snippet ? <pre className="le-copilot-rail__snippet">{c.snippet}</pre> : null}
                        </li>
                      ))}
                    </ol>
                  </details>
                ) : null}
                {m.role === 'assistant' && m.proposals && m.proposals.length > 0 ? (
                  <div className="le-copilot-rail__proposals">
                    <strong>Drafts</strong>
                    <ul>
                      {m.proposals.map((p) => (
                        <li key={p.id}>
                          <code className="le-mono">{p.tool_id}</code> — {p.title}
                          {proposalReadyId === p.id ? (
                            <>
                              <details className="le-technical-details le-copilot-proposal-preview" open>
                                <summary className="le-technical-details__summary">Payload</summary>
                                <div className="le-technical-details__body">
                                  <pre className="le-preview le-copilot-rail__proposal-json">
                                    {JSON.stringify(p.payload ?? {}, null, 2)}
                                  </pre>
                                </div>
                              </details>
                              <div className="le-copilot-rail__proposal-actions">
                                <button
                                  type="button"
                                  className="le-btn le-btn--primary le-btn--small"
                                  onClick={() => p.id && void commitProposal(p.id)}
                                >
                                  Confirm export
                                </button>
                                <button
                                  type="button"
                                  className="le-btn le-btn--small"
                                  onClick={() => setProposalReadyId(null)}
                                >
                                  Cancel
                                </button>
                              </div>
                            </>
                          ) : (
                            <button
                              type="button"
                              className="le-btn le-btn--small"
                              onClick={() => (p.id ? setProposalReadyId(p.id) : undefined)}
                            >
                              Review…
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </li>
            ))}
            {loading && pendingSince !== null ? (
              <li className="le-copilot-rail__pending-wrap" aria-hidden={false}>
                {streamUsage && streamUsage.total_tokens > 0 ? (
                  <p className="le-copilot-rail__stream-tokens forge-support" aria-live="polite">
                    Tokens so far (all rounds): {streamUsage.total_tokens} total — {streamUsage.prompt_tokens}{' '}
                    in + {streamUsage.completion_tokens} out
                  </p>
                ) : null}
                <div className="le-copilot-rail__thinking-blade" aria-live="polite">
                  <span className="le-copilot-rail__thinking-blade-text">
                    {streamProgress ||
                      COPILOT_THINKING_MESSAGES[thinkingIdx % COPILOT_THINKING_MESSAGES.length]}
                  </span>
                </div>
                <ChatRequestPendingRow
                  startedAt={pendingSince}
                  statusLabel="Lenses is thinking"
                  className="le-copilot-rail__pending"
                />
              </li>
            ) : null}
          </ul>
        )}
        <div ref={threadEndRef} />
      </div>

      <form className="le-copilot-rail__composer" onSubmit={onComposerSubmit}>
        <textarea
          className="le-copilot-rail__input"
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message Lenses Copilot…"
          disabled={loading}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submitFromComposer()
            }
          }}
        />
        <button
          type="submit"
          className="le-copilot-rail__send"
          disabled={loading || !input.trim()}
          aria-label={loading ? 'Sending' : 'Send message'}
        >
          {loading ? '…' : '↑'}
        </button>
      </form>
    </aside>
  )
}
