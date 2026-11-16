import { useState } from 'react'
import { apiPostJson } from '../../api/http'
import { OllamaSetupScriptPanel } from '../OllamaSetupScriptPanel'
import type { AiSetupTileDensity } from './aiSetupSourceLayout'
import { usedForLabels } from './usedFor'

type TaskRouteEntry = { provider?: string; model?: string; model_stack?: string[] }

type SettingsForOllama = {
  task_routes?: Record<string, TaskRouteEntry>
  main_models?: Record<string, string>
}

export type OllamaCatalogRow = {
  name: string
  size?: number
  modified_at?: string
  digest?: string
  last_used?: string | null
}

export type OllamaStatusPayload = {
  ok?: boolean
  reachable?: boolean
  base?: string
  configured?: boolean
  models?: string[]
  model_catalog?: OllamaCatalogRow[]
}

const OLLAMA_ROLE_ROWS: Array<{ label: string; taskId: string; hint: string }> = [
  { label: 'Chat', taskId: 'chat_assistant', hint: 'Studio chat and try-out' },
  { label: 'Code', taskId: 'code_automation', hint: 'Copilot-style automation' },
  { label: 'Vision', taskId: 'vision_ocr', hint: 'Screens and image understanding' },
  { label: 'Embeddings', taskId: 'embeddings_indexing', hint: 'Local indexing when wired' },
]

const TASK_LABELS_FOR_CHIPS: Array<{ id: string; label: string }> = [
  { id: 'chat_assistant', label: 'Chat assistant' },
  { id: 'search_knowledge', label: 'Search / knowledge answers' },
  { id: 'plans_generation', label: 'Plans / roadmaps generation' },
  { id: 'site_drafting', label: 'Site / blog drafting' },
  { id: 'code_automation', label: 'Code / automation' },
  { id: 'extraction_classification', label: 'Extraction / classification' },
  { id: 'vision_ocr', label: 'Vision / OCR' },
  { id: 'embeddings_indexing', label: 'Embeddings / indexing' },
]

function formatBytes(n: number | undefined): string {
  if (n == null || !Number.isFinite(n) || n <= 0) return '—'
  const gb = n / 1024 ** 3
  if (gb >= 1) return `${gb.toFixed(2)} GB`
  const mb = n / 1024 ** 2
  if (mb >= 1) return `${mb.toFixed(1)} MB`
  return `${(n / 1024).toFixed(0)} KB`
}

function formatShortTs(iso: string | null | undefined): string {
  if (!iso || !iso.trim()) return '—'
  const d = Date.parse(iso)
  if (Number.isNaN(d)) return iso.trim().slice(0, 19)
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(d)
  } catch {
    return iso.trim().slice(0, 19)
  }
}

function ollamaRoleSelectValue(tr: TaskRouteEntry | undefined): string {
  const p = (tr?.provider ?? '').trim()
  const m = (tr?.model ?? '').trim()
  if (p === 'ollama' && m) return `ollama:${m}`
  return ''
}

type ProbeState = { loading?: boolean; models?: string[]; error?: string; at?: number }

type Props = {
  ollamaStatus: OllamaStatusPayload | null
  settings: SettingsForOllama
  updateTaskRoute: (taskId: string, patch: Partial<TaskRouteEntry>) => void
  usageSummary: {
    last_ok?: Record<string, string>
  } | null
  providersMap: Record<string, boolean> | null
  probes: ProbeState | undefined
  ollamaReady: boolean
  onRefreshCatalog: () => Promise<void>
  runModelDiscovery: (providerId: string) => void | Promise<void>
  runProviderHealth: (providerId: string) => void | Promise<void>
  openTryOutChat: (providerId: string, modelId: string) => void
  /** ``compact`` = read-only summary (use section density for full panel); ``hero`` = hides heavy catalog table behind a disclosure; ``advanced`` = full panel. */
  density?: AiSetupTileDensity
}

