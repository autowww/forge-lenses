import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGetJson } from '../../api/http'

const DEMO_HYBRID = 'ogs:demo:b4:inst:hybrid'
const DEMO_BINDING = 'ogs:demo:b4:inst:binding'

type Readiness = {
  ok?: boolean
  complete?: boolean
  missing_required_outputs?: string[]
  missing_signoffs?: string[]
  missing_inputs?: string[]
  required_outputs?: string[]
  delivery_mode?: string
}

type Inspector = {
  ok?: boolean
  neutral_intent?: string
  mapped_forge_ritual?: string
  forge_projection_label?: string
  delivery_mode?: string
  completeness?: Readiness
}

function ReadinessList({ title, r }: { title: string; r: Readiness | null }) {
  if (!r?.ok) {
    return (
      <p className="forge-support">
        {title}: {r ? 'Could not load readiness.' : 'Loading…'}
      </p>
    )
  }
  return (
    <div className="le-muted" style={{ fontSize: '0.85rem', marginTop: '0.35rem' }}>
      <strong>{title}</strong>
      {r.delivery_mode ? (
        <span>
          {' '}
          — mode <code>{r.delivery_mode}</code>
        </span>
      ) : null}
      <ul className="le-list" style={{ marginTop: '0.25rem' }}>
        <li>
          Complete: <strong>{r.complete ? 'yes' : 'no'}</strong>
        </li>
        {(r.missing_required_outputs?.length ?? 0) > 0 ? (
          <li>Missing outputs: {r.missing_required_outputs?.join(', ')}</li>
        ) : null}
        {(r.missing_signoffs?.length ?? 0) > 0 ? (
          <li>Missing sign-offs: {r.missing_signoffs?.join(', ')}</li>
        ) : null}
        {(r.missing_inputs?.length ?? 0) > 0 ? (
          <li>Missing inputs: {r.missing_inputs?.join(', ')}</li>
        ) : null}
      </ul>
    </div>
  )
}

function InspectorBlock({ label, row }: { label: string; row: Inspector | null }) {
  if (!row?.ok) {
    return (
      <p className="forge-support">
        {label}: {row ? '—' : 'Loading…'}
      </p>
    )
  }
  const c = row.completeness
  return (
    <div className="le-card" style={{ padding: '0.5rem 0.65rem', marginBottom: '0.35rem' }}>
      <div style={{ fontWeight: 600 }}>{label}</div>
      <div className="le-muted" style={{ fontSize: '0.8rem' }}>
        Intent <code>{row.neutral_intent}</code> → Forge <em>{row.mapped_forge_ritual ?? row.forge_projection_label}</em>
        {row.delivery_mode ? (
          <>
            {' '}
            · mode <code>{row.delivery_mode}</code>
          </>
        ) : null}
      </div>
      {c ? (
        <ul className="le-list" style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
          <li>Required outputs: {(c.required_outputs ?? []).join(', ') || '—'}</li>
          <li>Gaps: outputs {(c.missing_required_outputs ?? []).join(', ') || 'none'}</li>
        </ul>
      ) : null}
    </div>
  )
}

/**
 * Sprint B4 — ceremony bridge inspector (neutral intent ↔ Forge ritual, delivery mode, readiness gaps).
 * Shown on Plan and Today without redesigning the page shell.
 */
export function CeremonyBridgePanel({ studioPlanHref }: { studioPlanHref?: string }) {
  const [enabled, setEnabled] = useState<boolean | null>(null)
  const [hybridR, setHybridR] = useState<Readiness | null>(null)
  const [bindR, setBindR] = useState<Readiness | null>(null)
  const [hybridI, setHybridI] = useState<Inspector | null>(null)
  const [bindI, setBindI] = useState<Inspector | null>(null)
  const [traceHref, setTraceHref] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const en = await apiGetJson<{ ok?: boolean; enabled?: boolean }>('/api/ceremonies/enabled')
        if (cancelled) return
        if (!en.ok || en.enabled === false) {
          setEnabled(false)
          return
        }
        setEnabled(true)
        const [hr, br, hi, bi] = await Promise.all([
          apiGetJson<Readiness>(`/api/ceremonies/readiness/${encodeURIComponent(DEMO_HYBRID)}`),
          apiGetJson<Readiness>(`/api/ceremonies/readiness/${encodeURIComponent(DEMO_BINDING)}`),
          apiGetJson<Inspector>(`/api/ceremonies/inspector/${encodeURIComponent(DEMO_HYBRID)}`),
          apiGetJson<Inspector>(`/api/ceremonies/inspector/${encodeURIComponent(DEMO_BINDING)}`),
        ])
        if (cancelled) return
        setHybridR(hr)
        setBindR(br)
        setHybridI(hi)
        setBindI(bi)
        setTraceHref(
          `/orchestration/trace?root=${encodeURIComponent(DEMO_BINDING)}&direction=both&max_depth=8&max_nodes=400`,
        )
      } catch {
        if (!cancelled) setEnabled(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (enabled === false || enabled === null) {
    return null
  }

  return (
    <section className="le-panel" aria-label="Ceremony bridge">
      <h3 className="le-panel__title">Ceremony bridge (B4)</h3>
      <p className="forge-support">
        Neutral intents C1–C6 project to Forge rituals via explicit mappings. Outputs record delivery mode; binding
        outputs require human sign-off.
      </p>
      <InspectorBlock label="Hybrid demo (non-binding synthesis)" row={hybridI} />
      <InspectorBlock label="Binding demo (human-signed gate)" row={bindI} />
      <ReadinessList title="Readiness — hybrid instance" r={hybridR} />
      <ReadinessList title="Readiness — binding instance" r={bindR} />
      <p className="forge-support" style={{ marginTop: '0.5rem' }}>
        API: <code>/api/ceremonies/intents</code>, <code>/api/ceremonies/templates</code>,{' '}
        <code>/api/ceremonies/instances/…</code>
        {traceHref ? (
          <>
            {' '}
            ·{' '}
            <Link to={traceHref}>Trace from binding ceremony</Link>
          </>
        ) : null}
        {studioPlanHref ? (
          <>
            {' '}
            · <Link to={studioPlanHref}>Studio plan</Link>
          </>
        ) : null}
      </p>
    </section>
  )
}
