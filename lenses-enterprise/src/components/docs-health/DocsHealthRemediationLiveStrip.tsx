import { useMemo } from 'react'
import type { DocsHealthSessionPayload } from '../../api/docsHealth'
import {
  ForgeAgentLiveLog,
  ForgeLivePulse,
  ForgeRunProgressTrack,
  type ForgeWorkflowStage,
} from '../../forgesdlc-kitchensink'
import { useElapsedSecondsSince, formatElapsedWallClock } from '../../hooks/useElapsedSecondsSince'
import { buildDocsHealthLiveLogLines } from '../../lib/docsHealthSessionLiveLog'
import {
  estimateRemediationEtaSeconds,
  formatEtaHint,
  workflowCompletionPercent,
  workflowStagesToMilestones,
} from '../../lib/docsHealthRemediationProgress'
import { fleetActivityPercent, formatFleetSandboxHeadline, type FleetSandboxSlice } from '../../lib/docsHealthFleetLive'
import { DOCS_HEALTH_PIPELINE_STEP_LABELS } from '../../lib/docsHealthStepLabels'
import { WORKFLOW_STAGE_LABELS, type WorkflowStageId } from '../../lib/docsHealthStageFlow'

const LIVE = new Set(['running', 'awaiting_approval', 'awaiting_input', 'paused'])

type Props = {
  session: DocsHealthSessionPayload | null
  wfStages: ForgeWorkflowStage[]
  activeWorkflow: WorkflowStageId
  /** Stage label for metrics row — follows agent / gate attention when present. */
  stageFocusId: WorkflowStageId
  streamMode: 'sse' | 'poll' | 'idle'
  busy: string | null
  taskletSandbox?: Record<string, unknown> | null
}

