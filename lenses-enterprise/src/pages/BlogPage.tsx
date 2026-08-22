import { Link } from 'react-router-dom'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { PageHeader, StatePanel } from '../components/page'
import { useForgesdlcBlog } from '../context/ForgesdlcBlogContext'
import { loadReadUrlSet, type BlogPostRow } from '../lib/forgesdlcBlogRead'
import { KNOWLEDGE_PUBLISH_COPILOT, STUDIO_VIEWER, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

function lastmodSortKey(lastmod: string): number {
  const t = Date.parse(lastmod || '')
  return Number.isFinite(t) ? t : 0
}

function sortedPosts(rows: BlogPostRow[]): BlogPostRow[] {
  return [...rows].sort(
    (a, b) => lastmodSortKey(b.lastmod) - lastmodSortKey(a.lastmod),
  )
}

function formatBlogDate(lastmod: string): string {
  const t = Date.parse(lastmod || '')
  if (!Number.isFinite(t)) return lastmod.trim() || '—'
  return new Date(t).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function BlogPage() {
  useLensesCopilotPage({ route: 'publish', defaultQuery: KNOWLEDGE_PUBLISH_COPILOT.publishBlog })
  const { posts, loading, syncedAt, lastSyncError, syncRemote } = useForgesdlcBlog()
  const readUrls = loadReadUrlSet()
  const hub = posts.filter((p) => p.is_hub)
  const articles = sortedPosts(posts.filter((p) => !p.is_hub))
  const hasAnyPosts = hub.length > 0 || articles.length > 0

  return (
    <>
      <PageHeader
        title={STUDIO_VIEWER.blogFeedTitle}
        purpose={STUDIO_VIEWER.blogFeedPurpose}
        subtitle={
          <>
            {STUDIO_VIEWER.blogFeedLead}{' '}
            <span className="le-shortcut-pill" title="Native list; post body may be embedded cached HTML">
              Native feed
            </span>
          </>
        }
        secondaryMenuItems={[
          { key: 'websites', label: STUDIO_VOCAB.websites, to: '/websites' },
          { key: 'today', label: STUDIO_VOCAB.today, to: '/plan?tab=today' },
          { key: 'notes', label: STUDIO_VOCAB.workspaceNotes, to: '/workspace-md' },
        ]}
        actions={
          <span className="forge-support" style={{ display: 'inline-flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
            <button type="button" className="le-btn le-btn--primary le-btn--small" onClick={() => void syncRemote()}>
              Refresh from site
            </button>
            {syncedAt ? (
              <span className="le-muted" style={{ fontSize: '0.82rem' }}>
                Last sync: {syncedAt}
              </span>
            ) : null}
          </span>
        }
      />
      <p className="forge-support" style={{ marginTop: '-0.25rem' }}>
        Live site:{' '}
        <a href="https://forgesdlc.com/blog/" target="_blank" rel="noreferrer">
          forgesdlc.com/blog
        </a>{' '}
        · {STUDIO_VOCAB.blog} tab is the in-Studio mirror.
      </p>

      {lastSyncError && hasAnyPosts ? (
        <StatePanel
          variant="stale"
          title={STUDIO_VIEWER.blogSyncNoteTitle}
          description={lastSyncError}
          telemetryTag="blog_sync_with_cached_posts"
          actions={
            <button type="button" className="le-btn le-btn--primary" onClick={() => void syncRemote()}>
              Retry refresh
            </button>
          }
        />
      ) : null}

      {lastSyncError && !hasAnyPosts ? (
        <StatePanel
          variant="error"
          title={STUDIO_VIEWER.blogSyncNoteTitle}
          telemetryTag="blog_sync_no_posts"
          description={
            <>
              {lastSyncError} Showing no cached posts—fix the issue above or open the live blog.
            </>
          }
          actions={
            <>
              <button type="button" className="le-btn le-btn--primary" onClick={() => void syncRemote()}>
                Retry refresh
              </button>
              <a
                className="le-btn"
                href="https://forgesdlc.com/blog/"
                target="_blank"
                rel="noreferrer"
              >
                Open live blog
              </a>
            </>
          }
        />
      ) : null}

      {!lastSyncError && loading && !hasAnyPosts ? (
        <StatePanel
          variant="loading"
          title={STUDIO_VIEWER.blogLoadingTitle}
          description={STUDIO_VIEWER.blogLoadingDescription}
        />
      ) : null}

      {!lastSyncError && !loading && !hasAnyPosts ? (
        <StatePanel
          variant="empty"
          title={STUDIO_VIEWER.blogEmptyTitle}
          description={STUDIO_VIEWER.blogEmptyDescription}
          telemetryTag="blog_feed_empty"
          actions={
            <>
              <button type="button" className="le-btn le-btn--primary" onClick={() => void syncRemote()}>
                Refresh from site
              </button>
              <Link className="le-btn" to="/plan?tab=today">
                {STUDIO_VOCAB.today}
              </Link>
              <Link className="le-btn" to="/workspace-md">
                {STUDIO_VOCAB.workspaceNotes}
              </Link>
              <a
                className="le-btn"
                href="https://forgesdlc.com/blog/"
                target="_blank"
                rel="noreferrer"
              >
                Open live blog
              </a>
            </>
          }
        />
      ) : null}

      {hub.map((p) => (
        <div key={p.url} className="le-card" style={{ marginBottom: '0.75rem' }}>
          <strong>Blog hub (cached)</strong>
          <div>
            <Link to={`/blog/post/${encodeURIComponent(p.slug)}`}>Open in Studio</Link>
            {' · '}
            <a href={p.url} target="_blank" rel="noreferrer">
              Live site
            </a>
          </div>
        </div>
      ))}
      <div className="le-blog-feed">
        {articles.map((p) => {
          const unread = !readUrls.has(p.url)
          const preview = p.preview_image_url?.trim() || null
          return (
            <article key={p.url} className="le-card le-blog-card">
              <Link className="le-blog-card__media" to={`/blog/post/${encodeURIComponent(p.slug)}`}>
                {preview ? (
                  <img src={preview} alt="" loading="lazy" />
                ) : (
                  <div className="le-blog-card__placeholder" />
                )}
              </Link>
              <div className="le-blog-card__body">
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '0.35rem',
                    alignItems: 'baseline',
                    marginBottom: '0.35rem',
                  }}
                >
                  <Link
                    to={`/blog/post/${encodeURIComponent(p.slug)}`}
                    style={{ fontWeight: 600, fontSize: '1rem' }}
                  >
                    {p.title || p.slug.replace(/\.html$/i, '')}
                  </Link>
                  {unread ? (
                    <span className="le-badge le-badge--dirty" title="Unread">
                      New
                    </span>
                  ) : null}
                  {p.cached ? (
                    <span className="le-muted" style={{ fontSize: '0.8rem' }}>
                      Cached
                    </span>
                  ) : (
                    <span className="le-muted" style={{ fontSize: '0.8rem' }}>
                      Not cached yet
                    </span>
                  )}
                </div>
                <div className="le-muted" style={{ fontSize: '0.82rem' }}>
                  {formatBlogDate(p.lastmod)}
                </div>
              </div>
            </article>
          )
        })}
      </div>
    </>
  )
}
