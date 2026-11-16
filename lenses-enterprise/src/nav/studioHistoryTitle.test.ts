import { describe, expect, it } from 'vitest'
import { buildStudioHistoryTitle } from './studioHistoryTitle'

describe('buildStudioHistoryTitle', () => {
  it('includes story id for plan story tab', () => {
    const t = buildStudioHistoryTitle('/plan', '?tab=story&id=M1E1S1', 'flow')
    expect(t).toContain('M1E1S1')
    expect(t).toContain('Story')
  })

  it('uses nav meta for projects', () => {
    const t = buildStudioHistoryTitle('/projects', '', 'flow')
    expect(t).toContain('Projects')
  })
})
