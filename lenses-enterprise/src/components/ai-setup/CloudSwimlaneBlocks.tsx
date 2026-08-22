import type { Dispatch, DragEvent, SetStateAction } from 'react'
import { AiSetupTileDensityPictograms } from './AiSetupSourceLayoutControls'
import type { AiSetupTileDensity, CloudCardId } from './aiSetupSourceLayout'
import { attentionLineFromRecentUsage } from './llmUsageAttention'
import { LlmProviderKeyField, type LlmProviderKeyInfo } from './LlmProviderKeyField'
import { usedForLabels } from './usedFor'
import type { SettingsPayload, UsageSummary } from '../LlmSettingsForm'

const CLOUD_TASK_ROWS: Array<{ id: string; label: string }> = [
  { id: 'chat_assistant', label: 'Chat assistant' },
  { id: 'search_knowledge', label: 'Search / knowledge answers' },
  { id: 'plans_generation', label: 'Plans / roadmaps generation' },
  { id: 'site_drafting', label: 'Site / blog drafting' },
  { id: 'code_automation', label: 'Code / automation' },
  { id: 'extraction_classification', label: 'Extraction / classification' },
  { id: 'vision_ocr', label: 'Vision / OCR' },
  { id: 'embeddings_indexing', label: 'Embeddings / indexing' },
]

export type CloudVendorId = 'openai' | 'anthropic' | 'gemini'

type ProviderProbeState = { loading?: boolean; models?: string[]; error?: string; at?: number }

type RevealMap = Partial<Record<CloudVendorId | 'openai_compatible', boolean>>

function formatDiagTs(iso?: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return String(iso)
  }
}

function recentEventsForProvider(summary: UsageSummary | null, providerId: string, limit = 5) {
  const ev = summary?.recent_events
  if (!ev?.length) return []
  return ev.filter((row) => row.provider === providerId || row.source === providerId).slice(0, limit)
}

function probeLogForProvider(summary: UsageSummary | null, providerId: string, limit = 8) {
  const pl = summary?.probe_log
  if (!pl?.length) return []
  return pl.filter((p) => p.provider === providerId).slice(-limit).reverse()
}

export type CloudVendorCardProps = {
  source: { id: CloudVendorId; label: string; outcome: string }
  density: AiSetupTileDensity
  onDensityChange: (next: AiSetupTileDensity) => void
  stripe: string
  slotIndex: number
  nCloudSlots: number
  slotId: CloudCardId
  mimeType: string
  onReorderCloud: (dragged: CloudCardId, target: CloudCardId) => void
  onMoveCloud: (dir: -1 | 1) => void
  providersMap: Record<string, boolean> | null
  settings: SettingsPayload
  keysOpenai: string
  keysAnthropic: string
  keysGemini: string
  setKeysOpenai: (v: string) => void
  setKeysAnthropic: (v: string) => void
  setKeysGemini: (v: string) => void
  usageSummary: UsageSummary | null
  probes: Record<string, ProviderProbeState>
  revealSecrets: RevealMap
  setRevealSecrets: Dispatch<SetStateAction<RevealMap>>
  openTryOutChat: (providerId: string, modelId: string) => void
  runModelDiscovery: (providerId: string) => Promise<void>
  runProviderHealth: (providerId: string) => Promise<void>
}

