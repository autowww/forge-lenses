import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGetJson } from '../../api/http'

type HandoffGaps = {
  missing_acceptance?: string[]
  missing_evidence?: string[]
  approval_status?: string
  return_incomplete?: boolean
}

type HandoffStatus = {
  launch_pack_version?: string
  target_key?: string
  return_status?: string
  branch?: string
  pr_url?: string
  partial_return?: boolean
  stale?: boolean
  latest_execution_return?: { id?: string; payload?: Record<string, unknown> }
}

type HubRow = {
  package_id?: string
  status?: HandoffStatus
  gaps?: HandoffGaps
}

/**
 * Sprint B5 — handoff / execution-return loop (Cursor, Claude, …) for Plan, Today, and project views.
 */
export function HandoffLoopPanel({
  workItemId,
  traceQueryStoryId,
}: {
  workItemId: string
  /** Graph root for trace link (often same as workItemId). */
  traceQueryStoryId?: string
}) {
  const [show, setShow] = useState(false)
  const [rows, setRows] = useState<HubRow[]>([])
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
        const en = await apiGetJson<{ ok?: boolean; enabled?: boolean }>('/api/handoffs/enabled')
        if (cancelled) return
        if (!en.ok || en.enabled === false) {
          setShow(false)
          return
        }
        setShow(true)
        const by = await apiGetJson<{ ok?: boolean; package_ids?: string[] }>(
          `/api/handoffs/by-work-unit?work_item_id=${encodeURIComponent(wid)}`,
        )
        if (cancelled || !by.ok || !(by.package_ids?.length ?? 0)) {
          setRows([])
          return
        }
        const out: HubRow[] = []
        for (const pid of (by.package_ids ?? []).slice(0, 3)) {
          const [st, gp] = await Promise.all([
            apiGetJson<HandoffStatus & { ok?: boolean }>(
              `/api/handoffs/${encodeURIComponent(pid)}/status`,
            ),
            apiGetJson<HandoffGaps & { ok?: boolean }>(`/api/handoffs/${encodeURIComponent(pid)}/gaps`),
          ])
          out.push({ package_id: pid, status: st, gaps: gp })
        }
        if (!cancelled) setRows(out)
      } catch (e) {
        if (!cancelled) {
          setErr(e instanceof Error ? e.message : 'handoff fetch failed')
          setShow(false)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [workItemId])

  if (!show && !err) return null

  return (
    <section className="le-panel" aria-label="Handoff and return loop">
      <h3 className="le-panel__title">Handoff / return (B5)</h3>
      {err ? <p className="forge-support">{err}</p> : null}
      {!rows.length && show ? (
        <p className="forge-support">No handoff packages scoped to this work item in the orchestration graph.</p>
      ) : null}
      {rows.map((row) => {
        const st = row.status
        const gp = row.gaps
        const ret = st?.latest_execution_return?.payload as Record<string, unknown> | undefined
        const files = (ret?.changed_files as string[] | undefined) ?? []
        return (
          <div key={row.package_id} className="le-card" style={{ marginBottom: '0.5rem', padding: '0.5rem 0.65rem' }}>
            <div style={{ fontWeight: 600 }}>
              <code className="le-mono">{row.package_id}</code>
            </div>
            <p className="le-muted" style={{ fontSize: '0.82rem', margin: '0.25rem 0' }}>
              Target <strong>{st?.target_key ?? '—'}</strong> · LP <code>{st?.launch_pack_version ?? '—'}</code> ·
              return <strong>{String(st?.return_status ?? '—')}</strong>
              {gp?.approval_status ? (
                <>
                  {' '}
                  · approval <strong>{gp.approval_status}</strong>
                </>
              ) : null}
              {st?.partial_return ? ' · partial return' : null}
              {st?.stale ? ' · stale' : null}
            </p>
            {st?.branch ? (
              <p className="forge-support" style={{ margin: '0.15rem 0' }}>
                Branch: <code>{st.branch}</code>
                {st.pr_url ? (
                  <>
                    {' '}
                    ·{' '}
                    <a href={st.pr_url} target="_blank" rel="noreferrer">
                      PR
                    </a>
                  </>
                ) : null}
              </p>
            ) : null}
            {files.length > 0 ? (
              <p className="forge-support" style={{ margin: '0.15rem 0' }}>
                Files changed: {files.slice(0, 5).join(', ')}
                {files.length > 5 ? '…' : ''}
              </p>
            ) : null}
            {(gp?.missing_acceptance?.length ?? 0) > 0 || (gp?.missing_evidence?.length ?? 0) > 0 ? (
              <ul className="le-list" style={{ fontSize: '0.8rem', margin: '0.35rem 0' }}>
                {(gp?.missing_acceptance ?? []).map((x) => (
                  <li key={`a-${x}`}>
                    Missing acceptance: <code>{x}</code>
                  </li>
                ))}
                {(gp?.missing_evidence ?? []).map((x) => (
                  <li key={`e-${x}`}>
                    Missing evidence: <code>{x}</code>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="forge-support" style={{ margin: '0.2rem 0' }}>
                No blocking gaps flagged for this package (or return not yet ingested).
              </p>
            )}
          </div>
        )
      })}
      {show && traceRoot ? (
        <p className="forge-support" style={{ marginTop: '0.35rem' }}>
          <Link
            to={`/orchestration/trace?root=${encodeURIComponent(traceRoot)}&direction=both&max_depth=9&max_nodes=500`}
          >
            Trace from work item
          </Link>{' '}
          · API <code>/api/handoffs</code>, <code>/api/execution-sessions/…</code>
        </p>
      ) : null}
    </section>
  )
}
