import type { ForgeRunProgressMilestone } from '../forgesdlc-kitchensink/ForgeRunProgressTrack'
import type { ForgeWorkflowStage } from '../forgesdlc-kitchensink/ForgeWorkflowStageBar'
import type { ForgeWorkflowStageStatus } from '../forgesdlc-kitchensink/forgeRunTypes'

function milestoneState(st: ForgeWorkflowStageStatus): ForgeRunProgressMilestone['state'] {
  if (st === 'completed' || st === 'skipped') return 'done'
  if (st === 'failed' || st === 'cancelled') return 'hold'
  if (st === 'in_progress' || st === 'waiting' || st === 'blocked') return 'current'
  return 'upcoming'
}

function shortLabel(label: string, max = 11): string {
  const t = label.trim()
  if (t.length <= max) return t
  return `${t.slice(0, max - 1)}…`
}

/** Milestone ticks aligned with the executive workflow stage bar. */
export function workflowStagesToMilestones(stages: ForgeWorkflowStage[]): ForgeRunProgressMilestone[] {
  return stages.map((s) => ({
    id: s.id,
    label: shortLabel(s.label),
    state: milestoneState(s.status),
  }))
}

/**
 * Rough completion: full weight for completed/skipped stages, partial for the active gate.
 */
export function workflowCompletionPercent(stages: ForgeWorkflowStage[]): number {
  if (!stages.length) return 0
  let pts = 0
  for (const s of stages) {
    const st = s.status
    if (st === 'completed' || st === 'skipped') pts += 1
    else if (st === 'in_progress' || st === 'waiting' || st === 'blocked') {
      pts += 0.42
      break
    } else {
      break
    }
  }
  return Math.min(100, Math.round((pts / stages.length) * 100))
}

/**
 * Heuristic ETA from average time per completed stage (bounded).
 */
export function estimateRemediationEtaSeconds(stages: ForgeWorkflowStage[], elapsedSec: number): number | null {
  if (!stages.length || elapsedSec < 20) return null
  const done = stages.filter((s) => s.status === 'completed' || s.status === 'skipped').length
  if (done === 0) return null
  if (done >= stages.length) return null
  const remaining = stages.length - done
  const rate = elapsedSec / done
  const raw = rate * remaining
  return Math.max(25, Math.min(raw, 6 * 3600))
}

export function formatEtaHint(seconds: number | null): string {
  if (seconds == null || !Number.isFinite(seconds)) return '—'
  if (seconds < 90) return `~${Math.round(seconds)}s remaining (estimate)`
  const m = Math.round(seconds / 60)
  if (m < 120) return `~${m} min remaining (estimate)`
  const h = Math.floor(m / 60)
  const mm = m % 60
  return `~${h}h ${mm}m remaining (estimate)`
}
