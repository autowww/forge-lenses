import { describe, expect, it, vi } from 'vitest'

describe('blueprintsWizardFeatureEnabled', () => {
  it('is true when VITE_EXPERIMENTAL_BLUEPRINTS_WIZARD is true', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_EXPERIMENTAL_BLUEPRINTS_WIZARD', 'true')
    const { blueprintsWizardFeatureEnabled } = await import('./experimentalFlags')
    expect(blueprintsWizardFeatureEnabled()).toBe(true)
  })

  it('is true when unset or empty (default on)', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_EXPERIMENTAL_BLUEPRINTS_WIZARD', '')
    const { blueprintsWizardFeatureEnabled } = await import('./experimentalFlags')
    expect(blueprintsWizardFeatureEnabled()).toBe(true)
  })

  it('is false when explicitly disabled', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_EXPERIMENTAL_BLUEPRINTS_WIZARD', 'false')
    const { blueprintsWizardFeatureEnabled } = await import('./experimentalFlags')
    expect(blueprintsWizardFeatureEnabled()).toBe(false)
  })
})
