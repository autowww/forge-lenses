/** Human-readable “where we are” copy for Copilot rail / panel (mirrors what the server sees in scope). */

export type CopilotContextScopeInput = {
  route?: string
  projectSlug?: string
  entityId?: string
  scopeSite?: string
  pageContextSummary?: string
  relatedMdRelPaths?: string[] | undefined
  /** When the operator is on `/chat` with Threads vs linear Chat (drives server grounding hint). */
  studioChatMode?: 'threads' | 'linear'
}

export function describeCopilotStudioContext(scope: CopilotContextScopeInput): {
  headline: string
  topicParts: string[]
} {
  const route = (scope.route || '').trim()
  const summary = (scope.pageContextSummary || '').trim()
  const headline = summary || (route ? `Studio · ${route}` : 'Forge Studio')

  const topicParts: string[] = []
  if (summary && route) topicParts.push(`route: ${route}`)
  else if (!summary && route) {
    /* headline already covers route */
  }
  const ps = (scope.projectSlug || '').trim()
  if (ps) topicParts.push(`project: ${ps}`)
  const ent = (scope.entityId || '').trim()
  if (ent) topicParts.push(`entity: ${ent}`)
  const site = (scope.scopeSite || '').trim()
  if (site) topicParts.push(`site: ${site}`)
  const md = (scope.relatedMdRelPaths ?? []).map((s) => s.trim()).filter(Boolean).length
  if (md) topicParts.push(`${md} context ${md === 1 ? 'doc' : 'docs'}`)
  if (scope.studioChatMode === 'threads') topicParts.push('Chat: Threads')
  else if (scope.studioChatMode === 'linear') topicParts.push('Chat: linear')
  return { headline, topicParts }
}
