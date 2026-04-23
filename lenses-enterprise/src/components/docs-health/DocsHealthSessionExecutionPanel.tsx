import type { DocsHealthSessionPayload } from '../../api/docsHealth'
import { ForgeAgentLiveLog, type ForgeAgentLiveLogLine } from '../../forgesdlc-kitchensink'
import { buildDocsHealthLiveLogLines } from '../../lib/docsHealthSessionLiveLog'
import { formatSessionInstant } from '../../lib/docsHealthSessionFormat'
import { DOCS_HEALTH_PIPELINE_STEP_LABELS as DOCS_HEALTH_STEP_LABELS } from '../../lib/docsHealthStepLabels'
import { useMemo } from 'react'
import { DocsHealthSessionTimeline } from './DocsHealthSessionTimeline'

export type DocsHealthSessionExecutionPanelProps = {
  session: DocsHealthSessionPayload | null
  projectSlug: string
}

/**
 * Execution: stage invocations and chronological events (token snapshots are under Diagnostics).
 */
export function DocsHealthSessionExecutionPanel({ session, projectSlug }: DocsHealthSessionExecutionPanelProps) {
  const logLines: ForgeAgentLiveLogLine[] = useMemo(
    () =>
      buildDocsHealthLiveLogLines(session?.events, 200).map((l) => ({
        id: l.id,
        ts: l.ts,
        text: l.text,
        tone: l.tone,
      })),
    [session?.events],
  )

  const rows = session?.step_metrics
  const sorted =
    rows && rows.length > 0
      ? [...rows].sort((a, b) => {
          const ta = a.ts ? Date.parse(String(a.ts)) : 0
          const tb = b.ts ? Date.parse(String(b.ts)) : 0
          if (Number.isNaN(ta) && Number.isNaN(tb)) return 0
          return ta - tb
        })
      : []

  return (
    <div className="le-dh-exec">
      <section className="le-dh-exec__stream" aria-labelledby="le-dh-exec-stream-h">
        <h3 id="le-dh-exec-stream-h" className="le-dh-wf-panel__h4">
          Live activity stream
        </h3>
        <p className="forge-support le-dh-exec__timeline-lead">
          Chronological tool and model events (Cursor-style). The structured timeline follows below.
        </p>
        <ForgeAgentLiveLog lines={logLines} maxHeight="min(38vh, 24rem)" />
      </section>

      {sorted.length > 0 ? (
        <section className="le-dh-exec__stages" aria-labelledby="le-dh-exec-stages-h">
          <h3 id="le-dh-exec-stages-h" className="le-dh-wf-panel__h4">
            Pipeline steps
          </h3>
          <p className="forge-support le-dh-exec__stages-lead">
            Recorded invocations in order. Gates indicate the run waited for approval or your reply.
          </p>
          <ol className="le-dh-exec-stages__list">
            {sorted.map((r, i) => {
              const sid = String(r.step || '').trim()
              const label = sid ? DOCS_HEALTH_STEP_LABELS[sid] || sid : 'Step'
              const when = r.ts ? formatSessionInstant(r.ts) : null
              return (
                <li key={`${sid}-${i}-${r.ts || ''}`} className="le-dh-exec-stages__item">
                  <div className="le-dh-exec-stages__title">
                    <strong>{label}</strong>
                    {r.gate ? (
                      <span className="le-dh-exec-stages__gate" title="Human gate">
                        {' '}
                        · {r.gate.replace(/_/g, ' ')}
                      </span>
                    ) : null}
                  </div>
                  <div className="le-dh-exec-stages__meta forge-support">
                    {when ? (
                      <time dateTime={when.dateTime} title={when.utcTitle}>
                        {when.text}
                      </time>
                    ) : null}
                    {r.total_tokens != null ? <span>{r.ts ? ' · ' : ''}{Number(r.total_tokens).toLocaleString()} tokens</span> : null}
                    {r.elapsed_ms != null ? (
                      <span>
                        {(r.ts || r.total_tokens != null ? ' · ' : '') + `${Number(r.elapsed_ms).toLocaleString()} ms`}
                      </span>
                    ) : null}
                  </div>
                </li>
              )
            })}
          </ol>
        </section>
      ) : null}

      <section className="le-dh-exec__timeline" aria-labelledby="le-dh-exec-timeline-h">
        <h3 id="le-dh-exec-timeline-h" className="le-dh-wf-panel__h4">
          Event timeline
        </h3>
        <p className="forge-support le-dh-exec__timeline-lead">
          Questions, replies, diffs, commands, verification, and score updates. Per-step token counts and raw usage are under{' '}
          <strong>Diagnostics</strong>.
        </p>
        <DocsHealthSessionTimeline
          events={session?.events || []}
          projectSlug={projectSlug}
          sessionStatus={session?.status}
          omitEventTypes={['token_stats']}
        />
      </section>
    </div>
  )
}
