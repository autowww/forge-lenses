import type { ForgeWorkflowStageStatus } from './forgeRunTypes'

export type ForgeWorkflowStage = {
  id: string
  label: string
  status: ForgeWorkflowStageStatus
}

export type ForgeWorkflowStageBarProps = {
  stages: ForgeWorkflowStage[]
  className?: string
  'aria-label'?: string
  /** When set, each stage is a focusable control (for tab / section navigation). */
  onStageClick?: (stageId: string) => void
  /** Highlights the stage that matches the active tab or section (e.g. keyboard nav). */
  currentStageId?: string | null
  /** `executive` uses calmer contrast and larger type for dashboards. */
  variant?: 'default' | 'executive'
}

function statusClass(s: ForgeWorkflowStageStatus): string {
  switch (s) {
    case 'completed':
      return 'ks-fe-stagebar__node--completed'
    case 'in_progress':
      return 'ks-fe-stagebar__node--active'
    case 'waiting':
      return 'ks-fe-stagebar__node--waiting'
    case 'blocked':
      return 'ks-fe-stagebar__node--blocked'
    case 'failed':
      return 'ks-fe-stagebar__node--failed'
    case 'skipped':
      return 'ks-fe-stagebar__node--skipped'
    case 'cancelled':
      return 'ks-fe-stagebar__node--cancelled'
    case 'not_started':
    default:
      return 'ks-fe-stagebar__node--pending'
  }
}

function statusLabel(s: ForgeWorkflowStageStatus): string {
  switch (s) {
    case 'not_started':
      return 'Not started'
    case 'in_progress':
      return 'In progress'
    case 'waiting':
      return 'Waiting'
    case 'blocked':
      return 'Blocked'
    case 'completed':
      return 'Completed'
    case 'failed':
      return 'Failed'
    case 'skipped':
      return 'Skipped'
    case 'cancelled':
      return 'Cancelled'
    default:
      return s
  }
}

/**
 * Horizontal workflow strip with semantic per-stage status. Optional navigation for tabbed run consoles.
 */
export function ForgeWorkflowStageBar({
  stages,
  className = '',
  'aria-label': ariaLabel = 'Workflow stages',
  onStageClick,
  currentStageId,
  variant = 'default',
}: ForgeWorkflowStageBarProps) {
  if (!stages.length) return null
  const nav = Boolean(onStageClick)
  const vClass = variant === 'executive' ? ' ks-fe-stagebar--executive' : ''
  return (
    <ol className={`ks-fe-stagebar${nav ? ' ks-fe-stagebar--nav' : ''}${vClass} ${className}`.trim()} aria-label={ariaLabel}>
      {stages.map((st, i) => {
        const isCurrent = currentStageId != null && st.id === currentStageId
        const nodeClass = [
          'ks-fe-stagebar__node',
          statusClass(st.status),
          isCurrent ? 'ks-fe-stagebar__node--current' : '',
        ]
          .filter(Boolean)
          .join(' ')
        const title = `${st.label}: ${statusLabel(st.status)}`
        const common = (
          <>
            <span className="ks-fe-stagebar__connector" aria-hidden={i === 0} />
            {nav ? (
              <button
                type="button"
                className={nodeClass}
                title={title}
                aria-label={title}
                aria-current={isCurrent ? 'step' : undefined}
                onClick={() => onStageClick?.(st.id)}
              >
                <span className="ks-fe-stagebar__label">{st.label}</span>
              </button>
            ) : (
              <span className={nodeClass} title={title}>
                <span className="ks-fe-stagebar__label">{st.label}</span>
              </span>
            )}
          </>
        )
        return (
          <li key={st.id} className={`ks-fe-stagebar__step ${statusClass(st.status)}`}>
            {common}
          </li>
        )
      })}
    </ol>
  )
}