export function DocsHealthRemediationLiveStrip({
  session,
  wfStages,
  activeWorkflow,
  stageFocusId,
  streamMode,
  busy,
  taskletSandbox,
}: Props) {
  const st = String(session?.status || '').toLowerCase()
  const isRunActive = LIVE.has(st) || Boolean(busy)
  const pulseActive = isRunActive

  const elapsed = useElapsedSecondsSince(session?.started_at)
  const percent = useMemo(() => workflowCompletionPercent(wfStages), [wfStages])
  const milestones = useMemo(() => workflowStagesToMilestones(wfStages), [wfStages])
  const sb = (taskletSandbox || null) as FleetSandboxSlice | null
  const fleetHead = formatFleetSandboxHeadline(sb)
  const fleetAct = fleetActivityPercent(sb)

  const activityPeekLines = useMemo(
    () =>
      buildDocsHealthLiveLogLines(session?.events, 48).map((l) => ({
        id: l.id,
        ts: l.ts,
        text: l.text,
        tone: l.tone,
      })),
    [session?.events],
  )

  const etaSec = useMemo(
    () => (isRunActive ? estimateRemediationEtaSeconds(wfStages, elapsed) : null),
    [isRunActive, wfStages, elapsed],
  )

  const streamLabel =
    streamMode === 'sse' ? 'Live · SSE' : streamMode === 'poll' ? 'Live · polling' : 'Idle'

  const busyId = String(busy || '').trim()
  const busyLabel =
    busyId && (DOCS_HEALTH_PIPELINE_STEP_LABELS[busyId] || busyId.replace(/_/g, ' '))

  const noStepsYet = !(session?.step_metrics && session.step_metrics.length > 0)
  const idleLiveRun = isRunActive && !busy && noStepsYet

  const tokens = session?.header_stats?.total_tokens
  const tokLine =
    typeof tokens === 'number' && tokens > 0 ? `${tokens.toLocaleString()} tokens` : null

  const stageTitle = WORKFLOW_STAGE_LABELS[stageFocusId]
  const panelDiffers = stageFocusId !== activeWorkflow

  return (
    <section className="le-panel le-dh-live-strip" aria-label="Live run monitor">
      <h2 className="le-panel__title le-dh-live-strip__title">Live run</h2>
      <p className="forge-support le-dh-live-strip__lead">
        <ForgeLivePulse active={pulseActive} label={streamLabel} />{' '}
        <span className="le-muted le-dh-live-strip__lead-muted">
          {busyLabel ? (
            <>
              <strong>Step in flight:</strong> {busyLabel}.{' '}
            </>
          ) : null}
          {idleLiveRun
            ? 'No pipeline step yet — the Summary tile and first progress tick are highlighted. Start · Cluster brief or Start · Gather context above (or Advanced pipeline steps).'
            : isRunActive
              ? 'Activity streams into Run activity · Execution. The highlighted workflow tile follows the live step or gate.'
              : 'Session idle or finished — open Run activity for the full stream.'}
        </span>
      </p>

      <div className="le-dh-live-strip__metrics forge-support" aria-live="polite">
        <span>
          <strong>Elapsed</strong> {formatElapsedWallClock(elapsed)}
        </span>
        <span>
          <strong>Progress</strong> {percent}%
        </span>
        {tokLine ? (
          <span>
            <strong>{tokLine}</strong>
          </span>
        ) : null}
        {isRunActive ? (
          <span>
            <strong>ETA</strong> {formatEtaHint(etaSec)}
          </span>
        ) : null}
        {busy && fleetHead ? (
          <span className="le-dh-live-strip__fleet-metric" title={fleetHead}>
            <strong>Fleet</strong> {String(sb?.fleet_job_status || sb?.phase || '—')}
            {typeof sb?.fleet_host_cpu_pct === 'number' ? ` · host CPU ${sb.fleet_host_cpu_pct}%` : ''}
            {typeof sb?.fleet_host_mem_pct === 'number' ? ` · host RAM ${sb.fleet_host_mem_pct}%` : ''}
            {sb?.container_id ? (
              <>
                {' '}
                · ctn <span className="le-mono">{String(sb.container_id).slice(0, 14)}</span>
                {String(sb.container_id).length > 14 ? '…' : ''}
              </>
            ) : null}
          </span>
        ) : null}
        <span>
          <strong>{panelDiffers ? 'Agent stage' : 'Stage'}</strong> {stageTitle}
          {panelDiffers ? (
            <span className="le-muted" title="You can keep another workflow tab open for reference.">
              {' '}
              (viewing {WORKFLOW_STAGE_LABELS[activeWorkflow]})
            </span>
          ) : null}
        </span>
      </div>

      <ForgeRunProgressTrack percent={percent} milestones={milestones} aria-label="Remediation pipeline progress" />
      {busy && fleetAct != null ? (
        <div className="le-dh-live-strip__fleet-progress" aria-label="Fleet worker activity">
          <p className="forge-support le-dh-live-strip__fleet-progress-label">
            <strong>Fleet worker activity</strong> (Docker step on the Fleet host — separate from the workflow stage bar
            above, which stays near the start until LLM stages advance).
          </p>
          <ForgeRunProgressTrack
            percent={fleetAct}
            milestones={[]}
            aria-label="Fleet worker activity estimate"
          />
        </div>
      ) : null}

      <div className="le-dh-live-strip__activity">
        <div className="le-dh-live-strip__activity-head">
          <h3 className="le-dh-live-strip__activity-title">Recent agent activity</h3>
          <button
            type="button"
            className="le-btn le-btn--small le-btn--ghost"
            onClick={() => document.getElementById('dh-activity-log')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
          >
            Open full log
          </button>
        </div>
        <p className="forge-support le-dh-live-strip__activity-scope">
          Lines below are for <strong>this remediation run</strong> only. Copilot or other Studio chats stay in the
          Copilot rail and are not merged here.
        </p>
        <ForgeAgentLiveLog
          lines={activityPeekLines}
          maxHeight="min(28vh, 14rem)"
          emptyHint="No model or tool events yet — after you start a step, streaming lines appear here and in Run activity."
        />
      </div>
    </section>
  )
}
