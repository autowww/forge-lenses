import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type {
  DocsHealthCluster,
  DocsHealthFinding,
  DocsHealthProjectPayload,
  DocsHealthSessionPayload,
} from '../../api/docsHealth'
import { ForgeKeyValueGrid, type ForgeKeyValueItem } from '../../forgesdlc-kitchensink'
import { stripInlineMarkdownForBrief } from '../../lib/docsHealthBriefText'
import './docs-health-session-layout.css'

export type DocsHealthSessionSummaryBriefProps = {
  session: DocsHealthSessionPayload | null
  projectSnapshot: DocsHealthProjectPayload | null
  /** Cluster row from latest scan (matched to session), or session cluster stub. */
  cluster: DocsHealthCluster | DocsHealthSessionPayload['cluster'] | null | undefined
  /** Primary finding for narrative fields. */
  finding: DocsHealthFinding | null | undefined
  projectSlug: string
  encProject: string
}

function fmtWhen(iso?: string) {
  if (!iso) return 'Not available'
  try {
    const d = new Date(iso)
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return iso
  }
}

function humanizeStatus(st?: string) {
  const s = String(st || '').toLowerCase()
  if (!s) return 'Not available'
  return s.replace(/_/g, ' ')
}

function verificationLine(session: DocsHealthSessionPayload | null): string {
  if (!session) return 'Not available'
  const st = String(session.status || '').toLowerCase()
  if (st === 'completed') {
    const ok = session.completion_summary?.verification_pipeline_ok
    if (ok === true) return 'Passed'
    if (ok === false) return 'Issues reported'
    return 'Completed (verification not summarized)'
  }
  if (st === 'cancelled') return 'Skipped'
  if (st === 'failed') return 'Failed'
  return 'Not run'
}

function collectAffectedPaths(
  session: DocsHealthSessionPayload | null,
  finding: DocsHealthFinding | null | undefined,
): string[] {
  const scope = session?.remediation_scope
  const fromScope = scope?.distinct_affected_paths ?? []
  const fromFinding = [...(finding?.affected_paths ?? []), ...(finding?.affected_files ?? [])]
  const samples = scope?.sample_findings?.flatMap((s) => s.affected_paths ?? []) ?? []
  return Array.from(new Set([...fromScope, ...fromFinding, ...samples].filter(Boolean) as string[]))
}

function BriefSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="le-dh-brief__section">
      <h3 className="le-dh-brief__h">{title}</h3>
      <div className="le-dh-brief__section-body">{children}</div>
    </section>
  )
}

function BriefParagraph({ text, emptyLabel = 'Not available' }: { text?: string | null; emptyLabel?: string }) {
  const raw = text?.trim()
  if (!raw) return <p className="le-dh-brief__empty">{emptyLabel}</p>
  const plain = stripInlineMarkdownForBrief(raw)
  if (!plain) return <p className="le-dh-brief__empty">{emptyLabel}</p>
  return <p className="le-dh-brief__prose">{plain}</p>
}

/**
 * Executive Summary tab: structured brief (no raw agent blob, no markdown markers).
 */
