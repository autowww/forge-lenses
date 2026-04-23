import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useWorkspace } from '../context/WorkspaceContext'
import { Splash } from './Splash'
import { useEffect, useRef, useState } from 'react'
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
import { LensesCopilotRail } from './LensesCopilotRail'
import { StudioThreadAnchorProvider } from '../context/StudioThreadAnchorContext'
import { hrefToStudioRouterTo } from '../util/studioSameOriginLink'
import { useNavigationMode } from '../nav/useNavigationMode'
import { getStudioDocumentTitle } from '../nav/studioRouteRegistry'
import { STUDIO_EXPORT_ROOT_ID } from '../lib/studioPageExport'

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
  const { loading, error, errorDescription, errorDetail, refresh } = useWorkspace()
  const [step, setStep] = useState<
    'init' | 'connect' | 'scan' | 'receive' | 'parse'
  >('init')
  const [showSplash, setShowSplash] = useState(true)
  const [electronShell, setElectronShell] = useState(false)
  const { mainContentInert } = useMainContentInert()

  useEffect(() => {
    setElectronShell(typeof window !== 'undefined' && !!window.lensesElectron)
  }, [])

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
    if (loading) {
      setShowSplash(true)
      splashCycleStartRef.current = Date.now()
    }
  }, [loading])

  useEffect(() => {
    if (!loading && !error) {
      setStep('parse')
      const elapsed = Date.now() - splashCycleStartRef.current
      const remaining = Math.max(0, 2000 - elapsed)
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
      className={`le-root${!showSplash && !error ? ' le-ready' : ''}${electronShell ? ' le-root--electron' : ''}`}
    >
      <Splash
        step={step}
        error={error}
        errorDescription={errorDescription}
        errorDetail={errorDetail}
        onRetry={() => void refresh()}
        hidden={!showSplash && !error}
      />
      {!showSplash && !error && (
        <ReleaseNotesProvider>
          <TraceabilityDrawerProvider>
          <StudioThreadAnchorProvider>
          <div className="le-studio-chrome" inert={mainContentInert || undefined}>
            <StudioDocumentTitle />
            <header className={`le-header${electronShell ? ' le-header--electron' : ''}`}>
              <div
                className={`le-header__row le-header__row--brand${electronShell ? ' le-header__row--brand--electron' : ''}`}
              >
                <NavLink
                  className={({ isActive }) =>
                    `le-nav__brand le-nav__brand--lockup${isActive ? ' le-nav__brand--home' : ''}`
                  }
                  to="/"
                  end
                  title="Home"
                  aria-label="Home"
                >
                  <span className="le-brand-icon" aria-hidden="true">
                    F
                  </span>
                  <span className="le-brand-text">Forge Studio</span>
                </NavLink>
                {electronShell ? (
                  <div
                    className="le-header__drag"
                    aria-label="Drag to move window"
                    title="Drag to move window"
                  />
                ) : null}
                <HeaderUtilities />
              </div>
              <nav className="le-nav" aria-label="Studio chrome">
                <div className="le-nav__bar">
                  <TopNavigation />
                  <div className="le-nav__trail">
                    <StudioHistoryControls />
                    <BreadcrumbBar />
                  </div>
                </div>
              </nav>
            </header>
            <div className="le-shell">
              <SectionSidebar />
              <div className="le-shell__workspace">
                <div className="le-shell__main-column" id={STUDIO_EXPORT_ROOT_ID}>
                  <StudioShellChrome>
                    <StudioRouteListener />
                    <Outlet />
                  </StudioShellChrome>
                </div>
                <LensesCopilotRail />
              </div>
            </div>
            <TraceabilityDrawer />
          </div>
          </StudioThreadAnchorProvider>
          </TraceabilityDrawerProvider>
        </ReleaseNotesProvider>
      )}
    </div>
  )
}
