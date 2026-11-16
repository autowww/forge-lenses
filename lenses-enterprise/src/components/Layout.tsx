import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useWorkspace } from '../context/WorkspaceContext'
import { Splash } from './Splash'
import { Suspense, useEffect, useRef, useState, lazy } from 'react'
import { BreadcrumbBar } from './BreadcrumbBar'
import { StudioHistoryControls } from './StudioHistoryControls'
import { HeaderUtilities } from './HeaderUtilities'
import { TopNavigation } from './TopNavigation'
import { SectionSidebar } from './SectionSidebar'
import { StudioShellChrome } from './shell/StudioShellChrome'
import { ReleaseNotesProvider } from '../context/ReleaseNotesContext'
import { StudioRouteListener } from './StudioRouteListener'
import { TraceabilityDrawerProvider } from '../context/TraceabilityDrawerContext'
import { TraceabilityDrawer } from './traceability/TraceabilityDrawer'
import { useMainContentInert } from '../context/MainContentInertContext'
import { StudioThreadAnchorProvider } from '../context/StudioThreadAnchorContext'
import { hrefToStudioRouterTo } from '../util/studioSameOriginLink'
import { useNavigationMode } from '../nav/useNavigationMode'
import { getStudioDocumentTitle } from '../nav/studioRouteRegistry'
import { STUDIO_EXPORT_ROOT_ID } from '../lib/studioPageExport'
import { virtualCameraElectronMode } from '../lib/studioElectronMode'
import { VirtualCameraSplash } from './VirtualCameraSplash'
import { WindowChrome } from './WindowChrome'

const LensesCopilotRail = lazy(() =>
  import('./LensesCopilotRail').then((m) => ({ default: m.LensesCopilotRail })),
)

function StudioDocumentTitle() {
  const { pathname, search } = useLocation()
  const { mode } = useNavigationMode()
  useEffect(() => {
    document.title = getStudioDocumentTitle(pathname, search, mode)
  }, [pathname, search, mode])
  return null
}