export function DocsHealthSessionSummaryBrief({
  session,
  projectSnapshot,
  cluster,
  finding,
  projectSlug,
  encProject,
}: DocsHealthSessionSummaryBriefProps) {
  const scope = session?.remediation_scope
  const rc = projectSnapshot?.run_compare

  const clusterSuggested =
    cluster && 'suggested_next' in cluster && cluster.suggested_next ? cluster.suggested_next : null

  const issueSummary =
    finding?.plain_language_summary ||
    finding?.summary ||
    finding?.title ||
    (cluster && 'label' in cluster && cluster.label ? cluster.label : null) ||
    session?.display_name

  const whyMatters = finding?.why_it_matters

  const recommendedOutcome = clusterSuggested || scope?.agent_intent || null

  const planNext =
    scope?.note ||
    (clusterSuggested && scope?.agent_intent && clusterSuggested !== scope.agent_intent ? scope.agent_intent : null)

  const paths = collectAffectedPaths(session, finding)

  const clusterGain =
    cluster && 'expected_score_gain_if_cleared' in cluster && typeof cluster.expected_score_gain_if_cleared === 'number'
      ? cluster.expected_score_gain_if_cleared
      : null
  const findingImpact =
    typeof finding?.expected_score_impact === 'number'
      ? finding.expected_score_impact
      : typeof finding?.score_impact === 'number'
        ? finding.score_impact
        : null

  const knowledge = session?.knowledge_links && Object.keys(session.knowledge_links).length > 0 ? session.knowledge_links : null
  const artifactLinks = session?.completion_summary?.artifact_links
  const hasArtifactLinks = artifactLinks && Object.keys(artifactLinks).length > 0

  const workItem = projectSnapshot?.work_items?.find((w) => w.finding_id && w.finding_id === finding?.id)

  const applyStepRuns = (session?.step_metrics ?? []).filter((m) => String(m.step) === 'apply').length
  const applyPipelineLabel = (() => {
    if (applyStepRuns > 0) return 'Changes applied'
    const st = String(session?.status || '').toLowerCase()
    if (st === 'cancelled') return 'No changes applied'
    return 'Not run'
  })()

  const category =
    finding?.category || (cluster && 'primary_category' in cluster ? cluster.primary_category : undefined)
  const severity =
    finding?.severity || (cluster && 'primary_severity' in cluster ? cluster.primary_severity : undefined)
  const scoreArea = finding?.score_area
  const scopeLabel = finding?.scope

  const runContextItems: ForgeKeyValueItem[] = [
    { label: 'Repository', value: <strong>{projectSlug}</strong> },
    {
      label: 'Cluster',
      value: cluster?.label || session?.cluster?.label || 'Not available',
    },
    {
      label: 'Category',
      value: category || 'Not available',
    },
    {
      label: 'Severity',
      value: severity || 'Not available',
    },
    {
      label: 'Work item',
      value: workItem?.title || 'Not available',
      title: workItem?.status ? `Status: ${workItem.status}` : undefined,
    },
    {
      label: 'Scope (finding)',
      value: scopeLabel || 'Not available',
    },
    {
      label: 'Score area',
      value: scoreArea || 'Not available',
    },
    {
      label: 'Session status',
      value: humanizeStatus(session?.status),
    },
    {
      label: 'Started',
      value: fmtWhen(session?.started_at),
    },
    {
      label: 'Last updated',
      value: fmtWhen(session?.updated_at),
    },
    {
      label: 'Docs scan run',
      value: session?.run_id ? (
        <code className="le-dh-run-id" title={session.run_id}>
          {String(session.run_id).slice(0, 16)}…
        </code>
      ) : (
        'Not available'
      ),
      title: session?.run_id,
    },
    {
      label: 'Baseline score (session)',
      value:
        session?.baseline_score != null && session.baseline_score !== undefined
          ? String(session.baseline_score)
          : 'Not available',
    },
    {
      label: 'Prior run comparison',
      value:
        rc && (rc.score_delta != null || rc.finding_count_delta != null) ? (
          <span>
            Score change{' '}
            {rc.score_delta != null ? (
              <strong>
                {rc.score_delta >= 0 ? '+' : ''}
                {rc.score_delta}
              </strong>
            ) : (
              'Not available'
            )}
            {', findings '}
            {rc.finding_count_delta != null ? (
              <strong>
                {rc.finding_count_delta >= 0 ? '+' : ''}
                {rc.finding_count_delta}
              </strong>
            ) : (
              'Not available'
            )}{' '}
            vs prior scan
          </span>
        ) : (
          'Not available'
        ),
    },
    {
      label: 'Verification',
      value: verificationLine(session),
    },
    {
      label: 'Apply (pipeline)',
      value: applyPipelineLabel,
    },
  ]

  const hasScoreHighlights = clusterGain != null || findingImpact != null

  return (
    <div className="le-dh-brief">
      <p className="forge-support le-dh-brief__intro">
        Executive brief for this remediation run. Model routing and token usage are not shown here.
      </p>

      {hasScoreHighlights ? (
        <div className="le-dh-brief__highlights" aria-label="Score impact">
          {clusterGain != null ? (
            <div className="le-dh-brief__highlight le-dh-brief__highlight--gain">
              <div className="le-dh-brief__highlight-label">Expected score gain if cluster cleared</div>
              <div className="le-dh-brief__highlight-value" title="From cluster.expected_score_gain_if_cleared">
                +{clusterGain.toFixed(1)} pts
              </div>
            </div>
          ) : null}
          {findingImpact != null ? (
            <div className="le-dh-brief__highlight le-dh-brief__highlight--gain">
              <div className="le-dh-brief__highlight-label">Finding score impact (estimate)</div>
              <div className="le-dh-brief__highlight-value" title="From finding score fields">
                {findingImpact >= 0 ? '+' : ''}
                {findingImpact.toFixed(1)} pts
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        <p className="le-dh-brief__empty le-dh-brief__highlights-fallback">
          No score gain estimate on this run yet (latest scan may not include cluster uplift).
        </p>
      )}

      <BriefSection title="Affected files">
        {paths.length > 0 ? (
          <ul className="le-dh-brief__file-list le-dh-brief__file-list--dense">
            {paths.map((p) => (
              <li key={p}>
                <code className="le-dh-brief__path">{p}</code>
              </li>
            ))}
          </ul>
        ) : (
          <p className="le-dh-brief__empty">No paths listed for this run yet.</p>
        )}
      </BriefSection>

      <BriefSection title="Issue summary">
        <BriefParagraph text={issueSummary} emptyLabel="Not available" />
      </BriefSection>

      <BriefSection title="Why it matters">
        <BriefParagraph text={whyMatters} emptyLabel="Not specified" />
      </BriefSection>

      <BriefSection title="Recommended outcome">
        <BriefParagraph text={recommendedOutcome} emptyLabel="Not available" />
      </BriefSection>

      <BriefSection title="Plan / next steps">
        {planNext ? (
          <BriefParagraph text={planNext} />
        ) : (
          <BriefParagraph
            text={null}
            emptyLabel="Use the workflow stages to gather context, draft changes, review, apply to a branch, then verify."
          />
        )}
      </BriefSection>

      <BriefSection title="Expected score gain">
        <ul className="le-dh-brief__metric-list">
          <li>
            <span className="le-dh-brief__metric-label">Cluster (if cleared): </span>
            {clusterGain != null ? (
              <strong>+{clusterGain.toFixed(1)} pts</strong>
            ) : (
              <span className="le-dh-brief__empty-inline">Not available</span>
            )}
          </li>
          <li>
            <span className="le-dh-brief__metric-label">Finding impact: </span>
            {findingImpact != null ? (
              <strong>
                {findingImpact >= 0 ? '+' : ''}
                {findingImpact.toFixed(1)} pts
              </strong>
            ) : (
              <span className="le-dh-brief__empty-inline">Not available</span>
            )}
          </li>
          <li>
            <span className="le-dh-brief__metric-label">Header score delta (session): </span>
            {session?.header_stats?.score_delta != null ? (
              <strong>
                {session.header_stats.score_delta >= 0 ? '+' : ''}
                {session.header_stats.score_delta}
              </strong>
            ) : (
              <span className="le-dh-brief__empty-inline">Not run</span>
            )}
          </li>
        </ul>
      </BriefSection>

      <BriefSection title="Related knowledge / evidence">
        {knowledge || hasArtifactLinks ? (
          <ul className="le-dh-brief__link-list">
            {knowledge
              ? Object.entries(knowledge).map(([label, href]) => (
                  <li key={label}>
                    <a href={href} className="le-dh-brief__link" rel="noreferrer noopener">
                      {label}
                    </a>
                  </li>
                ))
              : null}
            {hasArtifactLinks && artifactLinks
              ? Object.entries(artifactLinks).map(([label, href]) => (
                  <li key={`artifact-${label}`}>
                    <a href={href} className="le-dh-brief__link" rel="noreferrer noopener">
                      {label}
                    </a>
                  </li>
                ))
              : null}
          </ul>
        ) : scope?.repo_md_context?.hits?.length ? (
          <ul className="le-dh-brief__link-list">
            {scope.repo_md_context.hits.slice(0, 8).map((h, i) => (
              <li key={`${h.path}-${i}`}>
                <span className="le-dh-brief__evidence-path">
                  <code>{h.path}</code>
                  {h.excerpt ? <span className="le-muted"> — {stripInlineMarkdownForBrief(h.excerpt).slice(0, 120)}</span> : null}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="le-dh-brief__empty">No knowledge links or ranked repo excerpts on this session yet.</p>
        )}
        {scope?.repo_md_context?.note ? (
          <p className="forge-support le-dh-brief__note">{stripInlineMarkdownForBrief(scope.repo_md_context.note)}</p>
        ) : null}
      </BriefSection>

      <BriefSection title="Run context">
        <ForgeKeyValueGrid items={runContextItems} aria-label="Run context" dense />
        <p className="forge-support le-dh-brief__rail-hint" style={{ marginTop: '0.75rem' }}>
          <Link to={`/projects/${encProject}/docs-health`}>Project Docs health</Link>
          {' · '}
          <Link to={`/projects/${encProject}`}>Project dashboard</Link>
          {' · '}
          Full scope and live telemetry stay in the side rail.
        </p>
      </BriefSection>
    </div>
  )
}
