import { useEffect, useId, useMemo, useRef, useState, type RefObject } from 'react'
import { Link } from 'react-router-dom'
import type { DocsHealthSessionEvent, DocsHealthSessionHeaderStats } from '../../api/docsHealth'
import { formatSessionInstant } from '../../lib/docsHealthSessionFormat'
import { docsHealthEventKindLabel } from '../../lib/docsHealthTimelineLabels'
import { DOCS_HEALTH_PIPELINE_STEP_LABELS as DOCS_HEALTH_STEP_LABELS } from '../../lib/docsHealthStepLabels'
import { TechnicalDetails } from '../page'
import './docs-health-session.css'

export { DOCS_HEALTH_PIPELINE_STEP_LABELS as DOCS_HEALTH_STEP_LABELS } from '../../lib/docsHealthStepLabels'

function TimelineEventWhen({ iso }: { iso?: string }) {
  if (iso == null || String(iso).trim() === '') return null
  const { text, utcTitle, dateTime } = formatSessionInstant(iso)
  return (
    <div className="le-dh-block__meta">
      {dateTime ? (
        <time dateTime={dateTime} title={utcTitle}>
          {text}
        </time>
      ) : (
        <span title={utcTitle}>{text}</span>
      )}
    </div>
  )
}

function useElapsedSeconds(startedAt: string | undefined) {
  const [sec, setSec] = useState(0)
  useEffect(() => {
    if (!startedAt) {
      setSec(0)
      return
    }
    const start = Date.parse(startedAt)
    if (Number.isNaN(start)) {
      setSec(0)
      return
    }
    const tick = () => setSec(Math.max(0, Math.floor((Date.now() - start) / 1000)))
    tick()
    const id = window.setInterval(tick, 1000)
    return () => window.clearInterval(id)
  }, [startedAt])
  return sec
}

