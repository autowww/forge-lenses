import { describe, expect, it } from 'vitest'

import { formatDocsHealthScanDiagnosticsReport } from './docsHealthScanDiagnostics'

describe('formatDocsHealthScanDiagnosticsReport', () => {
  it('includes origins, flags, curl with encoded slug, and optional message', () => {
    const s = formatDocsHealthScanDiagnosticsReport({
      generatedAt: '2026-04-15T12:00:00.000Z',
      projectSlug: 'my/repo',
      pageHref: 'http://127.0.0.1:37813/studio/projects/my%2Frepo/docs-health',
      pageOrigin: 'http://127.0.0.1:37813',
      jsonApiOrigin: 'http://127.0.0.1:37813',
      viteLensApiBase: 'unset',
      importMetaDev: false,
      importMetaMode: 'production',
      staticMuseum: false,
      userAgent: 'Vitest',
      lastScanUiMessage: 'Failed to fetch',
    })
    expect(s).toContain('json_api_origin**: http://127.0.0.1:37813')
    expect(s).toContain('page_vs_json_api_origin**: same')
    expect(s).toContain('my%2Frepo')
    expect(s).toContain('"op":"ping"')
    expect(s).toContain('Failed to fetch')
  })

  it('truncates very long UI messages', () => {
    const long = 'x'.repeat(8000)
    const s = formatDocsHealthScanDiagnosticsReport({
      generatedAt: 't',
      projectSlug: 'p',
      pageHref: '',
      pageOrigin: '',
      jsonApiOrigin: 'http://localhost:1',
      viteLensApiBase: 'unset',
      importMetaDev: true,
      importMetaMode: 'development',
      staticMuseum: false,
      userAgent: '',
      lastScanUiMessage: long,
    })
    expect(s).toContain('…')
    expect((s.match(/x/g) || []).length).toBeLessThan(6500)
  })
})
