import { describe, expect, it } from 'vitest'
import { parseAvdTeamsDiagnostic, avdDiagnosticSummary } from './avdTeamsDiagnostic'
import { applyAvdTeamsPreset, buildOutputFormatOptions } from './virtualCameraEditorOptions'

describe('avdTeamsDiagnostic', () => {
  it('parses positive Cloud PC diagnostic lines', () => {
    const text = `
Teams installed: YES (C:\\Program Files\\Microsoft\\Teams\\current\\Teams.exe)
IsWVDEnvironment: 1
WebRTC Redirector Service: Running
Camera count: 2
Media optimization: likely when Teams shows AVD SlimCore Media Optimized
`
    const parsed = parseAvdTeamsDiagnostic(text)
    const summary = avdDiagnosticSummary(parsed)
    expect(summary.pass).toBeGreaterThan(2)
    expect(parsed.checks.find((c) => c.id === 'wvd_registry')?.ok).toBe(true)
  })
})

describe('avd teams preset', () => {
  it('prefers MJPEG output when virtual device supports MJPG', () => {
    const virtualFormats = [{ fourcc: 'MJPG', sizes: [] }]
    const applied = applyAvdTeamsPreset(undefined, virtualFormats)
    expect(applied.quality_preset).toBe('avd_teams')
    expect(applied.output_format).toBe('MJPEG')
  })

  it('builds output options from virtual caps', () => {
    const opts = buildOutputFormatOptions([{ fourcc: 'NV12', sizes: [] }, { fourcc: 'MJPG', sizes: [] }])
    expect(opts).toContain('MJPEG')
    expect(opts).toContain('NV12')
  })
})
