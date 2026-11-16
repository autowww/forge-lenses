import type { FoundryActivityLine, FoundryPhase } from './foundryTypes'
import type { ForgeAgentLiveLogLine } from '../forgesdlc-kitchensink'
import type { ForgeRunProgressMilestone } from '../forgesdlc-kitchensink/ForgeRunProgressTrack'
import type { ForgeWorkflowStageStatus } from '../forgesdlc-kitchensink/forgeRunTypes'

export function foundryActivityToLogLines(
  activity: FoundryActivityLine[] | undefined,
  limit = 200,
): ForgeAgentLiveLogLine[] {
  if (!activity?.length) return []
  const rows = activity.slice(-limit).map((a) => ({
    id: a.id || `${a.ts}-${a.text.slice(0, 8)}`,
    ts: a.ts,
    text: a.text,
    tone: (a.tone || 'info') as ForgeAgentLiveLogLine['tone'],
  }))
  return rows
}

const MILESTONE_IDS = ['context', 'plan', 'draft-unit', 'apply+verify', 'assay'] as const

export function foundryProgressFromPhases(phases: FoundryPhase[] | undefined): {
  percent: number
  milestones: ForgeRunProgressMilestone[]
} {
  const byId = new Map((phases ?? []).map((p) => [p.id, p]))
  const milestones: ForgeRunProgressMilestone[] = MILESTONE_IDS.map((id) => {
    const p = byId.get(id) ?? byId.get(id === 'draft-unit' ? 'draft-unit-0' : id)
    let state: ForgeRunProgressMilestone['state'] = 'upcoming'
    if (p?.status === 'completed') state = 'done'
    else if (p?.status === 'in_progress') state = 'current'
    else if (p?.status === 'failed' || p?.status === 'blocked') state = 'hold'
    const label = id === 'apply+verify' ? 'verify' : id.replace('draft-unit', 'draft')
    return { id, label, state }
  })
  const done = milestones.filter((m) => m.state === 'done').length
  const current = milestones.some((m) => m.state === 'current') ? 0.5 : 0
  const percent = Math.round(((done + current) / milestones.length) * 100)
  return { percent, milestones }
}

export function foundryStagesWithPulse(
  phases: FoundryPhase[] | undefined,
  status: string | undefined,
  currentPhase?: string | null,
): { id: string; label: string; status: ForgeWorkflowStageStatus }[] {
  const base = (phases ?? []).map((p) => ({
    id: p.id,
    label: p.label,
    status: p.status,
  }))
  if (status !== 'running' && status !== 'pending') return base
  const active = (currentPhase || '').trim()
  if (!active) return base
  return base.map((s) => {
    if (s.id === active && s.status === 'not_started') {
      return { ...s, status: 'in_progress' as const }
    }
    return s
  })
}
