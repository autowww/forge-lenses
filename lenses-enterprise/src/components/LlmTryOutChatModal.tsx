import type { FormEvent } from 'react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link, useHref } from 'react-router-dom'
import { ApiError, apiPostJson } from '../api/http'
import { resolveUxFailure } from '../lib/uxPageState'
import { ChatRequestPendingRow } from './chat/ChatRequestPendingRow'

type ChatRes = {
  ok?: boolean
  text?: string
  model?: string
  usage?: {
    prompt_tokens?: number
    completion_tokens?: number
    total_tokens?: number
  }
}

const PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  gemini: 'Google (Gemini)',
  ollama: 'Ollama',
  openai_compatible: 'Custom gateway',
}

function effectiveModelOverride(raw: string): string | undefined {
  const t = raw.trim()
  if (!t) return undefined
  const lower = t.toLowerCase()
  if (lower === 'optional' || lower === 'n/a' || lower === '—' || lower === '-') return undefined
  return t
}

function mergeModelOptions(catalog: string[], current: string): string[] {
  const set = new Set<string>()
  for (const id of catalog) {
    const t = id.trim()
    if (t) set.add(t)
  }
  const c = current.trim()
  if (c) set.add(c)
  return Array.from(set).sort((a, b) => a.localeCompare(b))
}

type ProbeRes = { ok?: boolean; models?: string[]; error?: string; detail?: string }

type TryOutMessage = {
  role: 'user' | 'assistant'
  text: string
  failed?: boolean
  retryPrompt?: string
}

export type LlmTryOutChatModalProps = {
  open: boolean
  onClose: () => void
  providerId: string
  /** Main model from AI Setup — pre-fills the try-out control */
  defaultModelId: string
  /** In-card panel on AI Setup (no backdrop). */
  layout?: 'modal' | 'embedded'
  /** After each send finishes (success or error) — e.g. refresh usage graphs. */
  onAfterExchange?: () => void
  /** Opens the full modal try-out (optional). */
  onOpenPopout?: () => void
}

