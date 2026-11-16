export type FeatureShowcaseItem = {
  id: string
  heading: string
  summary: string
  description?: string
  backgroundImage: { src: string; alt?: string }
  mainImage: { src: string; alt: string }
  cta: { label: string; href: string }
}

export type FeatureShowcaseProps = {
  items: FeatureShowcaseItem[]
  /** Section heading for aria-labelledby; rendered as h2 when set */
  title?: string
  /** id for aria-labelledby; auto-generated if title set without id */
  titleId?: string
  /** Sticky panel + parallax target id */
  visualPanelId?: string
  /** Vertical parallax range in px (background vs foreground move in opposite directions) */
  parallaxPx?: number
  /** IntersectionObserver rootMargin; more negative = narrower “active” band in viewport */
  observerRootMargin?: string
  /** Extra classes on the outer `<section>` */
  className?: string
}