export function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { loading, error, errorDescription, errorDetail, refresh, state } = useWorkspace()
  const [step, setStep] = useState<
    'init' | 'connect' | 'scan' | 'receive' | 'parse'
  >('init')
  const [showSplash, setShowSplash] = useState(true)
  const [electronShell, setElectronShell] = useState(false)
  const [minimalStudio, setMinimalStudio] = useState(false)
  const { mainContentInert } = useMainContentInert()

  useEffect(() => {
    setElectronShell(typeof window !== 'undefined' && !!window.lensesElectron)
    setMinimalStudio(virtualCameraElectronMode())
  }, [])

  useEffect(() => {
    if (!minimalStudio) return
    const path = location.pathname.replace(/\/+$/, '') || '/'
    if (path === '/' || path === '/overview' || path === '/overview/charts') {
      navigate('/labs/virtual-camera', { replace: true })
    }
  }, [minimalStudio, location.pathname, navigate])

  /** Preview iframes (/docs, /local-site, Classic browse) delegate same-origin nav here. */
  useEffect(() => {
    function onMessage(ev: MessageEvent) {
      if (ev.origin !== window.location.origin) return
      const d = ev.data as {
        type?: string
        pathname?: string
        search?: string
        hash?: string
      }
      if (!d || d.type !== 'lenses-studio-same-origin-nav') return
      const path = String(d.pathname ?? '')
      if (!path.startsWith('/')) return
      const qs = d.search ?? ''
      const hash = d.hash ?? ''

      if (path === '/websites/browse' && qs) {
        const sp = new URLSearchParams(qs.startsWith('?') ? qs.slice(1) : qs)
        const site = sp.get('site')
        if (site) {
          navigate(`/websites/browse/${encodeURIComponent(site)}${hash}`)
          return
        }
      }

      if (path.startsWith('/view/local-site/')) {
        const tail = path.slice('/view/local-site/'.length)
        const parts = tail.replace(/^\/+/, '').split('/').filter(Boolean)
        const site = parts[0]
        if (site) {
          const rest = parts.slice(1).join('/')
          navigate(`/websites/browse/${encodeURIComponent(site)}${rest ? `/${rest}` : ''}${hash}`)
          return
        }
      }

      navigate(path + qs + hash)
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [navigate])

  /**
   * Many UI surfaces still render `<a href="/plan?…">` (API payloads, helper links). Those skip
   * `/studio/` and unload the SPA. Intercept same-origin in-app targets and route client-side.
   */
  useEffect(() => {
    function onClickCapture(e: MouseEvent) {
      if (e.defaultPrevented) return
      if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return
      const t = e.target
      if (!t || !(t instanceof Element)) return
      const a = t.closest('a[href]')
      if (!a || !(a instanceof HTMLAnchorElement)) return
      if (a.target === '_blank' || a.target === '_top' || a.target === '_parent') return
      if (a.hasAttribute('download')) return
      const raw = a.getAttribute('href')
      if (!raw) return
      const to = hrefToStudioRouterTo(raw)
      if (to == null) return
      e.preventDefault()
      navigate(to)
    }
    document.addEventListener('click', onClickCapture, true)
    return () => document.removeEventListener('click', onClickCapture, true)
  }, [navigate])

  /** Start of the current workspace fetch; used so the splash stays up at least 2s (Electron + browser). */
  const splashCycleStartRef = useRef(Date.now())

  useEffect(() => {
    if (loading && state == null && !minimalStudio) {
      setShowSplash(true)
      splashCycleStartRef.current = Date.now()
    }
  }, [loading, state, minimalStudio])

  useEffect(() => {
    if (!loading && !error) {
      setStep('parse')
      const elapsed = Date.now() - splashCycleStartRef.current
      const minVisible = minimalStudio ? 0 : 2000
      const remaining = Math.max(0, minVisible - elapsed)
      const t = window.setTimeout(() => setShowSplash(false), remaining)
      return () => window.clearTimeout(t)
    }
    if (error) {
      setShowSplash(true)
      return
    }
    setStep('init')
    const id = window.requestAnimationFrame(() => setStep('connect'))
    const t1 = window.setTimeout(() => setStep('scan'), 120)
    const t2 = window.setTimeout(() => setStep('receive'), 400)
    return () => {
      cancelAnimationFrame(id)
      window.clearTimeout(t1)
      window.clearTimeout(t2)
    }
  }, [loading, error])

  return (
    <div
      className={`le-root${!showSplash && !error ? ' le-ready' : ''}${electronShell ? ' le-root--electron' : ''}${minimalStudio ? ' le-root--minimal-studio' : ''}`}
    >
      {minimalStudio && !error ? (
        <VirtualCameraSplash hidden={!showSplash} />
      ) : (
        <Splash
          step={step}
          error={error}
          errorDescription={errorDescription}
          errorDetail={errorDetail}
          onRetry={() => void refresh()}
          hidden={!showSplash && !error}
        />
      )}
      {!showSplash && !error && (
        <ReleaseNotesProvider>
          <TraceabilityDrawerProvider>
          <StudioThreadAnchorProvider>
          <div className="le-studio-chrome" inert={mainContentInert || undefined}>
            <StudioDocumentTitle />
            <header className={`le-header${electronShell ? ' le-header--electron' : ''}${minimalStudio ? ' le-header--minimal-studio' : ''}`}>
              <div
                className={`le-header__row le-header__row--brand${electronShell ? ' le-header__row--brand--electron' : ''}`}
              >
                <NavLink
                  className={({ isActive }) =>
                    `le-nav__brand le-nav__brand--lockup${isActive ? ' le-nav__brand--home' : ''}`
                  }
                  to={minimalStudio ? '/labs/virtual-camera' : '/'}
                  end={!minimalStudio}
                  title={minimalStudio ? 'Virtual Camera Studio' : 'Home'}
                  aria-label={minimalStudio ? 'Virtual Camera Studio' : 'Home'}
                >
                  <span className="le-brand-icon" aria-hidden="true">
                    {minimalStudio ? 'VC' : 'F'}
                  </span>
                  <span className="le-brand-text">
                    {minimalStudio ? 'Virtual Camera Studio' : 'Forge Studio'}
                  </span>
                </NavLink>
                {electronShell ? (
                  <div
                    className="le-header__drag"
                    aria-label="Drag to move window"
                    title="Drag to move window"
                  />
                ) : null}
                {minimalStudio ? (
                  <div className="le-header-chrome-panel le-header-chrome-panel--minimal">
                    <WindowChrome />
                  </div>
                ) : (
                  <HeaderUtilities />
                )}
              </div>
              {minimalStudio ? null : (
              <nav className="le-nav" aria-label="Studio chrome">
                <div className="le-nav__bar">
                  <TopNavigation />
                  <div className="le-nav__trail">
                    <StudioHistoryControls />
                    <BreadcrumbBar />
                  </div>
                </div>
              </nav>
              )}
            </header>
            <div className="le-shell">
              {minimalStudio ? null : <SectionSidebar />}
              <div className="le-shell__workspace">
                <div className="le-shell__main-column" id={STUDIO_EXPORT_ROOT_ID}>
                  <StudioShellChrome>
                    <StudioRouteListener />
                    <Outlet />
                  </StudioShellChrome>
                </div>
                {minimalStudio ? null : (
                <Suspense fallback={null}>
                  <LensesCopilotRail />
                </Suspense>
                )}
              </div>
            </div>
            {minimalStudio ? null : <TraceabilityDrawer />}
          </div>
          </StudioThreadAnchorProvider>
          </TraceabilityDrawerProvider>
        </ReleaseNotesProvider>
      )}
    </div>
  )
}
