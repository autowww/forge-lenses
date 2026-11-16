import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  getProjectDocsHealth,
  postDocsHealthSessionReply,
  postDocsHealthSessionResume,
  postProjectDocsHealth,
  type DocsHealthProjectPayload,
  type DocsHealthSessionPayload,
} from '../api/docsHealth'
import { ApiError } from '../api/http'
import { DocsHealthProjectContextBanner } from '../components/docs-health/DocsHealthProjectContextBanner'
import { ProjectLocalNav } from '../components/projects'
import { PageHeader, StatePanel } from '../components/page'
import { DocsHealthSessionPage } from '../components/docs-health/DocsHealthSessionPage'
import { useDocsHealthLive } from '../context/DocsHealthLiveContext'
import { chargeMdCandidates } from '../lib/copilotPageEvidence'
import { formatDocsHealthSessionCopilotContext } from '../lib/docsHealthCopilotContext'
import { useSetLensesCopilotPageScope } from '../context/LensesCopilotPageScopeContext'
import { useDocsHealthSessionStream } from '../hooks/useDocsHealthSessionStream'
import { useWorkspace } from '../context/WorkspaceContext'
import { ROUTE_SUBTITLE as SUB, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

const LIVE = new Set(['running', 'awaiting_approval', 'awaiting_input', 'paused'])

export function ProjectDocsHealthSessionPage() {
  const { name = '', sessionId = '' } = useParams()
  const decoded = decodeURIComponent(name)
  const sid = decodeURIComponent(sessionId)
  const enc = encodeURIComponent(decoded)
  const liveCtx = useDocsHealthLive()
  const { state: workspaceState } = useWorkspace()
  const setCopilotScope = useSetLensesCopilotPageScope()
  const relatedMdRelPaths = useMemo(
    () => chargeMdCandidates(decoded || undefined),
    [decoded],
  )

  const workspaceChild = useMemo(
    () => workspaceState?.children?.find((c) => c.name === decoded),
    [workspaceState?.children, decoded],
  )
  const projectScopeConfirmed = Boolean(workspaceChild)

  const [session, setSession] = useState<DocsHealthSessionPayload | null>(null)
  const [projectSnapshot, setProjectSnapshot] = useState<DocsHealthProjectPayload | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [cancelBusy, setCancelBusy] = useState(false)
  const [cancelErr, setCancelErr] = useState<string | null>(null)
  const [replyText, setReplyText] = useState('')
  const [replyBusy, setReplyBusy] = useState(false)
  const [resumeBusy, setResumeBusy] = useState(false)
  const [stepError, setStepError] = useState<string | null>(null)

  const refresh = useCallback(() => {
    if (!decoded || !sid) return
    void postProjectDocsHealth(decoded, { op: 'session_get', session_id: sid })
      .then((o) => {
        if (o.ok && o.session) setSession(o.session as DocsHealthSessionPayload)
        else setErr('session_not_found')
      })
      .catch(() => setErr('load_failed'))
  }, [decoded, sid])

  const refreshProject = useCallback(() => {
    if (!decoded) return
    void getProjectDocsHealth(decoded)
      .then((p) => setProjectSnapshot(p))
      .catch(() => {})
  }, [decoded])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    refreshProject()
  }, [refreshProject])

  const applyStreamSession = useCallback((s: DocsHealthSessionPayload) => {
    setSession(s)
    setErr(null)
  }, [])

  const stLower = String(session?.status || '').toLowerCase()
  const streamEnabled = Boolean(session) && (LIVE.has(stLower) || Boolean(busy))
  const streamConnected = useDocsHealthSessionStream(decoded, sid, streamEnabled, applyStreamSession)

  useEffect(() => {
    if (!session?.status) return
    const active = LIVE.has(String(session.status).toLowerCase()) || Boolean(busy)
    if (!active) return
    if (streamConnected) return
    const id = window.setInterval(() => refresh(), 900)
    return () => window.clearInterval(id)
  }, [session?.status, busy, refresh, streamConnected])

  const runStateLine = useMemo(() => {
    const tr = session?.tasklet_run
    if (tr?.state) {
      const sr = tr.stop_reason ? ` · ${tr.stop_reason}` : ''
      return `${tr.state}${sr}`
    }
    return session?.run_state ? String(session.run_state) : null
  }, [session?.tasklet_run, session?.run_state])

  const streamMode = streamConnected ? 'sse' : streamEnabled ? 'poll' : 'idle'

  useEffect(() => {
    if (!decoded || !sid) return
    const head = `Forge Studio · Docs health session · ${decoded} · session ${sid}`
    const detail = formatDocsHealthSessionCopilotContext(decoded, sid, session)
    const wsLine = projectScopeConfirmed
      ? `Workspace: repository folder "${decoded}" is listed in the current workspace scan (Projects uses this same folder). All Docs Health data and session artifacts are for this checkout only.`
      : `Workspace: project "${decoded}" from the URL — confirm it matches a folder under your workspace root if Copilot should stay repo-scoped.`
    const pageContextSummary = detail ? `${head}\n\n${wsLine}\n\n${detail}` : `${head}\n\n${wsLine}`
    setCopilotScope({
      route: 'docs-health-session',
      projectSlug: decoded,
      projectScopeConfirmed,
      scopeSite: decoded,
      entityId: sid,
      pageContextSummary,
      relatedMdRelPaths,
    })
  }, [decoded, relatedMdRelPaths, session, setCopilotScope, sid, projectScopeConfirmed])

  useEffect(() => {
    if (!liveCtx || !decoded || !sid) return undefined
    return () => {
      liveCtx.setDetailPulse(null)
    }
  }, [liveCtx, decoded, sid])

  useEffect(() => {
    if (!liveCtx || !decoded || !sid || !session) return
    const st = String(session.status || '').toLowerCase()
    const live = LIVE.has(st)
    const showPulse = live || Boolean(busy)
    if (!showPulse) {
      liveCtx.setDetailPulse(null)
      return
    }
    const hs = session.header_stats
    liveCtx.setDetailPulse({
      projectSlug: decoded,
      sessionId: sid,
      status: st,
      totalTokens: hs?.total_tokens ?? 0,
      promptTokens: hs?.prompt_tokens ?? 0,
      completionTokens: hs?.completion_tokens ?? 0,
      lastModel: hs?.active_model,
      href: `/projects/${encodeURIComponent(decoded)}/docs-health/session/${encodeURIComponent(sid)}`,
      clusterLabel: session.cluster?.label ?? null,
      activeStep: busy,
    })
  }, [liveCtx, decoded, sid, session, busy])

  const step = async (s: string) => {
    if (!decoded || !sid) return
    setStepError(null)
    setBusy(s)
    try {
      const o = await postProjectDocsHealth(decoded, { op: 'session_step', session_id: sid, step: s })
      const rec = o as { ok?: boolean; error?: string; detail?: string }
      if (rec.ok === false) {
        setStepError(
          String(rec.detail || rec.error || 'This step did not complete successfully.'),
        )
      }
      refresh()
      refreshProject()
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? `${e.message}${e.technicalNote ? ` — ${e.technicalNote}` : ''}`
          : e instanceof Error
            ? e.message
            : 'Step failed (network or server error).'
      setStepError(msg)
    } finally {
      setBusy(null)
    }
  }

  const cancelSession = async () => {
    if (!decoded || !sid) return
    setCancelBusy(true)
    setCancelErr(null)
    try {
      const o = await postProjectDocsHealth(decoded, { op: 'session_cancel', session_id: sid })
      if (o.ok && o.session) {
        setSession(o.session as DocsHealthSessionPayload)
        refresh()
        refreshProject()
        return
      }
      const errObj = o as { error?: string; detail?: string }
      setCancelErr(
        String(errObj.detail || errObj.error || 'Stop session could not complete. Try again or refresh the page.'),
      )
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? `${e.message}${e.technicalNote ? ` — ${e.technicalNote}` : ''}`
          : e instanceof Error
            ? e.message
            : 'Stop session failed (network or server error).'
      setCancelErr(msg)
    } finally {
      setCancelBusy(false)
    }
  }

  const sendReply = async (opts: { reply_text?: string; choice_id?: string; confirm?: boolean }) => {
    if (!decoded || !sid) return
    setReplyBusy(true)
    try {
      await postDocsHealthSessionReply(decoded, { session_id: sid, ...opts })
      setReplyText('')
      refresh()
      refreshProject()
    } finally {
      setReplyBusy(false)
    }
  }

  const resumeSession = async () => {
    if (!decoded || !sid) return
    setResumeBusy(true)
    try {
      const o = await postDocsHealthSessionResume(decoded, { session_id: sid })
      if (o.ok && o.session) setSession(o.session as DocsHealthSessionPayload)
      refresh()
      refreshProject()
    } finally {
      setResumeBusy(false)
    }
  }

  if (!decoded || !sid) {
    return (
      <StatePanel
        variant="not_configured"
        title="Missing session"
        description="Open Docs health from a project and start remediation."
      />
    )
  }

  if (err === 'session_not_found' || err === 'load_failed') {
    return (
      <StatePanel
        variant="error"
        title="Session not available"
        description="The session file may have been removed, or the server could not read it."
        actions={
          <Link className="le-btn le-btn--primary" to={`/projects/${enc}/docs-health`}>
            Back to Docs health
          </Link>
        }
      />
    )
  }

  const breadcrumbNav = useMemo(
    () => (
      <nav className="le-dh-breadcrumb" aria-label="Breadcrumb">
        <Link className="le-dh-breadcrumb__link" to={`/projects/${enc}`}>
          {STUDIO_VOCAB.project}
        </Link>
        <span className="le-dh-breadcrumb__sep" aria-hidden>
          /
        </span>
        <Link className="le-dh-breadcrumb__link" to={`/projects/${enc}/docs-health`}>
          {STUDIO_VOCAB.docsHealth}
        </Link>
        <span className="le-dh-breadcrumb__sep" aria-hidden>
          /
        </span>
        <span className="le-dh-breadcrumb__current">Remediation run</span>
      </nav>
    ),
    [enc],
  )

  return (
    <>
      <PageHeader
        preface={breadcrumbNav}
        title={STUDIO_VOCAB.documentationRemediationRun}
        purpose={SUB.docsHealthRemediationConsole}
        secondaryMenuItems={[
          { key: 'back', to: `/projects/${enc}/docs-health`, label: STUDIO_VOCAB.docsHealth },
          { key: 'master', to: `/projects/${enc}/docs-health/master`, label: STUDIO_VOCAB.docsHealthMaster },
          { key: 'proj', to: `/projects/${enc}`, label: STUDIO_VOCAB.projectDashboard },
        ]}
      />
      <ProjectLocalNav projectName={decoded} />

      <DocsHealthProjectContextBanner projectSlug={decoded} encProject={enc} />

      <DocsHealthSessionPage
        encProject={enc}
        projectSlug={decoded}
        sessionId={sid}
        session={session}
        projectSnapshot={projectSnapshot}
        busy={busy}
        cancelBusy={cancelBusy}
        cancelErr={cancelErr}
        replyText={replyText}
        replyBusy={replyBusy}
        resumeBusy={resumeBusy}
        streamMode={streamMode}
        runStateLine={runStateLine}
        stepError={stepError}
        onDismissStepError={() => setStepError(null)}
        onCancelSession={cancelSession}
        onReplyText={setReplyText}
        onSendReply={sendReply}
        onResume={() => void resumeSession()}
        onStep={(s) => void step(s)}
      />
    </>
  )
}
