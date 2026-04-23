import type { ReactNode } from 'react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type {
  DocsHealthCluster,
  DocsHealthFinding,
  DocsHealthProjectPayload,
  DocsHealthSessionPayload,
} from '../../api/docsHealth'
import { ForgeDecisionActionBar, ForgeStatusBanner } from '../../forgesdlc-kitchensink'
import { formatSessionInstant } from '../../lib/docsHealthSessionFormat'
import { getRemediationBannerMessage } from '../../lib/docsHealthSessionViewState'
import {
  buildDocsHealthWorkflowStages,
  deriveDefaultWorkflowTab,
  proposedKindToArtifactTab,
  resolveWorkflowStageAttentionStageId,
  WORKFLOW_STAGE_ORDER,
  type WorkflowStageId,
} from '../../lib/docsHealthStageFlow'
import { deriveShortRemediationRunTitle } from '../../lib/docsHealthRemediationRunTitle'
import { DocsHealthStageFlowchart } from './DocsHealthStageFlowchart'
import { DocsHealthSessionExecutionPanel } from './DocsHealthSessionExecutionPanel'
import { DocsDraftArtifactsTabs, type DraftArtifactTabId } from './DocsDraftArtifactsTabs'
import { DocsHealthSessionWorkflowPanel } from './DocsHealthSessionWorkflowPanel'
import { DocsHealthRemediationScopePanel } from './DocsHealthRemediationScope'
import { DocsHealthSessionSummaryBrief } from './DocsHealthSessionSummaryBrief'
import { DocsRunContextRail } from './DocsRunContextRail'
import { DocsRuntimeDiagnosticsTab } from './DocsRuntimeDiagnosticsTab'
import { DocsHealthVerificationTab } from './DocsHealthVerificationTab'
import {
  getRemediationConsoleContext,
  RemediationAdvancedPipelineSteps,
  RemediationPrimaryActions,
} from './DocsHealthSessionDecisionConsole'
import { DocsHealthRemediationLiveStrip } from './DocsHealthRemediationLiveStrip'
import { DocsHealthRunningBlade } from './DocsHealthRunningBlade'
import { DocsHealthRunSummaryCompact } from './DocsHealthRunSummaryCompact'
import { getClusterAffectedPaths } from './docsHealthAffectedPaths'
import { TechnicalDetails } from '../page'
import './docs-health-session-layout.css'
import './docs-health-session.css'

const LIVE = new Set(['running', 'awaiting_approval', 'awaiting_input', 'paused'])

function SessionInstant({ iso }: { iso?: string }) {
  if (iso == null || String(iso).trim() === '') {
    return <>Not recorded</>
  }
  const { text, utcTitle, dateTime } = formatSessionInstant(iso)
  if (!dateTime) {
    return <span title={utcTitle}>{text}</span>
  }
  return (
    <time dateTime={dateTime} title={utcTitle}>
      {text}
    </time>
  )
}

function nextActionsHint(st: string, showReply: boolean, busy: string | null): string {
  if (showReply) return 'Respond below so the run can continue.'
  const s = st.toLowerCase()
  if (s === 'completed') return 'Review Docs health results and close any remaining follow-ups.'
  if (s === 'cancelled') return 'Resume from the last checkpoint when ready, or return to the project.'
  if (busy) return 'A step is in progress. Watch Run activity for updates.'
  if (s === 'running' || s === 'paused') return 'Use pinned actions when you are ready for the next stage, or wait for the current work to finish.'
  return 'Use pinned actions and the workflow stages to move from summary through re-scan. Advanced steps stay available below.'
}

export type DocsHealthSessionPageProps = {
  encProject: string
  projectSlug: string
  sessionId: string
  session: DocsHealthSessionPayload | null
  projectSnapshot: DocsHealthProjectPayload | null
  busy: string | null
  cancelBusy: boolean
  cancelErr: string | null
  replyText: string
  replyBusy: boolean
  resumeBusy: boolean
  streamMode: 'sse' | 'poll' | 'idle'
  runStateLine: string | null
  /** Step request failed (network, 409, etc.) — dismissible banner above the run hero. */
  stepError?: string | null
  onDismissStepError?: () => void
  onCancelSession?: () => void
  onReplyText: (v: string) => void
  onSendReply: (opts: { reply_text?: string; choice_id?: string; confirm?: boolean }) => void | Promise<void>
  onResume: () => void
  onStep: (step: string) => void
}

/**
 * Documentation remediation run console — run-first layout; logs and diagnostics below the fold.
 */
