import { useId } from 'react'
import type { BranchingPolicy, CategoryCountRow, LaneVolumeRow, PayloadSchemaCard, PolicyResolutionStep } from '../../lib/branchingViewModel'

const MIX_COLORS = ['#3d8bfd', '#6ea8fe', '#9ec5fe', '#0dcaf0', '#20c997', '#ffc107', '#fd7e14', '#adb5bd']

export function BranchingLaneBarChart({ rows, maxBars = 11 }: { rows: LaneVolumeRow[]; maxBars?: number }) {
  const nonZero = rows.filter((r) => r.count > 0)
  const display = nonZero.length ? nonZero.slice(0, maxBars) : rows.slice(0, 8)
  const max = Math.max(1, ...display.map((r) => r.count))
  const w = 360
  const rowH = 18
  const labelW = 72
  const barW = w - labelW - 8
  const h = display.length * rowH + 8
  const aria = `Branch counts by lane: ${display.map((r) => `${r.lane} ${r.count}`).join(', ')}`

  return (
    <figure style={{ margin: '0.75rem 0 0' }}>
      <svg
        width="100%"
        height={h}
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label={aria}
        style={{ maxWidth: 420 }}
      >
        {display.map((r, idx) => {
          const y = 4 + idx * rowH
          const bw = (r.count / max) * barW
          const muted = r.count === 0
          return (
            <g key={r.lane}>
              <text x={0} y={y + 12} fontSize={11} fill="currentColor" opacity={muted ? 0.45 : 0.9}>
                {r.lane}
              </text>
              <rect
                x={labelW}
                y={y + 2}
                width={barW}
                height={rowH - 6}
                rx={2}
                fill="currentColor"
                opacity={0.08}
              />
              <rect
                x={labelW}
                y={y + 2}
                width={Math.max(bw, r.count > 0 ? 2 : 0)}
                height={rowH - 6}
                rx={2}
                fill="var(--bs-primary, #0d6efd)"
                opacity={muted ? 0.2 : 0.85}
              />
              <text
                x={labelW + barW + 4}
                y={y + 12}
                fontSize={11}
                fill="currentColor"
                opacity={muted ? 0.4 : 0.85}
              >
                {r.count}
              </text>
            </g>
          )
        })}
      </svg>
      <figcaption className="le-muted" style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
        {nonZero.length
          ? 'Lane counts from the latest payload (non-empty lanes only, capped for readability).'
          : 'No branch rows yet — showing the first lane buckets with zero counts until repo-workflow data arrives.'}
      </figcaption>
    </figure>
  )
}

export function BranchingCategoryMixBar({ rows }: { rows: CategoryCountRow[] }) {
  if (!rows.length) return null
  const total = rows.reduce((s, r) => s + r.count, 0) || 1
  const w = 400
  const h = 36
  type Seg = { x: number; segW: number; category: string; count: number; color: string }
  const built: Seg[] = []
  let curX = 2
  rows.forEach((r, i) => {
    const segW = (r.count / total) * (w - 4)
    const displayW = Math.max(segW, r.count > 0 ? 2 : 0)
    built.push({
      x: curX,
      segW: displayW,
      category: r.category,
      count: r.count,
      color: MIX_COLORS[i % MIX_COLORS.length],
    })
    curX += segW
  })
  const segs = built.map((seg, i) => (
    <rect key={`${seg.category}-${i}`} x={seg.x} y={6} width={seg.segW} height={h - 12} rx={3} fill={seg.color} opacity={0.88}>
      <title>{`${seg.category}: ${seg.count}`}</title>
    </rect>
  ))

  const aria = `Branch categories: ${rows.map((r) => `${r.category} ${r.count}`).join(', ')}`

  return (
    <figure style={{ margin: '0.75rem 0 0' }}>
      <svg width="100%" height={h + 28} viewBox={`0 0 ${w} ${h + 28}`} role="img" aria-label={aria} style={{ maxWidth: 440 }}>
        {segs}
        <text x={2} y={h + 18} fontSize={10} fill="currentColor" opacity={0.75}>
          {rows.map((r) => `${r.category} (${r.count})`).join(' · ')}
        </text>
      </svg>
      <figcaption className="le-muted" style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
        Share of listed branches by category (from host snapshot when repo workflow is enabled).
      </figcaption>
    </figure>
  )
}

