import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGetJson } from '../../api/http'

type LaunchBundle = {
  ok?: boolean
  launch?: { id?: string; display_name?: string }
  release_id?: string
  signal_count?: number
  learning_summary_ids?: string[]
  followon_ore_ids?: string[]
  demand_signal_ids?: string[]
  scores?: {
    launch_confidence?: number
    evidence_completeness?: number
    explanations?: string[]
  }
  signals?: unknown[]
}

/**
 * Sprint B6 — PDLC outcome loop (launch → signals → learning → Ore) on Plan, Today, and project views.
 */
export function OutcomeLoopPanel({
  workItemId,
  traceQueryStoryId,
}: {
  workItemId: string
  traceQueryStoryId?: string
}) {
  const [show, setShow] = useState(false)
  const [bundles, setBundles] = useState<LaunchBundle[]>([])
  const [err, setErr] = useState<string | null>(null)

  const traceRoot = (traceQueryStoryId || workItemId).trim()

  useEffect(() => {
    let cancelled = false
    const wid = workItemId.trim()
    if (!wid) {
      setShow(false)
      return
    }
    ;(async () => {
      try {
        const en = await apiGetJson<{ ok?: boolean; enabled?: boolean }>('/api/outcomes/enabled')
        if (cancelled) return
        if (!en.ok || en.enabled === false) {
          setShow(false)
          return
        }
        setShow(true)
        const by = await apiGetJson<{ ok?: boolean; launch_ids?: string[] }>(
          `/api/outcomes/by-work-unit?work_item_id=${encodeURIComponent(wid)}`,
        )
        if (cancelled || !by.ok || !(by.launch_ids?.length ?? 0)) {
          setBundles([])
          return
        }
        const out: LaunchBundle[] = []
        for (const lid of (by.launch_ids ?? []).slice(0, 2)) {
          const b = await apiGetJson<LaunchBundle>(`/api/launches/${encodeURIComponent(lid)}`)
          if (b.ok) out.push(b)
        }
        if (!cancelled) setBundles(out)
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : 'Outcome API error')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [workItemId])

  if (!show && !err) return null

  return (
    <section className="le-panel" aria-label="PDLC outcome loop">
      <h3 className="le-panel__title">Outcomes / PDLC loop (B6)</h3>
      {err ? <p className="forge-support">{err}</p> : null}
      {!bundles.length && show ? (
        <p className="forge-support">No launch records linked to this work item in the orchestration graph.</p>
      ) : null}
      {bundles.map((b) => {
        const lid = b.launch?.id ?? 'launch'
        const sc = b.scores
        const sigN = b.signals?.length ?? b.signal_count ?? 0
        return (
          <div key={lid} className="le-card" style={{ marginBottom: '0.5rem', padding: '0.5rem 0.65rem' }}>
            <div style={{ fontWeight: 600 }}>{b.launch?.display_name ?? 'Launch'}</div>
            <p className="le-muted" style={{ fontSize: '0.82rem', margin: '0.25rem 0' }}>
              Release <code>{b.release_id ?? '—'}</code> · {sigN} outcome signals · launch confidence{' '}
              <strong>{sc?.launch_confidence ?? '—'}</strong> · evidence completeness{' '}
              <strong>{sc?.evidence_completeness ?? '—'}</strong>
            </p>
            {(b.learning_summary_ids?.length ?? 0) > 0 ? (
              <p className="forge-support" style={{ margin: '0.15rem 0' }}>
                Learning summaries:{' '}
                {(b.learning_summary_ids ?? []).slice(0, 3).map((id) => (
                  <code key={id} className="le-mono" style={{ marginRight: '0.35rem' }}>
                    {id}
                  </code>
                ))}
              </p>
            ) : null}
            {(b.demand_signal_ids?.length ?? 0) > 0 ? (
              <p className="forge-support" style={{ margin: '0.15rem 0' }}>
                Follow-on Ore / demand:{' '}
                {(b.demand_signal_ids ?? []).map((id) => (
                  <code key={id} className="le-mono" style={{ marginRight: '0.35rem' }}>
                    {id}
                  </code>
                ))}
              </p>
            ) : (
              <p className="forge-support" style={{ margin: '0.15rem 0' }}>
                No demand signal linked yet from this launch window.
              </p>
            )}
            {(sc?.explanations?.length ?? 0) > 0 ? (
              <ul className="le-list" style={{ fontSize: '0.78rem', margin: '0.35rem 0' }}>
                {(sc?.explanations ?? []).slice(0, 4).map((x) => (
                  <li key={x.slice(0, 80)}>{x}</li>
                ))}
              </ul>
            ) : null}
            <p className="forge-support" style={{ marginTop: '0.25rem' }}>
              <Link to={`/orchestration/trace?root=${encodeURIComponent(lid)}&direction=both&max_depth=10&max_nodes=500`}>
                Trace from launch
              </Link>
            </p>
          </div>
        )
      })}
      {show && traceRoot ? (
        <p className="forge-support" style={{ marginTop: '0.35rem' }}>
          <Link
            to={`/orchestration/trace?root=${encodeURIComponent(traceRoot)}&direction=both&max_depth=12&max_nodes=500`}
          >
            Trace from work item
          </Link>{' '}
          · <code>/api/outcomes</code>, <code>/api/launches/…</code>
        </p>
      ) : null}
    </section>
  )
}
