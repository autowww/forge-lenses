/**
 * Extra Copilot grounding text for Docs Health Studio screens so page_context_summary
 * matches what the operator sees (scores, findings, session state).
 */
import type { DocsHealthProjectPayload, DocsHealthSessionPayload } from '../api/docsHealth'

function asRecord(v: unknown): Record<string, unknown> | null {
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null
}

function pickTopFindings(findings: unknown, max = 6): string[] {
  if (!Array.isArray(findings)) return []
  const out: string[] = []
  for (const f of findings) {
    const row = asRecord(f)
    if (!row) continue
    const title = String(row.title || row.rule_code || row.id || 'finding').trim()
    const sev = String(row.severity || '').trim()
    const rule = String(row.rule_code || '').trim()
    const bit = [sev && `sev=${sev}`, rule && `rule=${rule}`, title].filter(Boolean).join(' · ')
    if (bit) out.push(bit)
    if (out.length >= max) break
  }
  return out
}

function pickClusters(clusters: unknown, max = 4): string[] {
  if (!Array.isArray(clusters)) return []
  const out: string[] = []
  for (const c of clusters) {
    const row = asRecord(c)
    if (!row) continue
    const label = String(row.label || row.id || 'cluster').trim()
    const sev = String(row.primary_severity || '').trim()
    const cat = String(row.primary_category || '').trim()
    const bit = [label, cat && `cat=${cat}`, sev && `sev=${sev}`].filter(Boolean).join(' · ')
    if (bit) out.push(bit)
    if (out.length >= max) break
  }
  return out
}

/** Latest scan block on project docs-health / master pages. */
export function formatDocsHealthProjectCopilotContext(
  project: string,
  pageVariant: 'summary' | 'master',
  data: DocsHealthProjectPayload | null,
): string {
  const lines: string[] = []
  const head =
    pageVariant === 'master'
      ? `This screen is **Docs health (KTLO master)** for repo \`${project}\`: cluster-level waivers, closure posture, and remediation planning.`
      : `This screen is **Docs health** (latest scan, findings list, clusters, work items) for repo \`${project}\`.`
  lines.push(head)

  if (!data) {
    lines.push('Data: not loaded yet — explain scan vs inventory actions once data appears.')
    return lines.join('\n')
  }

  const lr = asRecord(data.latest_run)
  if (lr) {
    const fc = typeof lr.finding_count === 'number' ? lr.finding_count : undefined
    const findings = lr.findings
    const clusters = lr.clusters
    const scoreVal = asRecord(lr.score)?.value
    const scoreNum = typeof scoreVal === 'number' ? scoreVal : undefined
    const bits = [
      fc != null ? `open findings (this run): ${fc}` : null,
      scoreNum != null ? `score: ${scoreNum}` : null,
    ].filter(Boolean)
    if (bits.length) lines.push(`Latest scan: ${bits.join('; ')}.`)
    const topF = pickTopFindings(findings, 8)
    if (topF.length) lines.push(`Top findings: ${topF.join(' | ')}`)
    const topC = pickClusters(clusters, 5)
    if (topC.length) lines.push(`Clusters: ${topC.join(' | ')}`)
  } else {
    lines.push('No latest scan loaded — operator may need to run inventory/scan from this page.')
  }

  const inv = data.inventory_summary
  if (inv && typeof inv.document_count === 'number') {
    lines.push(`Inventory: ${inv.document_count} markdown/docs indexed for rules (partial=${Boolean(inv.partial)}).`)
  }

  const cs = data.closure_status
  if (cs && typeof cs === 'object') {
    const oc = typeof cs.open_critical_or_major === 'number' ? cs.open_critical_or_major : undefined
    const wi = typeof cs.open_docs_work_items === 'number' ? cs.open_docs_work_items : undefined
    if (oc != null || wi != null) {
      lines.push(
        `Closure: open critical/major=${oc ?? '—'}, open docs work items=${wi ?? '—'}.`,
      )
    }
  }

  const wi = data.work_items
  if (Array.isArray(wi) && wi.length) {
    lines.push(`Work items in view: ${wi.length} (tickets / manual follow-ups tied to findings).`)
  }

  lines.push(
    'When the user asks what matters **on this page**, prioritize: docs contract + inventory, latest scan score, severity mix, top findings/clusters, waivers/suppressions (master), and next safe remediation steps — not generic SDLC handbook essays.',
  )
  return lines.join('\n')
}

/** Active remediation session timeline. */
export function formatDocsHealthSessionCopilotContext(
  project: string,
  sessionId: string,
  session: DocsHealthSessionPayload | null,
): string {
  const lines: string[] = []
  lines.push(
    `PRIMARY SCOPE: All answers must treat **${project}** as the active workspace repository folder for this session (not other sibling repos unless the user explicitly names them).`,
  )
  lines.push(
    `This screen is **Docs health remediation session** \`${sessionId}\` for repo \`${project}\`: timeline events, token usage for this session, verification, and optional patch proposal.`,
  )
  if (!session) {
    lines.push('Session payload not loaded.')
    return lines.join('\n')
  }
  const st = String(session.status || '').trim()
  if (st) lines.push(`Status: ${st}.`)
  const cl = session.cluster?.label || session.cluster?.id
  if (cl) lines.push(`Cluster focus: ${cl}.`)
  const rs = session.remediation_scope
  if (rs && typeof rs.finding_count === 'number') {
    lines.push(
      `Remediation scope: ${rs.finding_count} documentation gap(s) in this cluster` +
        (rs.distinct_path_count != null ? ` across ${rs.distinct_path_count} path(s).` : '.'),
    )
    if (rs.agent_intent) lines.push(`Agent intent: ${rs.agent_intent}`)
    const rmd = rs.repo_md_context
    const hits = rmd?.hits
    const nhit = hits?.length
    if (typeof nhit === 'number' && nhit > 0 && hits) {
      const paths = hits.map((h) => h.path).filter(Boolean).slice(0, 6)
      lines.push(
        `Repository Markdown context: ${nhit} excerpt(s) from project .md files (keyword search for this finding set).` +
          (paths.length ? ` Examples: ${paths.join(', ')}.` : ''),
      )
    }
  }
  const hs = session.header_stats
  if (hs) {
    const tt = typeof hs.total_tokens === 'number' ? hs.total_tokens : undefined
    const pt = typeof hs.prompt_tokens === 'number' ? hs.prompt_tokens : undefined
    const ct = typeof hs.completion_tokens === 'number' ? hs.completion_tokens : undefined
    const tok =
      tt != null
        ? `session tokens (header): total=${tt}` +
          (pt != null && ct != null ? ` (prompt ${pt} + completion ${ct})` : '')
        : ''
    if (tok) lines.push(tok)
    if (hs.active_model) lines.push(`Active model: ${hs.active_model}.`)
  }
  const evs = session.events
  if (Array.isArray(evs) && evs.length) {
    const tail = evs.slice(-6)
    const titles = tail
      .map((e) => {
        const o = e as { title?: string; type?: string }
        return String(o.title || o.type || '').trim()
      })
      .filter(Boolean)
    if (titles.length) lines.push(`Recent timeline: ${titles.join(' → ')}`)
  }
  lines.push(
    'For “what is important here”, emphasize session status, cluster being fixed, last verification result, token/session cost, and the next operator action (reply / choice / confirm) — not unrelated handbook pages.',
  )
  return lines.join('\n')
}
