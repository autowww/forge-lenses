import { NavLink, useLocation, useParams } from 'react-router-dom'
import { useWorkspace } from '../context/WorkspaceContext'
import { useNavigationMode } from '../nav/useNavigationMode'
import {
  getSideNavEntries,
  withPlanningScopeOnSideNavEntries,
  type SideNavEntry,
} from '../nav/navigationConfig'
import { studioNavLinkEnd } from '../lib/planningClusterScope'
import {
  FULL_WORKSPACE_UI,
  SHELL_RAIL_HINT,
  STUDIO_UTILITIES,
  getPrimarySectionLabel,
  WORK_SECTION_ADVANCED_NAV,
} from '../nav/studioVisibleCopy'
import { isNavSectionRowGroup, navSectionHeadingHint, type NavSectionRowGroup } from '../nav/sidebarSectionMeta'
import { resolveTopSection } from '../nav/resolveNavSection'
import {
  getSidebarLinkSemantics,
  sidebarLinkAccessibleLabel,
} from '../nav/sidebarLinkSemantics'
import { recordSidebarNavClick } from '../telemetry/studioTelemetry'
import type { StudioTelemetryNavIntent } from '../telemetry/studioTelemetry'

type SidebarRow =
  | { kind: 'single'; entry: SideNavEntry }
  | { kind: 'utilities'; entries: SideNavEntry[] }
  | { kind: 'work_advanced'; entries: SideNavEntry[] }
  | { kind: 'nav_section'; group: NavSectionRowGroup; entries: SideNavEntry[] }

function buildSidebarRows(entries: SideNavEntry[]): SidebarRow[] {
  const rows: SidebarRow[] = []
  let util: SideNavEntry[] = []
  let adv: SideNavEntry[] = []
  let navSectionGroup: NavSectionRowGroup | null = null
  let navSectionBuf: SideNavEntry[] = []

  function flushUtil() {
    if (util.length) {
      rows.push({ kind: 'utilities', entries: util })
      util = []
    }
  }
  function flushAdv() {
    if (adv.length) {
      rows.push({ kind: 'work_advanced', entries: adv })
      adv = []
    }
  }
  function flushNavSection() {
    if (navSectionGroup && navSectionBuf.length) {
      rows.push({ kind: 'nav_section', group: navSectionGroup, entries: [...navSectionBuf] })
    }
    navSectionGroup = null
    navSectionBuf = []
  }

  for (const entry of entries) {
    if (entry.sidebarGroup === 'utilities') {
      flushNavSection()
      flushAdv()
      util.push(entry)
      continue
    }
    if (entry.sidebarGroup === 'work_advanced') {
      flushNavSection()
      flushUtil()
      adv.push(entry)
      continue
    }
    if (isNavSectionRowGroup(entry.sidebarGroup)) {
      flushUtil()
      flushAdv()
      if (navSectionGroup !== entry.sidebarGroup) {
        flushNavSection()
        navSectionGroup = entry.sidebarGroup
      }
      navSectionBuf.push(entry)
      continue
    }
    flushNavSection()
    flushUtil()
    flushAdv()
    rows.push({ kind: 'single', entry })
  }
  flushNavSection()
  flushUtil()
  flushAdv()
  return rows
}

/** Strip grouping marker before rendering links (metadata only). */
function linkEntry(e: SideNavEntry): SideNavEntry {
  const { sidebarGroup: _g, ...rest } = e
  void _g
  return rest
}

function SideNavLink({
  entry,
  section,
}: {
  entry: SideNavEntry
  section: ReturnType<typeof resolveTopSection>
}) {
  const { mode } = useNavigationMode()
  const semantics = getSidebarLinkSemantics(entry, section, mode)
  const a11y = sidebarLinkAccessibleLabel(entry, semantics)

  const meta =
    semantics.kind === 'shortcut' ? (
      <span className="le-sidebar__link-meta" aria-hidden="true">
        <span className="le-sidebar__pill">Shortcut</span>
        <span className="le-sidebar__link-dest">Opens in {semantics.ownerSectionLabel}</span>
      </span>
    ) : semantics.kind === 'classic' ? (
      <span className="le-sidebar__link-meta" aria-hidden="true">
        <span className="le-sidebar__pill le-sidebar__pill--classic">{FULL_WORKSPACE_UI.pill}</span>
        <span className="le-sidebar__link-dest">{semantics.hint}</span>
      </span>
    ) : semantics.kind === 'external' ? (
      <span className="le-sidebar__link-meta" aria-hidden="true">
        <span className="le-sidebar__pill le-sidebar__pill--external">External</span>
        <span className="le-sidebar__link-dest">{semantics.hint}</span>
      </span>
    ) : null

  const extraClass =
    semantics.kind === 'native'
      ? ''
      : semantics.kind === 'shortcut'
        ? ' le-sidebar__link--shortcut'
        : ' le-sidebar__link--out-of-section'

  const navIntent: StudioTelemetryNavIntent =
    semantics.kind === 'shortcut'
      ? 'shortcut'
      : semantics.kind === 'classic'
        ? 'classic'
        : semantics.kind === 'external'
          ? 'external'
          : 'native'

  function onSidebarActivate() {
    recordSidebarNavClick(navIntent, entry.label, entry.to ?? entry.href ?? '')
  }

  if (entry.disabled) {
    return (
      <span className="le-sidebar__link le-sidebar__link--disabled" title="Not available yet">
        {entry.label}
      </span>
    )
  }
  if (entry.href) {
    return (
      <a
        className={`le-sidebar__link${extraClass}`}
        href={entry.href}
        aria-label={a11y}
        onClick={onSidebarActivate}
        {...(entry.external ? { target: '_blank', rel: 'noreferrer' } : {})}
      >
        <span className="le-sidebar__link-stack">
          <span className="le-sidebar__link-primary">
            {entry.label}
            {entry.external ? <span className="le-sidebar__external-hint"> ↗</span> : null}
          </span>
          {meta}
        </span>
      </a>
    )
  }
  if (entry.to) {
    return (
      <NavLink
        className={({ isActive }) =>
          `le-sidebar__link${isActive ? ' le-sidebar__link--active' : ''}${extraClass}`
        }
        to={entry.to}
        end={entry.to ? studioNavLinkEnd(entry.to) : false}
        aria-label={a11y}
        onClick={onSidebarActivate}
      >
        <span className="le-sidebar__link-stack">
          <span className="le-sidebar__link-primary">{entry.label}</span>
          {meta}
        </span>
      </NavLink>
    )
  }
  return null
}