export function BranchingPolicyLadder({
  steps,
  activeIndex,
}: {
  steps: readonly PolicyResolutionStep[]
  activeIndex: number
}) {
  return (
    <ol
      style={{
        listStyle: 'none',
        padding: 0,
        margin: '0.75rem 0 0',
        borderLeft: '2px solid rgba(0,0,0,0.12)',
        paddingLeft: '1rem',
      }}
    >
      {steps.map((step, i) => {
        const active = i === activeIndex
        return (
          <li
            key={step.id}
            style={{
              marginBottom: '0.65rem',
              padding: '0.35rem 0.5rem',
              borderRadius: 6,
              background: active ? 'rgba(13, 110, 253, 0.08)' : undefined,
              fontWeight: active ? 600 : 400,
            }}
          >
            <div>{step.label}</div>
            <div className="le-muted" style={{ fontSize: '0.85rem', fontWeight: 400 }}>
              {step.detail}
            </div>
            {active ? (
              <div style={{ fontSize: '0.8rem', marginTop: '0.2rem' }} className="le-muted">
                Resolved for this repository
              </div>
            ) : null}
          </li>
        )
      })}
    </ol>
  )
}

export function BranchingPayloadSchemaGrid({ cards, jsonAnchorId }: { cards: readonly PayloadSchemaCard[]; jsonAnchorId: string }) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(11.5rem, 1fr))',
        gap: '0.65rem',
        marginTop: '0.75rem',
      }}
    >
      {cards.map((c) => (
        <div
          key={c.key}
          style={{
            border: '1px solid rgba(0,0,0,0.12)',
            borderRadius: 8,
            padding: '0.55rem 0.65rem',
            minHeight: '5.5rem',
          }}
        >
          <div style={{ fontFamily: 'ui-monospace, monospace', fontSize: '0.9rem', fontWeight: 600 }}>{c.title}</div>
          <p className="le-muted" style={{ margin: '0.35rem 0 0', fontSize: '0.82rem', lineHeight: 1.35 }}>
            {c.body}
          </p>
        </div>
      ))}
      <div
        style={{
          border: '1px dashed rgba(0,0,0,0.18)',
          borderRadius: 8,
          padding: '0.55rem 0.65rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '5.5rem',
        }}
      >
        <a href={`#${jsonAnchorId}`} className="forge-support" style={{ fontSize: '0.9rem' }}>
          Full JSON payload
        </a>
      </div>
    </div>
  )
}

export function BranchingKsRoadmapHint() {
  return (
    <figure style={{ margin: '0.75rem 0 0', maxWidth: 240 }}>
      <img
        src="/__ks/assets/svg/template-roadmap.svg"
        alt="Abstract roadmap lanes diagram (Kitchensink template)"
        width={220}
        height={220}
        loading="lazy"
        style={{ width: '100%', maxWidth: 220, height: 'auto', opacity: 0.92 }}
      />
      <figcaption className="le-muted" style={{ fontSize: '0.82rem', marginTop: '0.35rem' }}>
        Shared Kitchensink template for roadmap-style structure — use Classic Repo & strategy for submodule tables and registry notes.
      </figcaption>
    </figure>
  )
}

