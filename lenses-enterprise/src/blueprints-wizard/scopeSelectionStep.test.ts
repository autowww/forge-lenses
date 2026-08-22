import { describe, expect, it } from 'vitest'
import { normalizeClosureOptionsList } from './wizardDomainNormalize'
import { validateScopeSelectionForNext, scopeSpecFromSelection } from './scopeSelectionStep'
import { emptyWizardDomain } from './wizardDomainNormalize'

describe('validateScopeSelectionForNext', () => {
  it('requires milestone ref when boundary is milestone', () => {
    const v = validateScopeSelectionForNext({
      scopeBoundary: 'milestone',
      milestoneRef: '',
      wbePath: '',
      capabilityLabel: '',
      teamLabel: '',
      repoPathsText: '',
      recheckIssueRefs: '',
      closureOptions: [],
      advancedScopeExpanded: false,
    })
    expect(v.ok).toBe(false)
    expect(v.errors.detail).toBeDefined()
  })

  it('passes full_plan without extra refs', () => {
    const v = validateScopeSelectionForNext({
      scopeBoundary: 'full_plan',
      milestoneRef: '',
      wbePath: '',
      capabilityLabel: '',
      teamLabel: '',
      repoPathsText: '',
      recheckIssueRefs: '',
      closureOptions: [],
      advancedScopeExpanded: false,
    })
    expect(v.ok).toBe(true)
  })
})

describe('scopeSpecFromSelection', () => {
  it('merges closure options uniquely', () => {
    const base = emptyWizardDomain().scope_spec
    const merged = scopeSpecFromSelection(base, {
      scopeBoundary: 'full_plan',
      milestoneRef: '',
      wbePath: '',
      capabilityLabel: '',
      teamLabel: '',
      repoPathsText: '',
      recheckIssueRefs: '',
      closureOptions: ['exact_only', 'exact_only', 'include_required_upstream'],
      advancedScopeExpanded: true,
    })
    expect(merged.closure_options).toEqual(['exact_only', 'include_required_upstream'])
  })
})

describe('normalizeClosureOptionsList', () => {
  it('sorts and dedupes', () => {
    expect(normalizeClosureOptionsList(['include_verification_artifacts', 'exact_only', 'exact_only'])).toEqual([
      'exact_only',
      'include_verification_artifacts',
    ])
  })
})
