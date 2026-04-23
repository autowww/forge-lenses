import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useNavigationMode } from '../nav/useNavigationMode'
import { installGlobalTelemetryApi, recordStudioEvent } from '../telemetry/studioTelemetry'

/**
 * Records route views (pathname + lens) for UX diagnostics. Mount once under the app shell.
 */
export function StudioRouteListener() {
  const { pathname, search } = useLocation()
  const { mode } = useNavigationMode()
  const prevPath = useRef<string>('')

  useEffect(() => {
    installGlobalTelemetryApi()
  }, [])

  useEffect(() => {
    const key = `${pathname}${search}`
    if (key === prevPath.current) return
    prevPath.current = key
    recordStudioEvent('route_view', {
      pathname,
      search: search || '',
      lens: mode,
    })
  }, [pathname, search, mode])

  return null
}
