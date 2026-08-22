import { describe, expect, it } from 'vitest'
import {
  mergePlanningScopeIntoTo,
  parsePlanningScopeFromSearch,
  stripPlanningEntryFromTo,
  studioNavLinkEnd,
} from './planningClusterScope'

describe('planningClusterScope', () => {
  it('parses scope keys from search', () => {
    expect(parsePlanningScopeFromSearch('?wbs_p=a&repo=r&other=1')).toEqual({
      wbs_p: 'a',
      repo: 'r',
    })
  })

  it('merges scope into plan and matrix links without clobbering tab', () => {
    const scope = '?wbs_p=foo/bar.md&repo=myrepo&id=S1'
    const planMerged = mergePlanningScopeIntoTo('/plan?tab=today', scope)
    const qPlan = new URLSearchParams(planMerged.split('?')[1] || '')
    expect(qPlan.get('tab')).toBe('today')
    expect(qPlan.get('wbs_p')).toBe('foo/bar.md')
    expect(qPlan.get('repo')).toBe('myrepo')
    expect(qPlan.get('id')).toBe('S1')

    const matrixMerged = mergePlanningScopeIntoTo('/plan/matrix', scope)
    const qM = new URLSearchParams(matrixMerged.split('?')[1] || '')
    expect(qM.get('wbs_p')).toBe('foo/bar.md')
    expect(qM.get('repo')).toBe('myrepo')
  })

  it('does not merge into routes outside the Work scope carry list', () => {
    const scope = '?wbs_p=x'
    expect(mergePlanningScopeIntoTo('/chat', scope)).toBe('/chat')
  })

  it('merges scope into boards hub and readiness when backlog params are present', () => {
    const scope = '?wbs_p=foo.md&repo=r1'
    const boardMerged = mergePlanningScopeIntoTo('/board', scope)
    const qB = new URLSearchParams(boardMerged.split('?')[1] || '')
    expect(qB.get('wbs_p')).toBe('foo.md')
    expect(qB.get('repo')).toBe('r1')

    const readyMerged = mergePlanningScopeIntoTo('/knowledge/methodology/readiness', scope)
    const qR = new URLSearchParams(readyMerged.split('?')[1] || '')
    expect(qR.get('wbs_p')).toBe('foo.md')
    expect(qR.get('repo')).toBe('r1')
  })

  it('maps wbs_p to p on wbs/view when p missing', () => {
    expect(mergePlanningScopeIntoTo('/wbs/view', '?wbs_p=path%2Fwbs.md')).toBe(
      '/wbs/view?wbs_p=path%2Fwbs.md&p=path%2Fwbs.md',
    )
  })

  it('studioNavLinkEnd is true for /plan only', () => {
    expect(studioNavLinkEnd('/plan')).toBe(true)
    expect(studioNavLinkEnd('/plan?tab=today')).toBe(true)
    expect(studioNavLinkEnd('/plan/matrix')).toBe(false)
    expect(studioNavLinkEnd('/projects')).toBe(false)
  })

  it('merges validated from= when target omits it', () => {
    const merged = mergePlanningScopeIntoTo('/plan/matrix', '?wbs_p=a&from=delivery')
    const q = new URLSearchParams(merged.split('?')[1] || '')
    expect(q.get('from')).toBe('delivery')
    expect(q.get('wbs_p')).toBe('a')
  })

  it('does not override explicit from on target', () => {
    const merged = mergePlanningScopeIntoTo('/plan?tab=today&from=boards', '?from=delivery')
    expect(new URLSearchParams(merged.split('?')[1] || '').get('from')).toBe('boards')
  })

  it('stripPlanningEntryFromTo removes from only', () => {
    expect(stripPlanningEntryFromTo('/plan?tab=today&from=delivery&wbs_p=x')).toBe('/plan?tab=today&wbs_p=x')
    expect(stripPlanningEntryFromTo('/plan')).toBe('/plan')
  })
})
