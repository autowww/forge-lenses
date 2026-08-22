import { Link } from 'react-router-dom'
import { AttentionNotifications } from './AttentionNotifications'
import { HeaderAccount } from './HeaderAccount'
import { HeaderSettingsMenu } from './HeaderSettingsMenu'
import { StudioQuickNav } from './StudioQuickNav'
import { WindowChrome } from './WindowChrome'
import { StudioPageExportMenu } from './StudioPageExportMenu'
import { useStudioCommandBar } from '../context/StudioCommandBarContext'
import { useDocsHealthLive } from '../context/DocsHealthLiveContext'
import { DOCS_HEALTH_PIPELINE_STEP_LABELS } from '../lib/docsHealthStepLabels'
import { STUDIO_VOCAB } from '../nav/studioVisibleCopy'
import './docs-health/docs-health-session.css'

function docsHealthSessionStepLabel(step: string | null | undefined): string | null {
  if (!step) return null
  return DOCS_HEALTH_PIPELINE_STEP_LABELS[step] || step
}

function docsHealthSessionStatusLabel(status: string): string {
  const s = status.toLowerCase()
  if (s === 'running') return 'In progress'
  if (s === 'awaiting_input') return 'Needs reply'
  if (s === 'awaiting_approval') return 'Awaiting confirm'
  if (s === 'completed') return 'Complete'
  return status.trim() || 'Active'
}

function IconSearch() {
  return (
    <svg className="le-header-icon-svg" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        fill="currentColor"
        d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"
      />
    </svg>
  )
}

function IconChat() {
  return (
    <svg className="le-header-icon-svg" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        fill="currentColor"
        d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"
      />
    </svg>
  )
}

/** Opens unified command bar (Find) — replaces inline header search field. */
function CommandBarTrigger() {
  const { open } = useStudioCommandBar()
  return (
    <button
      type="button"
      className="le-header-search le-header-search--panel le-header-search--trigger"
      onClick={() => open('find')}
      title="Find — routes, files, and index hits (Ctrl+K / ⌘K)"
    >
      <span className="le-header-search__icon" aria-hidden="true">
        <IconSearch />
      </span>
      <span className="le-header-search__trigger-label">Find…</span>
      <kbd className="le-header-search__kbd" aria-hidden="true">
        ⌘K
      </kbd>
    </button>
  )
}

export function HeaderUtilities() {
  const { open } = useStudioCommandBar()
  const dhLive = useDocsHealthLive()
  const dhPulse = dhLive?.pulse
  const dhStepLbl = dhPulse ? docsHealthSessionStepLabel(dhPulse.activeStep) : null

  return (
    <div className="le-header-utilities" aria-label="Workspace utilities">
      <div className="le-header-chrome-panel" aria-label="Global tools and window">
        <div className="le-header-chrome-panel__leading" aria-label="Find, search, and Copilot">
          <div className="le-header-fad" aria-label="Find, Ask, Do">
            <button
              type="button"
              className="le-header-fad__btn"
              onClick={() => open('find')}
              title={`Find — ${STUDIO_VOCAB.search}`}
            >
              Find
            </button>
            <span className="le-header-fad__sep" aria-hidden="true">
              /
            </span>
            <button
              type="button"
              className="le-header-fad__btn"
              onClick={() => open('ask')}
              title={`Ask — ${STUDIO_VOCAB.copilot} (${STUDIO_VOCAB.llmChat})`}
            >
              Ask
            </button>
            <span className="le-header-fad__sep" aria-hidden="true">
              /
            </span>
            <button
              type="button"
              className="le-header-fad__btn"
              onClick={() => open('do')}
              title={`Do — ${STUDIO_VOCAB.toolset} and safe actions`}
            >
              Do
            </button>
          </div>
          {dhPulse ? (
            <Link
              to={dhPulse.href}
              className="le-dh-live-chip"
              aria-live="polite"
              title={[
                STUDIO_VOCAB.docsHealth,
                dhPulse.clusterLabel,
                docsHealthSessionStatusLabel(dhPulse.status),
                dhStepLbl ?? undefined,
                `${(dhPulse.totalTokens || 0).toLocaleString()} tokens`,
              ]
                .filter(Boolean)
                .join(' · ')}
              aria-label={[
                STUDIO_VOCAB.docsHealth,
                'session',
                dhPulse.clusterLabel,
                docsHealthSessionStatusLabel(dhPulse.status),
                dhStepLbl ? `current step ${dhStepLbl}` : null,
                `${(dhPulse.totalTokens || 0).toLocaleString()} tokens total`,
              ]
                .filter(Boolean)
                .join(', ')}
            >
              <span className="le-dh-live-chip__brand">Docs health</span>
              {dhPulse.clusterLabel ? (
                <span className="le-dh-live-chip__cluster">{dhPulse.clusterLabel}</span>
              ) : null}
              <span className="le-dh-live-chip__step">
                {dhStepLbl ? `${dhStepLbl}…` : docsHealthSessionStatusLabel(dhPulse.status)}
              </span>
              <span className="le-dh-live-chip__metrics">
                <span className="le-dh-live-chip__tok">{(dhPulse.totalTokens || 0).toLocaleString()}</span>
                <span className="le-dh-live-chip__tok-w">tokens</span>
              </span>
            </Link>
          ) : null}
          <CommandBarTrigger />
          <button
            type="button"
            className="le-header-global-link le-header-global-link--btn"
            onClick={() => open('ask')}
            title={`${STUDIO_VOCAB.copilot} — ${STUDIO_VOCAB.llmChat}; opens Ask in the command bar`}
            aria-label={`${STUDIO_VOCAB.copilot}, ${STUDIO_VOCAB.llmChat}, open Ask in command bar`}
          >
            <span className="le-header-global-link__icon" aria-hidden="true">
              <IconChat />
            </span>
            <span className="le-header-global-link__text">{STUDIO_VOCAB.copilot}</span>
          </button>
        </div>
        <StudioQuickNav />
        <div className="le-header-chrome-panel__actions" aria-label="Quick actions">
          <StudioPageExportMenu />
          <HeaderSettingsMenu />
          <AttentionNotifications />
        </div>
        <div className="le-header-chrome-panel__account">
          <HeaderAccount />
        </div>
        <WindowChrome />
      </div>
    </div>
  )
}