function fmtElapsed(totalSec: number) {
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  if (m >= 60) {
    const h = Math.floor(m / 60)
    const mm = m % 60
    return `${h}h ${mm}m`
  }
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

function CopyIdButton({ label, value }: { label: string; value: string }) {
  const [done, setDone] = useState(false)
  const copy = () => {
    void navigator.clipboard.writeText(value).then(
      () => {
        setDone(true)
        window.setTimeout(() => setDone(false), 2000)
      },
      () => {},
    )
  }
  return (
    <button
      type="button"
      className="le-btn le-btn--small le-btn--ghost"
      onClick={copy}
      aria-label={`Copy ${label}`}
    >
      {done ? 'Copied' : 'Copy'}
    </button>
  )
}

export function DocsHealthSessionHeaderStrip({
  startedAt,
  header,
  displayName,
  projectLabel,
  clusterLabel,
  sessionId,
  runId,
  busyStep,
  onCancelSession,
  cancelBusy,
  cancelDisabled,
  cancelError,
  runStateLine,
  streamMode = 'idle',
}: {
  startedAt?: string
  header?: DocsHealthSessionHeaderStats
  /** Human-readable runner name from the server (or derived for older sessions). */
  displayName?: string
  projectLabel: string
  clusterLabel?: string
  /** Full remediation session id (hex). */
  sessionId?: string
  /** Docs health scan run id this session is tied to. */
  runId?: string
  /** Server step request in flight (shows under the stats grid). */
  busyStep?: string | null
  onCancelSession?: () => void
  cancelBusy?: boolean
  cancelDisabled?: boolean
  cancelError?: string | null
  /** Tasklet run state line (e.g. ``running · cancelled``). */
  runStateLine?: string | null
  /** Live transport: SSE vs polling fallback. */
  streamMode?: 'sse' | 'poll' | 'idle'
}) {
  const liveId = useId()
  const elapsed = useElapsedSeconds(startedAt)
  const ver = header?.verification
  const verLabel =
    ver == null ? 'Not run' : ver.ok ? 'Approved' : 'Needs changes'
  const pipe = header?.verification_pipeline
  const pipeLabel = pipe == null ? 'Not run' : pipe.ok ? 'Passed' : 'Issues reported'

  return (
    <section className="le-panel" aria-labelledby={liveId}>
      <h2 id={liveId} className="le-panel__title">
        Run context
      </h2>
      {displayName ? (
        <p className="forge-support le-dh-session-header__runner-name">
          <strong>{displayName}</strong>
        </p>
      ) : null}
      <p className="forge-support le-muted" style={{ fontSize: '0.88rem', marginTop: displayName ? '0.25rem' : 0 }}>
        <strong>{projectLabel}</strong>
        {clusterLabel ? (
          <>
            {' '}
            · cluster: {clusterLabel}
          </>
        ) : null}
      </p>
      {sessionId || runId ? (
        <div className="le-dh-session-ids" aria-label="Session and scan identifiers">
          {sessionId ? (
            <div className="le-dh-session-ids__row">
              <span className="le-dh-session-ids__label">Session id</span>
              <code className="le-dh-session-ids__hash">{sessionId}</code>
              <CopyIdButton label="session id" value={sessionId} />
            </div>
          ) : null}
          {runId ? (
            <div className="le-dh-session-ids__row">
              <span className="le-dh-session-ids__label">Scan run id</span>
              <code className="le-dh-session-ids__hash">{runId}</code>
              <CopyIdButton label="scan run id" value={runId} />
            </div>
          ) : null}
        </div>
      ) : null}
      <div
        className="le-dh-session-header"
        aria-live="polite"
        aria-atomic="false"
        aria-label="Live session statistics"
      >
        <div className="le-dh-session-header__cell">
          <span className="le-dh-session-header__label">Elapsed</span>
          <span>{fmtElapsed(elapsed)}</span>
        </div>
        <div className="le-dh-session-header__cell">
          <span className="le-dh-session-header__label">Status</span>
          <div className="le-dh-session-header__status-row">
            <span>{header?.status || 'Not recorded'}</span>
            {onCancelSession ? (
              <button
                type="button"
                className="le-btn le-btn--small le-btn--ghost"
                onClick={onCancelSession}
                disabled={cancelDisabled === true || cancelBusy === true}
              >
                {cancelBusy ? 'Stopping…' : 'Stop session'}
              </button>
            ) : null}
          </div>
        </div>
        <div className="le-dh-session-header__cell">
          <span className="le-dh-session-header__label">Last model</span>
          <span title="Model used for the latest model call on this run">
            {header?.last_model_id || header?.active_model || 'Not recorded'}
          </span>
        </div>
        <div className="le-dh-session-header__cell">
          <span className="le-dh-session-header__label">Last provider</span>
          <span>{header?.last_provider || 'Not recorded'}</span>
        </div>
        <div className="le-dh-session-header__cell">
          <span className="le-dh-session-header__label">Tokens in / out</span>
          <span>
            {(header?.prompt_tokens ?? 0).toLocaleString()} / {(header?.completion_tokens ?? 0).toLocaleString()}
          </span>
        </div>
        <div className="le-dh-session-header__cell">
          <span className="le-dh-session-header__label">Total tokens</span>
          <span>{(header?.total_tokens ?? 0).toLocaleString()}</span>
        </div>
        <div className="le-dh-session-header__cell">
          <span className="le-dh-session-header__label">Commands</span>
          <span>{header?.commands_run ?? 0}</span>
        </div>
        <div className="le-dh-session-header__cell">
          <span className="le-dh-session-header__label">Files changed</span>
          <span>{header?.files_changed ?? 0}</span>
        </div>
        <div className="le-dh-session-header__cell">
          <span className="le-dh-session-header__label">Verification</span>
          <span>{verLabel}</span>
        </div>
        <div className="le-dh-session-header__cell">
          <span className="le-dh-session-header__label">Post-apply checks</span>
          <span>{pipeLabel}</span>
        </div>
        <div className="le-dh-session-header__cell">
          <span className="le-dh-session-header__label">Score delta</span>
          <span>
            {header?.score_delta == null
              ? 'Not recorded'
              : `${header.score_delta > 0 ? '+' : ''}${header.score_delta}`}
          </span>
        </div>
        {runStateLine ? (
          <div className="le-dh-session-header__cell">
            <span className="le-dh-session-header__label">Tasklet</span>
            <span title="Run lifecycle state from the orchestration layer">{runStateLine}</span>
          </div>
        ) : null}
        <div className="le-dh-session-header__cell">
          <span className="le-dh-session-header__label">Slot</span>
          <span>{header?.active_slot || 'Not recorded'}</span>
        </div>
        <div className="le-dh-session-header__cell">
          <span className="le-dh-session-header__label">Live feed</span>
          <span>
            {streamMode === 'sse'
              ? 'Streaming'
              : streamMode === 'poll'
                ? 'Polling'
                : 'Not connected'}
          </span>
        </div>
      </div>
      {busyStep ? (
        <p className="forge-support" role="status" aria-live="polite" style={{ marginTop: '0.65rem' }}>
          <strong>Working…</strong> {DOCS_HEALTH_STEP_LABELS[busyStep] ?? busyStep}
        </p>
      ) : null}
      {cancelError ? (
        <p className="forge-support le-dh-session-header__cancel-err" role="alert" style={{ marginTop: '0.65rem' }}>
          {cancelError}
        </p>
      ) : null}
      {header?.model_routing_preview?.slots ? (
        <div className="le-dh-session-routing" aria-label="Planned model routing per role">
          <h3 className="le-dh-session-routing__title">Planned model routing</h3>
          <p className="le-muted" style={{ fontSize: '0.82rem', marginTop: 0, maxWidth: '48rem' }}>
            Dispatch order follows your AI Setup model map for each role. Fallbacks run in the order shown. Change models
            under Settings → AI Setup.
          </p>
          <table className="le-dh-session-routing__table">
            <thead>
              <tr>
                <th scope="col">Role</th>
                <th scope="col">First provider</th>
                <th scope="col">Model id (settings)</th>
                <th scope="col">Fallback chain</th>
              </tr>
            </thead>
            <tbody>
              {(['triage.small', 'writer.medium', 'reviewer.high'] as const).map((key) => {
                const slot = header.model_routing_preview?.slots?.[key]
                if (!slot) return null
                const chain = (slot.chain_with_models || [])
                  .map((c) => `${c.provider ?? '?'}:${c.model ?? '—'}`)
                  .join(' → ')
                return (
                  <tr key={key}>
                    <td>{slot.label ?? key}</td>
                    <td>{slot.primary_provider ?? '—'}</td>
                    <td>
                      <code className="le-mono">{slot.primary_model ?? '—'}</code>
                    </td>
                    <td className="le-dh-session-routing__chain" title={chain}>
                      {chain || '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  )
}

function DhBlock({
  ev,
  focusRef,
  projectSlug,
}: {
  ev: DocsHealthSessionEvent
  focusRef?: RefObject<HTMLDivElement | null>
  projectSlug?: string
}) {
  const t = ev.type || 'note'
  const meta = <TimelineEventWhen iso={ev.ts} />

  if (t === 'summary') {
    return (
      <article className="le-dh-block" data-kind="summary">
        <h3 className="le-dh-block__title">{ev.title || 'Summary'}</h3>
        <p className="forge-support" style={{ whiteSpace: 'pre-wrap' }}>
          {ev.body}
        </p>
        {meta}
      </article>
    )
  }

  if (t === 'question') {
    return (
      <article
        className="le-dh-block"
        data-kind="question"
        ref={focusRef}
        tabIndex={-1}
        aria-label="Question from the documentation session"
      >
        <h3 className="le-dh-block__title">Question</h3>
        <p className="forge-support">{ev.prompt || ev.body}</p>
        {ev.choices?.length ? (
          <ul className="forge-support" style={{ margin: '0.35rem 0 0', paddingLeft: '1.2rem' }}>
            {ev.choices.map((c) => (
              <li key={c.id || c.label}>
                <strong>{c.label}</strong>
                {c.id ? <span className="le-muted"> · id: {c.id}</span> : null}
              </li>
            ))}
          </ul>
        ) : null}
        {meta}
      </article>
    )
  }

  if (t === 'file_inquiry') {
    return (
      <article className="le-dh-block" data-kind="file_inquiry">
        <h3 className="le-dh-block__title">File paths</h3>
        {ev.hint ? <p className="le-muted">{ev.hint}</p> : null}
        <ul style={{ margin: 0, paddingLeft: '1.2rem' }}>
          {(ev.paths || []).map((p) => (
            <li key={p}>
              <code>{p}</code>
            </li>
          ))}
        </ul>
        {meta}
      </article>
    )
  }

  if (t === 'plan') {
    const steps = ev.steps || []
    return (
      <article className="le-dh-block" data-kind="plan">
        <h3 className="le-dh-block__title">Plan</h3>
        <ol style={{ margin: 0 }}>
          {steps.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>
        {meta}
      </article>
    )
  }

  if (t === 'diff') {
    return (
      <article className="le-dh-block" data-kind="diff">
        <h3 className="le-dh-block__title">Proposed diff</h3>
        <p className="forge-support">
          <code>{ev.path}</code>
        </p>
        <p className="le-muted">{ev.unified}</p>
        {meta}
      </article>
    )
  }

  if (t === 'file_change') {
    return (
      <article className="le-dh-block" data-kind="file_change">
        <h3 className="le-dh-block__title">File change</h3>
        <p className="forge-support">
          <code>{ev.path}</code> · {ev.operation || 'write'} · {(ev.bytes_written ?? 0).toLocaleString()} bytes
        </p>
        {meta}
      </article>
    )
  }

  if (t === 'command') {
    return (
      <article className="le-dh-block" data-kind="command">
        <h3 className="le-dh-block__title">Command</h3>
        <p className="forge-support">
          <code>{ev.cmd}</code>
        </p>
        {ev.why ? <p className="forge-support">{ev.why}</p> : null}
        <p className="le-muted">
          Status: <strong>{ev.status || '—'}</strong>
          {ev.duration_ms != null ? ` · ${ev.duration_ms} ms` : null}
        </p>
        {ev.stdout_summary ? <p className="forge-support">{ev.stdout_summary}</p> : null}
        {ev.raw_output ? (
          <TechnicalDetails summary="Raw output (redacted)" defaultOpen={false}>
            <pre className="le-preview le-json" style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
              {ev.raw_output}
            </pre>
          </TechnicalDetails>
        ) : null}
        {meta}
      </article>
    )
  }

  if (t === 'command_result') {
    return (
      <article className="le-dh-block" data-kind="command_result">
        <h3 className="le-dh-block__title">Command result</h3>
        <p className="le-muted">
          Status: <strong>{ev.status || '—'}</strong>
          {ev.duration_ms != null ? ` · ${ev.duration_ms} ms` : null}
        </p>
        {ev.summary ? <p className="forge-support">{ev.summary}</p> : null}
        {ev.detail_raw ? (
          <TechnicalDetails summary="Raw detail (redacted)" defaultOpen={false}>
            <pre className="le-preview le-json" style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
              {ev.detail_raw}
            </pre>
          </TechnicalDetails>
        ) : null}
        {meta}
      </article>
    )
  }

  if (t === 'verification') {
    const layer =
      ev.layer === 'pipeline'
        ? 'Post-apply verification'
        : ev.layer === 'rules'
          ? 'Rule pass'
          : ev.layer === 'model'
            ? 'Model reviewer'
            : 'Verification'
    return (
      <article className="le-dh-block" data-kind="verification">
        <h3 className="le-dh-block__title">{layer}</h3>
        <p>
          <strong>{ev.ok ? 'Passed' : 'Needs attention'}</strong>
        </p>
        <p className="forge-support">{ev.detail}</p>
        {ev.layer === 'pipeline' && ev.pipeline ? (
          <TechnicalDetails summary="Pipeline detail" defaultOpen={false}>
            <pre className="le-preview le-json" style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(ev.pipeline, null, 2)}
            </pre>
          </TechnicalDetails>
        ) : null}
        {meta}
      </article>
    )
  }

  if (t === 'work_item') {
    const cid = ev.cluster_id ? String(ev.cluster_id) : ''
    const masterHref =
      projectSlug && cid
        ? `/projects/${encodeURIComponent(projectSlug)}/docs-health/master?cluster=${encodeURIComponent(cid)}`
        : null
    return (
      <article className="le-dh-block" data-kind="work_item">
        <h3 className="le-dh-block__title">Work item</h3>
        <p className="forge-support">{ev.title || 'Tracked item'}</p>
        <p className="le-muted">
          {cid ? (
            <>
              Cluster{' '}
              {masterHref ? (
                <Link to={masterHref} title="Open this cluster in Docs health Master">
                  <code>{cid}</code>
                </Link>
              ) : (
                <code>{cid}</code>
              )}
            </>
          ) : null}
          {ev.finding_count != null ? ` · ${ev.finding_count} findings` : null}
        </p>
        {masterHref ? (
          <p className="forge-support" style={{ fontSize: '0.85rem', marginTop: '0.35rem' }}>
            <Link to={masterHref}>Open cluster in Master</Link>
          </p>
        ) : null}
        {meta}
      </article>
    )
  }

  if (t === 'kpi_update') {
    return (
      <article className="le-dh-block" data-kind="kpi_update">
        <h3 className="le-dh-block__title">KPI update</h3>
        <p className="forge-support">
          Score: <strong>{ev.score ?? '—'}</strong> · findings: <strong>{ev.finding_count ?? '—'}</strong>
          {ev.score_delta != null ? (
            <>
              {' '}
              · delta <strong>{ev.score_delta > 0 ? '+' : ''}{ev.score_delta}</strong>
            </>
          ) : null}
        </p>
        {ev.run_id ? (
          <p className="le-muted">
            Run <code>{String(ev.run_id).slice(0, 12)}…</code>
          </p>
        ) : null}
        {meta}
      </article>
    )
  }

  if (t === 'token_stats') {
    const snap = ev.snapshot as Record<string, unknown> | undefined
    const pt = Number(snap?.prompt_tokens) || 0
    const ct = Number(snap?.completion_tokens) || 0
    const tt = Number(snap?.total_tokens) || (pt || ct ? pt + ct : 0)
    return (
      <article className="le-dh-block le-dh-block--token" data-kind="token_stats">
        <h3 className="le-dh-block__title">Runtime diagnostics</h3>
        <div className="le-dh-token-strip">
          {ev.last_model ? (
            <span className="le-dh-token-strip__model" title="Last model used for this step">
              {ev.last_model}
            </span>
          ) : null}
          <span className="le-dh-token-strip__nums">
            in {pt.toLocaleString()} · out {ct.toLocaleString()}
            {tt ? <> · Σ {tt.toLocaleString()}</> : null}
          </span>
        </div>
        <TechnicalDetails summary="Full usage snapshot (detail)" defaultOpen={false}>
          <pre className="le-preview le-json" style={{ fontSize: '0.82rem' }}>
            {JSON.stringify(snap, null, 2)}
          </pre>
        </TechnicalDetails>
        {meta}
      </article>
    )
  }

  if (t === 'user_reply') {
    return (
      <article className="le-dh-block" data-kind="user_reply">
        <h3 className="le-dh-block__title">Your reply</h3>
        <p className="forge-support" style={{ whiteSpace: 'pre-wrap' }}>
          {ev.body || '—'}
        </p>
        {ev.choice_id ? (
          <p className="le-muted">
            Choice: <code>{ev.choice_id}</code>
          </p>
        ) : null}
        {meta}
      </article>
    )
  }

  return (
    <article className="le-dh-block" data-kind={t}>
      <h3 className="le-dh-block__title">{docsHealthEventKindLabel(t)}</h3>
      <pre className="le-preview le-json">{JSON.stringify(ev, null, 2)}</pre>
      {meta}
    </article>
  )
}

export function DocsHealthSessionTimeline({
  events,
  projectSlug,
  sessionStatus,
  omitEventTypes,
}: {
  events: DocsHealthSessionEvent[]
  /** When set, cluster ids in timeline cards link to Master with this project. */
  projectSlug?: string
  /** Shown when there are no events yet (cold start / reload). */
  sessionStatus?: string
  /** Exclude event types from this feed (e.g. `token_stats` belongs in Diagnostics, not the execution story). */
  omitEventTypes?: readonly string[]
}) {
  const visible = useMemo(() => {
    if (!omitEventTypes?.length) return events
    const omit = new Set(omitEventTypes.map(String))
    return events.filter((e) => !omit.has(String(e.type || '')))
  }, [events, omitEventTypes])

  const questionRef = useRef<HTMLDivElement | null>(null)
  const wrapRef = useRef<HTMLDivElement | null>(null)
  const prevLen = useRef(0)
  const prevEventCount = useRef(0)

  useEffect(() => {
    const last = visible[visible.length - 1]
    const grew = visible.length > prevLen.current
    prevLen.current = visible.length
    if (grew && last?.type === 'question') {
      window.requestAnimationFrame(() => {
        questionRef.current?.focus()
      })
    }
  }, [visible])

  /**
   * Follow new timeline events inside the scrollable panel only.
   * Do **not** use ``scrollIntoView`` on inner nodes — it scrolls the page and fights user scroll (SSE updates).
   */
  useEffect(() => {
    if (visible.length === 0) {
      prevEventCount.current = 0
      return
    }
    const wrap = wrapRef.current
    const grew = visible.length > prevEventCount.current
    prevEventCount.current = visible.length
    if (!wrap || !grew) return
    window.requestAnimationFrame(() => {
      const threshold = 140
      const distFromBottom = wrap.scrollHeight - wrap.scrollTop - wrap.clientHeight
      const firstChunk = visible.length <= 3
      if (firstChunk || distFromBottom < threshold) {
        wrap.scrollTop = wrap.scrollHeight
      }
    })
  }, [visible])

  return (
    <div className="le-dh-timeline-wrap" ref={wrapRef}>
      <div className="le-dh-timeline" role="feed" aria-label="Documentation session timeline">
        {visible.length === 0 ? (
          <p className="forge-support le-dh-timeline__empty" role="status">
            {sessionStatus && String(sessionStatus).toLowerCase() === 'running'
              ? 'Waiting for the next events from this run…'
              : 'No events recorded yet. Start a step or refresh to load the history.'}
          </p>
        ) : null}
        {visible.map((ev, i) => {
          const isLastQuestion = i === visible.length - 1 && ev.type === 'question'
          return (
            <DhBlock
              key={`${i}-${ev.ts || ''}-${ev.type}`}
              ev={ev}
              focusRef={isLastQuestion ? questionRef : undefined}
              projectSlug={projectSlug}
            />
          )
        })}
      </div>
    </div>
  )
}
