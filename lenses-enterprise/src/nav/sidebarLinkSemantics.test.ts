import { describe, expect, it } from 'vitest'
import {
  getSidebarLinkSemantics,
  parseStudioTo,
  sidebarLinkAccessibleLabel,
} from './sidebarLinkSemantics'

describe('parseStudioTo', () => {
  it('splits path and query', () => {
    expect(parseStudioTo('/plan?tab=today')).toEqual({ pathname: '/plan', search: '?tab=today' })
    expect(parseStudioTo('/projects')).toEqual({ pathname: '/projects', search: '' })
  })
})

describe('getSidebarLinkSemantics', () => {
  it('marks same-section routes as native', () => {
    expect(
      getSidebarLinkSemantics({ label: 'X', to: '/plan' }, 'work', 'artifacts').kind,
    ).toBe('native')
  })

  it('marks cross-section spa links as shortcuts with owner label', () => {
    const s = getSidebarLinkSemantics(
      { label: 'Charts', to: '/overview/charts' },
      'work',
      'flow',
    )
    expect(s).toEqual({ kind: 'shortcut', ownerSectionLabel: 'Home' })
  })

  it('marks classic href as classic', () => {
    const s = getSidebarLinkSemantics({ label: 'R', href: '/roadmaps/summary' }, 'work', 'flow')
    expect(s.kind).toBe('classic')
  })

  it('exposes accessible label for shortcuts', () => {
    const sem = getSidebarLinkSemantics({ label: 'Today', to: '/plan?tab=today' }, 'home', 'flow')
    expect(sem.kind).toBe('shortcut')
    expect(
      sidebarLinkAccessibleLabel({ label: 'Today', to: '/plan?tab=today' }, sem),
    ).toContain('Work')
  })

  it('exposes accessible label for full-workspace (non-SPA) href', () => {
    const sem = getSidebarLinkSemantics({ label: 'R', href: '/roadmaps/summary' }, 'work', 'flow')
    expect(
      sidebarLinkAccessibleLabel({ label: 'R', href: '/roadmaps/summary' }, sem),
    ).toMatch(/Full Lenses workspace/i)
  })
})
