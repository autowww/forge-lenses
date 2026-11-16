import { describe, expect, it } from 'vitest'
import { describeCopilotStudioContext } from './copilotStudioContext'

describe('describeCopilotStudioContext', () => {
  it('prefers pageContextSummary as headline', () => {
    const o = describeCopilotStudioContext({
      route: 'search',
      pageContextSummary: 'Forge Studio · Search · scoped to acme',
      projectSlug: 'acme',
    })
    expect(o.headline).toBe('Forge Studio · Search · scoped to acme')
    expect(o.topicParts.join(' ')).toContain('route:')
    expect(o.topicParts.join(' ')).toContain('project:')
  })

  it('falls back to Studio · route when no summary', () => {
    const o = describeCopilotStudioContext({ route: 'plan' })
    expect(o.headline).toBe('Studio · plan')
  })
})
