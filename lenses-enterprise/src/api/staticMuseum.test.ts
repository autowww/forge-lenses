import { describe, expect, it } from 'vitest'
import { museumFileForApiPath } from './staticMuseum'

describe('museumFileForApiPath', () => {
  it('maps workspace state with query', () => {
    expect(museumFileForApiPath('/api/workspace-state?git_extended=1')).toBe(
      'workspace-state.json',
    )
  })

  it('maps project routes with dynamic name', () => {
    expect(museumFileForApiPath('/api/project/forgesdlc-kitchensink/stats')).toBe(
      'project-stats.json',
    )
    expect(museumFileForApiPath('/api/project/foo/context')).toBe('project-context.json')
    expect(museumFileForApiPath('/api/project/foo/chart-data')).toBe('project-chart-data.json')
  })

  it('maps forgesdlc blog index', () => {
    expect(museumFileForApiPath('/api/forgesdlc-blog')).toBe('forgesdlc-blog.json')
  })

  it('maps blueprints wizard enabled', () => {
    expect(museumFileForApiPath('/api/blueprints/wizard/enabled')).toBe(
      'blueprints-wizard-enabled.json',
    )
  })

  it('maps blueprints wizard sessions list', () => {
    expect(museumFileForApiPath('/api/blueprints/wizard/sessions')).toBe(
      'blueprints-wizard-sessions.json',
    )
  })

  it('maps blueprints wizard session by id', () => {
    expect(museumFileForApiPath('/api/blueprints/wizard/session/abc-id-123')).toBe(
      'blueprints-wizard-session.json',
    )
  })

  it('maps cicd control tower', () => {
    expect(museumFileForApiPath('/api/cicd/control-tower')).toBe('cicd-control-tower.json')
    expect(museumFileForApiPath('/api/cicd/enabled')).toBe('cicd-enabled.json')
  })

  it('maps quality overview and project quality', () => {
    expect(museumFileForApiPath('/api/quality/overview')).toBe('quality-overview.json')
    expect(museumFileForApiPath('/api/quality/enabled')).toBe('quality-enabled.json')
    expect(museumFileForApiPath('/api/project/foo/quality')).toBe('project-quality.json')
  })

  it('maps devsecops overview and project devsecops', () => {
    expect(museumFileForApiPath('/api/devsecops/overview')).toBe('devsecops-overview.json')
    expect(museumFileForApiPath('/api/devsecops/enabled')).toBe('devsecops-enabled.json')
    expect(museumFileForApiPath('/api/project/foo/devsecops')).toBe('project-devsecops.json')
  })

  it('maps cross-team release overview', () => {
    expect(museumFileForApiPath('/api/cross-team-release/overview')).toBe('cross-team-release-overview.json')
    expect(museumFileForApiPath('/api/cross-team-release/enabled')).toBe('cross-team-release-enabled.json')
  })

  it('maps ops-delivery overview', () => {
    expect(museumFileForApiPath('/api/ops-delivery/overview')).toBe('ops-delivery-overview.json')
    expect(museumFileForApiPath('/api/ops-delivery/enabled')).toBe('ops-delivery-enabled.json')
  })

  it('maps bridge spine API paths', () => {
    expect(museumFileForApiPath('/api/bridge/enabled')).toBe('bridge-enabled.json')
    expect(museumFileForApiPath('/api/bridge/registry')).toBe('bridge-registry.json')
    expect(
      museumFileForApiPath('/api/bridge/trace/ogs%3Ademo%3Astory%3Arate-limit-auth'),
    ).toBe('bridge-trace.json')
  })

  it('falls back to empty.json', () => {
    expect(museumFileForApiPath('/api/unknown-endpoint')).toBe('empty.json')
  })
})