export function BranchingTopologyFigure({ policy, lanesModel }: { policy: BranchingPolicy | undefined; lanesModel: boolean }) {
  const uid = useId().replace(/:/g, '')
  const trunk = (policy?.trunk || 'main').trim() || 'main'
  const fp = (policy?.feature_prefix || 'feature/').trim() || 'feature/'
  const fixp = (policy?.fix_prefix || 'fix/').trim() || 'fix/'
  const pp = (policy?.product_prefix || 'product/').trim() || 'product/'
  const ip = (policy?.iter_prefix || 'iter/').trim() || 'iter/'
  const sp = (policy?.spark_prefix || 'spark/').trim() || 'spark/'
  const mk = `url(#${uid}-arrow)`

  if (lanesModel) {
    return (
      <figure style={{ margin: '0.75rem 0 0' }}>
        <svg width="100%" viewBox="0 0 420 120" role="img" aria-label="Forge lanes topology: product to iteration to spark toward trunk" style={{ maxWidth: 440 }}>
          <defs>
            <marker id={`${uid}-arrow`} markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
              <polygon points="0 0, 8 4, 0 8" fill="#495057" />
            </marker>
          </defs>
          <rect x="10" y="20" width="88" height="36" rx="6" fill="#e7f1ff" stroke="#0d6efd" />
          <text x="54" y="42" textAnchor="middle" fontSize="11" fill="#052c65">
            {pp}*
          </text>
          <line x1="98" y1="38" x2="132" y2="38" stroke="#495057" strokeWidth="1.5" markerEnd={mk} />
          <rect x="132" y="20" width="88" height="36" rx="6" fill="#e7f1ff" stroke="#0d6efd" />
          <text x="176" y="42" textAnchor="middle" fontSize="11" fill="#052c65">
            {ip}*
          </text>
          <line x1="220" y1="38" x2="254" y2="38" stroke="#495057" strokeWidth="1.5" markerEnd={mk} />
          <rect x="254" y="20" width="88" height="36" rx="6" fill="#fff3cd" stroke="#ffc107" />
          <text x="298" y="42" textAnchor="middle" fontSize="11" fill="#664d03">
            {sp}*
          </text>
          <line x1="342" y1="38" x2="372" y2="38" stroke="#495057" strokeWidth="1.5" markerEnd={mk} />
          <rect x="372" y="22" width="44" height="32" rx="6" fill="#d1e7dd" stroke="#198754" />
          <text x="394" y="41" textAnchor="middle" fontSize="11" fill="#0a3622">
            {trunk}
          </text>
          <text x="210" y="100" textAnchor="middle" fontSize="10" fill="#6c757d">
            Promotion through review and checks still applies before merging to {trunk}.
          </text>
        </svg>
        <figcaption className="le-muted" style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
          Forge lanes: work flows product → iteration → spark (conceptual), then integrates to the trunk.
        </figcaption>
      </figure>
    )
  }

  return (
    <figure style={{ margin: '0.75rem 0 0' }}>
      <svg width="100%" viewBox="0 0 400 100" role="img" aria-label="Team tier: short-lived branches merge to trunk via pull request" style={{ maxWidth: 420 }}>
        <defs>
          <marker id={`${uid}-arrow`} markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <polygon points="0 0, 8 4, 0 8" fill="#495057" />
          </marker>
        </defs>
        <rect x="20" y="28" width="100" height="40" rx="8" fill="#e7f1ff" stroke="#0d6efd" />
        <text x="70" y="52" textAnchor="middle" fontSize="12" fill="#052c65">
          {fp}…
        </text>
        <rect x="150" y="28" width="100" height="40" rx="8" fill="#f8d7da" stroke="#dc3545" />
        <text x="200" y="52" textAnchor="middle" fontSize="12" fill="#58151c">
          {fixp}…
        </text>
        <line x1="120" y1="48" x2="168" y2="48" stroke="#adb5bd" strokeDasharray="4 3" />
        <line x1="250" y1="48" x2="288" y2="48" stroke="#495057" strokeWidth="1.5" markerEnd={mk} />
        <rect x="288" y="30" width="92" height="36" rx="8" fill="#d1e7dd" stroke="#198754" />
        <text x="334" y="52" textAnchor="middle" fontSize="12" fill="#0a3622">
          {trunk}
        </text>
        <text x="200" y="88" textAnchor="middle" fontSize="10" fill="#6c757d">
          Short-lived topic branches integrate through pull request and review.
        </text>
      </svg>
      <figcaption className="le-muted" style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
        Team tier: most work lands on feature or fix prefixes, then merges to the protected trunk.
      </figcaption>
    </figure>
  )
}

export type PrSpineRow = { number?: number; title?: string; head_ref?: string; base_ref?: string }

export function BranchingPrSpine({ prs }: { prs: PrSpineRow[] }) {
  if (!prs.length || prs.length > 12) return null
  return (
    <div style={{ marginTop: '0.85rem' }} aria-label="Pull request head to base mapping">
      <h4 className="le-panel__title" style={{ fontSize: '0.95rem', marginBottom: '0.35rem' }}>
        PR map (compact)
      </h4>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {prs.map((pr, idx) => (
          <li
            key={`${pr.number}-${idx}`}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              flexWrap: 'wrap',
              marginBottom: '0.4rem',
              paddingLeft: '0.5rem',
              borderLeft: '3px solid rgba(13,110,253,0.35)',
            }}
          >
            <span className="le-muted" style={{ fontSize: '0.8rem', minWidth: '2rem' }}>
              {pr.number != null ? `#${pr.number}` : '—'}
            </span>
            <code style={{ fontSize: '0.78rem' }}>{pr.head_ref || 'head'}</code>
            <span aria-hidden style={{ opacity: 0.5 }}>
              →
            </span>
            <code style={{ fontSize: '0.78rem' }}>{pr.base_ref || 'base'}</code>
            {pr.title ? (
              <span className="le-muted" style={{ fontSize: '0.8rem' }}>
                — {pr.title}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}