export function LlmTryOutChatModal({
  open,
  onClose,
  providerId,
  defaultModelId,
  layout = 'modal',
  onAfterExchange,
  onOpenPopout,
}: LlmTryOutChatModalProps) {
  const chatHref = useHref('/chat')
  const [selectedModel, setSelectedModel] = useState('')
  const [catalogStatus, setCatalogStatus] = useState<'idle' | 'loading' | 'ok' | 'error'>('loading')
  const [catalogModels, setCatalogModels] = useState<string[]>([])
  const [catalogHint, setCatalogHint] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<TryOutMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [pendingSince, setPendingSince] = useState<number | null>(null)
  const [banner, setBanner] = useState<string | null>(null)

  const fullChatTo = useMemo(() => {
    const u = new URL(chatHref, window.location.href)
    u.searchParams.set('provider', providerId)
    const m = effectiveModelOverride(selectedModel)
    if (m) u.searchParams.set('model', m)
    u.searchParams.set('studio_task_id', 'chat_assistant')
    return `${u.pathname}${u.search}`
  }, [chatHref, providerId, selectedModel])

  useEffect(() => {
    if (!open) return
    setInput('')
    setMessages([])
    setBanner(null)
    setLoading(false)
    setPendingSince(null)
    setSelectedModel(defaultModelId.trim())
    let cancelled = false
    setCatalogStatus('loading')
    setCatalogModels([])
    setCatalogHint(null)
    apiPostJson<ProbeRes>('/api/llm/provider-probe', { provider: providerId, action: 'models' })
      .then((res) => {
        if (cancelled) return
        if (res.ok) {
          const raw = Array.isArray(res.models) ? res.models : []
          setCatalogStatus('ok')
          setCatalogModels(raw.map((x) => String(x).trim()).filter(Boolean))
          if (res.detail === 'empty_catalog') {
            setCatalogHint('Provider returned an empty catalog — enter a model id manually if needed.')
          }
        } else {
          setCatalogStatus('error')
          setCatalogModels([])
          const parts = [res.error, res.detail].filter(Boolean)
          setCatalogHint(parts.length ? parts.join(' · ') : 'Could not load model list.')
        }
      })
      .catch((err) => {
        if (cancelled) return
        setCatalogStatus('error')
        setCatalogModels([])
        const ux = resolveUxFailure(err)
        setCatalogHint(ux.description)
      })
    return () => {
      cancelled = true
    }
  }, [open, providerId, defaultModelId])

  const selectOptions = useMemo(
    () => mergeModelOptions(catalogModels, selectedModel),
    [catalogModels, selectedModel],
  )

  useEffect(() => {
    if (!open || layout === 'embedded') return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose, layout])

  const runSend = useCallback(
    async (textRaw: string, opts?: { skipUserAppend?: boolean }) => {
      const text = textRaw.trim()
      if (!text || loading) return
      setBanner(null)
      if (!opts?.skipUserAppend) {
        setMessages((m) => [...m, { role: 'user', text }])
      }
      setPendingSince(Date.now())
      setLoading(true)
      const failBody =
        'That request did not succeed. Confirm keys or Ollama are reachable from the Lenses server.'
      try {
        const body: { provider: string; message: string; model?: string; studio_task_id?: string } = {
          provider: providerId,
          message: text,
          studio_task_id: 'chat_assistant',
        }
        const mo = effectiveModelOverride(selectedModel)
        if (mo) body.model = mo
        const res = await apiPostJson<ChatRes>('/api/llm/chat', body)
        if (res.ok && res.text) {
          const meta = res.model ? `\n\n— model: ${res.model}` : ''
          const ut = res.usage
          const useLine =
            ut && (ut.total_tokens || ut.prompt_tokens || ut.completion_tokens)
              ? `\n\n— tokens: ${ut.total_tokens ?? (Number(ut.prompt_tokens) || 0) + (Number(ut.completion_tokens) || 0)} total`
              : ''
          setMessages((m) => [...m, { role: 'assistant', text: res.text! + meta + useLine }])
        } else {
          setBanner('That message could not be completed. Check this source on AI Setup, then try again.')
          setMessages((m) => [...m, { role: 'assistant', text: failBody, failed: true, retryPrompt: text }])
        }
      } catch (err) {
        let assistantText = 'That request failed before a response arrived.'
        if (err instanceof ApiError && err.status === 403) {
          assistantText = 'This chat endpoint is not available from how you opened Lenses.'
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
        onAfterExchange?.()
      }
    },
    [loading, providerId, selectedModel, onAfterExchange],
  )

  const send = useCallback(
    (e: FormEvent) => {
      e.preventDefault()
      const text = input.trim()
      if (!text || loading) return
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

  if (!open) return null

  const label = PROVIDER_LABELS[providerId] ?? providerId
  const setupModel = effectiveModelOverride(defaultModelId)
  const embedded = layout === 'embedded'
  const inputRows = embedded ? 2 : 3

  const tryOutBody = (
    <>
      {banner ? (
        <p className="forge-support le-llm-tryout-chat-modal__banner" role="alert">
          {banner}
        </p>
      ) : null}
      <div className="le-llm-tryout-chat-modal__model-picker">
        <label className="forge-support le-llm-tryout-chat-modal__model-label">
          Model for this try-out
          {catalogStatus === 'loading' ? (
            <select className="le-input le-llm-tryout-chat-modal__model-select" disabled value="">
              <option value="">Loading catalog…</option>
            </select>
          ) : catalogStatus === 'ok' && selectOptions.length > 0 ? (
            <select
              className="le-input le-llm-tryout-chat-modal__model-select"
              value={selectedModel.trim() === '' ? '' : selectedModel.trim()}
              onChange={(e) => setSelectedModel(e.target.value)}
              aria-describedby="le-llm-tryout-model-hint"
            >
              <option value="">Server / routing default</option>
              {selectOptions.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          ) : (
            <input
              className="le-input le-llm-tryout-chat-modal__model-select"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              placeholder="Model id (optional — uses routing default if empty)"
              aria-describedby="le-llm-tryout-model-hint"
            />
          )}
        </label>
        <p id="le-llm-tryout-model-hint" className="forge-support le-llm-tryout-chat-modal__model-hint">
          {catalogStatus === 'loading'
            ? 'Fetching models from this source…'
            : catalogStatus === 'ok' && catalogModels.length > 0
              ? `${catalogModels.length} model id${catalogModels.length === 1 ? '' : 's'} available from the server.`
              : catalogStatus === 'ok'
                ? catalogHint || 'No model ids returned — type one above or leave blank for the server default.'
                : catalogHint
                  ? `Catalog unavailable (${catalogHint}). Type a model id or leave blank for the default.`
                  : null}
        </p>
        {catalogStatus === 'ok' && catalogModels.length > 0 ? (
          <details className="le-llm-tryout-chat-modal__catalog">
            <summary className="forge-support">Browse all ids</summary>
            <ul className="le-llm-tryout-chat-modal__catalog-list forge-support le-mono">
              {catalogModels.map((id) => (
                <li key={id}>
                  <button
                    type="button"
                    className="le-llm-tryout-chat-modal__catalog-pick"
                    onClick={() => setSelectedModel(id)}
                  >
                    {id}
                  </button>
                </li>
              ))}
            </ul>
          </details>
        ) : null}
      </div>
      <div className="le-llm-tryout-chat-modal__messages">
        {messages.length === 0 ? (
          <p className="forge-support le-llm-tryout-chat-modal__empty">
            Send a short message to confirm this source responds.
          </p>
        ) : (
          messages.map((m, i) => (
            <div
              key={`${i}-${m.role}`}
              className={`le-llm-tryout-chat-modal__bubble${m.role === 'assistant' && m.failed ? ' le-llm-tryout-chat-modal__bubble--failed' : ''}`}
              data-role={m.role}
            >
              <strong>{m.role === 'user' ? 'You' : 'Assistant'}</strong>
              <p className="forge-support" style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>
                {m.text}
              </p>
              {m.role === 'assistant' && m.failed && m.retryPrompt ? (
                <p className="forge-support" style={{ marginTop: '0.45rem', marginBottom: 0 }}>
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
          ))
        )}
        {loading && pendingSince !== null ? (
          <ChatRequestPendingRow
            startedAt={pendingSince}
            statusLabel="Waiting for reply"
            className="le-llm-tryout-chat-modal__pending"
          />
        ) : null}
      </div>
      <form className="le-llm-tryout-chat-modal__form" onSubmit={send}>
        <textarea
          className={`le-input le-llm-tryout-chat-modal__input${embedded ? ' le-llm-tryout-embed__input' : ''}`}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message…"
          disabled={loading}
          rows={inputRows}
        />
        <div className="le-llm-tryout-chat-modal__actions">
          <button className="le-btn le-btn--primary" type="submit" disabled={loading} style={{ color: '#141a12', fontWeight: 600 }}>
            {loading ? 'Sending…' : 'Send'}
          </button>
          <Link className="le-btn le-btn--small" to={fullChatTo} onClick={embedded ? undefined : onClose}>
            Full Chat page
          </Link>
        </div>
      </form>
    </>
  )

  if (embedded) {
    return (
      <div className="le-llm-tryout-embed">
        <div className="le-llm-tryout-embed__head">
          <h3 className="le-llm-tryout-embed__title forge-support">Test chat</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', alignItems: 'center' }}>
            {onOpenPopout ? (
              <button
                type="button"
                className="le-btn le-btn--secondary"
                style={{ fontSize: '0.74rem', padding: '0.16rem 0.42rem' }}
                onClick={onOpenPopout}
              >
                Pop out
              </button>
            ) : null}
            <span className="forge-support le-mono" style={{ fontSize: '0.72rem', opacity: 0.82 }} title="Default from AI Setup">
              {setupModel ? `Default: ${setupModel}` : label}
            </span>
          </div>
        </div>
        <div className="le-llm-settings-modal__body le-llm-tryout-chat-modal__body le-llm-tryout-embed__body">{tryOutBody}</div>
      </div>
    )
  }

  return createPortal(
    <div className="le-llm-settings-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="le-llm-settings-modal le-llm-tryout-chat-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="le-llm-tryout-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="le-llm-settings-modal__head">
          <div className="le-llm-tryout-chat-modal__head-main">
            <h2 id="le-llm-tryout-title" className="le-llm-settings-modal__title">
              Try model · {label}
            </h2>
            {setupModel ? (
              <p className="forge-support le-mono le-llm-tryout-chat-modal__model" title="Default from AI Setup">
                Setup default: {setupModel}
              </p>
            ) : null}
          </div>
          <button type="button" className="le-llm-settings-modal__close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="le-llm-settings-modal__body le-llm-tryout-chat-modal__body">{tryOutBody}</div>
      </div>
    </div>,
    document.body,
  )
}
