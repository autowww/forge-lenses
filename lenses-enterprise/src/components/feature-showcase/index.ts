/**
 * Feature showcase (scrollytelling)
 *
 * Customization:
 * - Content: edit `exampleFeatureShowcaseItems` or pass `items` to `<FeatureShowcase />`.
 * - Images: replace `src` strings (public assets or CDN). `backgroundImage.alt` can be "" for decorative.
 * - Motion: `parallaxPx` (default 12) — lower = subtler; set `0` to rely on reduced-motion only.
 * - Scroll sensitivity: `observerRootMargin` (default `-38% 0px -38% 0px`) — more negative = smaller band.
 */
export { FeatureShowcase } from './FeatureShowcase'
export type { FeatureShowcaseItem, FeatureShowcaseProps } from './types'
export { exampleFeatureShowcaseItems } from './featureShowcaseData.example'
export { FeatureItemButton } from './FeatureItemButton'
export { FeatureVisualPanel } from './FeatureVisualPanel'
export { useActiveFeatureIndex } from './useActiveFeatureIndex'