export function CloudVendorCard({
  source: c,
  density: cardDensity,
  onDensityChange,
  stripe,
  slotIndex,
  nCloudSlots,
  slotId,
  mimeType,
  onReorderCloud,
  onMoveCloud,
  providersMap,
  settings,
  keysOpenai,
  keysAnthropic,
  keysGemini,
  setKeysOpenai,
  setKeysAnthropic,
  setKeysGemini,
  usageSummary,
  probes,
  revealSecrets,
  setRevealSecrets,
  openTryOutChat,
  runModelDiscovery,
  runProviderHealth,
}: CloudVendorCardProps) {
  const isTile = cardDensity === 'compact'
  const isHero = cardDensity === 'hero'
  const isAdvanced = cardDensity === 'advanced'
  const cardPad =
    cardDensity === 'hero' ? '0.85rem 0.95rem' : cardDensity === 'advanced' ? '0.8rem 0.9rem' : '0.62rem 0.72rem'
  const on = Boolean(providersMap?.[c.id])
  const k = (settings.keys as Record<string, LlmProviderKeyInfo | undefined>)?.[c.id]
  const revealed = Boolean(revealSecrets[c.id])
  const modelId = (settings.main_models?.[c.id] ?? '').trim()
  const lastOk = usageSummary?.last_ok?.[c.id]
  const failLine = attentionLineFromRecentUsage(usageSummary?.recent_events, c.id)
  const pr = probes[c.id]
  const chips = usedForLabels(c.id, settings.task_routes, CLOUD_TASK_ROWS)
  const statusLabel = !on ? 'Not set up' : pr?.error || failLine ? 'Needs attention' : 'Ready'
  const statusColor =
    !on
      ? 'color-mix(in srgb, var(--le-fg, #fff) 55%, transparent)'
      : pr?.error || failLine
        ? 'var(--le-warn, #d96)'
        : 'var(--le-ok, #8d8)'

  const keyValue = c.id === 'openai' ? keysOpenai : c.id === 'anthropic' ? keysAnthropic : keysGemini
  const setKeyValue = c.id === 'openai' ? setKeysOpenai : c.id === 'anthropic' ? setKeysAnthropic : setKeysGemini

  const diagEvents = recentEventsForProvider(usageSummary, c.id)
  const diagProbes = probeLogForProvider(usageSummary, c.id)

  const footer = (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '0.5rem',
        marginTop: 'auto',
        paddingTop: '0.45rem',
        borderTop: '1px solid rgba(255,255,255,0.08)',
        flexWrap: 'wrap',
      }}
    >
      <AiSetupTileDensityPictograms
        value={cardDensity}
        onChange={onDensityChange}
        ariaGroupLabel={`${c.label} card density`}
      />
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
        <button
          type="button"
          className="le-btn le-btn--secondary"
          style={{ fontSize: '0.82rem', padding: '0.1rem 0.38rem', fontWeight: 700 }}
          disabled={slotIndex === 0}
          aria-label={`Move ${c.label} earlier in cloud row`}
          onClick={() => onMoveCloud(-1)}
        >
          ←
        </button>
        <button
          type="button"
          className="le-btn le-btn--secondary"
          style={{ fontSize: '0.82rem', padding: '0.1rem 0.38rem', fontWeight: 700 }}
          disabled={slotIndex >= nCloudSlots - 1}
          aria-label={`Move ${c.label} later in cloud row`}
          onClick={() => onMoveCloud(1)}
        >
          →
        </button>
      </div>
    </div>
  )

  return (
    <div
      draggable
      onDragStart={(e: DragEvent<HTMLDivElement>) => {
        e.dataTransfer.setData(mimeType, slotId)
        e.dataTransfer.effectAllowed = 'move'
      }}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e: DragEvent<HTMLDivElement>) => {
        e.preventDefault()
        const raw = e.dataTransfer.getData(mimeType)
        if (raw === 'openai' || raw === 'anthropic' || raw === 'gemini' || raw === 'more_providers') {
          onReorderCloud(raw as CloudCardId, slotId)
        }
      }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        height: '100%',
        boxSizing: 'border-box',
        padding: cardPad,
        borderRadius: '10px',
        border: '1px solid var(--le-border, rgba(255,255,255,0.12))',
        borderLeft: `4px solid ${stripe}`,
        background: isAdvanced
          ? 'color-mix(in srgb, var(--le-panel, #1a1a1f) 88%, transparent)'
          : 'color-mix(in srgb, var(--le-panel, #1a1a1f) 92%, transparent)',
        boxShadow: isAdvanced
          ? '0 0 0 1px color-mix(in srgb, var(--le-cyan, #5ec8d4) 26%, transparent)'
          : undefined,
        cursor: 'grab',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
        <div>
          <strong style={{ fontSize: isTile ? '0.9rem' : '0.98rem' }}>{c.label}</strong>
          {!isTile ? (
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', opacity: 0.86, lineHeight: 1.35 }}>{c.outcome}</p>
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

      {isTile ? (
        <>
          <p className="forge-support" style={{ fontSize: '0.78rem', margin: '0.45rem 0 0.15rem', opacity: 0.88 }}>
            <strong>Model id</strong>: <span className="le-mono">{modelId || '(server default)'}</span>
          </p>
          <p className="forge-support" style={{ fontSize: '0.76rem', margin: '0 0 0.25rem', opacity: 0.82 }}>
            <strong>Try result</strong>:{' '}
            {lastOk?.trim() ? (
              <>
                Last OK · <span className="le-mono">{lastOk.trim()}</span>
              </>
            ) : (
              'No successful Studio chat logged yet.'
            )}
          </p>
          {chips.length ? (
            <p className="forge-support" style={{ fontSize: '0.72rem', margin: '0 0 0.45rem', opacity: 0.82 }}>
              <strong>Used for</strong>: {chips.join(', ')}
            </p>
          ) : (
            <p className="forge-support" style={{ fontSize: '0.72rem', margin: '0 0 0.45rem', opacity: 0.78 }}>
              All tasks follow the primary source.
            </p>
          )}
          <button
            type="button"
            className="le-btn le-btn--secondary"
            style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem', alignSelf: 'flex-start' }}
            onClick={() => onDensityChange('hero')}
          >
            Expand to configure
          </button>
        </>
      ) : (
        <>
          {k?.set && !revealed ? (
            <p className="forge-support" style={{ fontSize: '0.74rem', margin: '0.4rem 0 0', opacity: 0.84 }}>
              Credential: {k.from_file ? 'saved on this host' : k.from_env ? 'from environment' : 'configured'} ·{' '}
              <span className="le-mono">{k.preview || '••••'}</span>
            </p>
          ) : null}
          <p className="forge-support" style={{ fontSize: '0.78rem', margin: '0.45rem 0 0.15rem', opacity: 0.88 }}>
            <strong>Model id</strong>: <span className="le-mono">{modelId || '(server default)'}</span>
          </p>
          <p className="forge-support" style={{ fontSize: '0.78rem', margin: '0 0 0.35rem', opacity: 0.82 }}>
            <strong>Try result</strong>:{' '}
            {lastOk?.trim() ? (
              <>
                Last OK chat · <span className="le-mono">{lastOk.trim()}</span>
              </>
            ) : (
              'No successful Studio chat logged for this source yet.'
            )}
          </p>
          {isHero ? (
            chips.length ? (
              <p className="forge-support" style={{ fontSize: '0.74rem', margin: '0.35rem 0', opacity: 0.86, lineHeight: 1.4 }}>
                <strong>Used for</strong>: {chips.join(', ')}
              </p>
            ) : (
              <p className="forge-support" style={{ fontSize: '0.72rem', margin: '0.35rem 0', opacity: 0.78, lineHeight: 1.4 }}>
                All tasks follow the primary source.
              </p>
            )
          ) : (
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
          )}
          {pr?.loading ? (
            <p style={{ fontSize: '0.74rem', opacity: 0.85, margin: '0 0 0.35rem' }}>Checking catalog…</p>
          ) : null}
          {pr?.models && pr.models.length > 0 ? (
            <p
              className="le-mono"
              style={{ fontSize: '0.68rem', opacity: 0.82, margin: '0 0 0.35rem', wordBreak: 'break-word' }}
            >
              {isAdvanced ? (
                <>
                  {pr.models.slice(0, 14).join(', ')}
                  {pr.models.length > 14 ? ` · +${pr.models.length - 14} more` : ''}
                </>
              ) : (
                <>
                  {pr.models.slice(0, 5).join(', ')}
                  {pr.models.length > 5 ? ` · +${pr.models.length - 5} more` : ''}
                  {pr.models.length > 5 ? (
                    <span style={{ fontFamily: 'var(--le-font-sans, system-ui, sans-serif)', opacity: 0.78 }}>
                      {' '}
                      — use <strong>Advanced</strong> for the full inline catalog.
                    </span>
                  ) : null}
                </>
              )}
            </p>
          ) : null}
          {pr?.error ? (
            <p style={{ fontSize: '0.74rem', color: 'var(--le-warn, #d96)', margin: '0 0 0.35rem' }}>{pr.error}</p>
          ) : null}
          {isAdvanced && (diagEvents.length > 0 || diagProbes.length > 0) ? (
            <div
              style={{
                margin: '0.35rem 0',
                padding: '0.45rem 0.55rem',
                borderRadius: '8px',
                border: '1px solid var(--le-border, rgba(255,255,255,0.12))',
                background: 'color-mix(in srgb, var(--le-panel, #1a1a1f) 96%, transparent)',
              }}
            >
              <div style={{ fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.06em', opacity: 0.8, marginBottom: '0.35rem' }}>
                Diagnostics (this host)
              </div>
              {diagEvents.length ? (
                <ul style={{ margin: '0 0 0.45rem', paddingLeft: '1.1rem', fontSize: '0.72rem', lineHeight: 1.4, opacity: 0.9 }}>
                  {diagEvents.map((ev, i) => (
                    <li key={`${ev.ts}-${i}`}>
                      <span className="le-mono">{formatDiagTs(ev.ts)}</span>
                      {ev.ok === false ? <span style={{ color: 'var(--le-warn, #d96)' }}> · failed</span> : null}
                      {ev.model ? (
                        <>
                          {' '}
                          · <span className="le-mono">{ev.model}</span>
                        </>
                      ) : null}
                      {ev.error ? (
                        <>
                          {' '}
                          — {ev.error}
                        </>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : null}
              {diagProbes.length ? (
                <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.72rem', lineHeight: 1.4, opacity: 0.88 }}>
                  {diagProbes.map((p, i) => (
                    <li key={`${p.ts}-${p.action}-${i}`}>
                      <span className="le-mono">{formatDiagTs(p.ts)}</span> · {p.action || 'probe'}
                      {p.ok === false ? <span style={{ color: 'var(--le-warn, #d96)' }}> · failed</span> : null}
                      {p.error ? <> — {p.error}</> : null}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
          {isAdvanced ? (
            <p className="forge-support" style={{ fontSize: '0.72rem', margin: '0.25rem 0 0.35rem', opacity: 0.85, lineHeight: 1.4 }}>
              <strong>Advanced</strong>: use Discover / Health when debugging; expand <strong>Usage & diagnostics</strong> at the
              bottom of AI Setup for full routing tables. Persist changes with <strong>Save changes</strong>.
            </p>
          ) : null}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', alignItems: 'center' }}>
            {on ? (
              <button
                type="button"
                className="le-btn le-btn--secondary"
                style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem' }}
                onClick={() => openTryOutChat(c.id, modelId)}
              >
                Test connection
              </button>
            ) : null}
            {isAdvanced ? (
              <>
                <button
                  type="button"
                  className="le-btn le-btn--secondary"
                  style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem' }}
                  disabled={Boolean(pr?.loading) || !on}
                  onClick={() => void runModelDiscovery(c.id)}
                >
                  Discover models
                </button>
                <button
                  type="button"
                  className="le-btn le-btn--secondary"
                  style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem' }}
                  disabled={Boolean(pr?.loading) || !on}
                  onClick={() => void runProviderHealth(c.id)}
                >
                  Health check
                </button>
              </>
            ) : null}
            <button
              type="button"
              className="le-btn le-btn--secondary"
              style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem' }}
              onClick={() =>
                setRevealSecrets((s) => {
                  const willOpen = !s[c.id]
                  const next: RevealMap = { ...s }
                  if (willOpen) {
                    for (const oid of ['openai', 'anthropic', 'gemini'] as const) {
                      if (oid !== c.id) delete next[oid]
                    }
                    next[c.id] = true
                  } else {
                    delete next[c.id]
                  }
                  return next
                })
              }
            >
              {revealed ? (on ? 'Hide credentials' : 'Cancel') : on ? 'Manage' : 'Connect'}
            </button>
          </div>
          {isHero ? (
            <details
              style={{
                marginTop: '0.4rem',
                padding: '0.35rem 0.45rem',
                borderRadius: '8px',
                border: '1px solid var(--le-border, rgba(255,255,255,0.1))',
                background: 'color-mix(in srgb, var(--le-panel, #1a1a1f) 96%, transparent)',
              }}
            >
              <summary
                className="forge-support"
                style={{ fontSize: '0.74rem', cursor: 'pointer', opacity: 0.9, fontWeight: 600 }}
              >
                Catalog and probe tools
              </summary>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.4rem', alignItems: 'center' }}>
                <button
                  type="button"
                  className="le-btn le-btn--secondary"
                  style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem' }}
                  disabled={Boolean(pr?.loading) || !on}
                  onClick={() => void runModelDiscovery(c.id)}
                >
                  Discover models
                </button>
                <button
                  type="button"
                  className="le-btn le-btn--secondary"
                  style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem' }}
                  disabled={Boolean(pr?.loading) || !on}
                  onClick={() => void runProviderHealth(c.id)}
                >
                  Health check
                </button>
              </div>
            </details>
          ) : null}
          {revealed ? (
            <div style={{ marginTop: '0.55rem', paddingTop: '0.55rem', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
              <LlmProviderKeyField
                label="API key"
                fieldKey={c.id}
                keyInfo={k}
                value={keyValue}
                onChange={setKeyValue}
                lastOk={lastOk}
                tryOut={on ? { onClick: () => openTryOutChat(c.id, modelId) } : undefined}
              />
            </div>
          ) : null}
        </>
      )}
      {footer}
    </div>
  )
}

export type CloudMoreProvidersCardProps = {
  density: AiSetupTileDensity
  onDensityChange: (next: AiSetupTileDensity) => void
  stripe: string
  slotIndex: number
  nCloudSlots: number
  mimeType: string
  onReorderCloud: (dragged: CloudCardId, target: CloudCardId) => void
  onMoveCloud: (dir: -1 | 1) => void
  moreProvidersOpen: boolean
  setMoreProvidersOpen: Dispatch<SetStateAction<boolean>>
  onOpenCustom: () => void
  onJumpOllama: () => void
}

export function CloudMoreProvidersCard({
  density: cardDensity,
  onDensityChange,
  stripe,
  slotIndex,
  nCloudSlots,
  mimeType,
  onReorderCloud,
  onMoveCloud,
  moreProvidersOpen,
  setMoreProvidersOpen,
  onOpenCustom,
  onJumpOllama,
}: CloudMoreProvidersCardProps) {
  const isTile = cardDensity === 'compact'
  const isAdvancedMp = cardDensity === 'advanced'
  const mpPad =
    cardDensity === 'hero' ? '0.75rem 0.85rem' : cardDensity === 'advanced' ? '0.8rem 0.9rem' : '0.55rem 0.65rem'

  const footer = (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '0.5rem',
        marginTop: 'auto',
        paddingTop: '0.45rem',
        borderTop: '1px solid rgba(255,255,255,0.08)',
        flexWrap: 'wrap',
      }}
    >
      <AiSetupTileDensityPictograms
        value={cardDensity}
        onChange={onDensityChange}
        ariaGroupLabel="More providers tile density"
      />
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
        <button
          type="button"
          className="le-btn le-btn--secondary"
          style={{ fontSize: '0.82rem', padding: '0.1rem 0.38rem', fontWeight: 700 }}
          disabled={slotIndex === 0}
          aria-label="Move More providers tile earlier"
          onClick={() => onMoveCloud(-1)}
        >
          ←
        </button>
        <button
          type="button"
          className="le-btn le-btn--secondary"
          style={{ fontSize: '0.82rem', padding: '0.1rem 0.38rem', fontWeight: 700 }}
          disabled={slotIndex >= nCloudSlots - 1}
          aria-label="Move More providers tile later"
          onClick={() => onMoveCloud(1)}
        >
          →
        </button>
      </div>
    </div>
  )

  return (
    <div
      draggable
      onDragStart={(e: DragEvent<HTMLDivElement>) => {
        e.dataTransfer.setData(mimeType, 'more_providers')
        e.dataTransfer.effectAllowed = 'move'
      }}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e: DragEvent<HTMLDivElement>) => {
        e.preventDefault()
        const raw = e.dataTransfer.getData(mimeType)
        if (raw === 'openai' || raw === 'anthropic' || raw === 'gemini' || raw === 'more_providers') {
          onReorderCloud(raw as CloudCardId, 'more_providers')
        }
      }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        height: '100%',
        boxSizing: 'border-box',
        padding: mpPad,
        borderRadius: '10px',
        border: '1px dashed var(--le-border, rgba(255,255,255,0.18))',
        borderLeft: `4px solid ${stripe}`,
        background: isAdvancedMp
          ? 'color-mix(in srgb, var(--le-panel, #1a1a1f) 84%, transparent)'
          : 'color-mix(in srgb, var(--le-panel, #1a1a1f) 88%, transparent)',
        boxShadow: isAdvancedMp
          ? '0 0 0 1px color-mix(in srgb, var(--le-cyan, #5ec8d4) 22%, transparent)'
          : undefined,
        cursor: 'grab',
      }}
    >
      <strong style={{ fontSize: isTile ? '0.88rem' : '0.98rem' }}>More providers</strong>
      {!isTile ? (
        <>
          <p style={{ margin: '0.3rem 0 0.35rem', fontSize: '0.8rem', opacity: 0.86, lineHeight: 1.35 }}>
            Local Ollama and custom gateways live outside the big-three cloud cards.
          </p>
          {isAdvancedMp ? (
            <p
              className="forge-support"
              style={{ fontSize: '0.72rem', margin: '0 0 0.5rem', opacity: 0.82, lineHeight: 1.4 }}
            >
              <strong>Advanced</strong>: vendor tile order uses drag-and-drop or the arrows on each card; per-tile density
              is stored in this browser only.
            </p>
          ) : null}
        </>
      ) : (
        <p style={{ margin: '0.35rem 0 0.45rem', fontSize: '0.76rem', opacity: 0.82, lineHeight: 1.35 }}>
          Shortcuts to custom gateway and Ollama. Expand for actions.
        </p>
      )}
      {isTile ? (
        <button
          type="button"
          className="le-btn le-btn--secondary"
          style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem', alignSelf: 'flex-start' }}
          onClick={() => onDensityChange('hero')}
        >
          Expand shortcuts
        </button>
      ) : isAdvancedMp ? (
        <>
          <button
            type="button"
            className="le-btn le-btn--secondary"
            style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem', alignSelf: 'flex-start' }}
            onClick={() => setMoreProvidersOpen((o) => !o)}
          >
            {moreProvidersOpen ? 'Hide shortcuts' : 'Show shortcuts'}
          </button>
          {moreProvidersOpen ? (
            <div style={{ marginTop: '0.55rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              <button
                type="button"
                className="le-btn le-btn--secondary"
                style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem', alignSelf: 'flex-start' }}
                onClick={onOpenCustom}
              >
                Open custom gateway
              </button>
              <button
                type="button"
                className="le-btn le-btn--secondary"
                style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem', alignSelf: 'flex-start' }}
                onClick={onJumpOllama}
              >
                Jump to Ollama
              </button>
            </div>
          ) : null}
        </>
      ) : (
        <div style={{ marginTop: '0.55rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          <button
            type="button"
            className="le-btn le-btn--secondary"
            style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem', alignSelf: 'flex-start' }}
            onClick={onOpenCustom}
          >
            Open custom gateway
          </button>
          <button
            type="button"
            className="le-btn le-btn--secondary"
            style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem', alignSelf: 'flex-start' }}
            onClick={onJumpOllama}
          >
            Jump to Ollama
          </button>
        </div>
      )}
      {footer}
    </div>
  )
}
