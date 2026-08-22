import { useEffect, useState, type ReactNode } from 'react'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useResilientJsonBlock } from '../../hooks/useResilientJsonBlock'
import { StatePanel } from '../page/StatePanel'
import { isScanOnlyProvider } from '../../lib/apiInternalFields'
import { recordPageFailure } from '../../telemetry/studioTelemetry'

type CalendarEvent = {
  type?: string
  start?: string
  title?: string
  active?: boolean
  ref_id?: string
}

type CrossTeamPayload = {
  ok?: boolean
  feature_enabled?: boolean
  provider_kind?: string
  resolved_at?: string
  hints?: string[]
  focus_release_version?: string
  teams?: { id?: string; name?: string }[]
  initiatives?: { id?: string; name?: string; summary?: string }[]
  readiness_views?: {
    id?: string
    environment_id?: string
    release_version?: string
    ready?: boolean
    gaps?: string[]
  }[]
  dependency_board?: {
    nodes?: { id?: string; kind?: string; label?: string }[]
    edges?: { from_id?: string; to_id?: string; relation?: string; note?: string }[]
  }
  change_requests?: {
    id?: string
    title?: string
    risk?: string
    scope?: string
    rollback_notes?: string
    approvers?: { role?: string; status?: string; login?: string }[]
  }[]
  cab_sessions?: {
    id?: string
    scheduled_at?: string
    decisions?: { change_request_id?: string; decision?: string; notes?: string }[]
  }[]
  release_calendar?: { events?: CalendarEvent[] }
  go_no_go_packet?: { markdown?: string; sections?: { title?: string; body_md?: string }[] }
  communication_artifacts?: {
    release_notes_md?: string
    stakeholder_summary_md?: string
    blocker_summary_md?: string
  }
  live_enrichment?: {
    release_train?: {
      name?: string
      current_focus?: string
      candidates?: { version?: string; status?: string }[]
    } | null
    blocked_promotions?: { promotion_id?: string; reason?: string; detail?: string }[]
    rollback_targets?: { environment_id?: string; rollback_target_version?: string }[]
  }
}

/**
 * Plan → Today: single release-manager lens — what ships, blockers, cross-team dependencies,
 * CAB-lite, rollback, and go/no-go packet built from live CI/CD + quality + security + fixture.
 */
