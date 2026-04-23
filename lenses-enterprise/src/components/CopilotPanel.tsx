import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, apiGetJson, apiPostJson } from '../api/http'
import { useWorkspaceOptional } from '../context/WorkspaceContext'
import { resolveUxFailure } from '../lib/uxPageState'
import { compactRelatedMdPathsForApi } from '../lib/copilotPageEvidence'
import {
  readStudioLlmPrefsForHydration,
  writeMirroredLlmSessionPrefs,
} from '../lib/copilotSessionPrefs'
import { ChatRequestPendingRow } from './chat/ChatRequestPendingRow'
import { CopilotModelSelect } from './copilot/CopilotModelSelect'
import { TechnicalDetails } from './page/TechnicalDetails'

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

type CopilotChatRes = {
  ok?: boolean
  text?: string
  error?: string
  detail?: string
  model?: string
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
}

type CopilotPanelMessage = {
  role: 'user' | 'assistant'
  text: string
  citations?: Citation[]
  proposals?: WriteProposal[]
  auditId?: string
  truncated?: boolean
  failed?: boolean
  retryPrompt?: string
  usage?: CopilotChatRes['usage']
}

export type CopilotPanelProps = {
  /** Logical Studio route name for audit trail (e.g. plan, search, chat). */
  route: string
  projectSlug?: string
  entityId?: string
  /** Search repo / site scope for FTS boosting. */
  scopeSite?: string
  /** Pre-fill input (e.g. current search query). */
  defaultQuery?: string
  pageContextSummary?: string
  relatedMdRelPaths?: string[]
  /** Tighter layout for embedding in plan/project pages. */
  compact?: boolean
  /** When true (e.g. Copilot page), tuck provider/model/tool controls under progressive disclosure so the thread leads. */
  collapseControls?: boolean
}

/** Preference order when auto-picking a configured provider (copilot + chat). */
const PROVIDER_IDS = [
  'anthropic',
  'openai',
  'gemini',
  'openai_compatible',
  'ollama',
] as const

const EMPTY_MAIN_MODELS: Record<string, string> = {}

function effectiveModelOverride(raw: string): string | undefined {
  const t = raw.trim()
  if (!t) return undefined
  const lower = t.toLowerCase()
  if (lower === 'optional' || lower === 'n/a' || lower === '—' || lower === '-') return undefined
  return t
}

