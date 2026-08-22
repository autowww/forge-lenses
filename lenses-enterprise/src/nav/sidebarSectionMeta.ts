import type { SideNavEntry } from './navPlacementTypes'
import { KNOWLEDGE_SECTION_NAV, PUBLISH_SECTION_NAV } from './studioVisibleCopy'

/** Sidebar groups rendered as titled sections (Sprint UX6). */
export type NavSectionRowGroup =
  | 'knowledge_learn'
  | 'knowledge_evidence'
  | 'knowledge_govern'
  | 'knowledge_labs'
  | 'knowledge_build'
  | 'publish_sites'
  | 'publish_stories'

export function isNavSectionRowGroup(g: SideNavEntry['sidebarGroup']): g is NavSectionRowGroup {
  return (
    g === 'knowledge_learn' ||
    g === 'knowledge_evidence' ||
    g === 'knowledge_govern' ||
    g === 'knowledge_labs' ||
    g === 'knowledge_build' ||
    g === 'publish_sites' ||
    g === 'publish_stories'
  )
}

export function navSectionHeadingHint(group: NavSectionRowGroup): { heading: string; hint: string } {
  switch (group) {
    case 'knowledge_learn':
      return { heading: KNOWLEDGE_SECTION_NAV.learnHeading, hint: KNOWLEDGE_SECTION_NAV.learnHint }
    case 'knowledge_evidence':
      return { heading: KNOWLEDGE_SECTION_NAV.evidenceHeading, hint: KNOWLEDGE_SECTION_NAV.evidenceHint }
    case 'knowledge_govern':
      return { heading: KNOWLEDGE_SECTION_NAV.governHeading, hint: KNOWLEDGE_SECTION_NAV.governHint }
    case 'knowledge_labs':
      return { heading: KNOWLEDGE_SECTION_NAV.labsHeading, hint: KNOWLEDGE_SECTION_NAV.labsHint }
    case 'knowledge_build':
      return { heading: KNOWLEDGE_SECTION_NAV.buildHeading, hint: KNOWLEDGE_SECTION_NAV.buildHint }
    case 'publish_sites':
      return { heading: PUBLISH_SECTION_NAV.shippedHeading, hint: PUBLISH_SECTION_NAV.shippedHint }
    case 'publish_stories':
      return { heading: PUBLISH_SECTION_NAV.storiesHeading, hint: PUBLISH_SECTION_NAV.storiesHint }
  }
}
