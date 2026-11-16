import { useMemo } from 'react'
import type { DocsHealthSessionPayload } from '../../api/docsHealth'
import {
  DOCS_HEALTH_STAGE_DEFS,
  aggregateStepMetrics,
  fmtStageDuration,
  fmtStageTokens,
  resolveBlockedStageId,
  type StageGroup,
  type StageId,
} from '../../lib/docsHealthStageFlow'
import './docs-health-session.css'

function groupLabel(g: StageGroup): string {
  if (g === 'triage') return 'Understand context'
  if (g === 'draft') return 'Draft (choose one or more paths)'
  return 'Review & ship'
}

export function DocsHealthStageFlowchart({
  session,
  busyStep,
  onScrollToReply,
}: {
  session: Pick<DocsHealthSessionPayload, 'status' | 'step_metrics' | 'proposed_patch_kind'> | null | undefined
  busyStep?: string | null
  onScrollToReply?: () => void
}) {
  const agg = useMemo(() => aggregateStepMetrics(session?.step_metrics), [session?.step_metrics])
  const blocked = useMemo(
    () => (session ? resolveBlockedStageId(session) : null),
    [session?.status, session?.proposed_patch_kind, session?.step_metrics],
  )
  const byGroup: Record<StageGroup, (typeof DOCS_HEALTH_STAGE_DEFS)[number][]> = {
    triage: DOCS_HEALTH_STAGE_DEFS.filter((d) => d.group === 'triage'),
    draft: DOCS_HEALTH_STAGE_DEFS.filter((d) => d.group === 'draft'),
    ship: DOCS_HEALTH_STAGE_DEFS.filter((d) => d.group === 'ship'),
  }

  const stageState = (id: StageId): 'done' | 'blocked' | 'running' | 'pending' => {
    if (busyStep === id) return 'running'
    if (blocked === id) return 'blocked'
    const a = agg[id]
    if (a && a.runs > 0) return 'done'
    return 'pending'
  }

  const renderCard = (id: StageId) => {
    const def = DOCS_HEALTH_STAGE_DEFS.find((d) => d.id === id)!
    const a = agg[id]
    const state = stageState(id)
    const tok = a?.total_tokens ?? 0
    const wall = a?.elapsed_ms ?? 0
    const st = String(session?.status || '').toLowerCase()
    const gateLine =
      state === 'blocked'
        ? st === 'awaiting_approval'
          ? 'Waiting for your approval'
          : st === 'awaiting_input'
            ? 'Waiting for your reply'
            : 'Action needed'
        : null

    return (
      <div
        key={id}
        className={`le-dh-flow__card le-dh-flow__card--${state}`}
        data-stage={id}
        role="group"
        aria-label={`${def.label}: ${state}`}
      >
        <div className="le-dh-flow__card-title">{def.short}</div>
        <div className="le-dh-flow__metrics">
          <span title="Total tokens attributed to this step (sum of runs)">{fmtStageTokens(tok)} tok</span>
          <span className="le-dh-flow__dot" aria-hidden>
            ·
          </span>
          <span title="Wall time for this step handler (includes model + local work)">{fmtStageDuration(wall)}</span>
        </div>
        {a && a.runs > 1 ? <div className="le-dh-flow__runs">{a.runs} runs</div> : null}
        {gateLine ? (
          <div className="le-dh-flow__gate">
            <strong>{gateLine}</strong>
            {onScrollToReply ? (
              <button type="button" className="le-btn le-btn--small le-btn--primary" onClick={onScrollToReply}>
                Respond
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    )
  }

  const groups: StageGroup[] = ['triage', 'draft', 'ship']

  return (
    <section className="le-dh-flow" aria-label="Remediation pipeline">
      <p className="forge-support le-dh-flow__intro">
        Typical flow: understand the cluster → draft a markdown change (writer, diagram, or ADR) → review → apply →
        re-scan. Metrics show <strong>token deltas</strong> and <strong>wall time</strong> per step (multiple runs add
        up).
      </p>
      <div className="le-dh-flow__groups">
        {groups.map((g) => (
          <div key={g} className="le-dh-flow__group">
            <div className="le-dh-flow__group-label">{groupLabel(g)}</div>
            <div className="le-dh-flow__row">
              {byGroup[g].map((d, i) => (
                <div className="le-dh-flow__step" key={d.id}>
                  {i > 0 ? (
                    <span className="le-dh-flow__arrow" aria-hidden>
                      →
                    </span>
                  ) : null}
                  {renderCard(d.id)}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
