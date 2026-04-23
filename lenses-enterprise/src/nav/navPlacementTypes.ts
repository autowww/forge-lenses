/** Top bar + sidebar placement (shared by navigationConfig and studioRouteRegistry). */

export type TopSectionId = 'home' | 'work' | 'projects' | 'knowledge' | 'publish'

export type SideNavEntry = {
  label: string
  to?: string
  /** Same-origin path outside SPA (e.g. classic roadmaps) */
  href?: string
  external?: boolean
  disabled?: boolean
  /**
   * - `utilities` — compact “Tools” heading (mirrors header).
   * - `work_advanced` — collapsed “Advanced & legacy” block (Work section, Sprint UX4).
   * - `knowledge_*` / `publish_*` — grouped section headings in the section sidebar (Sprint UX6).
   */
  sidebarGroup?:
    | 'utilities'
    | 'work_advanced'
    | 'knowledge_learn'
    | 'knowledge_evidence'
    | 'knowledge_govern'
    | 'knowledge_build'
    | 'publish_sites'
    | 'publish_stories'
}
