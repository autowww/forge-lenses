/** Injected by `forge-lenses/desktop/preload.js` when running Forge Studio in Electron (frameless window). */
export type LensesElectronApi = {
  minimize: () => Promise<void>
  maximize: () => Promise<void>
  close: () => Promise<void>
  isMaximized: () => Promise<boolean>
  platform: string
  onMaximizedChange: (callback: (maximized: boolean) => void) => () => void
}

declare global {
  interface Window {
    lensesElectron?: LensesElectronApi
  }
}

export {}
