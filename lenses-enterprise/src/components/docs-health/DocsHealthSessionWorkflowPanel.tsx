import type { ReactNode } from 'react'
import { ForgeWorkflowStageBar, type ForgeWorkflowStage } from '../../forgesdlc-kitchensink'
import { WORKFLOW_STAGE_ORDER, type WorkflowStageId } from '../../lib/docsHealthStageFlow'
import './docs-health-session-layout.css'

export type DocsHealthSessionWorkflowPanelProps = {
  wfStages: ForgeWorkflowStage[]
  activeWorkflow: WorkflowStageId
  /** Stage ring on the strip (agent / gate attention); defaults to the selected tab. */
  stageBarCurrentId?: WorkflowStageId
  onSelectWorkflow: (id: WorkflowStageId) => void
  /** Short lead under the title (e.g. next action hint). */
  lead?: string | null
  runStateLine?: string | null
  panels: Record<WorkflowStageId, ReactNode>
}

/**
 * Executive workflow strip + one visible stage panel (process stages only; artifacts live under Draft changes).
 */
export function DocsHealthSessionWorkflowPanel({
  wfStages,
  activeWorkflow,
  stageBarCurrentId,
  onSelectWorkflow,
  lead,
  runStateLine,
  panels,
}: DocsHealthSessionWorkflowPanelProps) {
  const barCurrent = stageBarCurrentId ?? activeWorkflow
  return (
    <section className="le-panel le-dh-workflow-console" aria-labelledby="dh-wf-title">
      <h2 id="dh-wf-title" className="le-panel__title">
        Documentation remediation workflow
      </h2>
      {lead ? (
        <p className="forge-support le-dh-console-lead" style={{ marginTop: 0 }}>
          {lead}
        </p>
      ) : null}

      <div className="le-dh-wf-stagebar-wrap">
        <ForgeWorkflowStageBar
          variant="executive"
          stages={wfStages}
          currentStageId={barCurrent}
          onStageClick={(id) => {
            if (isWorkflowStageId(id)) onSelectWorkflow(id)
          }}
          aria-label="Workflow stages: select a stage to view details"
        />
      </div>

      {WORKFLOW_STAGE_ORDER.map((id) => {
        const selected = activeWorkflow === id
        return (
          <div
            key={id}
            id={`dh-wf-panel-${id}`}
            role="region"
            aria-label={`${id} stage detail`}
            hidden={!selected}
            className="le-dh-wf-panel"
          >
            {panels[id]}
          </div>
        )
      })}

      {runStateLine ? (
        <p className="le-muted le-dh-wf-tasklet" style={{ fontSize: '0.84rem', marginTop: '0.65rem' }}>
          Run state: <strong>{runStateLine}</strong>
        </p>
      ) : null}
    </section>
  )
}

function isWorkflowStageId(s: string): s is WorkflowStageId {
  return (WORKFLOW_STAGE_ORDER as readonly string[]).includes(s)
}
