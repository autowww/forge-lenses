/**
 * Strip common inline markdown so executive surfaces read as plain prose (no visible ** markers).
 */
export function stripInlineMarkdownForBrief(input: string | undefined | null): string {
  if (input == null) return ''
  let s = String(input)
  s = s.replace(/\*\*([^*]+)\*\*/g, '$1')
  s = s.replace(/\*([^*]+)\*/g, '$1')
  s = s.replace(/`([^`]+)`/g, '$1')
  s = s.replace(/^#{1,6}\s+/gm, '')
  return s.trim()
}
