/** Client-side read tracking for Forge SDLC blog posts (canonical URLs). */

export const FORGESDLC_BLOG_READ_LS = 'studio-forgesdlc-blog-read-v1'

export function loadReadUrlSet(): Set<string> {
  try {
    const raw = localStorage.getItem(FORGESDLC_BLOG_READ_LS)
    if (!raw) return new Set()
    const data = JSON.parse(raw) as unknown
    if (!Array.isArray(data)) return new Set()
    return new Set(data.filter((x): x is string => typeof x === 'string' && x.length > 0))
  } catch {
    return new Set()
  }
}

export function persistReadUrlSet(urls: Set<string>): void {
  try {
    localStorage.setItem(FORGESDLC_BLOG_READ_LS, JSON.stringify([...urls]))
  } catch {
    /* ignore quota */
  }
}

export function markBlogPostRead(url: string): void {
  const u = url.trim()
  if (!u) return
  const next = loadReadUrlSet()
  next.add(u)
  persistReadUrlSet(next)
}

export type BlogPostRow = {
  url: string
  slug: string
  lastmod: string
  title: string | null
  cached_at: string | null
  is_hub: boolean
  cached: boolean
  /** Absolute URL for Open Graph preview; omitted or null when only the site default image applies. */
  preview_image_url?: string | null
}

/** Unread = non-hub posts whose canonical URL is not in the read set. */
export function countUnreadBlogPosts(
  posts: BlogPostRow[],
  readUrls: Set<string>,
): number {
  return posts.filter((p) => !p.is_hub && !readUrls.has(p.url)).length
}
