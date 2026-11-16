import { Link } from 'react-router-dom'
import type { WorkspaceChild } from '../../api/workspace'
import { useWorkspaceOptional } from '../../context/WorkspaceContext'
import './docs-health-session-layout.css'

function initialsFromSlug(slug: string): string {
  const parts = slug.split(/[-_/]+/).filter(Boolean)
  if (parts.length >= 2) {
    const a = parts[0][0]
    const b = parts[parts.length - 1][0]
    if (a && b) return (a + b).toUpperCase()
  }
  const t = slug.replace(/[^a-zA-Z0-9]/g, '')
  return t.slice(0, 2).toUpperCase() || 'P'
}

type Props = {
  projectSlug: string
  encProject: string
}

/**
 * Prominent workspace-repository identity for Docs Health flows (folder name + optional git hint).
 */
export function DocsHealthProjectContextBanner({ projectSlug, encProject }: Props) {
  const ws = useWorkspaceOptional()
  const children = ws?.state?.children
  const child: WorkspaceChild | undefined = Array.isArray(children)
    ? children.find((c) => String(c.name) === projectSlug)
    : undefined
  const inWorkspace = Boolean(child)
  const isGit = child?.is_git === true
  const dirty =
    isGit && child?.git && typeof child.git === 'object' && (child.git as { dirty?: boolean }).dirty === true

  return (
    <section className="le-dh-project-context le-dh-project-context--compact" aria-label="Active project">
      <div className="le-dh-project-context__avatar" aria-hidden>
        {initialsFromSlug(projectSlug)}
      </div>
      <div className="le-dh-project-context__body">
        <div className="le-dh-project-context__title-row">
          <h2 className="le-dh-project-context__name">{projectSlug}</h2>
          {inWorkspace ? (
            <span className="le-dh-project-context__badge le-dh-project-context__badge--ok">In workspace</span>
          ) : ws?.loading ? (
            <span className="le-dh-project-context__badge">Loading workspace…</span>
          ) : (
            <span className="le-dh-project-context__badge le-dh-project-context__badge--warn">
              Not in workspace scan
            </span>
          )}
          {isGit ? (
            <span className="le-dh-project-context__badge">{dirty ? 'Git · uncommitted' : 'Git'}</span>
          ) : inWorkspace ? (
            <span className="le-dh-project-context__badge">Folder</span>
          ) : null}
        </div>
        <p className="le-dh-project-context__meta">Docs Health data is scoped to this checkout.</p>
        <p className="le-dh-project-context__links">
          <Link className="le-btn le-btn--small le-btn--ghost" to={`/projects/${encProject}`}>
            Dashboard
          </Link>
          <Link className="le-btn le-btn--small le-btn--ghost" to={`/projects/${encProject}/docs-health`}>
            Docs health
          </Link>
          <Link className="le-btn le-btn--small le-btn--ghost" to={`/workspace-md?contextProject=${encProject}`}>
            Workspace MD
          </Link>
        </p>
      </div>
    </section>
  )
}
