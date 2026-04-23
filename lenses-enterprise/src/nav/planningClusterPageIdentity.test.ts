import { describe, expect, it } from 'vitest'
import { getPlanningClusterPageIdentity } from './planningClusterPageIdentity'
import { STUDIO_VOCAB } from './studioVisibleCopy'

describe('getPlanningClusterPageIdentity', () => {
  it('matches plan subview titles to registry canonical titles', () => {
    expect(getPlanningClusterPageIdentity('/plan', '', 'flow').title).toBe(STUDIO_VOCAB.planSummary)
    expect(getPlanningClusterPageIdentity('/plan', '?tab=today', 'flow').title).toBe(STUDIO_VOCAB.today)
    expect(getPlanningClusterPageIdentity('/plan', '?tab=source', 'artifacts').title).toBe(STUDIO_VOCAB.sources)
    expect(getPlanningClusterPageIdentity('/plan', '?tab=story', 'flow').title).toBe(STUDIO_VOCAB.story)
  })

  it('adds story work item line when id is present', () => {
    const id = getPlanningClusterPageIdentity('/plan', '?tab=story&id=ABC', 'flow')
    expect(id.storyWorkItemLine).toBe('Work item: ABC')
  })

  it('surfaces entry hint for from=delivery and from=boards', () => {
    expect(getPlanningClusterPageIdentity('/plan', '?tab=today&from=delivery', 'flow').entryHint).toContain('Linked')
    expect(getPlanningClusterPageIdentity('/plan', '?tab=today&from=boards', 'artifacts').entryHint).toContain(
      'Boards',
    )
    expect(getPlanningClusterPageIdentity('/plan', '?tab=today', 'flow').entryHint).toBeNull()
  })

  it('aligns matrix and WBS routes with registry titles', () => {
    expect(getPlanningClusterPageIdentity('/plan/matrix', '', 'flow').title).toBe(STUDIO_VOCAB.roadmapMatrix)
    expect(getPlanningClusterPageIdentity('/wbs', '', 'flow').title).toBe(STUDIO_VOCAB.workBreakdown)
    expect(getPlanningClusterPageIdentity('/timeline', '?from=delivery', 'flow').title).toBe(STUDIO_VOCAB.timeline)
  })
})
