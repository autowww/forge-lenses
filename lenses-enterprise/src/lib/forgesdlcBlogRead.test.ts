import { describe, expect, it } from 'vitest'
import { countUnreadBlogPosts, type BlogPostRow } from './forgesdlcBlogRead'

const samplePosts: BlogPostRow[] = [
  {
    url: 'https://forgesdlc.com/blog/index.html',
    slug: 'index.html',
    lastmod: '2026-04-01',
    title: 'Hub',
    cached_at: null,
    is_hub: true,
    cached: true,
    preview_image_url: null,
  },
  {
    url: 'https://forgesdlc.com/blog/a.html',
    slug: 'a.html',
    lastmod: '2026-03-01',
    title: 'A',
    cached_at: null,
    is_hub: false,
    cached: true,
    preview_image_url: 'https://forgesdlc.com/assets/blog/a-preview.svg',
  },
  {
    url: 'https://forgesdlc.com/blog/b.html',
    slug: 'b.html',
    lastmod: '2026-03-02',
    title: 'B',
    cached_at: null,
    is_hub: false,
    cached: true,
    preview_image_url: null,
  },
]

describe('countUnreadBlogPosts', () => {
  it('ignores hub and counts only unread non-hub URLs', () => {
    const read = new Set<string>(['https://forgesdlc.com/blog/a.html'])
    expect(countUnreadBlogPosts(samplePosts, read)).toBe(1)
  })

  it('returns zero when all articles read', () => {
    const read = new Set<string>([
      'https://forgesdlc.com/blog/a.html',
      'https://forgesdlc.com/blog/b.html',
    ])
    expect(countUnreadBlogPosts(samplePosts, read)).toBe(0)
  })
})
