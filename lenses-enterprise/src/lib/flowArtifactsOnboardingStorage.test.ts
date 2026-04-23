import { describe, expect, it, beforeEach } from 'vitest'
import {
  readFlowArtifactsBannerDismissed,
  readFlowArtifactsChipOverviewHidden,
  writeFlowArtifactsBannerDismissed,
  writeFlowArtifactsChipOverviewHidden,
} from './flowArtifactsOnboardingStorage'

describe('flowArtifactsOnboardingStorage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('defaults to banner dismissed (chip-only overview)', () => {
    expect(readFlowArtifactsBannerDismissed()).toBe(true)
  })

  it('migrates legacy permanent dismiss to banner dismissed', () => {
    localStorage.setItem('lenses_studio_onboarding_lens_dismissed', '1')
    expect(readFlowArtifactsBannerDismissed()).toBe(true)
    expect(localStorage.getItem('lenses_studio_flow_artifacts_banner_dismissed')).toBe('1')
  })

  it('tracks chip hide independently', () => {
    writeFlowArtifactsBannerDismissed()
    expect(readFlowArtifactsChipOverviewHidden()).toBe(false)
    writeFlowArtifactsChipOverviewHidden()
    expect(readFlowArtifactsChipOverviewHidden()).toBe(true)
  })
})
