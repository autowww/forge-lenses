import { describe, expect, it } from 'vitest'
import { emptyWizardDomain, normalizeRecheckSummary, normalizeWizardDomain } from './wizardDomainNormalize'

describe('normalizeWizardDomain', () => {
  it('matches empty defaults', () => {
    const e = emptyWizardDomain()
    expect(e.schema_version).toBe(1)
    expect(e.mission_type).toBe('explore')
    expect(e.prompt_snapshot).toBeNull()
  })

  it('coerces invalid enums to defaults', () => {
    const out = normalizeWizardDomain({
      mission_type: 'bogus',
      contribution_setup_kind: 'mega',
      target_stage: 'nope',
      context_sources: ['repo', 'invalid'],
    })
    expect(out.mission_type).toBe('explore')
    expect(out.contribution_setup_kind).toBe('single')
    expect(out.target_stage).toBe('idea')
    expect(out.context_sources).toEqual(['repo', 'other'])
  })

  it('preserves unknown top-level keys', () => {
    const out = normalizeWizardDomain({
      future_flag: { x: 1 },
      mission_type: 'deliver',
    } as Record<string, unknown>)
    expect((out as Record<string, unknown>).future_flag).toEqual({ x: 1 })
    expect(out.mission_type).toBe('deliver')
  })

  it('maps legacy target stage tokens', () => {
    const out = normalizeWizardDomain({ target_stage: 'discovery' })
    expect(out.target_stage).toBe('idea')
  })

  it('does not alias inner defaults on repeat normalize', () => {
    const a = emptyWizardDomain()
    const b = normalizeWizardDomain(a)
    ;(a as Record<string, unknown>).mission_type = 'sunset'
    expect(b.mission_type).toBe('explore')
  })

  it('includes empty recheck report by default', () => {
    const out = emptyWizardDomain()
    expect(out.recheck_summary.report.schema_version).toBe(1)
    expect(out.recheck_summary.report.artifacts).toEqual([])
  })
})

describe('normalizeRecheckSummary', () => {
  it('retains structured report with artifacts and recommendations', () => {
    const s = normalizeRecheckSummary({
      checked_at: '2024-01-01T00:00:00Z',
      passed: false,
      issues: ['x'],
      report: {
        schema_version: 1,
        computed_at: '2024-01-01T00:00:01Z',
        artifacts: [
          {
            artifact_key: 'roadmap',
            primary_label: 'stale',
            reasons: ['lineage_drift'],
            review_status: 'pending',
            generation_id: 'g1',
            created_at: 't',
            parent_generation_id: '',
          },
        ],
        buckets: [{ id: 'planning', worst_label: 'stale', artifact_keys: ['roadmap'] }],
        recommendations: {
          regenerate_keys: ['roadmap'],
          approve_first: ['foundation_brief_final'],
          unlock_or_request_changes: [],
          flag_for_review: ['note'],
        },
      },
    })
    expect(s.report.artifacts).toHaveLength(1)
    expect(s.report.artifacts[0].artifact_key).toBe('roadmap')
    expect(s.report.recommendations.regenerate_keys).toEqual(['roadmap'])
    expect(s.issues).toEqual(['x'])
  })
})
