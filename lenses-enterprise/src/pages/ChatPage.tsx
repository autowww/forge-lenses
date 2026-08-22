import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { ApiError, apiGetJson, apiPostJson } from '../api/http'
import { useWorkspace } from '../context/WorkspaceContext'
import {
  formatCopilotFailureMessage,
  pickOpenAiCompatFallbackModel,
  readStudioLlmPrefsForHydration,
  sanitizeStudioModelOverride,
  writeMirroredLlmSessionPrefs,
} from '../lib/copilotSessionPrefs'
import { resolveUxFailure } from '../lib/uxPageState'
import { chargeMdCandidates } from '../lib/copilotPageEvidence'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { OllamaSetupScriptPanel } from '../components/OllamaSetupScriptPanel'
import { ChatRequestPendingRow } from '../components/chat/ChatRequestPendingRow'
import { PageAiInsightCard, PageHeader, TechnicalDetails } from '../components/page'
import { useStudioCommandBar } from '../context/StudioCommandBarContext'
import { recordPageToolingChoice } from '../telemetry/studioTelemetry'
import { ROUTE_SUBTITLE, STUDIO_UTILITIES, STUDIO_VOCAB } from '../nav/studioVisibleCopy'
import { useNavigationMode } from '../nav/useNavigationMode'
import { buildStudioHistoryTitle } from '../nav/studioHistoryTitle'
import { getNavMeta } from '../nav/routeMeta'
import { useStudioThreadAnchor } from '../context/StudioThreadAnchorContext'
import { buildChatSourceHint } from '../lib/chatSourceHint'
import {
  LINEAR_CHAT_THREAD_KEY,
  listThreadSummaries,
  readThreadMessages,
  threadTitleFromKey,
  writeThreadMessages,
  type ChatThreadMessageV1,
} from '../lib/chatThreadsStorage'
import { splitThreadKey } from '../lib/threadKeyUtils'

type ProvidersRes = {
  ok?: boolean
  providers?: Record<string, boolean>
}

type LlmSettingsBrief = {
  ok?: boolean
  settings?: { provider?: string; main_models?: Record<string, string> }
}

const EMPTY_MAIN_MODELS: Record<string, string> = {}

type OllamaStatusRes = {
  ok?: boolean
  reachable?: boolean
  base?: string
  /** False when `OLLAMA_BASE_URL` is unset (native Ollama provider requires an explicit origin). */
  configured?: boolean
}

type ChatRes = {
  ok?: boolean
  text?: string
  error?: string
  detail?: string
  model?: string
  routing?: { source?: string; model?: string }
  usage?: {
    prompt_tokens?: number
    completion_tokens?: number
    total_tokens?: number
  }
}

type ChatPageMessage = ChatThreadMessageV1

type ChatModeKind = 'chat' | 'threads'

const PROVIDER_IDS = [
  'anthropic',
  'openai',
  'gemini',
  'ollama',
  'openai_compatible',
] as const

/** Ignore placeholder text mistaken for a real model id (matches input placeholder). */
function effectiveModelOverride(raw: string): string | undefined {
  const t = raw.trim()
  if (!t) return undefined
  const lower = t.toLowerCase()
  if (lower === 'optional' || lower === 'n/a' || lower === '—' || lower === '-') return undefined
  return t
}

