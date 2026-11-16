/** Typed helpers for Plan spine / work model readiness (Studio Flow cockpit). */

export type PlanMilestone = {
  epic_key?: string
  title?: string
  theme?: string
  stories?: { id: string; title?: string; task_count?: number }[]
}

export function getMilestones(spine: Record<string, unknown> | null): PlanMilestone[] {
  if (!spine) return []
  const plan = spine.plan as { milestones?: PlanMilestone[] } | undefined
  return Array.isArray(plan?.milestones) ? plan!.milestones! : []
}

export function getWorkModelStats(workModel: Record<string, unknown> | null): {
  rootIds: string[]
  nodeCount: number
  rootCount: number
} {
  if (!workModel) {
    return { rootIds: [], nodeCount: 0, rootCount: 0 }
  }
  const nodes = (workModel.nodes as Record<string, unknown> | undefined) ?? {}
  const rootIds = Array.isArray(workModel.root_ids)
    ? (workModel.root_ids as string[])
    : []
  return {
    rootIds,
    nodeCount: Object.keys(nodes).length,
    rootCount: rootIds.length,
  }
}

export type PlanReadinessMetrics = {
  wbsSelected: boolean
  spineLoaded: boolean
  spineError: string | null
  milestoneCount: number
  nodeCount: number
  rootCount: number
  roadmapLinked: boolean
}

export function computePlanReadiness(
  wbsP: string,
  spine: Record<string, unknown> | null,
  workModel: Record<string, unknown> | null,
  spineErr: string | null,
  roadmapP: string,
): PlanReadinessMetrics {
  const milestones = getMilestones(spine)
  const { nodeCount, rootCount } = getWorkModelStats(workModel)
  return {
    wbsSelected: Boolean(wbsP.trim()),
    spineLoaded: spine != null && !spineErr,
    spineError: spineErr,
    milestoneCount: milestones.length,
    nodeCount,
    rootCount,
    roadmapLinked: Boolean(roadmapP.trim()),
  }
}

export type OutcomeAlignment = {
  storyIdsInSpine: number
  matchedInWorkModel: number
  coveragePct: number | null
}

export function computeOutcomeAlignment(
  spine: Record<string, unknown> | null,
  workModel: Record<string, unknown> | null,
): OutcomeAlignment {
  const milestones = getMilestones(spine)
  const nodes = (workModel?.nodes as Record<string, unknown> | undefined) ?? {}
  const storyIds = new Set<string>()
  for (const ms of milestones) {
    for (const st of ms.stories ?? []) {
      if (st.id) storyIds.add(st.id)
    }
  }
  let matched = 0
  for (const id of storyIds) {
    if (Object.prototype.hasOwnProperty.call(nodes, id)) matched += 1
  }
  const n = storyIds.size
  return {
    storyIdsInSpine: n,
    matchedInWorkModel: matched,
    coveragePct: n > 0 ? Math.round((100 * matched) / n) : null,
  }
}
