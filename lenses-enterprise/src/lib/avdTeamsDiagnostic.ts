export type AvdDiagnosticCheck = {
  id: string
  label: string
  ok: boolean
  detail: string
}

export type ParsedAvdDiagnostic = {
  checks: AvdDiagnosticCheck[]
  rawLines: string[]
}

function lineMatches(line: string, pattern: RegExp): boolean {
  return pattern.test(line)
}

/** Parse output from scripts/avd-teams-vc-diagnostic.ps1 (paste into Studio). */
export function parseAvdTeamsDiagnostic(text: string): ParsedAvdDiagnostic {
  const rawLines = (text || '')
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)

  const joined = rawLines.join('\n').toLowerCase()

  const checks: AvdDiagnosticCheck[] = [
    {
      id: 'teams_installed',
      label: 'Teams desktop installed on Cloud PC',
      ok: lineMatches(joined, /teams.*installed:\s*yes/i) || joined.includes('teams.exe'),
      detail: 'Teams per-machine or per-user install required for desktop client.',
    },
    {
      id: 'wvd_registry',
      label: 'IsWVDEnvironment registry flag',
      ok: lineMatches(joined, /iswvdenvironment:\s*1/i) || lineMatches(joined, /iswvdenvironment=1/i),
      detail: 'HKLM\\SOFTWARE\\Microsoft\\Teams\\IsWVDEnvironment should be DWORD 1 on session hosts.',
    },
    {
      id: 'webrtc_redirector',
      label: 'WebRTC Redirector service',
      ok:
        lineMatches(joined, /webrtc.*redirector.*running/i) ||
        lineMatches(joined, /webrtc redirector service:\s*ok/i),
      detail: 'WebRTC Redirector Service must be installed and running for Teams optimization.',
    },
    {
      id: 'media_optimized_hint',
      label: 'Teams media optimization indicators',
      ok:
        lineMatches(joined, /media optimization:\s*likely/i) ||
        lineMatches(joined, /avd slimcore media optimized/i) ||
        lineMatches(joined, /media optimizations loaded/i),
      detail: 'In Teams, confirm banner mentions AVD SlimCore / media optimized (not Remote audio only).',
    },
    {
      id: 'cameras_enumerated',
      label: 'Cameras enumerated in session',
      ok: lineMatches(joined, /camera count:\s*[1-9]/i) || lineMatches(joined, /cameras found:/i),
      detail: 'At least one camera should appear when redirect or optimization is working.',
    },
  ]

  return { checks, rawLines }
}

export function avdDiagnosticSummary(parsed: ParsedAvdDiagnostic): { pass: number; total: number } {
  const total = parsed.checks.length
  const pass = parsed.checks.filter((c) => c.ok).length
  return { pass, total }
}
