import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { apiGetJson, apiPostJson } from '../api/http'
import {
  countUnreadBlogPosts,
  loadReadUrlSet,
  markBlogPostRead,
  type BlogPostRow,
} from '../lib/forgesdlcBlogRead'

type BlogPayload = {
  ok?: boolean
  posts?: BlogPostRow[]
  synced_at?: string | null
  last_sync_error?: string | null
}

type ForgesdlcBlogContextValue = {
  posts: BlogPostRow[]
  syncedAt: string | null
  lastSyncError: string | null
  loading: boolean
  unreadCount: number
  refresh: () => Promise<void>
  syncRemote: () => Promise<void>
  markRead: (canonicalUrl: string) => void
}

const ForgesdlcBlogContext = createContext<ForgesdlcBlogContextValue | null>(null)

export function ForgesdlcBlogProvider({ children }: { children: ReactNode }) {
  const [posts, setPosts] = useState<BlogPostRow[]>([])
  const [syncedAt, setSyncedAt] = useState<string | null>(null)
  const [lastSyncError, setLastSyncError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [readVersion, setReadVersion] = useState(0)

  const readUrls = useMemo(() => loadReadUrlSet(), [readVersion])

  const applyPayload = useCallback((p: BlogPayload) => {
    setPosts(Array.isArray(p.posts) ? p.posts : [])
    setSyncedAt(typeof p.synced_at === 'string' ? p.synced_at : null)
    setLastSyncError(typeof p.last_sync_error === 'string' ? p.last_sync_error : null)
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiGetJson<BlogPayload>('/api/forgesdlc-blog')
      applyPayload(data)
    } catch {
      applyPayload({ ok: false, posts: [] })
    } finally {
      setLoading(false)
    }
  }, [applyPayload])

  const syncRemote = useCallback(async () => {
    try {
      const data = await apiPostJson<BlogPayload>('/api/forgesdlc-blog/sync', {})
      applyPayload(data)
    } catch {
      /* keep prior posts; error may show from last sync */
    }
  }, [applyPayload])

  useEffect(() => {
    void (async () => {
      await refresh()
      void syncRemote().finally(() => {
        void refresh()
      })
    })()
  }, [refresh, syncRemote])

  const markRead = useCallback((canonicalUrl: string) => {
    markBlogPostRead(canonicalUrl)
    setReadVersion((v) => v + 1)
  }, [])

  const unreadCount = useMemo(
    () => countUnreadBlogPosts(posts, readUrls),
    [posts, readUrls],
  )

  const value = useMemo(
    (): ForgesdlcBlogContextValue => ({
      posts,
      syncedAt,
      lastSyncError,
      loading,
      unreadCount,
      refresh,
      syncRemote,
      markRead,
    }),
    [
      posts,
      syncedAt,
      lastSyncError,
      loading,
      unreadCount,
      refresh,
      syncRemote,
      markRead,
    ],
  )

  return (
    <ForgesdlcBlogContext.Provider value={value}>{children}</ForgesdlcBlogContext.Provider>
  )
}

export function useForgesdlcBlog(): ForgesdlcBlogContextValue {
  const ctx = useContext(ForgesdlcBlogContext)
  if (!ctx) {
    throw new Error('useForgesdlcBlog must be used within ForgesdlcBlogProvider')
  }
  return ctx
}
