import { describe, expect, it } from 'vitest'
import {
  getStudioAboutVersionLine,
  getStudioVersion,
  studioBuildFooterLine,
  studioSplashBuildLine,
} from './studioBuildInfo'

describe('studioBuildInfo', () => {
  it('exposes a semver-like version from the build', () => {
    expect(getStudioVersion()).toMatch(/^\d+\.\d+\.\d+/)
  })

  it('about line joins semver, commit or no-git, and time or em dash', () => {
    const line = getStudioAboutVersionLine()
    expect(line).toMatch(/^\d+\.\d+\.\d+ · (no-git|[0-9a-f]+) · /)
  })

  it('footer line includes the product name and version', () => {
    expect(studioBuildFooterLine()).toMatch(/^Forge Studio \d+\.\d+\.\d+/)
  })

  it('splash line is v-semver, commit or no-git, and time or em dash', () => {
    expect(studioSplashBuildLine()).toMatch(/^v\d+\.\d+\.\d+ · (no-git|[0-9a-f]+) · /)
  })
})
