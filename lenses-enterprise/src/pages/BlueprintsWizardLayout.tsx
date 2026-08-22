import { useCallback, useEffect, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { getBlueprintsWizardEnabled } from '../api/blueprintsWizard'
import { ApiError } from '../api/http'
import { WizardSessionProbeChrome } from '../blueprints-wizard/WizardSessionProbeChrome'
import { StatePanel } from '../components/page'
import { WIZARD_PROBE_COPY } from '../nav/studioVisibleCopy'
import { BlueprintsWizardLocalMode } from './BlueprintsWizardLocalMode'

export function BlueprintsWizardLayout() {
  const navigate = useNavigate()
  const [serverEnabled, setServerEnabled] = useState<boolean | null>(null)
  const [flagError, setFlagError] = useState<string | null>(null)
  const [probeKey, setProbeKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    setFlagError(null)
    setServerEnabled(null)
    getBlueprintsWizardEnabled()
      .then((en) => {
        if (!cancelled) setServerEnabled(en)
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setServerEnabled(false)
          setFlagError(e instanceof ApiError ? e.message : String(e))
        }
      })
    return () => {
      cancelled = true
    }
  }, [probeKey])

  const onExit = useCallback(() => navigate('/'), [navigate])

  const retryServerProbe = useCallback(() => {
    setProbeKey((k) => k + 1)
  }, [])

  if (serverEnabled === null && !flagError) {
    return (
      <WizardSessionProbeChrome>
        <StatePanel
          variant="loading"
          title="Checking wizard API"
          description={WIZARD_PROBE_COPY.layoutCheckingServer}
        />
      </WizardSessionProbeChrome>
    )
  }

  if (serverEnabled === false) {
    return (
      <BlueprintsWizardLocalMode
        onExit={onExit}
        onRetryServerProbe={flagError ? retryServerProbe : undefined}
        flagWarning={
          flagError
            ? `Could not read server wizard flag — using local draft only (${flagError}).`
            : undefined
        }
      />
    )
  }

  return <Outlet />
}