export function DocsHealthSessionPage({
  encProject,
  projectSlug,
  sessionId,
  session,
  projectSnapshot,
  busy,
  cancelBusy,
  cancelErr,
  replyText,
  replyBusy,
  resumeBusy,
  streamMode,
  runStateLine,
  stepError,
  onDismissStepError,
  onCancelSession,
  onReplyText,
  onSendReply,
  onResume,
  onStep,
}: DocsHealthSessionPageProps) {
  const st = String(session?.status || '').toLowerCase()
  const showStop = LIVE.has(st)
  const showReply = st === 'awaiting_input' || st === 'awaiting_approval'
  const lastQuestion = [...(session?.events || [])].reverse().find((e) => e.type === 'question')

  const wfStages = useMemo(() => buildDocsHealthWorkflowStages(session, busy), [session, busy])
  const workflowAttentionId = useMemo(() => resolveWorkflowStageAttentionStageId(wfStages), [wfStages])
  const defaultWorkflowTab = useMemo(() => {
    if (String(session?.status).toLowerCase() === 'awaiting_approval') return 'draft' as WorkflowStageId
    return deriveDefaultWorkflowTab(wfStages)
  }, [session?.status, wfStages])
  const [workflowTabPick, setWorkflowTabPick] = useState<WorkflowStageId | null>(null)
  const [artifactTab, setArtifactTab] = useState<DraftArtifactTabId>(() => proposedKindToArtifactTab(session?.proposed_patch_kind))
  const [sessionConsoleTab, setSessionConsoleTab] = useState<'execution' | 'diagnostics'>('execution')

  useEffect(() => {
    setWorkflowTabPick(null)
  }, [session?.id])

  useEffect(() => {
    setArtifactTab(proposedKindToArtifactTab(session?.proposed_patch_kind))
  }, [session?.proposed_patch_kind, session?.id])

  useEffect(() => {
    setSessionConsoleTab('execution')
  }, [session?.id])

  const activeWorkflow = workflowTabPick ?? defaultWorkflowTab

  const stageBarFocusId = useMemo((): WorkflowStageId => {
    if (workflowAttentionId && (WORKFLOW_STAGE_ORDER as readonly string[]).includes(workflowAttentionId)) {
      return workflowAttentionId as WorkflowStageId
    }
    return activeWorkflow
  }, [workflowAttentionId, activeWorkflow])

  const selectWorkflow = useCallback((id: WorkflowStageId) => {
    setWorkflowTabPick(id)
    requestAnimationFrame(() => {
      document.getElementById(`dh-wf-panel-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    })
  }, [])

  const goToDraftArtifacts = useCallback(() => {
    setWorkflowTabPick('draft')
    setArtifactTab(proposedKindToArtifactTab(session?.proposed_patch_kind))
    requestAnimationFrame(() => {
      document.getElementById('docs-health-drafts-anchor')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }, [session?.proposed_patch_kind])

  const latest = projectSnapshot?.latest_run as
    | { clusters?: DocsHealthCluster[]; findings?: DocsHealthFinding[] }
    | null
    | undefined
  const clusterMeta = latest?.clusters?.find(
    (c) => c.id === session?.cluster_id || c.id === session?.cluster?.id,
  )
  const firstFindingId = clusterMeta?.finding_ids?.[0]
  const findingRow =
    latest?.findings?.find((f) => f.id === firstFindingId) ?? latest?.findings?.[0]

  const workflowPanels = useMemo((): Record<WorkflowStageId, ReactNode> => {
    return {
      analyze: (
        <DocsHealthSessionSummaryBrief
          session={session}
          projectSnapshot={projectSnapshot}
          cluster={clusterMeta ?? session?.cluster}
          finding={findingRow ?? null}
          projectSlug={projectSlug}
          encProject={encProject}
        />
      ),
      gather: (
        <>
          <h3 className="le-dh-wf-panel__h">Gather context</h3>
          <p className="forge-support">Scope and evidence for this run, including enrichment findings.</p>
          <DocsHealthRemediationScopePanel scope={session?.remediation_scope} />
          <h4 className="le-dh-wf-panel__h4">Step cost and duration</h4>
          <p className="forge-support le-dh-wf-panel__micro">
            Token and wall-clock totals per pipeline step. Use this to compare enrichment and draft stages.
          </p>
          <DocsHealthStageFlowchart
            session={session ?? undefined}
            busyStep={busy}
            onScrollToReply={
              showReply
                ? () =>
                    document.getElementById('docs-health-reply-panel')?.scrollIntoView({
                      behavior: 'smooth',
                      block: 'start',
                    })
                : undefined
            }
          />
        </>
      ),
      draft: (
        <DocsDraftArtifactsTabs
          session={session}
          cluster={clusterMeta}
          finding={findingRow ?? null}
          awaitingApproval={st === 'awaiting_approval'}
          activeArtifactTab={artifactTab}
          onArtifactTabChange={setArtifactTab}
        />
      ),
      review: (
        <>
          <h3 className="le-dh-wf-panel__h">Review and policy checks</h3>
          <p className="forge-support">
            Validates proposed edits before apply. Details stream into Run activity; when the run waits here, use the reply
            panel when it appears.
          </p>
          <p className="forge-support">
            <button type="button" className="le-btn le-btn--small le-btn--ghost" onClick={() => selectWorkflow('draft')}>
              Back to Changes
            </button>{' '}
            <button
              type="button"
              className="le-btn le-btn--small le-btn--ghost"
              onClick={() =>
                document.getElementById('dh-activity-log')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }
            >
              Open run activity
            </button>
          </p>
        </>
      ),
      apply: (
        <>
          <h3 className="le-dh-wf-panel__h">Approve and apply to branch</h3>
          <p className="forge-support">
            Writes the approved proposal to the repository, usually on a dedicated branch. Use the pinned actions when the
            run allows apply.
          </p>
          {session?.suggested_git_branch ? (
            <>
              <p className="forge-support">
                Recommended branch: <code>{session.suggested_git_branch}</code>
              </p>
              {session.proposed_patch_kind ? (
                <p className="le-muted" style={{ fontSize: '0.9rem' }}>
                  Proposal type: <strong>{session.proposed_patch_kind}</strong>. See Run activity for the preview.
                </p>
              ) : null}
            </>
          ) : (
            <p className="le-muted">When a branch is recommended, it appears here for branch-first apply.</p>
          )}
        </>
      ),
      verify: (
        <>
          <h3 className="le-dh-wf-panel__h">Re-scan and verify</h3>
          <p className="forge-support">
            Post-apply scan results: scores, finding changes, and closure status.
          </p>
          <DocsHealthVerificationTab project={projectSnapshot} session={session} busy={busy} onStep={onStep} />
        </>
      ),
    }
  }, [artifactTab, busy, clusterMeta, findingRow, onStep, projectSnapshot, selectWorkflow, session, showReply, st])

  const severity = findingRow?.severity || clusterMeta?.primary_severity || ''
  const category = findingRow?.category || clusterMeta?.primary_category || ''

  const pathInfo = useMemo(
    () =>
      getClusterAffectedPaths(
        projectSnapshot,
        session?.cluster_id ?? session?.cluster?.id,
        session?.cluster?.label,
      ),
    [projectSnapshot, session?.cluster_id, session?.cluster?.id, session?.cluster?.label],
  )

  const affectedPathCount = useMemo(() => {
    const scopeN = session?.remediation_scope?.distinct_path_count
    const hs = session?.header_stats
    if (typeof scopeN === 'number') return scopeN
    if (pathInfo.count > 0) return pathInfo.count
    if (typeof hs?.files_changed === 'number') return hs.files_changed
    return 0
  }, [pathInfo.count, session?.remediation_scope?.distinct_path_count, session?.header_stats?.files_changed])

  const expectedGainPts = clusterMeta?.expected_score_gain_if_cleared
  const shortRunTitle = useMemo(
    () =>
      deriveShortRemediationRunTitle({
        displayName: session?.display_name,
        clusterLabel: session?.cluster?.label,
        category,
      }),
    [session?.display_name, session?.cluster?.label, category],
  )
  const remediationCtx = getRemediationConsoleContext(session, busy)
  const banner = getRemediationBannerMessage(remediationCtx.view, session, {
    hasReviewable: remediationCtx.hasReviewable,
    cancelledNoApplyChanges: remediationCtx.cancelledNoApply,
  })

  const hint = nextActionsHint(st, showReply, busy)

  return (
    <>
      <div className="le-dh-session-layout">
        <div className="le-dh-session-layout__main">
          <section className="le-panel le-dh-run-hero" aria-labelledby="le-dh-run-summary-title">
            {banner ? (
              <ForgeStatusBanner
                variant={banner.variant}
                title={banner.title}
                description={banner.description}
                role="status"
              />
            ) : null}
            {stepError ? (
              <ForgeStatusBanner
                variant="failed"
                title="Step could not complete"
                description={stepError}
                role="alert"
              >
                {onDismissStepError ? (
                  <button type="button" className="le-btn le-btn--small" onClick={onDismissStepError}>
                    Dismiss
                  </button>
                ) : null}
              </ForgeStatusBanner>
            ) : null}
            <DocsHealthRunningBlade
              status={session?.status}
              busyStep={busy}
              startedAt={session?.started_at}
              header={session?.header_stats}
              streamMode={streamMode}
              runStateLine={runStateLine}
              taskletSandbox={session?.tasklet_run?.sandbox as Record<string, unknown> | null}
            />
            <DocsHealthRunSummaryCompact
              session={session}
              sessionId={sessionId}
              runTitle={shortRunTitle}
              severity={severity}
              category={category}
              expectedGainPts={expectedGainPts}
              affectedPathCount={affectedPathCount}
              streamMode={streamMode}
              affectedPaths={pathInfo.paths}
              cancelErr={cancelErr}
              advancedPipeline={
                <RemediationAdvancedPipelineSteps
                  allowNewSteps={remediationCtx.allowNewSteps}
                  showApply={remediationCtx.showApplyInAdvanced}
                  blocked={remediationCtx.blocked}
                  busy={busy}
                  onStep={onStep}
                />
              }
            >
              <div id="dh-primary-run-actions" className="le-dh-primary-actions-anchor">
                <ForgeDecisionActionBar sticky aria-label="Primary run actions">
                  <RemediationPrimaryActions
                    view={remediationCtx.view}
                    encProject={encProject}
                    session={session}
                    blocked={remediationCtx.blocked}
                    busy={busy}
                    cancelBusy={cancelBusy}
                    replyText={replyText}
                    replyBusy={replyBusy}
                    resumeBusy={resumeBusy}
                    hasReviewable={remediationCtx.hasReviewable}
                    branchHint={remediationCtx.branchHint}
                    appliedAwait={remediationCtx.appliedAwait}
                    allowNewSteps={remediationCtx.allowNewSteps}
                    onCancelSession={showStop ? onCancelSession : undefined}
                    onSendReply={onSendReply}
                    onResume={onResume}
                    onStep={onStep}
                    onNavigateToDraft={goToDraftArtifacts}
                  />
                </ForgeDecisionActionBar>
              </div>
            </DocsHealthRunSummaryCompact>
          </section>

          <DocsHealthRemediationLiveStrip
            session={session}
            wfStages={wfStages}
            activeWorkflow={activeWorkflow}
            stageFocusId={stageBarFocusId}
            streamMode={streamMode}
            busy={busy}
            taskletSandbox={session?.tasklet_run?.sandbox as Record<string, unknown> | null}
          />

          {showReply ? (
            <div id="docs-health-reply-panel" className="le-dh-reply-panel le-panel" aria-label="Reply to this run">
              <h2 className="le-panel__title">Your response</h2>
              <p className="forge-support">
                Replies are recorded on Run activity. Use a suggested choice when offered, or add detail on paths,
                boundaries, or diagram versus ticket preference.
              </p>
              {lastQuestion?.choices?.length ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.65rem' }}>
                  {lastQuestion.choices.map((c) => (
                    <button
                      key={c.id || c.label}
                      type="button"
                      className="le-btn le-btn--small"
                      disabled={replyBusy}
                      onClick={() => void onSendReply({ choice_id: c.id, reply_text: replyText.trim() || '' })}
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
              ) : null}
              {st === 'awaiting_approval' ? (
                <p className="forge-support" style={{ marginBottom: '0.65rem' }}>
                  Open the <strong>Changes</strong> stage (draft artifacts) for the proposal, then use the{' '}
                  <strong>pinned approval actions</strong> at the bottom of the screen. Optional notes go in the message
                  field.
                </p>
              ) : null}
              <label className="forge-support" htmlFor="dh-session-reply">
                Message
              </label>
              <textarea
                id="dh-session-reply"
                className="le-input"
                rows={3}
                value={replyText}
                onChange={(e) => onReplyText(e.target.value)}
                style={{ width: '100%', marginTop: '0.35rem' }}
              />
              <div style={{ marginTop: '0.5rem' }}>
                <button
                  type="button"
                  className="le-btn le-btn--primary"
                  disabled={replyBusy || !replyText.trim()}
                  onClick={() => void onSendReply({ reply_text: replyText })}
                >
                  {replyBusy ? 'Sending…' : 'Send reply'}
                </button>
              </div>
            </div>
          ) : null}

          <DocsHealthSessionWorkflowPanel
            wfStages={wfStages}
            activeWorkflow={activeWorkflow}
            stageBarCurrentId={stageBarFocusId}
            onSelectWorkflow={selectWorkflow}
            lead={hint}
            runStateLine={runStateLine}
            panels={workflowPanels}
          />

          <section className="le-panel" id="dh-activity-log" aria-label="Run activity">
            <h2 className="le-panel__title">Run activity</h2>
            <div className="le-dh-console-tabs" role="tablist" aria-label="Execution and diagnostics">
              <button
                type="button"
                role="tab"
                id="dh-console-tab-exec"
                className={`le-dh-console-tabs__btn${sessionConsoleTab === 'execution' ? ' le-dh-console-tabs__btn--active' : ''}`}
                aria-selected={sessionConsoleTab === 'execution'}
                aria-controls="dh-console-panel"
                onClick={() => setSessionConsoleTab('execution')}
              >
                Execution
              </button>
              <button
                type="button"
                role="tab"
                id="dh-console-tab-diag"
                className={`le-dh-console-tabs__btn${sessionConsoleTab === 'diagnostics' ? ' le-dh-console-tabs__btn--active' : ''}`}
                aria-selected={sessionConsoleTab === 'diagnostics'}
                aria-controls="dh-console-panel"
                onClick={() => setSessionConsoleTab('diagnostics')}
              >
                Diagnostics
              </button>
            </div>
            <div
              id="dh-console-panel"
              role="tabpanel"
              aria-labelledby={sessionConsoleTab === 'execution' ? 'dh-console-tab-exec' : 'dh-console-tab-diag'}
            >
              {sessionConsoleTab === 'execution' ? (
                <>
                  <p className="forge-support le-dh-console-tabs__lead">
                    What happened, in order: pipeline steps, questions, replies, diffs, commands, and verification. Per-step
                    token rows and raw usage are under Diagnostics.
                  </p>
                  <DocsHealthSessionExecutionPanel session={session} projectSlug={projectSlug} />
                </>
              ) : (
                <>
                  <p className="forge-support le-dh-console-tabs__lead">
                    Models, tokens, routing, policy, per-step token rows, and raw ledgers. Summary first; structured detail
                    on demand.
                  </p>
                  <DocsRuntimeDiagnosticsTab session={session} streamMode={streamMode} />
                </>
              )}
            </div>
          </section>

          {session && st === 'cancelled' ? (
            <section className="le-panel" aria-label="Resume run">
              <h2 className="le-panel__title">After cancel</h2>
              <p className="forge-support" role="status">
                This run was stopped. Use <strong>Resume run</strong> or <strong>Start new run</strong> in the action bar
                above when you are ready. Resume continues from persisted checkpoints when policy allows.
              </p>
              {session.cancelled_at ? (
                <p className="le-muted" style={{ fontSize: '0.9rem' }}>
                  Stopped at <SessionInstant iso={session.cancelled_at} />.
                </p>
              ) : null}
            </section>
          ) : null}

          {session && st === 'completed' ? (
            <section className="le-panel" aria-label="Run finished">
              <h2 className="le-panel__title">Results detail</h2>
              <p className="forge-support" role="status">
                Post-apply checks:{' '}
                <strong>
                  {(() => {
                    const ok = session.completion_summary?.verification_pipeline_ok
                    if (ok === true) return 'Passed'
                    if (ok === false) return 'Issues reported'
                    return 'Not summarized on this run'
                  })()}
                </strong>
                . Score delta (vs session start):{' '}
                <strong>
                  {(() => {
                    const em = session.efficiency_metrics as { score_delta?: number } | undefined
                    const d = em?.score_delta
                    return d == null ? 'Not recorded' : `${d > 0 ? '+' : ''}${d}`
                  })()}
                </strong>
                .
              </p>
              {session.closure_status?.notes ? <p className="le-muted">{session.closure_status.notes}</p> : null}
              {session.verification_run_id ? (
                <p className="le-muted" style={{ fontSize: '0.9rem' }}>
                  Verification run id: <code>{String(session.verification_run_id).slice(0, 14)}…</code>
                </p>
              ) : null}
              <p className="forge-support">
                <Link className="le-btn le-btn--small le-btn--primary" to={`/projects/${encProject}/docs-health`}>
                  Open project Docs health
                </Link>{' '}
                for the updated score, closure status, and waived findings.
              </p>
              {session.efficiency_metrics && Object.keys(session.efficiency_metrics).length > 0 ? (
                <TechnicalDetails summary="Efficiency metrics (detail)" defaultOpen={false}>
                  <pre className="le-preview le-json" style={{ fontSize: '0.85rem' }}>
                    {JSON.stringify(session.efficiency_metrics, null, 2)}
                  </pre>
                </TechnicalDetails>
              ) : null}
            </section>
          ) : null}

        </div>

        <DocsRunContextRail
          projectSlug={projectSlug}
          encProject={encProject}
          session={session}
          projectSnapshot={projectSnapshot}
          streamMode={streamMode}
        />
      </div>
    </>
  )
}
