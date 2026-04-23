import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { apiGetJson, qs } from '../api/http'
import { chargeMdCandidates } from '../lib/copilotPageEvidence'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { PageAiInsightCard, PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import { useStudioCommandBar } from '../context/StudioCommandBarContext'
import { recordPageToolingChoice } from '../telemetry/studioTelemetry'
import { resolveUxFailure, type UxResolvedFailure } from '../lib/uxPageState'
import { embedUrlForStaticPath } from '../util/staticPreviewUrl'
import { ROUTE_SUBTITLE, STUDIO_UTILITIES, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

type Hit = {
  title?: string
  url?: string
  snippet?: string
  path_key?: string
}

type SearchRes = {
  hits?: Hit[]
  total?: number
  query?: string
  limit?: number
  offset?: number
}

const PAGE = 25

function highlightSnippet(text: string, query: string): ReactNode {
  const term = query.trim().split(/\s+/).filter(Boolean)[0]
  if (!term || !text) return text
  const lower = text.toLowerCase()
  const idx = lower.indexOf(term.toLowerCase())
  if (idx < 0) return text
  const end = idx + term.length
  return (
    <>
      {text.slice(0, idx)}
      <mark>{text.slice(idx, end)}</mark>
      {text.slice(end)}
    </>
  )
}

export function SearchPage() {
  const cmd = useStudioCommandBar()
  const [sp, setSp] = useSearchParams()
  const q = sp.get('q') || ''
  const repo = sp.get('repo') || ''
  const offset = Math.max(0, parseInt(sp.get('offset') || '0', 10) || 0)

  const copilotEvidence = useMemo(() => {
    const r = repo.trim()
    const qt = q.trim()
    const base = ['Forge Studio · Search']
    if (r) base.push(`scoped repo ${r}`)
    if (qt) base.push(`search box: ${qt.slice(0, 120)}`)
    return {
      pageContextSummary: base.join(' · '),
      relatedMdRelPaths: chargeMdCandidates(r || undefined),
    }
  }, [repo, q])

  useLensesCopilotPage({
    route: 'search',
    scopeSite: repo || undefined,
    defaultQuery: q || undefined,
    pageContextSummary: copilotEvidence.pageContextSummary,
    relatedMdRelPaths: copilotEvidence.relatedMdRelPaths,
  })
  const [data, setData] = useState<SearchRes | null>(null)
  const [input, setInput] = useState(q)
  const [loading, setLoading] = useState(false)
  const [searchFailure, setSearchFailure] = useState<UxResolvedFailure | null>(null)
  const [retryNonce, setRetryNonce] = useState(0)

  useEffect(() => {
    setInput(q)
  }, [q])

  useEffect(() => {
    if (!q.trim()) {
      setData(null)
      setSearchFailure(null)
      return
    }
    setLoading(true)
    setSearchFailure(null)
    const p = qs({
      q,
      limit: String(PAGE),
      offset: String(offset),
      repo: repo || undefined,
    })
    apiGetJson<SearchRes>(`/api/search${p}`)
      .then((r) => {
        setData(r)
        setSearchFailure(null)
      })
      .catch((e) => {
        setData(null)
        setSearchFailure(resolveUxFailure(e))
      })
      .finally(() => setLoading(false))
  }, [q, repo, offset, retryNonce])

  function runSearch(e: React.FormEvent) {
    e.preventDefault()
    recordPageToolingChoice('search_form', 'submit')
    const next = new URLSearchParams()
    if (input.trim()) next.set('q', input.trim())
    if (repo) next.set('repo', repo)
    next.set('offset', '0')
    setSp(next)
  }

  const total = data?.total ?? 0
  const hasMore = offset + PAGE < total
  const canPrev = offset > 0

  const pageInfo = useMemo(() => {
    if (total === 0) return null
    return `${offset + 1}–${Math.min(offset + PAGE, total)} of ${total}`
  }, [total, offset])

  function goPage(delta: number) {
    const next = Math.max(0, offset + delta * PAGE)
    const n = new URLSearchParams(sp)
    n.set('offset', String(next))
    if (q) n.set('q', q)
    if (repo) n.set('repo', repo)
    setSp(n)
  }

  return (
    <>
      <PageHeader
        title={STUDIO_VOCAB.search}
        purpose={ROUTE_SUBTITLE.searchUtility}
        statusChips={[{ label: 'Workspace tool', tone: 'muted' }]}
        primaryAction={
          <button type="submit" form="le-search-main-form" className="le-btn le-btn--primary">
            Search
          </button>
        }
        secondaryMenuItems={[
          { key: 'tutorials', label: 'Tutorials (Knowledge)', to: '/tutorials' },
          { key: 'docs', label: 'Embedded docs', to: '/view/docs' },
          { key: 'notes', label: STUDIO_VOCAB.workspaceNotes, to: '/workspace-md' },
          { key: 'chat', label: 'Copilot', to: '/chat' },
        ]}
      />
      <TechnicalDetails summary="Using Find vs this page" defaultOpen={false}>
        <p className="forge-support">
          Header <strong>Find</strong> searches routes and index hits in the command bar. This page keeps larger
          batches, snippets, and repo-scoped filters for evidence review.
        </p>
      </TechnicalDetails>
      <PageAiInsightCard
        whatChanged={q.trim() ? `Active query: “${q.trim()}”.` : 'No query yet — run a search or open Ask from the header.'}
        whyItMatters="Use results to open evidence and docs; narrow with the repo filter below when the workspace is large."
        nextAction={
          <span className="le-form-row" style={{ flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
            <button
              type="button"
              className="le-btn le-btn--small le-btn--primary"
              onClick={() => {
                recordPageToolingChoice('search_insight', 'header_ask')
                cmd.open('ask')
              }}
            >
              Ask in command bar
            </button>
            <Link
              className="le-btn le-btn--small"
              to="/chat"
              onClick={() => recordPageToolingChoice('search_insight', 'copilot_page')}
            >
              Copilot page
            </Link>
          </span>
        }
      />
      <form id="le-search-main-form" className="le-form-row" onSubmit={runSearch}>
        <input
          className="le-input"
          style={{ minWidth: '16rem' }}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Keywords"
          aria-label="Search keywords"
        />
        <button className="le-btn le-btn--primary" type="submit">
          Search
        </button>
      </form>
      <TechnicalDetails summary="Search options — limit to one repository">
        <label className="le-form-row" style={{ marginBottom: 0 }}>
          <span className="forge-support" style={{ minWidth: '6rem' }}>
            Repo scope
          </span>
          <input
            className="le-input"
            placeholder="Repository name filter"
            value={repo}
            onChange={(e) => {
              const next = new URLSearchParams(sp)
              if (e.target.value) next.set('repo', e.target.value)
              else next.delete('repo')
              if (q) next.set('q', q)
              next.set('offset', '0')
              setSp(next)
            }}
            aria-label="Limit search to repository name"
          />
        </label>
      </TechnicalDetails>
      {loading ? (
        <StatePanel
          variant="loading"
          title="Searching workspace"
          description="Looking for matches in your indexed notes, docs, and code."
        />
      ) : null}
      {!loading && !q.trim() ? (
        <StatePanel
          variant="empty"
          title={STUDIO_UTILITIES.searchEmptyTitle}
          description={
            <>
              {STUDIO_UTILITIES.searchEmptyBody}
              <br />
              <br />
              {STUDIO_UTILITIES.searchShortcutHint}
            </>
          }
          actions={
            <Link className="le-btn le-btn--primary" to="/tutorials">
              Tutorials (Knowledge)
            </Link>
          }
          telemetryTag="search_no_query"
        />
      ) : null}
      {!loading && q.trim() && searchFailure ? (
        <StatePanel
          variant={
            searchFailure.kind === 'permission_denied'
              ? 'permission'
              : searchFailure.kind === 'missing_configuration'
                ? 'not_configured'
                : searchFailure.kind === 'disconnected' || searchFailure.kind === 'unavailable'
                  ? 'unavailable'
                  : 'error'
          }
          title={searchFailure.title}
          description={searchFailure.description}
          technicalDetail={searchFailure.technical}
          aiRecovery={{
            prompt: `Workspace search failed for “${q}”. What should I check or try next in Forge Lenses?`,
            label: 'Ask Chat how to fix search',
          }}
          actions={
            <button type="button" className="le-btn le-btn--primary" onClick={() => setRetryNonce((n) => n + 1)}>
              Retry search
            </button>
          }
          telemetryTag="search_request_failed"
        />
      ) : null}
      {!loading && q.trim() && data && (
        <p className="forge-support">
          {total} result(s) for “{data.query}”
          {pageInfo ? ` · ${pageInfo}` : ''}
        </p>
      )}
      {!loading && q.trim() ? (
        <div className="le-form-row">
          <button type="button" className="le-btn" disabled={!canPrev} onClick={() => goPage(-1)}>
            Previous
          </button>
          <button type="button" className="le-btn" disabled={!hasMore} onClick={() => goPage(1)}>
            Next
          </button>
        </div>
      ) : null}
      <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
        {(data?.hits ?? []).map((h, i) => (
          <li key={`${h.path_key}-${i}`} className="le-card" style={{ marginBottom: '0.5rem' }}>
            <strong>{h.title || h.path_key}</strong>
            <div>
              {/^https?:\/\//i.test(h.url || '') ? (
                <a href={h.url}>{h.url}</a>
              ) : (
                <Link to={embedUrlForStaticPath(h.url || '/')}>{h.url}</Link>
              )}
            </div>
            <p className="forge-support">{highlightSnippet(h.snippet ?? '', q)}</p>
          </li>
        ))}
      </ul>
    </>
  )
}
