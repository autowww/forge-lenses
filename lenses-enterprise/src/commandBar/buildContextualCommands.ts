import type { DoAction, FindResult } from './commandBarTypes'
import { STUDIO_VOCAB } from '../nav/studioVisibleCopy'

const NAV: FindResult[] = [
  { id: 'nav-home', kind: 'nav', label: 'Home', description: 'Workspace overview', to: '/' },
  { id: 'nav-work', kind: 'nav', label: STUDIO_VOCAB.work, description: 'Plan, boards, timeline', to: '/plan' },
  { id: 'nav-today', kind: 'nav', label: STUDIO_VOCAB.today, description: 'Immediate Work focus', to: '/plan?tab=today' },
  { id: 'nav-projects', kind: 'nav', label: STUDIO_VOCAB.projects, description: 'Repositories', to: '/projects' },
  { id: 'nav-boards', kind: 'nav', label: STUDIO_VOCAB.boards, description: 'Execution boards', to: '/board' },
  { id: 'nav-knowledge', kind: 'nav', label: STUDIO_VOCAB.knowledge, description: 'Tutorials & reference', to: '/tutorials' },
  { id: 'nav-md', kind: 'nav', label: STUDIO_VOCAB.workspaceNotes, description: 'Evidence markdown', to: '/workspace-md' },
  { id: 'nav-publish', kind: 'nav', label: STUDIO_VOCAB.publish, description: 'Sites & blog', to: '/websites' },
  { id: 'nav-search-adv', kind: 'nav', label: 'Advanced search (full results)', description: 'Filters & paging', to: '/search' },
  { id: 'nav-chat-adv', kind: 'nav', label: 'Copilot page (threads)', description: 'History & providers', to: '/chat' },
  { id: 'nav-toolset', kind: 'nav', label: STUDIO_VOCAB.toolset, description: 'Automation scripts', to: '/toolset' },
]

function matches(q: string, ...parts: (string | undefined)[]) {
  const t = q.trim().toLowerCase()
  if (!t) return true
  return parts.some((p) => (p || '').toLowerCase().includes(t))
}

export function filterNavResults(query: string): FindResult[] {
  const q = query.trim()
  if (!q) return NAV.slice(0, 8)
  return NAV.filter((n) => matches(q, n.label, n.description)).slice(0, 12)
}

function askSuggestion(id: string, label: string, askPrefill: string, description?: string): FindResult {
  return { id, kind: 'suggestion', label, description: description ?? 'Opens Ask in this command bar', askPrefill }
}

/** Contextual shortcuts for Find and Quick assist — Ask-style rows use `askPrefill` (header command flow). */
export function buildSuggestionFindResults(pathname: string, projectSlug: string | undefined): FindResult[] {
  const out: FindResult[] = []
  const p = pathname || '/'

  if (p === '/' || p === '') {
    out.push(
      askSuggestion(
        'sug-summarize-home',
        'Summarize this page',
        'Summarize the workspace overview: what needs attention first?',
        'Ask — grounded on scan',
      ),
      askSuggestion(
        'sug-today',
        'Explain blockers for Today',
        'What blockers and commitments should I look at first on Today for this workspace?',
      ),
      askSuggestion(
        'sug-readiness-gap',
        'Show missing readiness inputs',
        'What release or quality readiness inputs look missing or stale in the latest workspace scan?',
      ),
    )
  } else if (p.startsWith('/plan')) {
    out.push(
      askSuggestion(
        'sug-variance',
        'Plan vs execution variance',
        'Summarize plan-to-execution variance for the current backlog scope: what drifted from the plan and why?',
      ),
      askSuggestion(
        'sug-slip',
        'Explain what is slipping',
        'Given milestones and today signals for this scope, what work looks like it is slipping and what should we do next?',
      ),
      askSuggestion(
        'sug-readiness',
        'Readiness gaps',
        'What readiness inputs are missing for the current plan scope before release?',
      ),
      { id: 'sug-board', kind: 'suggestion', label: 'Open boards', description: 'Navigate', to: '/board' },
    )
  } else if (p.startsWith('/projects/') && projectSlug) {
    out.push(
      askSuggestion(
        'sug-health',
        'Explain project health',
        `Explain health signals for repository "${projectSlug}" in this workspace in plain language.`,
      ),
      {
        id: 'sug-evidence',
        kind: 'suggestion',
        label: 'Find related evidence',
        description: 'Workspace notes',
        to: `/workspace-md?contextProject=${encodeURIComponent(projectSlug)}`,
      },
    )
  } else if (p.startsWith('/workspace-md') || p.startsWith('/tutorials') || p.startsWith('/view/docs')) {
    out.push(
      askSuggestion(
        'sug-extract',
        'Extract decisions (Ask)',
        'List decision-style statements implied by the current knowledge context.',
      ),
      { id: 'sug-related', kind: 'suggestion', label: 'Related tutorials', description: 'Navigate', to: '/tutorials' },
    )
  } else if (p.startsWith('/websites') || p.startsWith('/blog')) {
    out.push(
      askSuggestion(
        'sug-release-ask',
        'Draft release note',
        'Draft a concise release note for publish outputs in this workspace.',
      ),
    )
  } else if (p.startsWith('/search')) {
    out.push(
      askSuggestion(
        'sug-search-summarize',
        'Summarize top themes in results',
        'From the current workspace search intent, what themes appear across hits and what should I open first?',
      ),
      askSuggestion(
        'sug-search-evidence',
        'Find evidence for this query',
        'Where should I look in workspace notes or docs for evidence related to my last search keywords?',
      ),
    )
  } else if (p.startsWith('/board')) {
    out.push(
      askSuggestion(
        'sug-board-blockers',
        'Explain blockers on boards',
        'What execution blockers or stale items should stand out on boards for this workspace?',
      ),
    )
  }

  return out
}

export function buildDoActions(pathname: string, projectSlug: string | undefined): DoAction[] {
  const p = pathname || '/'
  const actions: DoAction[] = [
    {
      id: 'do-open-today',
      label: 'Open Today',
      description: 'Navigate',
      kind: 'navigate',
      to: '/plan?tab=today',
    },
    {
      id: 'do-open-boards',
      label: 'Open boards',
      description: 'Navigate',
      kind: 'navigate',
      to: '/board',
    },
    {
      id: 'do-adv-search',
      label: 'Open advanced search',
      description: 'Full-page filters',
      kind: 'open_advanced',
      to: '/search',
    },
    {
      id: 'do-daily-brief',
      label: 'Draft daily brief (copy)',
      description: 'Preview only — copy to clipboard yourself',
      kind: 'copy_draft',
      draftTitle: 'Daily brief draft',
      draftBody: `Workspace focus — ${new Date().toISOString().slice(0, 10)}\n\n- Review Today for blockers and gates.\n- Scan project charts for drift.\n- Confirm evidence notes for decisions in flight.\n\n(Fill in specifics after you review Studio.)`,
    },
  ]

  if (projectSlug) {
    actions.unshift({
      id: 'do-open-project',
      label: `Open project: ${projectSlug}`,
      kind: 'navigate',
      to: `/projects/${encodeURIComponent(projectSlug)}`,
    })
  }

  if (p.startsWith('/websites') || p.startsWith('/blog')) {
    actions.unshift({
      id: 'do-release-note',
      label: 'Draft stakeholder update (copy)',
      kind: 'copy_draft',
      draftTitle: 'Stakeholder update draft',
      draftBody: `Release / publish update\n\nWhat shipped:\n- \n\nRisks:\n- \n\nUse header Ask for grounded wording from your workspace.`,
    })
  }

  return actions
}
