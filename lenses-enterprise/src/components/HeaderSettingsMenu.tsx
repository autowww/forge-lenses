import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { NavLink } from 'react-router-dom'
import { WorkspaceLensControl } from './WorkspaceLensControl'
import { getAuthStatus, type AuthStatus } from '../api/auth'
import { useWorkspace } from '../context/WorkspaceContext'
import { getStudioAboutVersionLine } from '../util/studioBuildInfo'
import { useReleaseNotes } from '../context/ReleaseNotesContext'
import { useNavigationMode } from '../nav/useNavigationMode'
import { getSettingsGearMenuSections, type SideNavEntry } from '../nav/navigationConfig'
import { flowArtifactsHelpHomeTo } from '../nav/studioHelpQuery'
import { ADMIN_INSPECT_COPY, STUDIO_ONBOARDING, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

const STUDIO_VERSIONING_URL =
  'https://github.com/autowww/forge-lenses/blob/main/lenses-enterprise/VERSIONING.md' as const

function IconGear() {
  return (
    <svg className="le-header-icon-svg" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        fill="currentColor"
        d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58a.49.49 0 00.12-.61l-1.92-3.32a.488.488 0 00-.59-.22l-2.39.96c-.52-.4-1.06-.73-1.69-.98l-.36-2.54a.484.484 0 00-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.63.25-1.17.59-1.69.98l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58a.49.49 0 00-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.52.4 1.06.73 1.69.98l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.63-.25 1.17-.59 1.69-.98l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.08-.47-.12-.61l-2.01-1.58zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"
      />
    </svg>
  )
}

function MenuEntry({
  entry,
  onNavigate,
}: {
  entry: SideNavEntry
  onNavigate: () => void
}) {
  if (entry.disabled) {
    return (
      <span
        className="le-settings-menu__item le-settings-menu__item--disabled"
        title="Not available yet"
        role="menuitem"
        aria-disabled="true"
      >
        {entry.label}
      </span>
    )
  }
  if (entry.href) {
    return (
      <a
        className="le-settings-menu__item le-settings-menu__item--link"
        href={entry.href}
        role="menuitem"
        {...(entry.external ? { target: '_blank', rel: 'noreferrer' } : {})}
        onClick={onNavigate}
      >
        {entry.label}
        {entry.external ? <span className="le-sidebar__external-hint"> ↗</span> : null}
      </a>
    )
  }
  if (entry.to) {
    return (
      <NavLink
        className={({ isActive }) =>
          `le-settings-menu__item le-settings-menu__item--link${isActive ? ' le-settings-menu__item--active' : ''}`
        }
        to={entry.to}
        role="menuitem"
        onClick={onNavigate}
        end={entry.to === '/'}
      >
        {entry.label}
      </NavLink>
    )
  }
  return null
}

export function HeaderSettingsMenu() {
  const menuId = useId()
  const [open, setOpen] = useState(false)
  const [aboutOpen, setAboutOpen] = useState(false)
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const { mode } = useNavigationMode()
  const { openReleaseNotes } = useReleaseNotes()
  const gearSections = getSettingsGearMenuSections(mode)
  const { state } = useWorkspace()
  const workspaceProfile =
    state?.workspace_root?.split(/[/\\]/).filter(Boolean).pop() ?? 'Local workspace'

  useEffect(() => {
    void getAuthStatus()
      .then(setAuthStatus)
      .catch(() => setAuthStatus(null))
  }, [open])

  useEffect(() => {
    if (!open) return
    function onDoc(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  useEffect(() => {
    if (!aboutOpen) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setAboutOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [aboutOpen])

  const close = () => setOpen(false)

  return (
    <div className="le-settings-menu-wrap" ref={wrapRef}>
      <button
        type="button"
        className="le-icon-btn le-icon-btn--panel"
        aria-expanded={open}
        aria-haspopup="true"
        aria-controls={menuId}
        title="Settings"
        aria-label="Settings menu"
        onClick={() => setOpen((o) => !o)}
      >
        <IconGear />
      </button>
      {open ? (
        <div id={menuId} className="le-settings-menu" role="menu">
          {!authStatus?.session_ok ? (
            <p className="le-settings-menu__localIdentity le-settings-menu__micro">
              <span className="le-settings-menu__workspaceProfile" title={state?.workspace_root}>
                Workspace: {workspaceProfile}
              </span>
              {' — '}
              <span className="le-settings-menu__guidedSignIn">
                {authStatus?.expected_configured
                  ? 'Sign in optional — GitHub token enriches attribution.'
                  : 'Local-first profile — no sign-in required.'}
              </span>
              {' '}
              <NavLink to="/tutorials" className="le-settings-menu__item--link" onClick={close}>
                Workspace docs
              </NavLink>
              {authStatus?.expected_configured ? (
                <>
                  {' · '}
                  <NavLink to="/settings/llm" className="le-settings-menu__item--link" onClick={close}>
                    Sign in
                  </NavLink>
                </>
              ) : null}
            </p>
          ) : (
            <p className="le-settings-menu__localIdentity le-settings-menu__micro">
              <span className="le-settings-menu__workspaceProfile">Signed in as {authStatus.session_login}</span>
              {' · '}
              <span className="le-settings-menu__workspaceProfile">Workspace: {workspaceProfile}</span>
            </p>
          )}
          <p className="le-settings-menu__section">{ADMIN_INSPECT_COPY.settingsSectionSetup}</p>
          <p className="le-settings-menu__micro" id="le-gear-pref-intro">
            {ADMIN_INSPECT_COPY.gearMenuPreferencesIntro}
          </p>
          <NavLink
            className={({ isActive }) =>
              `le-settings-menu__item le-settings-menu__item--link${isActive ? ' le-settings-menu__item--active' : ''}`
            }
            to="/settings/llm"
            role="menuitem"
            onClick={close}
          >
            {STUDIO_VOCAB.llmPreferences}
          </NavLink>
          <NavLink
            className={({ isActive }) =>
              `le-settings-menu__item le-settings-menu__item--link${isActive ? ' le-settings-menu__item--active' : ''}`
            }
            to="/settings/fleet"
            role="menuitem"
            onClick={close}
          >
            {STUDIO_VOCAB.fleetPreferences}
          </NavLink>
          <details className="le-settings-menu__lens-details">
            <summary className="le-settings-menu__micro le-settings-menu__lens-details-sum">
              Layout lens (inspect)
            </summary>
            <p className="le-settings-menu__micro">
              Flow vs Artifacts is an advanced layout preference (sidebar emphasis and some labels). Primary
              navigation uses Home, Work, Projects, Knowledge, and Publish.
            </p>
          </details>
          <div className="le-settings-menu__lens" role="group" aria-label="Workspace lens preference">
            <WorkspaceLensControl presentation="dropdown" className="le-workspace-lens le-workspace-lens--in-menu" />
          </div>
          {gearSections.map((sec) => (
            <div key={sec.heading}>
              <p className="le-settings-menu__section">{sec.heading}</p>
              {sec.entries.map((entry, i) => (
                <MenuEntry key={`${sec.heading}-${entry.label}-${i}`} entry={entry} onNavigate={close} />
              ))}
            </div>
          ))}
          <NavLink
            className="le-settings-menu__item le-settings-menu__item--link"
            to={flowArtifactsHelpHomeTo()}
            role="menuitem"
            onClick={close}
          >
            {STUDIO_ONBOARDING.flowArtifactsChipLabel}
          </NavLink>
          <button
            type="button"
            className="le-settings-menu__item le-settings-menu__item--link"
            role="menuitem"
            onClick={() => {
              close()
              setAboutOpen(true)
            }}
          >
            About Forge Studio
          </button>
        </div>
      ) : null}
      {aboutOpen
        ? createPortal(
            <div
              className="le-llm-settings-modal-backdrop"
              role="presentation"
              onClick={() => setAboutOpen(false)}
            >
              <div
                className="le-llm-settings-modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="le-studio-about-title"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="le-llm-settings-modal__head">
                  <h2 id="le-studio-about-title" className="le-llm-settings-modal__title">
                    About Forge Studio
                  </h2>
                  <button
                    type="button"
                    className="le-llm-settings-modal__close"
                    onClick={() => setAboutOpen(false)}
                    aria-label="Close"
                  >
                    ×
                  </button>
                </div>
                <div className="le-llm-settings-modal__body">
                  <dl className="le-studio-about-dl">
                    <div>
                      <dt>Version</dt>
                      <dd className="le-studio-about-version">{getStudioAboutVersionLine()}</dd>
                    </div>
                  </dl>
                  <p className="le-studio-about-version-hint">
                    Leading value is release semver from <code className="le-mono">package.json</code>; commit
                    and time identify this exact bundle.
                  </p>
                  <p className="le-studio-about-links">
                    <button
                      type="button"
                      className="le-studio-about-links__btn"
                      onClick={() => {
                        setAboutOpen(false)
                        openReleaseNotes()
                      }}
                    >
                      Release notes (CHANGELOG)
                    </button>
                    {' · '}
                    <a href={STUDIO_VERSIONING_URL} target="_blank" rel="noopener noreferrer">
                      Version policy
                    </a>
                  </p>
                </div>
              </div>
            </div>,
            document.body,
          )
        : null}
    </div>
  )
}
