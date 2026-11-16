import { describe, expect, it } from 'vitest'
import {
  listProbeRouteDefinitions,
  matchStudioRoute,
  routeProbeKindForPath,
  SR,
  validateStudioRouteRegistry,
} from './studioRouteRegistry'

describe('probe route registry', () => {
  it('keeps a valid registry', () => {
    expect(validateStudioRouteRegistry()).toEqual([])
  })

  it('classifies wizard session URL as wizard_session probe', () => {
    const m = matchStudioRoute('/blueprints/wizard/session/fake-or-expired-id', '')
    expect(m.definition.id).toBe(SR.blueprintsWizardSession)
    expect(m.definition.probeKind).toBe('wizard_session')
    expect(routeProbeKindForPath('/blueprints/wizard/session/x', '')).toBe('wizard_session')
  })

  it('does not mark the wizard hub as a probe route', () => {
    expect(routeProbeKindForPath('/blueprints/wizard', '')).toBeNull()
  })

  it('lists at least the wizard session row', () => {
    const rows = listProbeRouteDefinitions()
    expect(rows.some((d) => d.id === SR.blueprintsWizardSession)).toBe(true)
    expect(rows.some((d) => d.id === SR.projectDocsHealthSession)).toBe(true)
  })

  it('classifies docs health session URL as docs_health_session probe', () => {
    const m = matchStudioRoute('/projects/my-repo/docs-health/session/abc123', '')
    expect(m.definition.id).toBe(SR.projectDocsHealthSession)
    expect(m.definition.probeKind).toBe('docs_health_session')
    expect(routeProbeKindForPath('/projects/x/docs-health/session/y', '')).toBe('docs_health_session')
  })

  it('classifies docs health master URL before generic docs-health', () => {
    const m = matchStudioRoute('/projects/my-repo/docs-health/master', '')
    expect(m.definition.id).toBe(SR.projectDocsHealthMaster)
    expect(routeProbeKindForPath('/projects/x/docs-health/master', '')).toBeNull()
  })
})