export function CopilotPanel({
  route,
  projectSlug,
  entityId,
  scopeSite,
  defaultQuery,
  pageContextSummary,
  relatedMdRelPaths,
  compact,
  collapseControls = false,
}: CopilotPanelProps) {
  const wsOpt = useWorkspaceOptional()
  const [copilotOn, setCopilotOn] = useState<boolean | null>(null)
  const [providers, setProviders] = useState<Record<string, boolean> | null>(null)
  const [provider, setProvider] = useState<string>('ollama')
  const [modelOverride, setModelOverride] = useState('')
  const [toolMode, setToolMode] = useState<'read_only' | 'propose_writes'>('read_only')
  const [input, setInput] = useState(defaultQuery || '')
  const [messages, setMessages] = useState<CopilotPanelMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [pendingSince, setPendingSince] = useState<number | null>(null)
  const [banner, setBanner] = useState<string | null>(null)
  const [proposalReadyId, setProposalReadyId] = useState<string | null>(null)
  const [mainModelsHint, setMainModelsHint] = useState<Record<string, string>>(EMPTY_MAIN_MODELS)
  const [llmSessionHydrated, setLlmSessionHydrated] = useState(false)

  useEffect(() => {
    if (defaultQuery !== undefined && defaultQuery !== '') {
      setInput(defaultQuery)
    }
  }, [defaultQuery])

  useEffect(() => {
    let cancel = false
    const ac = new AbortController()
    setLlmSessionHydrated(false)
    const workspaceRoot = wsOpt?.state?.workspace_root?.trim() || ''
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
        const saved = readStudioLlmPrefsForHydration(workspaceRoot || undefined)
        if (saved && typeof saved.model === 'string') setModelOverride(saved.model)
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
  }, [wsOpt?.state?.workspace_root])

  useEffect(() => {
    if (!providers || !llmSessionHydrated) return
    const root = wsOpt?.state?.workspace_root?.trim() || ''
    writeMirroredLlmSessionPrefs(root || undefined, {
      provider,
      model: modelOverride,
      toolMode,
    })
  }, [provider, modelOverride, toolMode, providers, wsOpt?.state?.workspace_root, llmSessionHydrated])

  /** If AI Setup’s main id is not on this gateway, pick a catalog id so requests don’t use a bogus default. */
  useEffect(() => {
    if (!llmSessionHydrated) return
    if (provider !== 'openai_compatible' || !providers?.['openai_compatible']) return
    if (modelOverride.trim()) return
    const hint = (mainModelsHint['openai_compatible'] || '').trim()
    let cancelled = false
    void apiPostJson<{ ok?: boolean; models?: string[] }>('/api/llm/provider-probe', {
      provider: 'openai_compatible',
      action: 'models',
    }).then((out) => {
      if (cancelled || !out.ok || !Array.isArray(out.models) || out.models.length === 0) return
      const ids = new Set(out.models.map((x) => String(x).trim()).filter(Boolean))
      if (hint && ids.has(hint)) return
      const sorted = [...ids].sort((a, b) => a.localeCompare(b))
      const pick = sorted[0]
      if (pick) setModelOverride(pick)
    })
    return () => {
      cancelled = true
    }
  }, [provider, providers, modelOverride, mainModelsHint, llmSessionHydrated])

  const runSend = useCallback(
    async (textRaw: string, opts?: { skipUserAppend?: boolean }) => {
      const text = textRaw.trim()
      if (!text || loading || copilotOn !== true) return
      setBanner(null)
      if (!opts?.skipUserAppend) {
        setMessages((m) => [...m, { role: 'user', text }])
      }
      setPendingSince(Date.now())
      setLoading(true)
      const hadModelOverride = Boolean(effectiveModelOverride(modelOverride))
      const failBody =
        'Something blocked that copilot response. Retry with a shorter question or confirm your provider is configured.'
      try {
        const body: Record<string, unknown> = {
          provider,
          message: text,
          refine: false,
          tool_mode: toolMode,
          route,
          studio_task_id: 'search_knowledge',
          project_slug: projectSlug || undefined,
          entity_id: entityId || undefined,
          scope_site: scopeSite || undefined,
        }
        const pcs = pageContextSummary?.trim()
        if (pcs) body.page_context_summary = pcs
        const mdApi = compactRelatedMdPathsForApi(relatedMdRelPaths)
        if (mdApi) body.related_md_rel_paths = mdApi
        const mo = effectiveModelOverride(modelOverride)
        if (mo) body.model = mo
        const res = await apiPostJson<CopilotChatRes>('/api/sdlc-copilot/chat', body)
        if (res.ok && res.text) {
          if (!hadModelOverride && provider === 'openai_compatible' && res.model?.trim()) {
            setModelOverride(res.model.trim())
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
            },
          ])
        } else {
          setBanner('The copilot could not answer that turn. Try again, switch to read-only, or check LLM settings.')
          setMessages((m) => [...m, { role: 'assistant', text: failBody, failed: true, retryPrompt: text }])
        }
      } catch (err) {
        let assistantText = 'That request failed before a response arrived.'
        if (err instanceof ApiError && err.status === 403) {
          assistantText =
            toolMode === 'propose_writes'
              ? 'Write proposals need a signed-in session with access to the selected project. Try read-only, or open this page from a project dashboard.'
              : 'This copilot endpoint isn’t available from how you opened Lenses. Use your local Studio URL or ask an admin.'
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
      }
    },
    [
      copilotOn,
      entityId,
      loading,
      modelOverride,
      pageContextSummary,
      projectSlug,
      provider,
      (relatedMdRelPaths ?? [])
        .map((s) => s.trim())
        .filter(Boolean)
        .sort()
        .join('\n'),
      route,
      scopeSite,
      toolMode,
    ],
  )

  const send = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      const text = input.trim()
      if (!text || loading || copilotOn !== true) return
      setBanner(null)
      setInput('')
      void runSend(text)
    },
    [copilotOn, input, loading, runSend],
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
      <section className={`le-panel${compact ? ' le-copilot-panel--compact' : ''}`}>
        <h2 className="le-panel__title">SDLC copilot</h2>
        <p className="forge-support">Checking copilot availability…</p>
      </section>
    )
  }

  if (!copilotOn) {
    return null
  }

  return (
    <section
      className={`le-panel le-copilot-panel${compact ? ' le-copilot-panel--compact' : ''}`}
      aria-labelledby="le-copilot-panel-h"
    >
      <h2 className="le-panel__title" id="le-copilot-panel-h">
        {collapseControls ? 'Workspace Copilot' : 'SDLC copilot'}
      </h2>
      <p className="forge-support" style={{ fontSize: compact ? '0.82rem' : undefined }}>
        {collapseControls
          ? 'Grounded answers about delivery, quality, and evidence in this workspace. For a quick question from any screen, use header Ask.'
          : 'Grounded on the orchestration graph, search index, release/quality/DevSecOps/Ops payloads, and recent LLM run metadata. Citations show workspace context; write actions stay drafts until you export them.'}
      </p>
      {banner ? (
        <p className="forge-support" style={{ color: 'var(--le-warning-fg, #a60)' }}>
          {banner}
        </p>
      ) : null}
      <p className="forge-support" style={{ fontSize: compact ? '0.8rem' : '0.85rem', marginBottom: '0.5rem' }}>
        Cloud, OpenAI-compatible, and Ollama routing (quality tier, optional auto model pick, pools) live in{' '}
        <Link to="/settings/llm">AI Setup</Link>. Leave the model on the first dropdown option to use those defaults
        for the provider you select here.
      </p>
      <form onSubmit={send} className="le-copilot-panel__form">
        {collapseControls ? (
          <TechnicalDetails summary="Model, provider, and tool mode" defaultOpen={false}>
            <label className="forge-support" style={{ display: 'block', marginBottom: '0.35rem' }}>
              Provider{' '}
              <select
                className="le-select"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                disabled={loading}
              >
                {PROVIDER_IDS.map((id) => (
                  <option key={id} value={id} disabled={Boolean(providers && !providers[id])}>
                    {id}
                    {providers && !providers[id] ? ' (unconfigured)' : ''}
                  </option>
                ))}
              </select>
            </label>
            <label className="forge-support" style={{ display: 'block', marginBottom: '0.35rem' }}>
              Model override (optional){' '}
              <CopilotModelSelect
                className="le-select le-input"
                provider={provider}
                providers={providers}
                modelOverride={modelOverride}
                onModelOverride={setModelOverride}
                setupDefaultModelId={(mainModelsHint[provider] || '').trim()}
                disabled={loading}
                style={{ maxWidth: '100%', display: 'block', marginTop: '0.2rem' }}
              />
            </label>
            <label className="forge-support" style={{ display: 'block', marginBottom: '0.35rem' }}>
              Tool mode{' '}
              <select
                className="le-select"
                value={toolMode}
                onChange={(e) =>
                  setToolMode(e.target.value === 'propose_writes' ? 'propose_writes' : 'read_only')
                }
                disabled={loading}
              >
                <option value="read_only">Read-only answers</option>
                <option value="propose_writes">Propose write drafts (permissioned)</option>
              </select>
            </label>
            {toolMode === 'propose_writes' && !(projectSlug || '').trim() ? (
              <p className="forge-support" style={{ fontSize: '0.85rem' }}>
                For propose-writes with RBAC on, open this page with a project context or enter scope from a project
                dashboard so the server can check membership.
              </p>
            ) : null}
          </TechnicalDetails>
        ) : (
          <>
            <label className="forge-support" style={{ display: 'block', marginBottom: '0.35rem' }}>
              Provider{' '}
              <select
                className="le-select"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                disabled={loading}
              >
                {PROVIDER_IDS.map((id) => (
                  <option key={id} value={id} disabled={Boolean(providers && !providers[id])}>
                    {id}
                    {providers && !providers[id] ? ' (unconfigured)' : ''}
                  </option>
                ))}
              </select>
            </label>
            <label className="forge-support" style={{ display: 'block', marginBottom: '0.35rem' }}>
              Model override (optional){' '}
              <CopilotModelSelect
                className="le-select le-input"
                provider={provider}
                providers={providers}
                modelOverride={modelOverride}
                onModelOverride={setModelOverride}
                setupDefaultModelId={(mainModelsHint[provider] || '').trim()}
                disabled={loading}
                style={{ maxWidth: '100%', display: 'block', marginTop: '0.2rem' }}
              />
            </label>
            <label className="forge-support" style={{ display: 'block', marginBottom: '0.35rem' }}>
              Tool mode{' '}
              <select
                className="le-select"
                value={toolMode}
                onChange={(e) =>
                  setToolMode(e.target.value === 'propose_writes' ? 'propose_writes' : 'read_only')
                }
                disabled={loading}
              >
                <option value="read_only">Read-only answers</option>
                <option value="propose_writes">Propose write drafts (permissioned)</option>
              </select>
            </label>
            {toolMode === 'propose_writes' && !(projectSlug || '').trim() ? (
              <p className="forge-support" style={{ fontSize: '0.85rem' }}>
                For propose-writes with RBAC on, open this page with a project context or enter scope from a project
                dashboard so the server can check membership.
              </p>
            ) : null}
          </>
        )}
        <textarea
          className="le-input"
          rows={compact ? 2 : collapseControls ? 4 : 3}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about delivery, quality, release readiness, risks…"
          disabled={loading}
          style={{ width: '100%', marginBottom: '0.5rem' }}
        />
        <button type="submit" className="le-btn le-btn--primary" disabled={loading || !input.trim()}>
          {loading ? 'Thinking…' : 'Ask (grounded)'}
        </button>
      </form>
      {messages.length > 0 ? (
        <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0, marginTop: '1rem' }}>
          {messages.map((m, i) => (
            <li
              key={i}
              className={`le-card${m.role === 'assistant' && m.failed ? ' le-chat-msg--failed' : ''}`}
              style={{ marginBottom: '0.75rem', padding: '0.65rem' }}
            >
              <strong>{m.role === 'user' ? 'You' : 'Copilot'}</strong>
              <div style={{ whiteSpace: 'pre-wrap', marginTop: '0.35rem' }}>{m.text}</div>
              {m.role === 'assistant' && m.failed && m.retryPrompt ? (
                <div style={{ marginTop: '0.45rem' }}>
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
                <p className="forge-support" style={{ fontSize: '0.78rem', marginTop: '0.35rem' }}>
                  Audit id: <code className="le-mono">{m.auditId}</code>
                  {m.truncated ? ' · Grounding truncated for size' : null}
                </p>
              ) : null}
              {m.role === 'assistant' &&
              m.usage &&
              (typeof m.usage.total_tokens === 'number' ||
                typeof m.usage.prompt_tokens === 'number' ||
                typeof m.usage.completion_tokens === 'number') ? (
                <p className="forge-support" style={{ fontSize: '0.78rem', marginTop: '0.25rem' }}>
                  Tokens (this reply)
                  {typeof m.usage.total_tokens === 'number' ? `: ${m.usage.total_tokens} total` : ''}
                  {typeof m.usage.prompt_tokens === 'number' &&
                  typeof m.usage.completion_tokens === 'number'
                    ? ` — ${m.usage.prompt_tokens} prompt + ${m.usage.completion_tokens} completion`
                    : ''}
                </p>
              ) : null}
              {m.role === 'assistant' && m.citations && m.citations.length > 0 ? (
                <details style={{ marginTop: '0.5rem' }}>
                  <summary>Context ({m.citations.length})</summary>
                  <ol style={{ fontSize: '0.82rem', paddingLeft: '1.2rem' }}>
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
                        {c.snippet ? (
                          <pre
                            className="le-preview"
                            style={{ fontSize: '0.75rem', marginTop: '0.25rem', whiteSpace: 'pre-wrap' }}
                          >
                            {c.snippet}
                          </pre>
                        ) : null}
                      </li>
                    ))}
                  </ol>
                </details>
              ) : null}
              {m.role === 'assistant' && m.proposals && m.proposals.length > 0 ? (
                <div style={{ marginTop: '0.5rem' }}>
                  <strong className="forge-support">Draft proposals (preview before export)</strong>
                  <ul className="le-list" style={{ fontSize: '0.85rem' }}>
                    {m.proposals.map((p) => (
                      <li key={p.id} style={{ marginTop: '0.35rem' }}>
                        <code className="le-mono">{p.tool_id}</code> — {p.title}
                        {proposalReadyId === p.id ? (
                          <>
                            <details className="le-technical-details le-copilot-proposal-preview" open>
                              <summary className="le-technical-details__summary">Payload preview</summary>
                              <div className="le-technical-details__body">
                                <pre className="le-preview" style={{ fontSize: '0.72rem', whiteSpace: 'pre-wrap' }}>
                                  {JSON.stringify(p.payload ?? {}, null, 2)}
                                </pre>
                              </div>
                            </details>
                            <button
                              type="button"
                              className="le-btn le-btn--primary"
                              style={{ marginTop: '0.35rem', fontSize: '0.75rem' }}
                              onClick={() => p.id && void commitProposal(p.id)}
                            >
                              Confirm export to workspace storage
                            </button>
                            <button
                              type="button"
                              className="le-btn"
                              style={{ marginLeft: '0.35rem', marginTop: '0.35rem', fontSize: '0.75rem' }}
                              onClick={() => setProposalReadyId(null)}
                            >
                              Cancel
                            </button>
                          </>
                        ) : (
                          <button
                            type="button"
                            className="le-btn"
                            style={{ marginLeft: '0.5rem', fontSize: '0.75rem' }}
                            onClick={() => (p.id ? setProposalReadyId(p.id) : undefined)}
                          >
                            Review export…
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
            <li style={{ listStyle: 'none' }}>
              <ChatRequestPendingRow startedAt={pendingSince} statusLabel="Copilot is thinking" />
            </li>
          ) : null}
        </ul>
      ) : null}
    </section>
  )
}
