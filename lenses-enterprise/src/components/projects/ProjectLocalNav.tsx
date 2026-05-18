import { Link, NavLink } from 'react-router-dom'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'

type Props = {
  projectName: string
}

/**
 * In-page subnavigation for a single repository: dashboard, charts, strategy, and notes/evidence.
 */
export function ProjectLocalNav({ projectName }: Props) {
  const enc = encodeURIComponent(projectName)
  const base = `/projects/${enc}`
  const evidenceTo = `/workspace-md?contextProject=${enc}`

  const linkClass = (isActive: boolean) =>
    `le-project-local-nav__link${isActive ? ' le-project-local-nav__link--active' : ''}`

  return (
    <nav className="le-project-local-nav" aria-label={`${projectName} sections`}>
      <ul className="le-project-local-nav__list">
        <li>
          <NavLink to={base} end className={({ isActive }) => linkClass(isActive)}>
            {STUDIO_VOCAB.projectDashboard}
          </NavLink>
        </li>
        <li>
          <NavLink to={`${base}/charts`} className={({ isActive }) => linkClass(isActive)}>
            {STUDIO_VOCAB.repositoryCharts}
          </NavLink>
        </li>
        <li>
          <NavLink to={`${base}/strategy`} className={({ isActive }) => linkClass(isActive)}>
            {STUDIO_VOCAB.architectureStrategy}
          </NavLink>
        </li>
        <li>
          <NavLink to={`${base}/forge-run`} className={({ isActive }) => linkClass(isActive)}>
            {STUDIO_VOCAB.forgePlatformRun}
          </NavLink>
        </li>
        <li>
          <NavLink to={`${base}/docs-health`} className={({ isActive }) => linkClass(isActive)}>
            {STUDIO_VOCAB.docsHealth}
          </NavLink>
        </li>
        <li>
          <NavLink to={`${base}/docs-health/master`} className={({ isActive }) => linkClass(isActive)}>
            {STUDIO_VOCAB.docsHealthMaster}
          </NavLink>
        </li>
        <li>
          <Link className="le-project-local-nav__link le-project-local-nav__link--related" to={evidenceTo}>
            {STUDIO_VOCAB.projectEvidenceBrowse}
          </Link>
        </li>
      </ul>
    </nav>
  )
}
