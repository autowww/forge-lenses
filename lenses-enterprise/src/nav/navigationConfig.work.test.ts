import { describe, expect, it } from 'vitest'
import { getSideNavEntries } from './navigationConfig'

describe('Work section sidebar (UX4)', () => {
  it('lists primary journey first and buckets advanced entries', () => {
    const w = getSideNavEntries('work', 'flow')
    expect(w[0].to).toBe('/plan?tab=today')
    expect(w.map((e) => e.sidebarGroup)).toContain('work_advanced')
    const adv = w.filter((e) => e.sidebarGroup === 'work_advanced')
    expect(adv.length).toBeGreaterThanOrEqual(4)
    expect(adv.some((e) => e.to?.includes('/plan/matrix'))).toBe(true)
    expect(w.some((e) => e.to === '/foundry')).toBe(true)
  })
})
