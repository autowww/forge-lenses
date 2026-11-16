import { AnimatePresence, motion, useReducedMotion, useScroll, useTransform } from 'framer-motion'
import type { RefObject } from 'react'
import type { FeatureShowcaseItem } from './types'

const DEFAULT_TRANSITION = { duration: 0.28, ease: [0.22, 1, 0.36, 1] as const }

type FeatureVisualPanelProps = {
  item: FeatureShowcaseItem
  activeKey: string
  panelId: string
  sectionRef: RefObject<HTMLElement | null>
  parallaxPx: number
}

export function FeatureVisualPanel({
  item,
  activeKey,
  panelId,
  sectionRef,
  parallaxPx,
}: FeatureVisualPanelProps) {
  const reduceMotion = useReducedMotion()
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ['start end', 'end start'],
  })

  const parallaxRange = reduceMotion ? 0 : parallaxPx
  const yBg = useTransform(scrollYProgress, [0, 1], [parallaxRange, -parallaxRange])
  const yFg = useTransform(scrollYProgress, [0, 1], [-parallaxRange * 0.65, parallaxRange * 0.65])

  return (
    <div
      id={panelId}
      className="relative h-[min(42vh,22rem)] w-full overflow-hidden rounded-3xl bg-zinc-900 shadow-2xl ring-1 ring-white/10 lg:aspect-[4/5] lg:max-h-[min(100vh-6rem,44rem)]"
    >
      <motion.div
        className="absolute inset-0 scale-105"
        style={{ y: yBg }}
      >
        <img
          src={item.backgroundImage.src}
          alt=""
          className="h-full w-full object-cover opacity-55"
          decoding="async"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-zinc-950/90 via-zinc-950/25 to-zinc-950/40" />
      </motion.div>

      <div className="relative flex h-full flex-col items-center justify-center p-6 sm:p-8">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={activeKey}
            initial={
              reduceMotion
                ? { opacity: 1 }
                : { opacity: 0, scale: 0.985 }
            }
            animate={{ opacity: 1, scale: 1 }}
            exit={
              reduceMotion
                ? { opacity: 1 }
                : { opacity: 0, scale: 0.99 }
            }
            transition={DEFAULT_TRANSITION}
            className="relative w-full max-w-[min(100%,24rem)]"
            style={{ y: yFg }}
          >
            <div className="overflow-hidden rounded-2xl shadow-[0_24px_64px_-12px_rgba(0,0,0,0.55)] ring-1 ring-white/15">
              <img
                src={item.mainImage.src}
                alt={item.mainImage.alt}
                className="aspect-[4/3] w-full object-cover"
                decoding="async"
              />
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}
