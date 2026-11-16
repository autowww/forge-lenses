import type { ReactNode } from 'react'
import { useCallback, useState } from 'react'
import type { AiSetupSourceLayoutV2, AiSetupSourceSectionId, AiSetupTileDensity } from './aiSetupSourceLayout'
import { AI_SETUP_SECTION_SHORT, aiSetupSectionStripeCss } from './aiSetupSourceLayout'

const MIME_SECTION = 'application/x-forge-ai-setup-section'

export function IconTileCompact({ active }: { active: boolean }) {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden style={{ opacity: active ? 1 : 0.55 }}>
      <rect x="4" y="4" width="8" height="8" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  )
}

/** Hero tile: taller card with title band + body lines (matches real “hero” cards, not a wide strip). */
export function IconTileHero({ active }: { active: boolean }) {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden style={{ opacity: active ? 1 : 0.55 }}>
      <rect x="3.5" y="2.5" width="9" height="11" rx="1.35" fill="none" stroke="currentColor" strokeWidth="1.25" />
      <rect x="5" y="4.25" width="6" height="1.85" rx="0.45" fill="currentColor" opacity={active ? 0.35 : 0.22} />
      <path
        d="M5.2 8.1h5.6M5.2 9.85h4.2M5.2 11.55h5.1"
        stroke="currentColor"
        strokeWidth="0.95"
        strokeLinecap="round"
        opacity={active ? 0.9 : 0.55}
      />
    </svg>
  )
}

export function IconTileAdvanced({ active }: { active: boolean }) {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden style={{ opacity: active ? 1 : 0.55 }}>
      <rect x="2.5" y="2.5" width="11" height="11" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.25" />
      <circle cx="8" cy="8" r="2.1" fill="none" stroke="currentColor" strokeWidth="1.1" />
      <path
        d="M8 4.2v1.1M8 10.7v1.1M4.2 8h1.1M10.7 8h1.1M5.35 5.35l.78.78M9.87 9.87l.78.78M10.65 5.35l-.78.78M6.13 9.87l-.78.78"
        stroke="currentColor"
        strokeWidth="0.9"
        strokeLinecap="round"
      />
    </svg>
  )
}

const DENSITY_HINTS: Record<AiSetupTileDensity, string> = {
  compact: 'Compact card — minimal fields',
  hero: 'Hero card — standard detail',
  advanced: 'Advanced — full diagnostics',
}

/** Icon-only density control; active uses a cool outline (not primary yellow). */
export function AiSetupTileDensityPictograms({
  value,
  onChange,
  ariaGroupLabel,
}: {
  value: AiSetupTileDensity
  onChange: (next: AiSetupTileDensity) => void
  /** e.g. "OpenAI card density" — for screen readers */
  ariaGroupLabel: string
}) {
  const modes: AiSetupTileDensity[] = ['compact', 'hero', 'advanced']
  return (
    <div
      role="group"
      aria-label={ariaGroupLabel}
      style={{
        display: 'inline-flex',
        borderRadius: '8px',
        border: '1px solid var(--le-border, rgba(255,255,255,0.16))',
        overflow: 'hidden',
        background: 'color-mix(in srgb, var(--le-panel, #1a1a1f) 88%, transparent)',
      }}
    >
      {modes.map((m, mi) => {
        const active = value === m
        return (
          <button
            key={m}
            type="button"
            title={DENSITY_HINTS[m]}
            aria-label={`${DENSITY_HINTS[m]}${active ? ' (selected)' : ''}`}
            aria-pressed={active}
            className="le-btn le-btn--secondary"
            style={{
              padding: '0.26rem 0.4rem',
              minWidth: '2.1rem',
              borderRadius: 0,
              border: 'none',
              borderRight:
                mi < modes.length - 1 ? '1px solid var(--le-border, rgba(255,255,255,0.1))' : undefined,
              boxShadow: 'none',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: active
                ? 'color-mix(in srgb, var(--le-cyan, #5ec8d4) 22%, var(--le-panel, #1a1a1f) 78%)'
                : 'transparent',
              color: active ? 'var(--le-cyan, #9ee8f0)' : 'color-mix(in srgb, var(--le-fg, #fff) 78%, transparent)',
              outline: active ? '1px solid color-mix(in srgb, var(--le-cyan, #5ec8d4) 55%, transparent)' : 'none',
              outlineOffset: '-1px',
            }}
            onClick={() => onChange(m)}
          >
            {m === 'compact' ? <IconTileCompact active={active} /> : null}
            {m === 'hero' ? <IconTileHero active={active} /> : null}
            {m === 'advanced' ? <IconTileAdvanced active={active} /> : null}
          </button>
        )
      })}
    </div>
  )
}

/** @deprecated use AiSetupTileDensityPictograms */
export function AiSetupTileDensityToggle(props: {
  value: AiSetupTileDensity
  onChange: (next: AiSetupTileDensity) => void
  sectionLabel: string
}) {
  return <AiSetupTileDensityPictograms value={props.value} onChange={props.onChange} ariaGroupLabel={props.sectionLabel} />
}

