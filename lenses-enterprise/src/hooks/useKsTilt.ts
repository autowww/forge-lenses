import { useEffect, useRef } from 'react'

/**
 * Cursor-driven perspective tilt matching Kitchen Sink `ks-tilt-tiles.js`
 * (`.ks-tilt-wrap` + `.ks-tilt-inner`). Required for React because the global
 * script only runs on DOMContentLoaded.
 */
export function useKsTilt(maxDeg = 10) {
  const wrapRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const wrap = wrapRef.current
    if (!wrap) return
    const inner = wrap.querySelector('.ks-tilt-inner') as HTMLElement | null
    if (!inner) return

    const mqReduce = window.matchMedia('(prefers-reduced-motion: reduce)')
    const mqCoarse = window.matchMedia('(pointer: coarse)')
    const capped = Math.min(Math.max(maxDeg, 0.5), 24)

    const off = () => mqReduce.matches || mqCoarse.matches

    const onMove = (ev: PointerEvent) => {
      if (off()) return
      wrap.classList.add('ks-tilt-wrap--tracking')
      const r = wrap.getBoundingClientRect()
      if (r.width < 1 || r.height < 1) return
      let mx = ((ev.clientX - r.left) / r.width - 0.5) * 2
      let my = ((ev.clientY - r.top) / r.height - 0.5) * 2
      mx = Math.max(-1, Math.min(1, mx))
      my = Math.max(-1, Math.min(1, my))
      const rx = -my * capped
      const ry = mx * capped
      inner.style.transform = `rotateX(${rx}deg) rotateY(${ry}deg) translateZ(8px)`
    }

    const onLeave = () => {
      wrap.classList.remove('ks-tilt-wrap--tracking')
      inner.style.transform = ''
    }

    wrap.addEventListener('pointermove', onMove)
    wrap.addEventListener('pointerleave', onLeave)
    wrap.addEventListener('pointercancel', onLeave)
    return () => {
      wrap.removeEventListener('pointermove', onMove)
      wrap.removeEventListener('pointerleave', onLeave)
      wrap.removeEventListener('pointercancel', onLeave)
      inner.style.transform = ''
    }
  }, [maxDeg])

  return wrapRef
}
