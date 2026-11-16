import { useEffect, useState } from 'react'
import { apiPostJson } from '../../api/http'
import { resolveUxFailure } from '../../lib/uxPageState'
import type { KeyInfo, SettingsPayload } from '../LlmSettingsForm'

type Props = {
  open: boolean
  onClose: () => void
  settings: SettingsPayload
  compatBaseUrl: string
  setCompatBaseUrl: (v: string) => void
  setCompatUrlTouched: (v: boolean) => void
  keysCompat: string
  setKeysCompat: (v: string) => void
  /** Masked key presence from GET /api/llm/settings (secret is never returned). */
  compatKeyInfo?: KeyInfo
  onApplied: () => Promise<void>
}

export function CustomProviderDrawer({
  open,
  onClose,
  settings,
  compatBaseUrl,
  setCompatBaseUrl,
  setCompatUrlTouched,
  keysCompat,
  setKeysCompat,
  compatKeyInfo,
  onApplied,
}: Props) {
  const [displayName, setDisplayName] = useState('')
  const [transport, setTransport] = useState('openai_compatible')
  const [auth, setAuth] = useState('bearer')
  const [baseUrlDraft, setBaseUrlDraft] = useState('')
  const [tokenDraft, setTokenDraft] = useState('')
  const [saving, setSaving] = useState(false)
  const [banner, setBanner] = useState<string | null>(null)
  const [probe, setProbe] = useState<{ loading?: boolean; models?: string[]; error?: string }>({})

  useEffect(() => {
    if (!open) return
    const cp = settings.custom_provider ?? {}
    setDisplayName((cp.display_name ?? '').trim())
    setTransport((cp.transport ?? 'openai_compatible').trim() || 'openai_compatible')
    setAuth((cp.auth ?? 'bearer').trim() || 'bearer')
    setBaseUrlDraft(compatBaseUrl)
    setTokenDraft(keysCompat)
    setBanner(null)
    setProbe({})
  }, [
    open,
    settings.custom_provider?.display_name,
    settings.custom_provider?.transport,
    settings.custom_provider?.auth,
    compatBaseUrl,
    keysCompat,
  ])

  async function apply() {
    setSaving(true)
    setBanner(null)
    const payload: Record<string, unknown> = {
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
      custom_provider: {
        display_name: displayName.trim(),
        transport,
        auth,
      },
    }
    const bu = baseUrlDraft.trim()
    if (bu) payload.openai_compatible_base_url = bu
    const keys: Record<string, string> = {}
    if (tokenDraft.trim()) keys.openai_compatible = tokenDraft.trim()
    if (Object.keys(keys).length) payload.keys = keys
    try {
      await apiPostJson('/api/llm/settings', { settings: payload })
      setCompatBaseUrl('')
      setCompatUrlTouched(false)
      setKeysCompat('')
      await onApplied()
      onClose()
    } catch (err) {
      const ux = resolveUxFailure(err)
      setBanner(ux.description)
    } finally {
      setSaving(false)
    }
  }

  function probeBody() {
    const body: Record<string, string> = {
      provider: 'openai_compatible',
    }
    const u = baseUrlDraft.trim()
    if (u) body.probe_openai_compatible_base_url = u
    const t = tokenDraft.trim()
    if (t) body.probe_openai_compatible_bearer = t
    return body
  }

  async function runDiscover() {
    setProbe({ loading: true, error: undefined, models: undefined })
    setBanner(null)
    try {
      const out = await apiPostJson<{ ok?: boolean; models?: string[]; error?: string; detail?: string }>(
        '/api/llm/provider-probe',
        { ...probeBody(), action: 'models' },
      )
      if (out.ok && Array.isArray(out.models)) {
        setProbe({ models: out.models, error: undefined, loading: false })
      } else {
        setProbe({
          loading: false,
          error: [out.error, out.detail].filter(Boolean).join(' · ') || 'Discovery failed',
        })
      }
    } catch (err) {
      const ux = resolveUxFailure(err)
      setProbe({ loading: false, error: ux.description })
    }
  }

  async function runHealth() {
    setProbe({ loading: true, error: undefined, models: undefined })
    setBanner(null)
    try {
      const out = await apiPostJson<{
        ok?: boolean
        healthy?: boolean
        model_count?: number
        detail?: string
        error?: string
      }>('/api/llm/provider-probe', { ...probeBody(), action: 'health' })
      if (out.healthy) {
        setProbe({
          error: undefined,
          models: [`Reachable · ${out.model_count ?? 0} models in catalog`],
          loading: false,
        })
      } else {
        setProbe({
          loading: false,
          error: ['Not healthy', out.detail, out.error].filter(Boolean).join(' · ') || 'Check base URL and auth',
        })
      }
    } catch (err) {
      const ux = resolveUxFailure(err)
      setProbe({ loading: false, error: ux.description })
    }
  }

  if (!open) return null

  const transportNote =
    transport === 'openai_compatible'
      ? 'Studio sends OpenAI-style chat requests to your base URL.'
      : 'Not wired in this Studio build yet — save as notes only; routing still uses OpenAI-compatible HTTP when you pick that mode below.'

  return (
    <div
      className="le-ai-custom-drawer-backdrop"
      role="presentation"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1200,
        background: 'rgba(0,0,0,0.45)',
        display: 'flex',
        justifyContent: 'flex-end',
        alignItems: 'stretch',
      }}
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="le-ai-custom-drawer-title"
        className="forge-support le-ai-custom-drawer"
        style={{
          width: 'min(26rem, 100vw)',
          maxHeight: '100vh',
          overflowY: 'auto',
          background: 'var(--le-panel, #1a1a1f)',
          borderLeft: '1px solid var(--le-border, rgba(255,255,255,0.12))',
          boxShadow: '-4px 0 24px rgba(0,0,0,0.35)',
          padding: '1rem 1.1rem 1.25rem',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem' }}>
          <h2 id="le-ai-custom-drawer-title" style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700 }}>
            Add custom provider
          </h2>
          <button type="button" className="le-btn le-btn--secondary" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <p style={{ margin: '0.5rem 0 0.85rem', fontSize: '0.86rem', opacity: 0.9, lineHeight: 1.45 }}>
          Runs on this Lenses machine. Nothing here is stored in your browser.
        </p>

        <label className="forge-support" style={{ display: 'block', marginBottom: '0.65rem' }}>
          Display name
          <input
            type="text"
            className="le-input"
            style={{ display: 'block', width: '100%', marginTop: '0.25rem' }}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="e.g. LM Studio on laptop"
            autoComplete="off"
          />
        </label>

        <label className="forge-support" style={{ display: 'block', marginBottom: '0.65rem' }}>
          Compatibility
          <select
            className="le-input"
            style={{ display: 'block', width: '100%', marginTop: '0.25rem' }}
            value={transport}
            onChange={(e) => setTransport(e.target.value)}
          >
            <option value="openai_compatible">OpenAI-compatible (chat completions)</option>
            <option value="anthropic_messages">Anthropic-compatible (reserved)</option>
            <option value="custom_adapter">Custom adapter (reserved)</option>
          </select>
        </label>
        <p style={{ fontSize: '0.78rem', opacity: 0.85, margin: '-0.35rem 0 0.65rem' }}>{transportNote}</p>

        <label className="forge-support" style={{ display: 'block', marginBottom: '0.65rem' }}>
          Base URL
          <input
            type="url"
            className="le-input"
            style={{ display: 'block', width: '100%', marginTop: '0.25rem' }}
            value={baseUrlDraft}
            onChange={(e) => {
              setBaseUrlDraft(e.target.value)
              setCompatUrlTouched(true)
            }}
            placeholder="https://host or http://127.0.0.1:1234 (no /v1 suffix)"
            autoComplete="off"
          />
        </label>

        <label className="forge-support" style={{ display: 'block', marginBottom: '0.65rem' }}>
          Auth
          <select
            className="le-input"
            style={{ display: 'block', width: '100%', marginTop: '0.25rem' }}
            value={auth}
            onChange={(e) => setAuth(e.target.value)}
          >
            <option value="bearer">Bearer token (optional for some gateways)</option>
            <option value="none">No bearer token</option>
          </select>
        </label>

        {auth === 'bearer' ? (
          <label className="forge-support" style={{ display: 'block', marginBottom: '0.65rem' }}>
            Token (optional)
            <input
              type="password"
              className="le-input"
              style={{ display: 'block', width: '100%', marginTop: '0.25rem' }}
              value={tokenDraft}
              onChange={(e) => setTokenDraft(e.target.value)}
              placeholder={
                compatKeyInfo?.set && !tokenDraft.trim()
                  ? 'Token saved on this host — paste only to replace'
                  : 'Paste only to set or replace'
              }
              autoComplete="off"
            />
          </label>
        ) : null}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem', marginBottom: '0.65rem' }}>
          <button type="button" className="le-btn le-btn--secondary" disabled={probe.loading} onClick={() => void runDiscover()}>
            {probe.loading ? 'Checking…' : 'Discover models'}
          </button>
          <button type="button" className="le-btn le-btn--secondary" disabled={probe.loading} onClick={() => void runHealth()}>
            Test connection
          </button>
        </div>
        {probe.models && probe.models.length > 0 && !probe.error ? (
          <p className="le-mono" style={{ fontSize: '0.72rem', opacity: 0.88, margin: '0 0 0.65rem', wordBreak: 'break-word' }}>
            {probe.models.slice(0, 24).join(', ')}
            {probe.models.length > 24 ? ` … +${probe.models.length - 24}` : ''}
          </p>
        ) : null}
        {probe.error ? (
          <p style={{ fontSize: '0.82rem', color: 'var(--le-warn, #d96)', margin: '0 0 0.65rem' }}>{probe.error}</p>
        ) : null}

        {banner ? <p style={{ fontSize: '0.82rem', color: 'var(--le-warn, #d96)', margin: '0 0 0.65rem' }}>{banner}</p> : null}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.5rem' }}>
          <button type="button" className="le-btn le-btn--primary" disabled={saving} onClick={() => void apply()}>
            {saving ? 'Saving…' : 'Save provider'}
          </button>
          <button type="button" className="le-btn le-btn--secondary" disabled={saving} onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
