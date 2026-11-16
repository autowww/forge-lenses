import { createContext } from 'react'
import type { NavMode } from './workspaceLensCookie'

export type NavModeContextValue = {
  mode: NavMode
  setMode: (m: NavMode) => void
}

export const NavModeContext = createContext<NavModeContextValue | null>(null)