export function AiSetupSourcePriorityRail({
  layout,
  onReorder,
}: {
  layout: AiSetupSourceLayoutV2
  onReorder: (nextOrder: AiSetupSourceSectionId[]) => void
}) {
  const { order } = layout
  const [dragOverId, setDragOverId] = useState<AiSetupSourceSectionId | null>(null)

  const moveSection = useCallback(
    (id: AiSetupSourceSectionId, dir: -1 | 1) => {
      const i = order.indexOf(id)
      const j = i + dir
      if (i < 0 || j < 0 || j >= order.length) return
      const next = [...order]
      const a = next[i]!
      const b = next[j]!
      next[i] = b
      next[j] = a
      onReorder(next)
    },
    [order, onReorder],
  )

  const reorderDrag = useCallback(
    (draggedId: AiSetupSourceSectionId, targetId: AiSetupSourceSectionId) => {
      if (draggedId === targetId) return
      const from = order.indexOf(draggedId)
      const to = order.indexOf(targetId)
      if (from < 0 || to < 0) return
      const next = [...order]
      next.splice(from, 1)
      next.splice(to, 0, draggedId)
      onReorder(next)
    },
    [order, onReorder],
  )

  return (
    <div
      role="group"
      aria-label="Model source sections — drag cards or use arrows to change order"
      className="forge-support"
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0.45rem',
        marginBottom: '0.85rem',
        alignItems: 'stretch',
      }}
    >
      {order.map((id, idx) => (
        <div
          key={id}
          draggable
          onDragStart={(e) => {
            e.dataTransfer.setData(MIME_SECTION, id)
            e.dataTransfer.effectAllowed = 'move'
          }}
          onDragEnter={(e) => {
            e.preventDefault()
            setDragOverId(id)
          }}
          onDragOver={(e) => {
            e.preventDefault()
            e.dataTransfer.dropEffect = 'move'
          }}
          onDragLeave={() => {
            setDragOverId((cur) => (cur === id ? null : cur))
          }}
          onDrop={(e) => {
            e.preventDefault()
            setDragOverId(null)
            const raw = e.dataTransfer.getData(MIME_SECTION)
            if (raw && (raw === 'cloud' || raw === 'custom' || raw === 'ollama')) {
              reorderDrag(raw, id)
            }
          }}
          onDragEnd={() => setDragOverId(null)}
          style={{
            flex: '1 1 7.5rem',
            minWidth: '6.5rem',
            borderRadius: '10px',
            border:
              dragOverId === id
                ? '1px dashed color-mix(in srgb, var(--le-cyan, #5ec8d4) 65%, transparent)'
                : '1px solid var(--le-border, rgba(255,255,255,0.12))',
            borderLeft: `4px solid ${aiSetupSectionStripeCss(id, idx)}`,
            background: 'color-mix(in srgb, var(--le-panel, #1a1a1f) 92%, transparent)',
            padding: '0.45rem 0.55rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.3rem',
            cursor: 'grab',
          }}
        >
          <div style={{ fontWeight: 700, fontSize: '0.8rem', letterSpacing: '0.02em' }}>{AI_SETUP_SECTION_SHORT[id]}</div>
          <div style={{ fontSize: '0.68rem', opacity: 0.82, lineHeight: 1.25 }}>
            Priority {idx + 1} · drag to reorder
          </div>
          <div style={{ display: 'flex', gap: '0.25rem', marginTop: 'auto' }}>
            <button
              type="button"
              className="le-btn le-btn--secondary"
              style={{ fontSize: '0.85rem', padding: '0.12rem 0.42rem', flex: 1, fontWeight: 700 }}
              disabled={idx === 0}
              aria-label={`Move ${AI_SETUP_SECTION_SHORT[id]} earlier`}
              title="Move earlier"
              onClick={() => moveSection(id, -1)}
            >
              ←
            </button>
            <button
              type="button"
              className="le-btn le-btn--secondary"
              style={{ fontSize: '0.85rem', padding: '0.12rem 0.42rem', flex: 1, fontWeight: 700 }}
              disabled={idx >= order.length - 1}
              aria-label={`Move ${AI_SETUP_SECTION_SHORT[id]} later`}
              title="Move later"
              onClick={() => moveSection(id, 1)}
            >
              →
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

export function AiSetupSectionChrome({
  stripeColor,
  headerRight,
  children,
}: {
  stripeColor: string
  headerRight?: ReactNode
  children: ReactNode
}) {
  return (
    <div
      style={{
        marginBottom: '0.15rem',
        borderLeft: `4px solid ${stripeColor}`,
        paddingLeft: '0.65rem',
      }}
    >
      {headerRight ? (
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.35rem' }}>{headerRight}</div>
      ) : null}
      {children}
    </div>
  )
}
