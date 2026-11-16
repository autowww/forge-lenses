import type { ReactNode } from 'react'
import { PageHeader } from '../components/page'
import { ROUTE_SUBTITLE, STUDIO_VOCAB, WIZARD_PROBE_COPY } from '../nav/studioVisibleCopy'

type Props = {
  children: ReactNode
}

/**
 * Framed shell for wizard **probe** states (loading / invalid session) so dogfood and tours
 * never see a bare paragraph where `PageHeader` + `StatePanel` normally anchor the main column.
 */
export function WizardSessionProbeChrome({ children }: Props) {
  return (
    <div className="le-wizard-probe-chrome">
      <PageHeader title={STUDIO_VOCAB.blueprintsWizard} subtitle={ROUTE_SUBTITLE.wizardExperimental} />
      {children}
      <p className="le-wizard-probe-chrome__note forge-support" role="note">
        {WIZARD_PROBE_COPY.devAccessibilityNote}
      </p>
    </div>
  )
}
