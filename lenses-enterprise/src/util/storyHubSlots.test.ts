import { describe, expect, it } from 'vitest'
import { storyDefinitionMarkdown, storySlotCellToMarkdown } from './storyHubSlots'

describe('storySlotCellToMarkdown', () => {
  it('returns plain strings', () => {
    expect(storySlotCellToMarkdown('hello')).toBe('hello')
  })

  it('extracts .text from API slot objects', () => {
    expect(
      storySlotCellToMarkdown({
        text: 'Do the thing',
        sources: [{ href: '/wbs/view?p=x' }],
      }),
    ).toBe('Do the thing')
  })

  it('stringifies other objects', () => {
    expect(storySlotCellToMarkdown({ foo: 1 })).toBe(JSON.stringify({ foo: 1 }, null, 2))
  })
})

describe('storyDefinitionMarkdown', () => {
  it('prefers story_view.definition when present', () => {
    expect(
      storyDefinitionMarkdown(
        { definition: { kind: 'story' } },
        { definition: 'from sv' },
      ),
    ).toBe('from sv')
  })

  it('falls back to top-level definition object', () => {
    const md = storyDefinitionMarkdown(
      { definition: { kind: 'story', id: 'M1E1S1' } },
      undefined,
    )
    expect(md).toContain('"kind": "story"')
    expect(md).toContain('M1E1S1')
  })
})
