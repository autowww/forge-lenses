/** Electron shell mode from `forge-lenses/desktop/preload.js`. */
export type LensesElectronStudioMode = 'studio' | 'virtual-camera'

export function lensesElectronStudioMode(): LensesElectronStudioMode | null {
  if (typeof window === 'undefined') return null
  const mode = window.lensesElectron?.studioMode
  if (mode === 'studio' || mode === 'virtual-camera') return mode
  return null
}

export function virtualCameraElectronMode(): boolean {
  return lensesElectronStudioMode() === 'virtual-camera'
}
