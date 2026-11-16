import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { apiGetJson } from '../api/http'
import { MarkdownBody } from '../components/MarkdownBody'
import { PlanningClusterLocalNav, PlanningClusterPageHeader } from '../components/plan'
import { StatePanel } from '../components/page'
import { mergePlanningScopeIntoTo } from '../lib/planningClusterScope'
import { useNavigationMode } from '../nav/useNavigationMode'
import { getPlanningClusterPageIdentity } from '../nav/planningClusterPageIdentity'
import { STUDIO_VOCAB } from '../nav/studioVisibleCopy'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'

export function WbsViewPage() {
  useLensesCopilotPage({ route: 'wbs-view' })
  const [sp, setSp] = useSearchParams()
  const location = useLocation()
  const { mode } = useNavigationMode()
  const pageIdentity = useMemo(
    () => getPlanningClusterPageIdentity(location.pathname, location.search, mode),
    [location.pathname, location.search, mode],
  )
  const p = sp.get('p') || sp.get('wbs_p') || ''
  const [text, setText] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

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
    apiGetJson<{ ok?: boolean; text?: string }>(`/api/wbs-file?p=${encodeURIComponent(p)}`)
      .then((r) => {
        if (r.ok && r.text != null) {
          setText(r.text)
          setErr(null)
        } else {
          setText(null)
          setErr('The server returned no content for this path (not found or not allowlisted).')
        }
      })
      .catch((e) => {
        setText(null)
        setErr(e instanceof Error ? e.message : String(e))
      })
      .finally(() => setLoading(false))
  }, [p])

  const wbsIndexTo = mergePlanningScopeIntoTo('/wbs', location.search)

  return (
    <>
      <PlanningClusterLocalNav />
      <PlanningClusterPageHeader
        identity={pageIdentity}
        preface={
          <Link to={wbsIndexTo} className="forge-support">
            ← {STUDIO_VOCAB.workBreakdown} index
          </Link>
        }
      />
      <form
        className="le-form-row"
        onSubmit={(e) => {
          e.preventDefault()
          const fd = new FormData(e.currentTarget)
          const v = String(fd.get('p') || '').trim()
          const next = new URLSearchParams(sp)
          if (v) {
            next.set('p', v)
            next.set('wbs_p', v)
          } else {
            next.delete('p')
            next.delete('wbs_p')
          }
          setSp(next)
        }}
      >
        <label>
          Path{' '}
          <input
            key={p || 'empty'}
            name="p"
            className="le-input"
            style={{ minWidth: '24rem' }}
            defaultValue={p}
          />
        </label>
        <button type="submit" className="le-btn">
          Load
        </button>
      </form>

      {loading ? (
        <StatePanel variant="loading" title="Loading WBS file" description="Fetching markdown or text from the server." />
      ) : null}
      {!loading && err ? (
        <StatePanel
          variant="error"
          title="Could not load this WBS file"
          description="Confirm the path matches an entry from the WBS index and that your Lenses server allows reading it."
          technicalDetail={err}
          actions={
            <>
              <Link className="le-btn le-btn--primary" to={wbsIndexTo}>
                Back to WBS index
              </Link>
              <button type="button" className="le-btn" onClick={() => window.location.reload()}>
                Retry
              </button>
            </>
          }
        />
      ) : null}
      {!loading && !err && !p.trim() ? (
        <StatePanel
          variant="empty"
          title="No file selected"
          description="Enter a path (or choose a file from the WBS index) to render markdown here."
          actions={<Link to={wbsIndexTo}>Open WBS index</Link>}
        />
      ) : null}
      {text != null ? (
        <>
          <MarkdownBody text={text} />
          <details className="le-raw-wrap">
            <summary>Raw source</summary>
            <pre className="le-preview le-json" style={{ maxHeight: '40vh', whiteSpace: 'pre-wrap' }}>
              {text}
            </pre>
          </details>
        </>
      ) : null}
    </>
  )
}
