import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { ReleaseNotesModal } from '../components/ReleaseNotesModal'

type Ctx = { openReleaseNotes: () => void }

const ReleaseNotesContext = createContext<Ctx | null>(null)

export function ReleaseNotesProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const openReleaseNotes = useCallback(() => setOpen(true), [])
  const closeReleaseNotes = useCallback(() => setOpen(false), [])

  return (
    <ReleaseNotesContext.Provider value={{ openReleaseNotes }}>
      {children}
      <ReleaseNotesModal open={open} onClose={closeReleaseNotes} />
    </ReleaseNotesContext.Provider>
  )
}

export function useReleaseNotes() {
  const c = useContext(ReleaseNotesContext)
  if (!c) throw new Error('useReleaseNotes must be used within ReleaseNotesProvider')
  return c
}
