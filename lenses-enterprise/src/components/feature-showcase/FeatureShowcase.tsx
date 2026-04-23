import { useId, useRef } from 'react'
import { FeatureItemButton } from './FeatureItemButton'
import { FeatureVisualPanel } from './FeatureVisualPanel'
import type { FeatureShowcaseItem, FeatureShowcaseProps } from './types'
import { useActiveFeatureIndex } from './useActiveFeatureIndex'

/**
 * Split scrollytelling section: scroll or click left items to drive the sticky visual.
 *
 * Customize: pass `items`, tweak `parallaxPx` / `observerRootMargin`, swap image URLs in data.
 * Stronger scroll snap: tighten `observerRootMargin` (e.g. `-42% 0px -42% 0px`).
 */
export function FeatureShowcase({
  items,
  title,
  titleId: titleIdProp,
  visualPanelId: visualPanelIdProp,
  parallaxPx = 12,
  observerRootMargin,
  className,
}: FeatureShowcaseProps) {
  const sectionRef = useRef<HTMLElement>(null)
  const reactId = useId()
  const titleId = titleIdProp ?? `feature-showcase-h-${reactId.replace(/:/g, '')}`
  const panelId = visualPanelIdProp ?? `feature-showcase-panel-${reactId.replace(/:/g, '')}`

  const count = items.length
  const itemDependencyKey = items.map((x) => x.id).join('|')
  const { activeIndex, setItemRef, activate } = useActiveFeatureIndex({
    itemCount: count,
    rootMargin: observerRootMargin,
    dependencyKey: itemDependencyKey,
  })

  const safeIndex = Math.min(activeIndex, Math.max(0, count - 1))
  const activeItem: FeatureShowcaseItem | undefined = items[safeIndex]
  const liveHeading = activeItem?.heading ?? ''

  if (count === 0) {
    return null
  }

  return (
    <section
      ref={sectionRef}
      className={[
        'mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 lg:py-16',
        className ?? '',
      ].join(' ')}
      aria-labelledby={title ? titleId : undefined}
    >
      {title ? (
        <h2 id={titleId} className="mb-10 max-w-2xl text-3xl font-semibold tracking-tight text-zinc-50 sm:text-4xl">
          {title}
        </h2>
      ) : null}

      <p className="sr-only" aria-live="polite" aria-atomic="true">
        {liveHeading}
      </p>

      <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-2 lg:gap-12 xl:gap-16">
        <div className="order-2 lg:order-1">
          <div role="list" aria-label="Features">
            {items.map((item, i) => (
              <div
                key={item.id}
                ref={setItemRef(i)}
                className="mb-6 scroll-mt-24 last:mb-0 sm:scroll-mt-28"
                role="listitem"
              >
                <FeatureItemButton
                  item={item}
                  isActive={safeIndex === i}
                  onActivate={() => activate(i)}
                  visualPanelId={panelId}
                />
              </div>
            ))}
          </div>
        </div>

        <div className="order-1 z-10 mb-8 lg:order-2 lg:mb-0">
          <div className="sticky top-0 bg-zinc-950/90 pb-1 pt-1 backdrop-blur-sm lg:sticky lg:top-8 lg:bg-transparent lg:pb-0 lg:pt-0 lg:backdrop-blur-none">
            {activeItem ? (
              <FeatureVisualPanel
                item={activeItem}
                activeKey={activeItem.id}
                panelId={panelId}
                sectionRef={sectionRef}
                parallaxPx={parallaxPx}
              />
            ) : null}
          </div>
        </div>
      </div>
    </section>
  )
}
