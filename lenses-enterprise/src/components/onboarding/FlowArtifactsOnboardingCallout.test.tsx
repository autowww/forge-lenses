import { describe, expect, it, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { FlowArtifactsOnboardingCallout } from './FlowArtifactsOnboardingCallout'
import { writeFlowArtifactsBannerOptIn } from '../../lib/flowArtifactsOnboardingStorage'
import { STUDIO_ONBOARDING } from '../../nav/studioVisibleCopy'

describe('FlowArtifactsOnboardingCallout', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('defaults to compact lens help chip (no expanded explainer)', () => {
    render(
      <MemoryRouter>
        <FlowArtifactsOnboardingCallout />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('region', { name: /flow vs artifacts/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: STUDIO_ONBOARDING.flowArtifactsChipLabel })).toBeInTheDocument()
  })

  it('shows expanded explainer when opted in (banner not dismissed)', () => {
    writeFlowArtifactsBannerOptIn()
    render(
      <MemoryRouter>
        <FlowArtifactsOnboardingCallout />
      </MemoryRouter>,
    )
    expect(screen.getByRole('region', { name: /flow vs artifacts/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: STUDIO_ONBOARDING.flowArtifactsGotIt })).toBeInTheDocument()
  })

  it('shows compact chip after Got it', async () => {
    localStorage.setItem('lenses_studio_flow_artifacts_banner_dismissed', '1')
    render(
      <MemoryRouter>
        <FlowArtifactsOnboardingCallout />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('region', { name: /flow vs artifacts/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: STUDIO_ONBOARDING.flowArtifactsChipLabel })).toBeInTheDocument()
  })
})
