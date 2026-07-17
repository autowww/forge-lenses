import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { createDocManagementSession } from '../api/docManagement'
import { EmbeddedPreviewFrame } from '../components/EmbeddedPreviewFrame'
import { PageHeader, StatePanel } from '../components/page'
import { useForgesdlcBlog } from '../context/ForgesdlcBlogContext'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { STUDIO_VIEWER } from '../nav/studioVisibleCopy'
import { docManagementFeatureEnabled } from '../util/experimentalFlags'

const FORGE_BLOG_BASE = 'https://forgesdlc.com/blog/'

export function BlogPostPage() {
  const { slug: slugParam } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const [hydrateBusy, setHydrateBusy] = useState(false)
  const slug = slugParam ? decodeURIComponent(slugParam) : ''
  useLensesCopilotPage({ route: 'publish', entityId: slug || undefined })
  const canonicalUrl = `${FORGE_BLOG_BASE}${slug}`
  const { markRead, posts } = useForgesdlcBlog()

  const slugLower = slug.toLowerCase()
  const meta = posts.find((p) => p.slug === slugLower)
  const readUrl = meta?.url || canonicalUrl

  useEffect(() => {
    if (!slug) return
    markRead(readUrl)
  }, [slug, readUrl, markRead])

  const iframeSrc =
    slug && slug.match(/^[a-z0-9][-a-z0-9]*\.html$/i)
      ? `/api/forgesdlc-blog/content?slug=${encodeURIComponent(slugLower)}`
      : ''

  return (
    <>
      <PageHeader
        title={meta?.title ?? 'Blog post'}
        subtitle={iframeSrc ? STUDIO_VIEWER.blogPostSubtitleWithMirror : undefined}
        preface={
          <span className="forge-support">
            <Link to="/blog">← All posts</Link>
            {' · '}
            <a href={readUrl} target="_blank" rel="noreferrer">
              Open on forgesdlc.com
            </a>
            {docManagementFeatureEnabled() && slugLower ? (
              <>
                {' · '}
                <button
                  type="button"
                  className="le-link-btn"
                  disabled={hydrateBusy}
                  onClick={() => {
                    void (async () => {
                      setHydrateBusy(true)
                      try {
                        const res = await createDocManagementSession(
                          `Hydrate: ${meta?.title || slug}`,
                          { intake_source: 'blog', blog_slug: slugLower },
                        )
                        const sid = String((res.session as { id?: string })?.id || '')
                        if (sid) {
                          navigate(
                            `/doc-management/session/${encodeURIComponent(sid)}?blog_slug=${encodeURIComponent(slugLower)}`,
                          )
                        }
                      } finally {
                        setHydrateBusy(false)
                      }
                    })()
                  }}
                >
                  {hydrateBusy ? 'Starting…' : 'Hydrate from this post'}
                </button>
              </>
            ) : null}
          </span>
        }
      />
      {!iframeSrc ? (
        <StatePanel
          variant="invalid"
          title={STUDIO_VIEWER.blogPostInvalidTitle}
          description={
            <>
              {STUDIO_VIEWER.blogPostInvalidDescription}{' '}
              <span className="le-shortcut-pill" title="Expected URL shape">
                Slug like post.html
              </span>
            </>
          }
          technicalDetail={slug || '(empty slug)'}
          actions={
            <>
              <Link className="le-btn le-btn--primary" to="/blog">
                Blog in Studio
              </Link>
              <a className="le-btn" href={readUrl} target="_blank" rel="noreferrer">
                Open live post
              </a>
            </>
          }
        />
      ) : (
        <EmbeddedPreviewFrame
          title={meta?.title || slug}
          src={iframeSrc}
          disclosureKind="blog-cached-html"
        />
      )}
    </>
  )
}
