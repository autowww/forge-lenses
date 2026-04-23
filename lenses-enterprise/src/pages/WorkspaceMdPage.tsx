import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useWorkspace } from '../context/WorkspaceContext'
import { apiGetJson } from '../api/http'
import type { WorkspaceMdIndexEntry } from '../api/workspaceMdIndex'
import { getWorkspaceMdIndex } from '../api/workspaceMdIndex'
import { MarkdownBody } from '../components/MarkdownBody'
import { WorkspaceMdHub } from '../components/workspaceMd/WorkspaceMdHub'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { TraceabilityLaunchButton } from '../components/traceability'
import { PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import {
  clearWorkspaceMdRecent,
  isWorkspaceMdPinned,
  readWorkspaceMdPinned,
  readWorkspaceMdRecent,
  recordWorkspaceMdRecent,
  toggleWorkspaceMdPin,
} from '../lib/workspaceMdClientStorage'
import { DEMO_BRIDGE_DEMAND_ID, DEMO_ORCHESTRATION_STORY_ID } from '../constants/demoOrchestration'
import { chargeMdCandidates } from '../lib/copilotPageEvidence'
import { EVIDENCE_IA, PROJECT_OBJECT_HOME, STUDIO_GLOSSARY, STUDIO_IA, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

function hubQueryString(contextProjectName: string): string {
  if (!contextProjectName.trim()) return ''
  return `?contextProject=${encodeURIComponent(contextProjectName.trim())}`
}

export function WorkspaceMdPage() {
  const { state: wsState } = useWorkspace()
  const [sp, setSp] = useSearchParams()
  const p = sp.get('p') || ''
  const contextProjectName = (sp.get('contextProject') || '').trim()
  const projectDashboardHref = contextProjectName
    ? `/projects/${encodeURIComponent(contextProjectName)}`
    : null

  const [text, setText] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const [indexFiles, setIndexFiles] = useState<WorkspaceMdIndexEntry[]>([])
  const [indexLoading, setIndexLoading] = useState(true)
  const [indexErr, setIndexErr] = useState<string | null>(null)
  const [indexTruncated, setIndexTruncated] = useState(false)

  const [pinned, setPinned] = useState(readWorkspaceMdPinned)
  const [recent, setRecent] = useState(readWorkspaceMdRecent)

  const hasPath = p.trim().length > 0
  const pinnedNow = hasPath && isWorkspaceMdPinned(p.trim())

  const copilotRelatedMd = useMemo(() => {
    const paths = new Set<string>()
    const cur = p.trim()
    if (cur) paths.add(cur)
    for (const x of pinned) {
      if (paths.size >= 8) break
      const t = x.trim()
      if (t) paths.add(t)
    }
    for (const x of recent) {
      if (paths.size >= 8) break
      const t = x.trim()
      if (t) paths.add(t)
    }
    for (const x of chargeMdCandidates(contextProjectName || undefined)) {
      if (paths.size >= 8) break
      if (x.trim()) paths.add(x.trim())
    }
    return [...paths]
  }, [p, pinned, recent, contextProjectName])

  const copilotPageSummary = useMemo(() => {
    const parts = ['Forge Studio · Knowledge · workspace markdown']
    if (contextProjectName) parts.push(`context project: ${contextProjectName}`)
    const op = p.trim()
    parts.push(op ? `open file: ${op}` : 'hub (no file open)')
    return parts.join(' · ')
  }, [contextProjectName, p])

  useLensesCopilotPage({
    route: 'knowledge',
    projectSlug: contextProjectName || undefined,
    defaultQuery: hasPath ? undefined : EVIDENCE_IA.copilotEvidenceExtract,
    pageContextSummary: copilotPageSummary,
    relatedMdRelPaths: copilotRelatedMd.length ? copilotRelatedMd : undefined,
  })

  useEffect(() => {
    let cancel = false
    setIndexLoading(true)
    void getWorkspaceMdIndex()
      .then((r) => {
        if (cancel) return
        if (r.ok && Array.isArray(r.files)) {
          setIndexFiles(r.files)
          setIndexTruncated(!!r.truncated)
          setIndexErr(null)
        } else {
          setIndexFiles([])
          setIndexErr('Unexpected index response from server.')
        }
      })
      .catch((e) => {
        if (!cancel) {
          setIndexFiles([])
          setIndexErr(e instanceof Error ? e.message : String(e))
        }
      })
      .finally(() => {
        if (!cancel) setIndexLoading(false)
      })
    return () => {
      cancel = true
    }
  }, [])

  useEffect(() => {
    if (!p.trim()) {
      /* eslint-disable react-hooks/set-state-in-effect -- clear viewer when path param is empty */
      setText(null)
      setErr(null)
      setLoading(false)
      /* eslint-enable react-hooks/set-state-in-effect */
      return
    }
    setLoading(true)
    setErr(null)
    apiGetJson<{ ok?: boolean; text?: string }>(`/api/workspace-md-file?p=${encodeURIComponent(p)}`)
      .then((r) => {
        if (r.ok && r.text != null) {
          setText(r.text)
          setErr(null)
          recordWorkspaceMdRecent(p.trim())
          setRecent(readWorkspaceMdRecent())
        } else {
          setText(null)
          setErr('Not found or not allowlisted for this workspace notes path.')
        }
      })
      .catch((e) => {
        setText(null)
        setErr(e instanceof Error ? e.message : String(e))
      })
      .finally(() => setLoading(false))
  }, [p])

  const refreshPinned = () => setPinned([...readWorkspaceMdPinned()])

  const freshness =
    wsState?.resolved_at != null ? (
      <>
        Last scan:{' '}
        <time dateTime={wsState.resolved_at}>
          {new Date(wsState.resolved_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
        </time>
      </>
    ) : (
      'Last scan: not recorded'
    )

  return (
    <>
      <PageHeader
        title={STUDIO_VOCAB.workspaceNotes}
        purpose={
          hasPath ? STUDIO_GLOSSARY.workspaceNotes.short : 'Indexed evidence markdown — pick a file or search the workspace.'
        }
        freshness={freshness}
        statusChips={[{ label: 'Evidence', tone: 'muted' }]}
        primaryAction={
          hasPath ? (
            <Link className="le-btn le-btn--primary" to={`/workspace-md${hubQueryString(contextProjectName)}`}>
              Evidence home
            </Link>
          ) : (
            <Link className="le-btn le-btn--primary" to="/search">
              {STUDIO_VOCAB.search}
            </Link>
          )
        }
        secondaryMenuItems={[
          { key: 'tutorials', label: STUDIO_VOCAB.tutorials, to: '/tutorials' },
          { key: 'search', label: STUDIO_VOCAB.search, to: '/search' },
        ]}
      />

      {!hasPath ? (
        <TechnicalDetails summary="Evidence vs reference" defaultOpen={false}>
          <p className="forge-support">{STUDIO_IA.workspaceMdEvidenceVersusRef}</p>
        </TechnicalDetails>
      ) : null}

      {contextProjectName && projectDashboardHref ? (
        <div
          className="le-plan-scope"
          style={{ marginBottom: '1rem', padding: '0.55rem 0.75rem' }}
          role="status"
        >
          <p className="forge-support" style={{ margin: 0, lineHeight: 1.45 }}>
            {PROJECT_OBJECT_HOME.contextFromProject(contextProjectName)}{' '}
            <Link to={projectDashboardHref} className="le-btn le-btn--small le-btn--primary">
              {STUDIO_VOCAB.projectDashboard}
            </Link>
          </p>
        </div>
      ) : null}

      {!hasPath ? (
        <WorkspaceMdHub
          contextProject={contextProjectName}
          files={indexFiles}
          indexLoading={indexLoading}
          indexError={indexErr}
          indexTruncated={indexTruncated}
          pinned={pinned}
          recent={recent}
          onTogglePin={(path) => {
            toggleWorkspaceMdPin(path)
            refreshPinned()
            setRecent([...readWorkspaceMdRecent()])
          }}
          onClearRecent={() => {
            clearWorkspaceMdRecent()
            setRecent([])
          }}
        />
      ) : null}

      {!hasPath ? (
        <TechnicalDetails summary="Load by path (expert)" defaultOpen={false} className="le-ws-md-manual">
          <p className="forge-support" style={{ marginTop: 0 }}>
            Prefer pinned, recent, and indexed lists above. Use this only for bookmarks, CI links, or paths not yet in
            the index.
          </p>
          <form
            className="le-form-row le-ws-md-manual__form"
            onSubmit={(e) => {
              e.preventDefault()
              const v = String(new FormData(e.currentTarget).get('p') || '').trim()
              const next = new URLSearchParams()
              if (v) next.set('p', v)
              if (contextProjectName) next.set('contextProject', contextProjectName)
              setSp(next)
            }}
          >
            <input
              name="p"
              className="le-input"
              style={{ minWidth: '22rem' }}
              placeholder="relative path (e.g. forge/charge.md)"
              defaultValue={p}
              key={p || 'empty'}
            />
            <button type="submit" className="le-btn le-btn--primary">
              Load
            </button>
          </form>
        </TechnicalDetails>
      ) : null}

      {!hasPath ? null : (
        <div className="le-ws-md-view-toolbar">
          <Link className="le-btn le-btn--small" to={`/workspace-md${hubQueryString(contextProjectName)}`}>
            ← Evidence home
          </Link>
          <button
            type="button"
            className={`le-btn le-btn--small${pinnedNow ? ' le-btn--primary' : ''}`}
            onClick={() => {
              toggleWorkspaceMdPin(p.trim())
              refreshPinned()
            }}
          >
            {pinnedNow ? 'Pinned' : 'Pin this file'}
          </button>
        </div>
      )}

      {hasPath ? (
        <TechnicalDetails summary="Open a different path (expert)" defaultOpen={false} className="le-ws-md-manual">
          <form
            className="le-form-row le-ws-md-manual__form"
            onSubmit={(e) => {
              e.preventDefault()
              const v = String(new FormData(e.currentTarget).get('p') || '').trim()
              const next = new URLSearchParams()
              if (v) next.set('p', v)
              if (contextProjectName) next.set('contextProject', contextProjectName)
              setSp(next)
            }}
          >
            <input
              name="p"
              className="le-input"
              style={{ minWidth: '22rem' }}
              placeholder="relative path (e.g. forge/charge.md)"
              defaultValue={p}
              key={p || 'viewer-path'}
            />
            <button type="submit" className="le-btn le-btn--primary">
              Load
            </button>
          </form>
        </TechnicalDetails>
      ) : null}

      <TechnicalDetails summary="Demo trace (optional)" defaultOpen={false}>
        <div
          className="forge-support"
          style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}
        >
          <TraceabilityLaunchButton
            rootId={DEMO_BRIDGE_DEMAND_ID}
            label="From Ore (demand)"
            variant="secondary"
            title="Open trace from demo demand_signal through ingot, story, release"
          />
          <TraceabilityLaunchButton
            rootId={DEMO_ORCHESTRATION_STORY_ID}
            label="From story"
            variant="secondary"
            title="Open trace from demo story node"
          />
        </div>
      </TechnicalDetails>

      {loading ? (
        <StatePanel variant="loading" title="Loading evidence" description="Opening the selected markdown from your workspace." />
      ) : null}
      {!loading && err ? (
        <StatePanel
          variant="error"
          title="Could not open this markdown file"
          description="Paths must be allowlisted on the server. Go back to Evidence home for pinned, recent, and indexed files — or open a link from Plan or your project dashboard. Expert path entry stays collapsed under “Open a different path” when you already have a file open."
          technicalDetail={err}
          actions={
            <>
              <Link className="le-btn le-btn--primary" to={`/workspace-md${hubQueryString(contextProjectName)}`}>
                Evidence home
              </Link>
              <Link className="le-btn" to="/tutorials">
                Tutorials & handbooks
              </Link>
              <Link className="le-btn" to="/view/docs">
                Lenses reference
              </Link>
            </>
          }
        />
      ) : null}
      {text != null ? (
        <>
          <MarkdownBody text={text} />
          <TechnicalDetails summary="Raw markdown source (technical)">
            <pre className="le-preview le-json" style={{ whiteSpace: 'pre-wrap' }}>
              {text}
            </pre>
          </TechnicalDetails>
        </>
      ) : null}
    </>
  )
}