export function ChatPage() {
  const cmd = useStudioCommandBar()
  const ws = useWorkspace()
  const loc = useLocation()
  const [sp, setSp] = useSearchParams()
  const { mode } = useNavigationMode()
  const anchor = useStudioThreadAnchor()
  const chatMode: ChatModeKind = sp.get('chatMode') === 'threads' ? 'threads' : 'chat'
  const setChatMode = useCallback(
    (next: ChatModeKind) => {
      setSp((prev) => {
        const n = new URLSearchParams(prev)
        if (next === 'threads') n.set('chatMode', 'threads')
        else n.delete('chatMode')
        return n
      })
    },
    [setSp],
  )
  const [providers, setProviders] = useState<Record<string, boolean> | null>(null)
  const [provider, setProvider] = useState<string>('ollama')
  const [modelOverride, setModelOverride] = useState('')
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatPageMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [pendingSince, setPendingSince] = useState<number | null>(null)
  const [banner, setBanner] = useState<string | null>(null)
  const [refine, setRefine] = useState(false)
  /** `checking` until first probe; `unconfigured` when `OLLAMA_BASE_URL` is unset. */
  const [ollamaLine, setOllamaLine] = useState<'checking' | 'unconfigured' | 'up' | 'down'>('checking')
  const [ollamaBase, setOllamaBase] = useState<string>('')
  const [copilotEnabled, setCopilotEnabled] = useState<boolean | null>(null)
  const [mainModelsHint, setMainModelsHint] = useState<Record<string, string>>(EMPTY_MAIN_MODELS)
  const [selectedThreadKey, setSelectedThreadKey] = useState<string | null>(null)
  const [threadHydrated, setThreadHydrated] = useState(false)
  /** False until provider/model are applied for the current workspace (avoids clobbering saved prefs on switch). */
  const [llmSessionHydrated, setLlmSessionHydrated] = useState(false)

  const activeThreadKey = selectedThreadKey ?? anchor.threadKey

  const prefill = sp.get('prefill')?.trim() ?? ''

  const copilotChatScope = useMemo(
    () => ({
      pageContextSummary: 'Forge Studio · Chat · multi-turn conversation page',
      relatedMdRelPaths: chargeMdCandidates(undefined),
    }),
    [],
  )
  useLensesCopilotPage({
    route: 'chat',
    defaultQuery: prefill || undefined,
    pageContextSummary: copilotChatScope.pageContextSummary,
    relatedMdRelPaths: copilotChatScope.relatedMdRelPaths,
  })

  useEffect(() => {
    if (prefill) setInput(prefill)
  }, [prefill])

  useEffect(() => {
    if (!loc.pathname.startsWith('/chat')) setSelectedThreadKey(null)
  }, [loc.pathname])

  /** Load persisted messages for Threads (per route key) or linear Chat (single key). */
  useEffect(() => {
    const root = ws.state?.workspace_root?.trim() || ''
    setThreadHydrated(false)
    if (chatMode === 'threads') {
      const loaded = readThreadMessages(root || undefined, activeThreadKey)
      setMessages(loaded)
    } else {
      const loaded = readThreadMessages(root || undefined, LINEAR_CHAT_THREAD_KEY)
      setMessages(loaded)
    }
    setThreadHydrated(true)
  }, [chatMode, activeThreadKey, ws.state?.workspace_root])

  useEffect(() => {
    if (!threadHydrated) return
    const root = ws.state?.workspace_root?.trim() || ''
    if (chatMode === 'threads') {
      writeThreadMessages(root || undefined, activeThreadKey, messages)
    } else if (chatMode === 'chat') {
      writeThreadMessages(root || undefined, LINEAR_CHAT_THREAD_KEY, messages)
    }
  }, [messages, activeThreadKey, chatMode, threadHydrated, ws.state?.workspace_root])

  const threadSidebarEntries = useMemo(() => {
    const root = ws.state?.workspace_root?.trim() || undefined
    const sums = listThreadSummaries(root).filter((s) => !s.threadKey.startsWith('__'))
    return sums.map((s) => {
      const { pathname: p, search: se } = splitThreadKey(s.threadKey)
      return {
        ...s,
        title: buildStudioHistoryTitle(p, se, mode),
        groupId: getNavMeta(p, se, mode).groupId,
      }
    })
  }, [ws.state?.workspace_root, messages, mode, chatMode])

  const threadsBySection = useMemo(() => {
    const m = new Map<string, typeof threadSidebarEntries>()
    for (const row of threadSidebarEntries) {
      const g = row.groupId
      if (!m.has(g)) m.set(g, [])
      m.get(g)!.push(row)
    }
    return [...m.entries()]
  }, [threadSidebarEntries])

  const loadOllamaStatus = useCallback(() => {
    const ac = new AbortController()
    const tid = window.setTimeout(() => ac.abort(), 10_000)
    apiGetJson<OllamaStatusRes>('/api/llm/ollama-status', { signal: ac.signal })
      .then((d) => {
        if (d.configured === false) {
          setOllamaBase('')
          setOllamaLine('unconfigured')
          return
        }
        const baseTrim = (d.base || '').trim()
        if (!baseTrim) {
          setOllamaBase('')
          setOllamaLine('unconfigured')
          return
        }
        setOllamaBase(baseTrim)
        setOllamaLine(d.reachable === true ? 'up' : 'down')
      })
      .catch(() => {
        setOllamaLine('down')
        setOllamaBase('')
      })
      .finally(() => clearTimeout(tid))
  }, [])

  useEffect(() => {
    loadOllamaStatus()
    const id = setInterval(loadOllamaStatus, 12_000)
    return () => clearInterval(id)
  }, [loadOllamaStatus])

  useEffect(() => {
    let cancelled = false
    const ac = new AbortController()
    setLlmSessionHydrated(false)

    void apiGetJson<{ ok?: boolean; enabled?: boolean }>('/api/sdlc-copilot/enabled', { signal: ac.signal })
      .then((d) => {
        if (cancelled) return
        setCopilotEnabled(d.ok === true && d.enabled === true)
      })
      .catch(() => {
        if (cancelled) return
        setCopilotEnabled(false)
      })

    const workspaceRoot = ws.state?.workspace_root?.trim() || ''
    Promise.all([
      apiGetJson<ProvidersRes>('/api/llm/providers', { signal: ac.signal }),
      apiGetJson<LlmSettingsBrief>('/api/llm/settings', { signal: ac.signal }).catch(() => ({}) as LlmSettingsBrief),
    ])
      .then(([data, st]) => {
        if (cancelled) return
        const mainModels =
          st.settings?.main_models && typeof st.settings.main_models === 'object'
            ? (st.settings.main_models as Record<string, string>)
            : {}
        const saved = readStudioLlmPrefsForHydration(workspaceRoot || undefined)
        if (Object.keys(mainModels).length) {
          setMainModelsHint(mainModels)
        }
        const resolveModel = (raw: string | undefined, prov: string) => {
          const cleaned = sanitizeStudioModelOverride(raw, mainModels[prov])
          setModelOverride(cleaned)
          if (raw && cleaned !== raw.trim()) {
            writeMirroredLlmSessionPrefs(workspaceRoot || undefined, { model: cleaned })
          }
        }
        if (!data.providers) {
          if (saved && typeof saved.model === 'string') {
            const prov = (saved.provider || st.settings?.provider || 'openai_compatible').trim().toLowerCase()
            resolveModel(saved.model, prov)
          }
          setLlmSessionHydrated(true)
          return
        }
        setProviders(data.providers)
        const qp = sp.get('provider')?.trim().toLowerCase()
        const fromQuery =
          qp && (PROVIDER_IDS as readonly string[]).includes(qp) && data.providers[qp] ? qp : null
        let activeProvider = fromQuery || 'openai_compatible'
        if (fromQuery) {
          setProvider(fromQuery)
        } else {
          const spv = (saved?.provider || '').trim().toLowerCase()
          const savedIsKnown =
            Boolean(spv) && (PROVIDER_IDS as readonly string[]).includes(spv)
          if (savedIsKnown) {
            setProvider(spv)
            activeProvider = spv
          } else {
            const first = PROVIDER_IDS.find((id) => data.providers![id])
            if (first) {
              setProvider(first)
              activeProvider = first
            }
          }
        }
        const qm = sp.get('model')?.trim()
        if (qm) {
          let decoded = qm
          try {
            decoded = decodeURIComponent(qm)
          } catch {
            decoded = qm
          }
          resolveModel(decoded, activeProvider)
        } else if (!fromQuery) {
          if (saved && typeof saved.model === 'string') resolveModel(saved.model, activeProvider)
        } else {
          setModelOverride('')
        }
        setLlmSessionHydrated(true)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        if (err instanceof DOMException && err.name === 'AbortError') return
        const ux = resolveUxFailure(err)
        setBanner(
          `${ux.description} If you run Studio from a separate dev server, keep the Lenses workspace app running and aligned with that UI (see README).`,
        )
        setLlmSessionHydrated(true)
      })
    return () => {
      cancelled = true
      ac.abort()
    }
  }, [sp, ws.state?.workspace_root])

  useEffect(() => {
    if (!providers || !llmSessionHydrated) return
    const root = ws.state?.workspace_root?.trim() || ''
    writeMirroredLlmSessionPrefs(root || undefined, { provider, model: modelOverride })
  }, [provider, modelOverride, providers, ws.state?.workspace_root, llmSessionHydrated])

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

  const runSend = useCallback(
    async (textRaw: string, opts?: { skipUserAppend?: boolean }) => {
      const text = textRaw.trim()
      if (!text || loading) return
      setBanner(null)
      if (!opts?.skipUserAppend) {
        const srcPath = anchor.pathname
        const srcSearch = anchor.search
        const title = buildStudioHistoryTitle(srcPath, srcSearch, mode)
        const hint = buildChatSourceHint(srcPath, srcSearch, ws.state?.workspace_root)
        setMessages((m) => [
          ...m,
          { role: 'user', text, source: { pathname: srcPath, search: srcSearch, title, hint } },
        ])
      }
      setPendingSince(Date.now())
      setLoading(true)
      const failBody =
        'That request did not succeed. If it keeps happening, open AI Setup and expand “Show technical details” after a failed save or load.'
      try {
        const stidRaw = sp.get('studio_task_id')?.trim()
        const body: { provider: string; message: string; model?: string; refine?: boolean; studio_task_id?: string } = {
          provider,
          message: text,
          refine,
          studio_task_id: stidRaw || 'chat_assistant',
        }
        const mo = effectiveModelOverride(modelOverride)
        if (mo) body.model = mo
        const res = await apiPostJson<ChatRes>('/api/llm/chat', body)
        if (res.ok && res.text) {
          const meta = res.model ? `\n\n— model: ${res.model}` : ''
          const ut = res.usage
          const useLine =
            ut && (ut.total_tokens || ut.prompt_tokens || ut.completion_tokens)
              ? `\n\n— tokens: ${ut.total_tokens ?? (Number(ut.prompt_tokens) || 0) + (Number(ut.completion_tokens) || 0)} total (prompt ${ut.prompt_tokens ?? 0}, completion ${ut.completion_tokens ?? 0})`
              : ''
          setMessages((m) => [
            ...m,
            { role: 'assistant', text: res.text! + meta + useLine, usage: res.usage },
          ])
        } else {
          setBanner(
            'That message could not be completed. Check AI Setup and provider availability, then try again.',
          )
          setMessages((m) => [
            ...m,
            {
              role: 'assistant',
              text: formatCopilotFailureMessage(res, failBody),
              failed: true,
              retryPrompt: text,
            },
          ])
        }
      } catch (err) {
        let assistantText = 'That request failed before a response arrived.'
        if (err instanceof ApiError && err.status === 403) {
          assistantText =
            'This chat endpoint isn’t available from how you opened Lenses. Use the local Studio URL your admin recommends, or ask about remote access.'
          setBanner(assistantText)
        } else {
          const ux = resolveUxFailure(err)
          assistantText = ux.description
          setBanner(ux.description)
        }
        setMessages((m) => [
          ...m,
          { role: 'assistant', text: assistantText, failed: true, retryPrompt: text },
        ])
      } finally {
        setLoading(false)
        setPendingSince(null)
        if (provider === 'ollama') loadOllamaStatus()
      }
    },
    [
      loading,
      modelOverride,
      provider,
      refine,
      sp,
      loadOllamaStatus,
      anchor.pathname,
      anchor.search,
      mode,
      ws.state?.workspace_root,
    ],
  )

  const send = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      const text = input.trim()
      if (!text || loading) return
      setBanner(null)
      setInput('')
      void runSend(text)
    },
    [input, loading, runSend],
  )

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

  return (
    <>
      <PageHeader
        title={STUDIO_VOCAB.llmChat}
        purpose={ROUTE_SUBTITLE.llmChatUtility}
        statusChips={[
          { label: 'Grounded', tone: 'ok' },
          { label: 'Operator-reviewed', tone: 'muted' },
        ]}
        primaryAction={
          <Link className="le-btn le-btn--primary" to="/settings/llm">
            AI Setup
          </Link>
        }
        secondaryMenuItems={[
          { key: 'search', label: STUDIO_VOCAB.search, to: '/search' },
          { key: 'tutorials', label: 'Tutorials', to: '/tutorials' },
        ]}
      />
      <div
        className="le-form-row"
        style={{ flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center', marginBottom: '0.35rem' }}
      >
        <span className="forge-support" style={{ marginRight: '0.25rem' }}>
          Mode
        </span>
        <button
          type="button"
          className={`le-btn le-btn--small${chatMode === 'chat' ? ' le-btn--primary' : ''}`}
          onClick={() => setChatMode('chat')}
          aria-pressed={chatMode === 'chat'}
        >
          Chat
        </button>
        <button
          type="button"
          className={`le-btn le-btn--small${chatMode === 'threads' ? ' le-btn--primary' : ''}`}
          onClick={() => setChatMode('threads')}
          aria-pressed={chatMode === 'threads'}
        >
          Threads
        </button>
      </div>
      {chatMode === 'chat' ? (
        <p className="forge-support" style={{ marginBottom: '0.65rem' }}>
          Each send records the <strong>last Studio page</strong> you were on before this screen. Your lines show a
          title link back there and a short locator hint underneath. This conversation is saved in this browser for this
          workspace so you can pick it up after closing Studio.
        </p>
      ) : (
        <p className="forge-support" style={{ marginBottom: '0.65rem' }}>
          <strong>Threads</strong> stores one conversation per Studio route (path + query). Browse the workspace, then
          return here — the list selects the thread for the page you were on. Pick another thread from the sidebar, or
          use <strong>Follow page</strong> to match navigation again. Threads are saved in this browser for this
          workspace across sessions.
        </p>
      )}
      <TechnicalDetails summary="Header Ask vs this page" defaultOpen={false}>
        <p className="forge-support">
          Use header <strong>Ask</strong> for short, read-only answers while you stay on another screen. This page keeps
          multi-turn threads, optional write proposals, and legacy provider chat in one place.
        </p>
      </TechnicalDetails>
      <PageAiInsightCard
        whatChanged={
          copilotEnabled
            ? 'Conversation and workspace context stay in the Lenses Copilot rail on the right.'
            : 'Grounded Lenses Copilot is off — use Advanced below or enable it on the server.'
        }
        whyItMatters="Prefer header Ask for quick checks; use this page for legacy multi-turn chat, exports, or provider experiments."
        nextAction={
          <span className="le-form-row" style={{ flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
            <button
              type="button"
              className="le-btn le-btn--small le-btn--primary"
              onClick={() => {
                recordPageToolingChoice('chat_insight', 'header_ask')
                cmd.open('ask', { initialQuery: prefill || undefined })
              }}
            >
              Ask in command bar
            </button>
            <Link
              className="le-btn le-btn--small"
              to="/search"
              onClick={() => recordPageToolingChoice('chat_insight', 'advanced_search')}
            >
              {STUDIO_VOCAB.search}
            </Link>
          </span>
        }
      />
      {messages.length === 0 && !copilotEnabled ? (
        <p className="forge-support le-tool-landing-lead">{STUDIO_UTILITIES.chatLandingBody}</p>
      ) : null}
      <TechnicalDetails
        summary={copilotEnabled ? 'Advanced: legacy LLM chat, providers, and Ollama diagnostics' : 'LLM chat and provider controls'}
        defaultOpen={!copilotEnabled}
        className="le-chat-legacy-panel"
      >
        <p className="forge-support">
          Server-side proxy: configure keys in the server environment or{' '}
          <Link to="/settings/llm">AI Setup</Link> (stored on the Lenses host, not in the browser). See README for
          setup.
        </p>
      {provider === 'ollama' ? (
        <>
          <div
            className="forge-support"
            style={{
              fontSize: '0.88rem',
              marginBottom: '0.5rem',
              padding: '0.55rem 0.65rem',
              borderRadius: '6px',
              border: '1px solid var(--le-border, rgba(255,255,255,0.12))',
              background: 'color-mix(in srgb, var(--le-panel, #1a1a1f) 92%, transparent)',
            }}
          >
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.5rem 1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexShrink: 0 }}>
                {ollamaLine === 'checking' ? (
                  <span style={{ opacity: 0.75 }}>Checking Ollama…</span>
                ) : ollamaLine === 'unconfigured' ? (
                  <>
                    <span
                      title="OLLAMA_BASE_URL is not set on the Lenses server"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '1.25rem',
                        height: '1.25rem',
                        borderRadius: '4px',
                        border: '1px solid color-mix(in srgb, var(--le-risk, #c96) 45%, transparent)',
                        color: 'var(--le-risk, #c96)',
                        fontSize: '0.75rem',
                        lineHeight: 1,
                      }}
                      aria-label="Ollama base URL not configured"
                    >
                      !
                    </span>
                    <strong style={{ color: 'var(--le-risk, #c96)' }}>Ollama URL not set</strong>
                  </>
                ) : ollamaLine === 'up' ? (
                  <>
                    <span
                      title="Ollama responded on this machine"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '1.25rem',
                        height: '1.25rem',
                        borderRadius: '4px',
                        border: '1px solid color-mix(in srgb, var(--le-ok, #7d7) 55%, transparent)',
                        background: 'color-mix(in srgb, var(--le-ok, #7d7) 14%, transparent)',
                        color: 'var(--le-ok, #7d7)',
                        fontSize: '0.85rem',
                        lineHeight: 1,
                      }}
                      aria-label="Ollama daemon reachable"
                    >
                      ✓
                    </span>
                    <strong style={{ color: 'var(--le-ok, #7d7)' }}>Ollama reachable</strong>
                  </>
                ) : (
                  <>
                    <span
                      title="Ollama did not respond on this machine"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '1.25rem',
                        height: '1.25rem',
                        borderRadius: '4px',
                        border: '1px solid color-mix(in srgb, var(--le-risk, #c96) 45%, transparent)',
                        color: 'var(--le-risk, #c96)',
                        fontSize: '0.75rem',
                        lineHeight: 1,
                      }}
                      aria-label="Ollama daemon not reachable"
                    >
                      ✕
                    </span>
                    <strong style={{ color: 'var(--le-risk, #c96)' }}>Ollama not reachable</strong>
                  </>
                )}
                {ollamaBase ? (
                  <code className="le-mono" style={{ fontSize: '0.8rem' }}>
                    {ollamaBase}
                  </code>
                ) : null}
              </div>
              <p style={{ margin: 0, opacity: 0.92, flex: '1 1 14rem' }}>
                <strong>Ollama</strong> requires an explicit HTTP(S) origin on the server:{' '}
                <code className="le-mono">{'export OLLAMA_BASE_URL=\'http://127.0.0.1:11434\''}</code> (adjust host
                or port if needed), then restart Lenses. Start the Ollama app or <code className="le-mono">ollama serve</code>
                . Use <code className="le-mono">ollama pull …</code> for your model.
              </p>
            </div>
          </div>
          <OllamaSetupScriptPanel />
        </>
      ) : null}
      <div
        style={
          chatMode === 'threads'
            ? { display: 'flex', gap: '1rem', alignItems: 'flex-start' }
            : undefined
        }
      >
        {chatMode === 'threads' ? (
          <aside
            aria-label="Threads by studio area"
            style={{
              flex: '0 0 13.5rem',
              position: 'sticky',
              top: '0.75rem',
              alignSelf: 'flex-start',
              maxHeight: 'min(70vh, 32rem)',
              overflow: 'auto',
              padding: '0.35rem 0.5rem',
              borderRadius: '6px',
              border: '1px solid var(--le-border, rgba(255,255,255,0.12))',
              background: 'color-mix(in srgb, var(--le-panel, #1a1a1f) 92%, transparent)',
            }}
          >
            {threadsBySection.map(([sectionId, rows]) => (
              <div key={sectionId} style={{ marginBottom: '0.65rem' }}>
                <div
                  className="forge-support"
                  style={{
                    fontWeight: 600,
                    fontSize: '0.78rem',
                    opacity: 0.85,
                    textTransform: 'capitalize',
                    marginBottom: '0.25rem',
                  }}
                >
                  {sectionId}
                </div>
                <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                  {rows.map((row) => {
                    const active = row.threadKey === activeThreadKey
                    return (
                      <li key={row.threadKey} style={{ marginBottom: '0.35rem' }}>
                        <button
                          type="button"
                          className={`le-btn le-btn--small${active ? ' le-btn--primary' : ''}`}
                          style={{
                            width: '100%',
                            textAlign: 'left',
                            justifyContent: 'flex-start',
                            fontWeight: active ? 600 : 400,
                          }}
                          onClick={() => setSelectedThreadKey(row.threadKey)}
                        >
                          {row.title}
                        </button>
                        <div className="forge-support" style={{ fontSize: '0.72rem', opacity: 0.75 }}>
                          {row.messageCount} messages
                        </div>
                      </li>
                    )
                  })}
                </ul>
              </div>
            ))}
            <button
              type="button"
              className="le-btn le-btn--small"
              onClick={() => setSelectedThreadKey(null)}
              disabled={!selectedThreadKey}
            >
              Follow page
            </button>
          </aside>
        ) : null}
        <div style={{ flex: '1 1 auto', minWidth: 0 }}>
          {chatMode === 'threads' ? (
            <p className="forge-support" style={{ marginBottom: '0.5rem' }}>
              Active thread:{' '}
              {(() => {
                const { pathname: tp, search: ts } = splitThreadKey(activeThreadKey)
                return (
                  <Link to={tp + ts}>
                    {threadTitleFromKey(activeThreadKey, (p, s) => buildStudioHistoryTitle(p, s, mode))}
                  </Link>
                )
              })()}
              {!selectedThreadKey ? (
                <span style={{ opacity: 0.8 }}> (follows last Studio page)</span>
              ) : (
                <span style={{ opacity: 0.8 }}> (pinned)</span>
              )}
            </p>
          ) : null}
          {banner && (
            <p className="forge-support" style={{ color: 'var(--le-risk, #c96)' }}>
              {banner}
            </p>
          )}
      <form onSubmit={send}>
        <div className="le-form-row" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
          <label className="forge-support" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            Provider
            <select
              className="le-input"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              aria-label="LLM provider"
            >
              {PROVIDER_IDS.map((id) => (
                <option key={id} value={id} disabled={providers ? providers[id] === false : false}>
                  {id}
                  {providers && !providers[id] ? ' (not configured)' : ''}
                </option>
              ))}
            </select>
          </label>
          <label className="forge-support" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            Model override
            <input
              className="le-input"
              style={{ minWidth: '12rem' }}
              value={modelOverride}
              onChange={(e) => setModelOverride(e.target.value)}
              placeholder="optional"
              aria-label="Model override"
            />
          </label>
          <label className="forge-support" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <input
              type="checkbox"
              checked={refine}
              onChange={(e) => setRefine(e.target.checked)}
            />
            Refine pass (cheaper model shift)
          </label>
          <button className="le-btn le-btn--primary" type="submit" disabled={loading}>
            {loading ? 'Sending…' : 'Send'}
          </button>
        </div>
        <textarea
          className="le-input"
          style={{ width: '100%', minHeight: '5rem', marginTop: '0.75rem' }}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message"
          disabled={loading}
        />
      </form>
      <div style={{ marginTop: '1rem' }}>
        {messages.map((m, i) => (
          <div
            key={`${i}-${m.role}`}
            className={`le-card${m.role === 'assistant' && m.failed ? ' le-chat-msg--failed' : ''}`}
            style={{
              marginBottom: '0.5rem',
              whiteSpace: 'pre-wrap',
              borderLeft: m.role === 'user' ? '3px solid var(--le-cyan, #0ff)' : '3px solid var(--le-amber, #fa0)',
            }}
          >
            <strong>{m.role === 'user' ? 'You' : 'Assistant'}</strong>
            {m.role === 'user' && m.source ? (
              <div style={{ marginTop: '0.25rem', marginBottom: '0.35rem' }}>
                <Link
                  className="forge-support"
                  style={{ fontWeight: 600, display: 'inline-block' }}
                  to={m.source.pathname + (m.source.search || '')}
                >
                  {m.source.title}
                </Link>
                <div
                  className="forge-support"
                  style={{ fontSize: '0.82rem', opacity: 0.82, marginTop: '0.12rem' }}
                >
                  {m.source.hint}
                </div>
              </div>
            ) : null}
            <p className="forge-support" style={{ marginBottom: 0 }}>
              {m.text}
            </p>
            {m.role === 'assistant' && m.failed && m.retryPrompt ? (
              <p style={{ marginTop: '0.45rem', marginBottom: 0 }}>
                <button
                  type="button"
                  className="le-btn le-btn--small le-btn--primary"
                  onClick={() => handleRetry(m.retryPrompt!)}
                  disabled={loading}
                >
                  Retry
                </button>
              </p>
            ) : null}
          </div>
        ))}
        {loading && pendingSince !== null ? (
          <div style={{ marginTop: '0.35rem' }}>
            <ChatRequestPendingRow startedAt={pendingSince} statusLabel="Assistant is replying" />
          </div>
        ) : null}
      </div>
        </div>
      </div>
      </TechnicalDetails>
    </>
  )
}