export function OllamaLocalPanel({
  ollamaStatus,
  settings,
  updateTaskRoute,
  usageSummary,
  providersMap,
  probes,
  ollamaReady,
  onRefreshCatalog,
  runModelDiscovery,
  runProviderHealth,
  openTryOutChat,
  density = 'advanced',
}: Props) {
  const [pullName, setPullName] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [actionNote, setActionNote] = useState<string | null>(null)

  const catalog = Array.isArray(ollamaStatus?.model_catalog) ? ollamaStatus!.model_catalog! : []
  const configured = ollamaStatus?.configured !== false
  const reachable = Boolean(ollamaStatus?.reachable)
  const baseDisplay = (ollamaStatus?.base || '').trim() || '(default: http://127.0.0.1:11434 — set OLLAMA_BASE_URL)'

  async function runOllamaAction(action: 'pull' | 'update' | 'delete', model: string) {
    const m = model.trim()
    if (!m) return
    setBusy(`${action}:${m}`)
    setActionNote(null)
    try {
      const out = await apiPostJson<{ ok?: boolean; error?: string; detail?: string }>('/api/llm/ollama-action', {
        action,
        model: m,
      })
      if (out.ok) {
        setActionNote(action === 'delete' ? `Removed “${m}”.` : `Finished “${action}” for “${m}”.`)
      } else {
        setActionNote([out.error, out.detail].filter(Boolean).join(' · ') || 'Action failed')
      }
      await onRefreshCatalog()
    } catch (e) {
      setActionNote(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setBusy(null)
    }
  }

  function onRoleChange(taskId: string, v: string) {
    if (!v) {
      updateTaskRoute(taskId, { provider: '', model: '' })
      return
    }
    const model = v.startsWith('ollama:') ? v.slice('ollama:'.length).trim() : v.trim()
    updateTaskRoute(taskId, { provider: 'ollama', model })
  }

  const modelOptions = catalog.map((r) => r.name).filter(Boolean)
  const chips = usedForLabels('ollama', settings.task_routes, TASK_LABELS_FOR_CHIPS)
  const pr = probes
  const compact = density === 'compact'
  const hero = density === 'hero'
  const baseShort =
    baseDisplay.length > 72 ? `${baseDisplay.slice(0, 70)}…` : baseDisplay

  const tableBlock = (
    <div style={{ overflowX: 'auto' }}>
      <table className="forge-support" style={{ fontSize: '0.78rem', borderCollapse: 'collapse', width: '100%', minWidth: '22rem' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', padding: '0.35rem 0.4rem', borderBottom: '1px solid var(--le-border)' }}>Model</th>
            <th style={{ textAlign: 'left', padding: '0.35rem 0.4rem', borderBottom: '1px solid var(--le-border)' }}>Size</th>
            <th style={{ textAlign: 'left', padding: '0.35rem 0.4rem', borderBottom: '1px solid var(--le-border)' }}>Updated</th>
            <th style={{ textAlign: 'left', padding: '0.35rem 0.4rem', borderBottom: '1px solid var(--le-border)' }}>Last used</th>
            <th style={{ textAlign: 'right', padding: '0.35rem 0.4rem', borderBottom: '1px solid var(--le-border)' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {catalog.length === 0 ? (
            <tr>
              <td colSpan={5} style={{ padding: '0.5rem 0.4rem', opacity: 0.85 }}>
                {reachable
                  ? 'No models in the library yet. Pull a tag above, or run ollama pull in a terminal.'
                  : 'Connect to Ollama to list models—start the daemon or fix OLLAMA_BASE_URL.'}
              </td>
            </tr>
          ) : (
            catalog.map((row) => {
              const name = row.name || ''
              return (
                <tr key={name}>
                  <td className="le-mono" style={{ padding: '0.35rem 0.4rem', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {name}
                    {row.digest ? (
                      <div style={{ fontSize: '0.65rem', opacity: 0.65, marginTop: '0.12rem' }}>{row.digest}</div>
                    ) : null}
                  </td>
                  <td style={{ padding: '0.35rem 0.4rem', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{formatBytes(row.size)}</td>
                  <td style={{ padding: '0.35rem 0.4rem', borderBottom: '1px solid rgba(255,255,255,0.06)', whiteSpace: 'nowrap' }}>
                    {formatShortTs(row.modified_at)}
                  </td>
                  <td style={{ padding: '0.35rem 0.4rem', borderBottom: '1px solid rgba(255,255,255,0.06)', whiteSpace: 'nowrap' }}>
                    {formatShortTs(row.last_used ?? undefined)}
                  </td>
                  <td
                    style={{
                      padding: '0.35rem 0.4rem',
                      borderBottom: '1px solid rgba(255,255,255,0.06)',
                      textAlign: 'right',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    <button
                      type="button"
                      className="le-btn le-btn--secondary"
                      style={{ fontSize: '0.68rem', padding: '0.12rem 0.4rem', marginRight: '0.25rem' }}
                      disabled={!configured || Boolean(busy)}
                      title="Re-pull this tag to refresh weights"
                      onClick={() => void runOllamaAction('update', name)}
                    >
                      {busy === `update:${name}` ? '…' : 'Update'}
                    </button>
                    <button
                      type="button"
                      className="le-btn le-btn--secondary"
                      style={{ fontSize: '0.68rem', padding: '0.12rem 0.4rem' }}
                      disabled={!configured || Boolean(busy)}
                      title="Remove from local library"
                      onClick={() => {
                        if (!window.confirm(`Remove Ollama model “${name}” from this machine?`)) return
                        void runOllamaAction('delete', name)
                      }}
                    >
                      {busy === `delete:${name}` ? '…' : 'Remove'}
                    </button>
                  </td>
                </tr>
              )
            })
          )}
        </tbody>
      </table>
    </div>
  )

  const mainCard = (
      <div
        style={{
          padding: '0.85rem 0.95rem',
          borderRadius: '12px',
          border: '1px solid var(--le-border, rgba(255,255,255,0.12))',
          background: 'color-mix(in srgb, var(--le-panel, #1a1a1f) 94%, transparent)',
          marginBottom: '1rem',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 'min(100%, 18rem)' }}>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.06em', opacity: 0.75, marginBottom: '0.2rem' }}>
              OLLAMA HOST
            </div>
            <div className="le-mono" style={{ fontSize: '0.88rem', wordBreak: 'break-all', lineHeight: 1.35 }}>
              {baseDisplay}
            </div>
            <p style={{ margin: '0.45rem 0 0', fontSize: '0.8rem', opacity: 0.88, lineHeight: 1.4 }}>
              {!configured
                ? 'Studio is not pointed at Ollama yet. Set OLLAMA_BASE_URL on the Lenses host (see Technical details), then restart Lenses.'
                : reachable
                  ? 'Daemon responded to a tags probe—your library and actions below use this origin.'
                  : 'URL is set, but nothing answered. Start Ollama on this host or fix the URL / firewall.'}
            </p>
          </div>
          <span
            className="le-mono"
            style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              padding: '0.2rem 0.5rem',
              borderRadius: '999px',
              border: '1px solid var(--le-border, rgba(255,255,255,0.15))',
              color: ollamaReady ? 'var(--le-ok, #8d8)' : 'color-mix(in srgb, var(--le-fg, #fff) 55%, transparent)',
              alignSelf: 'flex-start',
            }}
          >
            {ollamaReady ? 'Ready for Studio' : 'Not wired'}
          </span>
        </div>

        <p className="forge-support" style={{ fontSize: '0.78rem', margin: '0.65rem 0 0.25rem', opacity: 0.86 }}>
          <strong>Try result</strong>:{' '}
          {usageSummary?.last_ok?.ollama?.trim() ? (
            <>
              Last OK chat · <span className="le-mono">{usageSummary.last_ok.ollama.trim()}</span>
            </>
          ) : (
            'No successful Studio chat logged for Ollama yet—use Test connection after a model is installed.'
          )}
        </p>

        <details
          className="forge-support"
          style={{
            marginTop: '0.55rem',
            marginBottom: '0.65rem',
            padding: '0.55rem 0.65rem',
            borderRadius: '8px',
            border: '1px solid var(--le-border, rgba(255,255,255,0.1))',
            background: 'color-mix(in srgb, var(--le-cyan, #5ec8d4) 6%, transparent)',
          }}
        >
          <summary style={{ cursor: 'pointer', fontWeight: 700, fontSize: '0.88rem' }}>
            First-time setup: install, start, connect
          </summary>
          <ol style={{ margin: '0.55rem 0 0.5rem', paddingLeft: '1.2rem', fontSize: '0.82rem', lineHeight: 1.45, opacity: 0.92 }}>
            <li>
              Install <strong>Ollama</strong> for your OS, or run the bundled helper script below (installs / starts / pulls
              a starter model when you want it to).
            </li>
            <li>
              Ensure the daemon is listening (typically <span className="le-mono">127.0.0.1:11434</span>). Advanced: set{' '}
              <span className="le-mono">OLLAMA_BASE_URL</span> on the <strong>Lenses server</strong> if Ollama runs elsewhere.
            </li>
            <li>Restart the Lenses workspace process after changing environment variables.</li>
            <li>Use <strong>Pull a model</strong> below or <span className="le-mono">ollama pull …</span>, then assign roles and save.</li>
          </ol>
          <OllamaSetupScriptPanel />
        </details>

        <div style={{ marginBottom: '0.55rem' }}>
          <span style={{ fontSize: '0.72rem', fontWeight: 600, opacity: 0.88 }}>Ollama used for (saved routes)</span>
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
              <span style={{ fontSize: '0.72rem', opacity: 0.75 }}>No task overrides yet — tasks follow the primary source.</span>
            )}
          </div>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(11rem, 1fr))',
            gap: '0.5rem',
            marginBottom: '0.85rem',
          }}
        >
          {OLLAMA_ROLE_ROWS.map((row) => {
            const tr = settings.task_routes?.[row.taskId]
            const sel = ollamaRoleSelectValue(tr)
            return (
              <label key={row.taskId} className="forge-support" style={{ display: 'block', fontSize: '0.8rem' }}>
                <div style={{ fontWeight: 600, marginBottom: '0.15rem' }}>{row.label}</div>
                <div style={{ fontSize: '0.72rem', opacity: 0.8, marginBottom: '0.2rem' }}>{row.hint}</div>
                <select
                  className="le-input"
                  style={{ display: 'block', width: '100%', marginTop: '0.15rem' }}
                  value={sel}
                  onChange={(e) => onRoleChange(row.taskId, e.target.value)}
                >
                  <option value="">Primary default (no Ollama override)</option>
                  {modelOptions.map((name) => (
                    <option key={`${row.taskId}:${name}`} value={`ollama:${name}`}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
            )
          })}
        </div>
        <p className="forge-support" style={{ fontSize: '0.74rem', opacity: 0.82, margin: '0 0 0.75rem' }}>
          Role picks are part of workspace settings—use <strong>Save</strong> at the bottom of AI Setup to persist them.
        </p>

        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.45rem',
            alignItems: 'flex-end',
            marginBottom: '0.65rem',
            paddingBottom: '0.65rem',
            borderBottom: '1px solid var(--le-border, rgba(255,255,255,0.08))',
          }}
        >
          <label className="forge-support" style={{ flex: '1 1 12rem', minWidth: '10rem', fontSize: '0.82rem' }}>
            Pull a model (name or tag)
            <input
              type="text"
              className="le-input"
              style={{ display: 'block', width: '100%', marginTop: '0.2rem' }}
              value={pullName}
              onChange={(e) => setPullName(e.target.value)}
              placeholder="e.g. llama3.2 or qwen2.5-coder:7b"
              autoComplete="off"
              disabled={!configured}
            />
          </label>
          <button
            type="button"
            className="le-btn le-btn--primary"
            style={{ fontSize: '0.78rem', padding: '0.28rem 0.65rem', color: '#141a12', fontWeight: 600 }}
            disabled={!configured || !pullName.trim() || Boolean(busy)}
            onClick={() => void runOllamaAction('pull', pullName)}
          >
            {busy?.startsWith('pull:') ? 'Pulling…' : 'Pull'}
          </button>
        </div>

        {actionNote ? (
          <p className="forge-support" style={{ fontSize: '0.78rem', margin: '0 0 0.55rem', opacity: 0.9 }}>
            {actionNote}
          </p>
        ) : null}

        {hero ? (
          <details className="forge-support" style={{ marginTop: '0.15rem', marginBottom: '0.55rem' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 600, fontSize: '0.82rem' }}>
              Installed models ({catalog.length}) — expand for catalog table
            </summary>
            <div style={{ marginTop: '0.45rem' }}>{tableBlock}</div>
          </details>
        ) : (
          tableBlock
        )}

        {pr?.loading ? (
          <p style={{ fontSize: '0.74rem', opacity: 0.85, margin: '0.5rem 0 0.25rem' }}>Refreshing catalog…</p>
        ) : null}
        {pr?.models && pr.models.length > 0 ? (
          <p
            className="le-mono"
            style={{ fontSize: '0.68rem', opacity: 0.78, margin: '0.25rem 0', wordBreak: 'break-word' }}
          >
            Provider probe: {pr.models.slice(0, 6).join(', ')}
            {pr.models.length > 6 ? ` · +${pr.models.length - 6}` : ''}
          </p>
        ) : null}
        {pr?.error ? (
          <p style={{ fontSize: '0.74rem', color: 'var(--le-warn, #d96)', margin: '0.15rem 0 0.35rem' }}>{pr.error}</p>
        ) : null}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', alignItems: 'center', marginTop: '0.65rem' }}>
          {providersMap?.ollama ? (
            <button
              type="button"
              className="le-btn le-btn--secondary"
              style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem' }}
              onClick={() => openTryOutChat('ollama', (settings.main_models?.ollama ?? '').trim())}
            >
              Test connection
            </button>
          ) : null}
          <button
            type="button"
            className="le-btn le-btn--secondary"
            style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem' }}
            disabled={Boolean(pr?.loading) || !configured}
            onClick={() => void runModelDiscovery('ollama')}
          >
            Discover models
          </button>
          <button
            type="button"
            className="le-btn le-btn--secondary"
            style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem' }}
            disabled={Boolean(pr?.loading) || !configured}
            onClick={() => void runProviderHealth('ollama')}
          >
            Health check
          </button>
          <button
            type="button"
            className="le-btn"
            style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem' }}
            disabled={Boolean(busy)}
            onClick={() => void onRefreshCatalog()}
          >
            Refresh list
          </button>
        </div>
      </div>
  )

  if (compact) {
    const defaultModel = (settings.main_models?.ollama ?? '').trim()
    return (
      <div
        className="forge-support"
        style={{
          marginBottom: '1rem',
          borderRadius: '12px',
          border: '1px solid var(--le-border, rgba(255,255,255,0.12))',
          background: 'color-mix(in srgb, var(--le-panel, #1a1a1f) 92%, transparent)',
          padding: '0.62rem 0.72rem',
          boxSizing: 'border-box',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', flexWrap: 'wrap' }}>
          <strong style={{ fontSize: '0.9rem' }}>Local models (Ollama)</strong>
          <span
            className="le-mono"
            style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              padding: '0.15rem 0.45rem',
              borderRadius: '999px',
              border: '1px solid var(--le-border, rgba(255,255,255,0.15))',
              color: ollamaReady ? 'var(--le-ok, #8d8)' : 'color-mix(in srgb, var(--le-fg, #fff) 55%, transparent)',
            }}
          >
            {ollamaReady ? 'Ready' : 'Not wired'}
          </span>
        </div>
        <div className="le-mono" style={{ fontSize: '0.74rem', opacity: 0.82, marginTop: '0.35rem', wordBreak: 'break-all' }}>
          {baseShort}
        </div>
        <p className="forge-support" style={{ fontSize: '0.76rem', margin: '0.4rem 0 0.15rem', opacity: 0.88 }}>
          <strong>Default model</strong>: <span className="le-mono">{defaultModel || '(not set)'}</span>
        </p>
        <p className="forge-support" style={{ fontSize: '0.76rem', margin: '0 0 0.25rem', opacity: 0.82 }}>
          <strong>Try result</strong>:{' '}
          {usageSummary?.last_ok?.ollama?.trim() ? (
            <>
              Last OK · <span className="le-mono">{usageSummary.last_ok.ollama.trim()}</span>
            </>
          ) : (
            'No successful Studio chat logged for Ollama yet.'
          )}
        </p>
        <p className="forge-support" style={{ fontSize: '0.72rem', margin: '0 0 0.35rem', opacity: 0.82 }}>
          <strong>Library</strong>: {catalog.length} tag{catalog.length === 1 ? '' : 's'}
          {chips.length ? (
            <>
              {' '}
              · <strong>Used for</strong>: {chips.join(', ')}
            </>
          ) : (
            <> · tasks follow primary source</>
          )}
        </p>
        <p className="forge-support" style={{ fontSize: '0.7rem', margin: 0, opacity: 0.75, lineHeight: 1.35 }}>
          Tile mode is read-only. Use the density control above this section for roles, catalog, and actions.
        </p>
      </div>
    )
  }

  return (
    <>
      <h3
        className="forge-support"
        style={{ fontSize: '0.95rem', margin: '0 0 0.5rem', fontWeight: 700, letterSpacing: '0.02em' }}
      >
        Local models (Ollama)
      </h3>
      <p className="forge-support" style={{ fontSize: '0.82rem', margin: '-0.15rem 0 0.55rem', opacity: 0.85 }}>
        Install models on this machine or LAN—no vendor account required. This panel talks to your Ollama HTTP API and
        maps models to Studio roles.
      </p>
      {mainCard}
    </>
  )
}
