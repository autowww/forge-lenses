import { describe, expect, it } from 'vitest'
import { getSideNavEntries } from './navigationConfig'

describe('getSideNavEntries (Sprint UX6 — Knowledge & Publish grouping)', () => {
  it('groups Knowledge sidebar entries by learn / evidence / govern / build', () => {
    const k = getSideNavEntries('knowledge', 'flow')
    const groups = k.map((e) => e.sidebarGroup)
    expect(groups.filter((g) => g === 'knowledge_learn')).toHaveLength(2)
    expect(groups.filter((g) => g === 'knowledge_evidence')).toHaveLength(2)
    expect(groups.filter((g) => g === 'knowledge_govern')).toHaveLength(2)
    const build = groups.filter((g) => g === 'knowledge_build')
    expect(build.length === 0 || build.length === 1).toBe(true)
  })

  it('groups Publish sidebar entries by sites vs stories', () => {
    const p = getSideNavEntries('publish', 'flow', undefined, 'demo-site')
    const groups = p.map((e) => e.sidebarGroup)
    expect(groups.filter((g) => g === 'publish_sites')).toHaveLength(2)
    expect(groups.filter((g) => g === 'publish_stories')).toHaveLength(2)
  })
})
