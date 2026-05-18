/** Maps `/api/…` paths to static JSON files under `/studio/museum-data/` (ks.forgesdlc.com museum build). */

export function museumFileForApiPath(apiPath: string): string {
  const pathOnly = apiPath.split('?')[0]

  if (pathOnly === '/api/workspace-state') return 'workspace-state.json'
  if (pathOnly === '/api/chart-data/overview') return 'chart-data-overview.json'
  if (pathOnly === '/api/delivery/enabled') return 'delivery-enabled.json'
  if (pathOnly === '/api/delivery/overview') return 'delivery-overview.json'
  if (pathOnly === '/api/repo-workflow/enabled') return 'repo-workflow-enabled.json'
  if (pathOnly === '/api/repo-workflow/overview') return 'repo-workflow-overview.json'
  if (pathOnly === '/api/cicd/enabled') return 'cicd-enabled.json'
  if (pathOnly === '/api/cicd/control-tower') return 'cicd-control-tower.json'
  if (pathOnly === '/api/quality/enabled') return 'quality-enabled.json'
  if (pathOnly === '/api/quality/overview') return 'quality-overview.json'
  if (pathOnly === '/api/devsecops/enabled') return 'devsecops-enabled.json'
  if (pathOnly === '/api/devsecops/overview') return 'devsecops-overview.json'
  if (pathOnly === '/api/cross-team-release/enabled') return 'cross-team-release-enabled.json'
  if (pathOnly === '/api/cross-team-release/overview') return 'cross-team-release-overview.json'
  if (pathOnly === '/api/ops-delivery/enabled') return 'ops-delivery-enabled.json'
  if (pathOnly === '/api/ops-delivery/overview') return 'ops-delivery-overview.json'
  if (pathOnly === '/api/orchestration/enabled') return 'orchestration-enabled.json'
  if (pathOnly.startsWith('/api/orchestration/portfolio-context')) return 'portfolio-context.json'
  if (pathOnly === '/api/orchestration/status') return 'orchestration-status.json'
  if (pathOnly === '/api/orchestration/trace') return 'orchestration-trace.json'
  if (pathOnly === '/api/orchestration/entity') return 'orchestration-entity.json'
  if (pathOnly === '/api/bridge/enabled') return 'bridge-enabled.json'
  if (pathOnly === '/api/bridge/registry') return 'bridge-registry.json'
  if (pathOnly.startsWith('/api/bridge/trace')) return 'bridge-trace.json'
  if (pathOnly === '/api/handoffs/enabled') return 'handoffs-enabled.json'
  if (pathOnly.startsWith('/api/handoffs/by-work-unit')) return 'handoffs-by-work-unit.json'
  if (pathOnly === '/api/outcomes/enabled') return 'outcomes-enabled.json'
  if (pathOnly.startsWith('/api/outcomes/by-work-unit')) return 'outcomes-by-work-unit.json'
  if (pathOnly === '/api/auth/status') return 'auth-status.json'
  if (pathOnly === '/api/sdlc-copilot/enabled') return 'sdlc-copilot-enabled.json'
  if (pathOnly === '/api/connectors/health') return 'connectors-health.json'
  if (pathOnly === '/api/governance/audit') return 'governance-audit.json'
  if (pathOnly === '/api/governance/scopes') return 'governance-scopes.json'
  if (pathOnly === '/api/auth/oidc/status') return 'auth-oidc-status.json'
  if (pathOnly === '/api/llm/providers') return 'llm-providers.json'
  if (pathOnly === '/api/llm/settings') return 'llm-settings.json'
  if (pathOnly === '/api/llm/usage') return 'llm-usage.json'
  if (pathOnly === '/api/llm/diagnostics') return 'llm-diagnostics.json'
  if (pathOnly === '/api/llm/ollama-status') return 'ollama-status.json'
  if (pathOnly === '/api/llm/model-catalog-notifications') return 'llm-model-catalog-notifications.json'
  if (pathOnly === '/api/llm/routing-preview' || pathOnly === '/api/llm/routing-preview-draft') {
    return 'routing-preview.json'
  }
  if (pathOnly === '/api/agent-runtime/overview') return 'agent-runtime-overview.json'
  if (pathOnly === '/api/blueprints/wizard/enabled') return 'blueprints-wizard-enabled.json'
  if (pathOnly === '/api/blueprints/wizard/sessions') return 'blueprints-wizard-sessions.json'
  if (
    pathOnly.startsWith('/api/blueprints/wizard/session/') &&
    pathOnly !== '/api/blueprints/wizard/session'
  ) {
    return 'blueprints-wizard-session.json'
  }
  if (pathOnly.startsWith('/api/search')) return 'search.json'
  if (pathOnly.startsWith('/api/plan-spine')) return 'plan-spine.json'
  if (pathOnly.startsWith('/api/roadmaps-matrix')) return 'roadmaps-matrix.json'
  if (pathOnly.startsWith('/api/forge-work-model')) return 'forge-work-model.json'
  if (pathOnly.startsWith('/api/today-charge')) return 'today-charge.json'
  if (pathOnly.startsWith('/api/story-hub')) return 'story-hub.json'
  if (pathOnly === '/api/wbs-management') return 'wbs-management.json'
  if (pathOnly.startsWith('/api/timeline-context')) return 'timeline-context.json'
  if (pathOnly === '/api/tutorials-index') return 'tutorials-index.json'
  if (pathOnly === '/api/docs-health/summary') return 'docs-health-summary.json'
  if (pathOnly === '/api/docs-health/work-items') return 'docs-health-work-items.json'
  if (pathOnly === '/api/docs-health/live-sessions') return 'docs-health-live-sessions.json'
  if (pathOnly === '/api/forgesdlc-blog') return 'forgesdlc-blog.json'
  if (pathOnly.startsWith('/api/roadmap-section')) return 'roadmap-section.json'
  if (pathOnly.startsWith('/api/wbs-file')) return 'wbs-file.json'
  if (pathOnly.startsWith('/api/workspace-md-file')) return 'workspace-md-file.json'
  if (pathOnly === '/api/workspace-md-index') return 'workspace-md-index.json'
  if (pathOnly.startsWith('/api/sticker-board-registry')) {
    return 'sticker-board-registry.json'
  }
  if (pathOnly.startsWith('/api/sticker-board')) return 'sticker-board.json'
  if (/\/stats$/.test(pathOnly) && pathOnly.startsWith('/api/project/')) {
    return 'project-stats.json'
  }
  if (/\/context$/.test(pathOnly) && pathOnly.startsWith('/api/project/')) {
    return 'project-context.json'
  }
  if (/\/chart-data$/.test(pathOnly) && pathOnly.startsWith('/api/project/')) {
    return 'project-chart-data.json'
  }
  if (/\/repo-workflow$/.test(pathOnly) && pathOnly.startsWith('/api/project/')) {
    return 'project-repo-workflow.json'
  }
  if (/\/quality$/.test(pathOnly) && pathOnly.startsWith('/api/project/')) {
    return 'project-quality.json'
  }
  if (/\/devsecops$/.test(pathOnly) && pathOnly.startsWith('/api/project/')) {
    return 'project-devsecops.json'
  }
  if (/\/docs-health$/.test(pathOnly) && pathOnly.startsWith('/api/project/')) {
    return 'docs-health-project.json'
  }
  if (/\/forge-runs$/.test(pathOnly) && pathOnly.startsWith('/api/project/')) {
    return 'project-forge-runs.json'
  }
  return 'empty.json'
}

/** URL under the Studio base (`import.meta.env.BASE_URL`) for a museum JSON file. */
export function museumDataUrl(file: string): string {
  const base = import.meta.env.BASE_URL || '/'
  const root = base.endsWith('/') ? base : `${base}/`
  return `${root}museum-data/${file}`.replace(/([^:])\/{2,}/g, '$1/')
}