export function ReleaseManagerCard() {
  const { state } = useWorkspace()
  const refreshKey = state?.resolved_at ?? null
  const [copyOk, setCopyOk] = useState<string | null>(null)

  const block = useResilientJsonBlock<CrossTeamPayload>('/api/cross-team-release/overview', {
    snapshotKey: 'cross-team-release-overview',
    refreshKey,
  })

  const data = block.data
  const phase = block.phase

  useEffect(() => {
    if (phase === 'error' && block.failure) {
      recordPageFailure('cross_team_release_overview', block.failure.summary)
    }
  }, [phase, block.failure])

  const copyMd = async (label: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopyOk(label)
      window.setTimeout(() => setCopyOk(null), 2000)
    } catch {
      setCopyOk(null)
    }
  }

  let inner: ReactNode

  if (phase === 'loading' && !data) {
    inner = (
      <StatePanel
        variant="loading"
        density="compact"
        title="Loading release manager overview"
        description="Dependency board, calendar, change records, CAB, and go/no-go packet."
      />
    )
  } else if (phase === 'error' && !data) {
    inner = (
      <StatePanel
        variant="error"
        density="compact"
        title="Could not load release manager overview"
        description="Confirm the Lenses server is running, then retry."
        technicalDetail={block.failure?.summary ?? null}
        actions={
          <button type="button" className="le-btn le-btn--primary" onClick={() => block.retry()}>
            Retry
          </button>
        }
      />
    )
  } else if (!data?.ok) {
    inner = (
      <StatePanel variant="error" density="compact" title="Unexpected payload" description="Try again or check the API." />
    )
  } else if (data.feature_enabled === false) {
    inner = (
      <StatePanel
        variant="empty"
        density="compact"
        title="Cross-team release orchestration disabled"
        description="Set LENSES_EXPERIMENTAL_CROSS_TEAM_RELEASE=1 (default on) to enable this card."
      />
    )
  } else if (isScanOnlyProvider(data)) {
    inner = (
      <StatePanel
        variant="empty"
        density="compact"
        title="No cross-team release fixture"
        description={
          <>
            Add <code className="le-mono">.lenses-local/cross-team-release.json</code> or set{' '}
            <code className="le-mono">LENSES_CROSS_TEAM_RELEASE_SEED_DEMO=1</code> for the demo board, change
            requests, CAB, and generated packets.
          </>
        }
      />
    )
  } else {
    const live = data.live_enrichment || {}
    const train = live.release_train
    const blocked = live.blocked_promotions || []
    const roll = live.rollback_targets || []
    const board = data.dependency_board || {}
    const nodes = board.nodes || []
    const edges = board.edges || []
    const byKind: Record<string, number> = {}
    for (const n of nodes) {
      const k = n.kind || 'other'
      byKind[k] = (byKind[k] || 0) + 1
    }
    const crs = data.change_requests || []
    const cab = data.cab_sessions || []
    const cal = (data.release_calendar?.events || []).slice(0, 8)
    const pkt = data.go_no_go_packet?.markdown || ''
    const comm = data.communication_artifacts || {}

    inner = (
      <>
        <p className="forge-support" style={{ marginTop: 0 }}>
          Answers in one place: <strong>what ships</strong>, <strong>what blocks it</strong>,{' '}
          <strong>cross-team dependencies</strong>, <strong>approvals</strong>, and <strong>rollback</strong>. Packet
          and comms are generated from live CI/CD, quality, and security data plus your fixture.
        </p>

        <div className="le-stats" style={{ marginTop: '0.75rem' }}>
          <div className="le-stat">
            <span className="le-stat__value">{train?.current_focus || data.focus_release_version || '—'}</span>
            <span className="le-stat__label">Train focus</span>
          </div>
          <div className="le-stat">
            <span className="le-stat__value">{blocked.length}</span>
            <span className="le-stat__label">Blocked promos</span>
          </div>
          <div className="le-stat">
            <span className="le-stat__value">{edges.length}</span>
            <span className="le-stat__label">Dependency edges</span>
          </div>
        </div>

        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginTop: '1rem', marginBottom: '0.35rem' }}>
          What ships
        </h3>
        {train?.name ? (
          <p className="forge-support" style={{ marginTop: 0 }}>
            Train <strong>{train.name}</strong>
            {train.candidates?.length ? (
              <>
                {' '}
                — candidates:{' '}
                {train.candidates
                  .slice(0, 4)
                  .map((c) => c.version)
                  .join(', ')}
              </>
            ) : null}
          </p>
        ) : (
          <p className="forge-support" style={{ marginTop: 0 }}>No release train in live CI/CD payload.</p>
        )}

        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginTop: '0.85rem', marginBottom: '0.35rem' }}>
          What blocks it
        </h3>
        {blocked.length ? (
          <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem', fontSize: '0.9rem' }}>
            {blocked.slice(0, 8).map((b, i) => (
              <li key={`${b.promotion_id}-${i}`}>
                <code className="le-mono">{b.promotion_id}</code> — {b.reason}
                {b.detail ? <span className="forge-support"> — {b.detail}</span> : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="forge-support" style={{ marginTop: 0 }}>No blocked promotions in merged live data.</p>
        )}

        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginTop: '0.85rem', marginBottom: '0.35rem' }}>
          Dependency board
        </h3>
        <p className="forge-support" style={{ marginTop: 0 }}>
          Nodes by kind:{' '}
          {Object.entries(byKind)
            .map(([k, v]) => `${k} (${v})`)
            .join(' · ') || '—'}
        </p>
        <div className="le-table-wrap" style={{ maxHeight: '11rem', overflow: 'auto' }}>
          <table className="le-table" style={{ fontSize: '0.85rem' }}>
            <thead>
              <tr>
                <th>From</th>
                <th>Relation</th>
                <th>To</th>
              </tr>
            </thead>
            <tbody>
              {edges.slice(0, 14).map((e, i) => (
                <tr key={`${e.from_id}-${e.to_id}-${i}`}>
                  <td>
                    <code className="le-mono">{e.from_id}</code>
                  </td>
                  <td>{e.relation || '—'}</td>
                  <td>
                    <code className="le-mono">{e.to_id}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginTop: '0.85rem', marginBottom: '0.35rem' }}>
          Readiness by environment
        </h3>
        <div className="le-table-wrap">
          <table className="le-table" style={{ fontSize: '0.85rem' }}>
            <thead>
              <tr>
                <th>Env</th>
                <th>Version</th>
                <th>Ready</th>
                <th>Gaps</th>
              </tr>
            </thead>
            <tbody>
              {(data.readiness_views || []).map((r) => (
                <tr key={r.id}>
                  <td>{r.environment_id}</td>
                  <td>{r.release_version}</td>
                  <td>{r.ready === true ? 'Yes' : r.ready === false ? 'No' : '—'}</td>
                  <td className="forge-support">{(r.gaps || []).join('; ') || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginTop: '0.85rem', marginBottom: '0.35rem' }}>
          Change requests &amp; rollback
        </h3>
        <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem', fontSize: '0.9rem' }}>
          {crs.map((cr) => (
            <li key={cr.id}>
              <code className="le-mono">{cr.id}</code> — {cr.title}{' '}
              <span className="forge-support">
                (risk: {cr.risk || '?'})
              </span>
              {cr.rollback_notes ? (
                <div className="forge-support" style={{ marginTop: '0.2rem' }}>
                  Rollback: {cr.rollback_notes.slice(0, 220)}
                  {cr.rollback_notes.length > 220 ? '…' : ''}
                </div>
              ) : null}
            </li>
          ))}
        </ul>

        {roll.length ? (
          <p className="forge-support" style={{ marginTop: '0.5rem' }}>
            <strong>Live rollback targets:</strong>{' '}
            {roll
              .map((r) => `${r.environment_id}→${r.rollback_target_version}`)
              .join('; ')}
          </p>
        ) : null}

        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginTop: '0.85rem', marginBottom: '0.35rem' }}>
          CAB-lite
        </h3>
        <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem', fontSize: '0.9rem' }}>
          {cab.map((c) => (
            <li key={c.id}>
              <code className="le-mono">{c.id}</code> @ {c.scheduled_at || '—'}
              {(c.decisions || []).map((d, j) => (
                <div key={j} className="forge-support">
                  CHG {d.change_request_id}: <strong>{d.decision}</strong>
                  {d.notes ? ` — ${d.notes}` : ''}
                </div>
              ))}
            </li>
          ))}
        </ul>

        <h3 className="le-panel__title" style={{ fontSize: '0.95rem', marginTop: '0.85rem', marginBottom: '0.35rem' }}>
          Release calendar (next events)
        </h3>
        <ul className="le-list" style={{ margin: '0.25rem 0', paddingLeft: '1.1rem', fontSize: '0.85rem' }}>
          {cal.map((ev, i) => (
            <li key={`${ev.ref_id}-${i}`}>
              <code className="le-mono">{ev.type}</code> — {ev.title}{' '}
              <span className="forge-support">{ev.start}</span>
              {ev.active ? ' (active)' : ''}
            </li>
          ))}
        </ul>

        <details style={{ marginTop: '0.75rem' }}>
          <summary className="le-delivery-link" style={{ cursor: 'pointer' }}>
            Go / no-go packet (Markdown)
          </summary>
          <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button type="button" className="le-btn le-btn--small" onClick={() => copyMd('packet', pkt)}>
              Copy packet
            </button>
          </div>
          <pre
            className="forge-support"
            style={{
              marginTop: '0.5rem',
              maxHeight: '14rem',
              overflow: 'auto',
              fontSize: '0.75rem',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {pkt || '—'}
          </pre>
        </details>

        <details style={{ marginTop: '0.5rem' }}>
          <summary className="le-delivery-link" style={{ cursor: 'pointer' }}>
            Communication artifacts
          </summary>
          <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="le-btn le-btn--small"
              onClick={() => copyMd('notes', comm.release_notes_md || '')}
            >
              Copy release notes draft
            </button>
            <button
              type="button"
              className="le-btn le-btn--small"
              onClick={() => copyMd('stake', comm.stakeholder_summary_md || '')}
            >
              Copy stakeholder summary
            </button>
            <button
              type="button"
              className="le-btn le-btn--small"
              onClick={() => copyMd('block', comm.blocker_summary_md || '')}
            >
              Copy blocker summary
            </button>
            {copyOk ? <span className="forge-support">Copied.</span> : null}
          </div>
        </details>

        {data.hints?.length ? (
          <ul className="le-list forge-support" style={{ marginTop: '0.75rem', fontSize: '0.85rem' }}>
            {data.hints.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        ) : null}

        <p style={{ marginTop: '0.75rem', marginBottom: 0 }}>
          <a className="le-btn le-btn--small" href="/api/cross-team-release/overview">
            Raw JSON
          </a>
        </p>
      </>
    )
  }

  return (
    <section className="le-delivery-section" aria-labelledby="le-release-manager-h" id="le-release-manager">
      <h2 id="le-release-manager-h" className="le-delivery-section__title">
        Release manager (cross-team)
      </h2>
      {inner}
    </section>
  )
}
