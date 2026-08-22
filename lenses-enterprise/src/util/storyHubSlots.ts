/**
 * `/api/story-hub` returns `story_view.slots` as `{ [slot]: { text, sources?, ... } }`.
 * Older clients assumed string values; normalize for markdown rendering.
 */
export function storySlotCellToMarkdown(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'object') {
    const t = (value as { text?: unknown }).text
    if (typeof t === 'string') return t
  }
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

/** Definition block: optional string or structured object from the API. */
export function storyDefinitionMarkdown(
  story: Record<string, unknown>,
  sv: Record<string, unknown> | undefined,
): string | undefined {
  const rawDef = sv?.definition ?? story.definition
  if (typeof rawDef === 'string') return rawDef
  if (rawDef != null && typeof rawDef === 'object') return JSON.stringify(rawDef, null, 2)
  return undefined
}
