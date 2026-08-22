import { afterEach, describe, expect, it } from 'vitest'
import {
  LEGACY_NAV_MODE_COOKIE,
  readWorkspaceLens,
  writeWorkspaceLens,
  WORKSPACE_LENS_COOKIE,
} from './workspaceLensCookie'

describe('workspaceLensCookie', () => {
  afterEach(() => {
    document.cookie = `${WORKSPACE_LENS_COOKIE}=; Path=/; Max-Age=0`
    document.cookie = `${LEGACY_NAV_MODE_COOKIE}=; Path=/; Max-Age=0`
  })

  it('returns null when no cookie', () => {
    expect(readWorkspaceLens()).toBeNull()
  })

  it('round-trips flow via workspace_lens', () => {
    writeWorkspaceLens('flow')
    expect(readWorkspaceLens()).toBe('flow')
  })

  it('round-trips artifacts via workspace_lens', () => {
    writeWorkspaceLens('artifacts')
    expect(readWorkspaceLens()).toBe('artifacts')
  })

  it('returns null for invalid workspace_lens value', () => {
    document.cookie = `${WORKSPACE_LENS_COOKIE}=nope; Path=/`
    expect(readWorkspaceLens()).toBeNull()
  })

  it('falls back to legacy nav_mode when workspace_lens missing', () => {
    document.cookie = `${LEGACY_NAV_MODE_COOKIE}=artifacts; Path=/`
    expect(readWorkspaceLens()).toBe('artifacts')
  })

  it('prefers workspace_lens over legacy nav_mode', () => {
    document.cookie = `${WORKSPACE_LENS_COOKIE}=flow; Path=/`
    document.cookie = `${LEGACY_NAV_MODE_COOKIE}=artifacts; Path=/`
    expect(readWorkspaceLens()).toBe('flow')
  })
})
