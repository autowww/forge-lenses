import { describe, expect, it } from 'vitest'
import { MockContextSnippetProvider } from './contextIntakeAdapters'

describe('MockContextSnippetProvider', () => {
  it('returns a placeholder string', async () => {
    const p = new MockContextSnippetProvider()
    const s = await p.getSnippet('repo', 'x/y')
    expect(s).toContain('mock repo')
    expect(s).toContain('x/y')
  })
})
