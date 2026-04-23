import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { CommandMode } from '../commandBar/commandBarTypes'
import { StudioCommandBar } from '../components/StudioCommandBar'
import { recordCommandBar } from '../telemetry/studioTelemetry'
import { LensesCopilotPageScopeProvider } from './LensesCopilotPageScopeContext'

export type StudioCommandBarOpenOptions = {
  initialQuery?: string
}

type StudioCommandBarCtx = {
  isOpen: boolean
  open: (mode?: CommandMode, options?: StudioCommandBarOpenOptions) => void
  close: () => void
  lastMode: CommandMode
}

const StudioCommandBarContext = createContext<StudioCommandBarCtx | null>(null)

export function StudioCommandBarProvider({ children }: { children: ReactNode }) {
  const [isOpen, setOpen] = useState(false)
  const [launch, setLaunch] = useState<{ mode: CommandMode; initialQuery: string }>({
    mode: 'find',
    initialQuery: '',
  })
  const [lastMode, setLastMode] = useState<CommandMode>('find')

  const open = useCallback((mode: CommandMode = 'find', options?: StudioCommandBarOpenOptions) => {
    setLaunch({
      mode,
      initialQuery: options?.initialQuery ?? '',
    })
    setLastMode(mode)
    setOpen(true)
    recordCommandBar('open', { mode })
  }, [])

  const close = useCallback(() => {
    setOpen(false)
    recordCommandBar('close', {})
  }, [])

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== 'k' && e.key !== 'K') return
      if (!(e.metaKey || e.ctrlKey)) return
      if (e.altKey || e.shiftKey) return
      const t = e.target
      if (t instanceof HTMLInputElement || t instanceof HTMLTextAreaElement || t instanceof HTMLSelectElement) {
        return
      }
      if (t instanceof HTMLElement && t.isContentEditable) return
      if (document.querySelector('[role="dialog"][aria-modal="true"]')) return
      e.preventDefault()
      open('find')
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open])

  const value = useMemo(
    () => ({
      isOpen,
      open,
      close,
      lastMode,
    }),
    [isOpen, open, close, lastMode],
  )

  return (
    <StudioCommandBarContext.Provider value={value}>
      <LensesCopilotPageScopeProvider>
        {children}
        {isOpen ? (
          <StudioCommandBar
            key={`${launch.mode}-${launch.initialQuery}`}
            initialMode={launch.mode}
            initialQuery={launch.initialQuery}
            onClose={close}
          />
        ) : null}
      </LensesCopilotPageScopeProvider>
    </StudioCommandBarContext.Provider>
  )
}

export function useStudioCommandBar(): StudioCommandBarCtx {
  const v = useContext(StudioCommandBarContext)
  if (!v) throw new Error('useStudioCommandBar requires StudioCommandBarProvider')
  return v
}
