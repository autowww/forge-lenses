import { useContext } from 'react'
import { NavModeContext, type NavModeContextValue } from './navModeContext'

export function useNavigationMode(): NavModeContextValue {
  const ctx = useContext(NavModeContext)
  if (!ctx) {
    throw new Error('useNavigationMode must be used within NavModeProvider')
  }
  return ctx
}
