/**
 * Browser-agnostic bundle for Docs Health scan connectivity issues.
 * Lenses often binds an **ephemeral or CLI-chosen port** each run — callers pass
 * the resolved JSON API origin (same rules as `apiUrl` / `lensesJsonApiOrigin`).
 */

export type DocsHealthScanDiagnosticsInput = {
  generatedAt: string
  projectSlug: string
  pageHref: string
  pageOrigin: string
  jsonApiOrigin: string
  viteLensApiBase: 'unset' | 'set_non_empty'
  importMetaDev: boolean
  importMetaMode: string
  staticMuseum: boolean
  userAgent: string
  /** Last scan error text from the client (truncated in output if very long). */
  lastScanUiMessage?: string | null
}

const MAX_UI_MESSAGE = 6000

export function formatDocsHealthScanDiagnosticsReport(d: DocsHealthScanDiagnosticsInput): string {
  const same = d.pageOrigin === d.jsonApiOrigin
  let ui = (d.lastScanUiMessage ?? '').trim()
  if (ui.length > MAX_UI_MESSAGE) ui = `${ui.slice(0, MAX_UI_MESSAGE)}…`
  const enc = encodeURIComponent(d.projectSlug)
  const lines = [
    '### Forge Studio — Docs Health scan diagnostics',
    '_Lenses may use a different TCP port on each run; values below are from this browser tab at capture time._',
    '',
    `- **generated_at**: ${d.generatedAt}`,
    `- **project_slug**: ${d.projectSlug}`,
    `- **page_href**: ${d.pageHref}`,
    `- **page_origin**: ${d.pageOrigin}`,
    `- **json_api_origin**: ${d.jsonApiOrigin}`,
    `- **page_vs_json_api_origin**: ${same ? 'same (typical single-port Lenses or Vite proxy same-tab)' : 'different (SPA likely uses VITE_LENSES_API_BASE or similar)'}`,
    `- **VITE_LENSES_API_BASE**: ${d.viteLensApiBase} (no raw value; avoids leaking env in screenshots)`,
    `- **import.meta.env.DEV**: ${d.importMetaDev}`,
    `- **import.meta.env.MODE**: ${d.importMetaMode}`,
    `- **VITE_STATIC_MUSEUM**: ${d.staticMuseum}`,
    `- **navigator.userAgent**: ${d.userAgent}`,
  ]
  if (ui) lines.push(`- **last_scan_ui_message** (client):\n\n\`\`\`\n${ui}\n\`\`\``)
  lines.push('')
  lines.push('#### Ping API from the machine running Lenses (no scan work)')
  lines.push('```bash')
  lines.push(
    `curl -sS -X POST "${d.jsonApiOrigin}/api/project/${enc}/docs-health" \\\n  -H "Content-Type: application/json" \\\n  -d '{"op":"ping"}'`,
  )
  lines.push('```')
  lines.push('Expect JSON containing `"ok":true`. If this fails, the Studio button will fail too.')
  lines.push('')
  lines.push('#### Optional: ask maintainers with this block')
  lines.push('Paste the whole report above + what you see in DevTools → Network for the `docs-health` POST (status or `(failed)`).')
  return lines.join('\n')
}

/** Build the markdown report in the browser (reads `window`, `import.meta.env`). */
export function collectDocsHealthScanDiagnosticsFromBrowser(
  projectSlug: string,
  jsonApiOrigin: string,
  lastScanUiMessage?: string | null,
): string {
  const rawBase = (import.meta.env.VITE_LENSES_API_BASE as string | undefined)?.trim() ?? ''
  const pageHref = typeof window !== 'undefined' ? window.location.href : ''
  const pageOrigin = typeof window !== 'undefined' ? window.location.origin : ''
  return formatDocsHealthScanDiagnosticsReport({
    generatedAt: new Date().toISOString(),
    projectSlug,
    pageHref,
    pageOrigin,
    jsonApiOrigin,
    viteLensApiBase: rawBase ? 'set_non_empty' : 'unset',
    importMetaDev: import.meta.env.DEV,
    importMetaMode: import.meta.env.MODE,
    staticMuseum: import.meta.env.VITE_STATIC_MUSEUM === 'true',
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
    lastScanUiMessage: lastScanUiMessage ?? null,
  })
}