export function SectionSidebar() {
  const { mode } = useNavigationMode()
  const { state } = useWorkspace()
  const location = useLocation()
  const { name: projectName } = useParams<{ name?: string }>()
  const section = resolveTopSection(location.pathname, location.search, mode)
  const browseSiteName = state?.websites?.[0]?.name
  const main = withPlanningScopeOnSideNavEntries(
    getSideNavEntries(section, mode, projectName, browseSiteName),
    location.search,
  )
  const rows = buildSidebarRows(main)

  const sectionRailHint = SHELL_RAIL_HINT[section]

  return (
    <aside className="le-sidebar" aria-label={`${getPrimarySectionLabel(section)} navigation`}>
      <div className="le-sidebar__block">
        <h2 className="le-sidebar__heading">{getPrimarySectionLabel(section)}</h2>
        <p className="le-sidebar__hint" id="le-sidebar-hint">
          {sectionRailHint}
        </p>
        <ul className="le-sidebar__list" aria-describedby="le-sidebar-hint">
          {rows.map((row, ri) =>
            row.kind === 'single' ? (
              <li key={`single-${row.entry.label}-${ri}`}>
                <SideNavLink entry={linkEntry(row.entry)} section={section} />
              </li>
            ) : row.kind === 'nav_section' ? (
              <li key={`navsec-${row.group}-${ri}`} className="le-sidebar__section-wrap">
                {(() => {
                  const meta = navSectionHeadingHint(row.group)
                  const hid = `le-sidebar-sec-${row.group}-${ri}`
                  const did = `le-sidebar-sec-desc-${row.group}-${ri}`
                  return (
                    <>
                      <div className="le-sidebar__section-head" id={hid}>
                        {meta.heading}
                      </div>
                      <p className="le-sidebar__section-hint forge-support" id={did}>
                        {meta.hint}
                      </p>
                      <ul className="le-sidebar__section-list" aria-labelledby={hid} aria-describedby={did}>
                        {row.entries.map((entry, j) => (
                          <li key={`${entry.label}-${j}`}>
                            <SideNavLink entry={linkEntry(entry)} section={section} />
                          </li>
                        ))}
                      </ul>
                    </>
                  )
                })()}
              </li>
            ) : row.kind === 'utilities' ? (
              <li key={`util-${ri}`} className="le-sidebar__utilities-wrap">
                <div className="le-sidebar__utilities-head" id={`le-sidebar-util-${ri}`}>
                  {STUDIO_UTILITIES.sidebarGroupLabel}
                </div>
                <p className="le-sidebar__utilities-hint forge-support">Same shortcuts as the header.</p>
                <ul className="le-sidebar__utilities-list" aria-labelledby={`le-sidebar-util-${ri}`}>
                  {row.entries.map((entry, j) => (
                    <li key={`${entry.label}-${j}`}>
                      <SideNavLink entry={linkEntry(entry)} section={section} />
                    </li>
                  ))}
                </ul>
              </li>
            ) : (
              <li key={`adv-${ri}`} className="le-sidebar__advanced-wrap">
                <details className="le-sidebar__advanced-details">
                  <summary className="le-sidebar__advanced-summary">{WORK_SECTION_ADVANCED_NAV.summary}</summary>
                  <p className="le-sidebar__advanced-hint forge-support" id={`le-sidebar-adv-hint-${ri}`}>
                    {WORK_SECTION_ADVANCED_NAV.hint}
                  </p>
                  <ul className="le-sidebar__advanced-list" aria-describedby={`le-sidebar-adv-hint-${ri}`}>
                    {row.entries.map((entry, j) => (
                      <li key={`${entry.label}-${j}`}>
                        <SideNavLink entry={linkEntry(entry)} section={section} />
                      </li>
                    ))}
                  </ul>
                </details>
              </li>
            ),
          )}
        </ul>
      </div>
    </aside>
  )
}
