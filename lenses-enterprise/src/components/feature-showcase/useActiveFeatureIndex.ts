import { useCallback, useLayoutEffect, useRef, useState } from 'react'

const DEFAULT_THRESHOLDS = Array.from({ length: 21 }, (_, i) => i / 20)

export type UseActiveFeatureIndexOptions = {
  itemCount: number
  /** Which item is “active” while scrolling (narrower band = snappier changes) */
  rootMargin?: string
  /** Re-run observers when item ids change (e.g. new data) */
  dependencyKey?: string
}

/**
 * Tracks which feature block is most aligned with the viewport “focus” band while scrolling.
 * Click `activate` to jump to an item and sync the sticky visual.
 */
export function useActiveFeatureIndex({
  itemCount,
  rootMargin = '-38% 0px -38% 0px',
  dependencyKey = '',
}: UseActiveFeatureIndexOptions) {
  const [activeIndex, setActiveIndex] = useState(0)
  const itemRefs = useRef<(HTMLDivElement | null)[]>([])
  const ratiosRef = useRef<number[]>([])

  const setItemRef = useCallback((index: number) => (el: HTMLDivElement | null) => {
    itemRefs.current[index] = el
  }, [])

  const activate = useCallback((index: number) => {
    if (index < 0 || index >= itemCount) return
    setActiveIndex(index)
    const el = itemRefs.current[index]
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [itemCount])

  useLayoutEffect(() => {
    ratiosRef.current = new Array(itemCount).fill(0)
  }, [itemCount])

  useLayoutEffect(() => {
    if (itemCount === 0) return

    const observers: IntersectionObserver[] = []

    const pickBest = () => {
      let best = 0
      let bestRatio = -1
      for (let j = 0; j < itemCount; j++) {
        const r = ratiosRef.current[j] ?? 0
        if (r > bestRatio) {
          bestRatio = r
          best = j
        }
      }
      if (bestRatio > 0) {
        setActiveIndex(best)
      }
    }

    for (let i = 0; i < itemCount; i++) {
      const el = itemRefs.current[i]
      if (!el) continue

      const observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            ratiosRef.current[i] = entry.intersectionRatio
          }
          pickBest()
        },
        {
          root: null,
          rootMargin,
          threshold: DEFAULT_THRESHOLDS,
        },
      )
      observer.observe(el)
      observers.push(observer)
    }

    return () => {
      observers.forEach((o) => o.disconnect())
    }
  }, [itemCount, rootMargin, dependencyKey])

  return {
    activeIndex,
    itemRefs,
    setItemRef,
    activate,
  }
}
