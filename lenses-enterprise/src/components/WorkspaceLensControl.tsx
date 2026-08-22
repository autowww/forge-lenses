import { useCallback, useState } from 'react'
import type { WorkspaceLensControlProps as KsLensProps } from '../forgesdlc-kitchensink'
import { WorkspaceLensControl as KitchensinkWorkspaceLensControl } from '../forgesdlc-kitchensink'
import { useNavigationMode } from '../nav/useNavigationMode'
import { dismissLensHint, isLensHintDismissed } from '../nav/routeMeta'

export type StudioWorkspaceLensControlProps = {
  /** `toggle` for header chrome; `dropdown` fits settings menus and dense panels. */
  presentation?: KsLensProps['presentation']
  className?: string
}

/**
 * Lenses Studio wiring: navigation mode context.
 * Lens is a saved preference (not a primary top-nav split). Use `presentation="dropdown"` in settings menus.
 */
export function WorkspaceLensControl({
  presentation = 'toggle',
  className = 'le-workspace-lens',
}: StudioWorkspaceLensControlProps) {
  const { mode, setMode } = useNavigationMode()
  const [hintDismissed, setHintDismissed] = useState(() => isLensHintDismissed())

  const onDismissHint = useCallback(() => {
    dismissLensHint()
    setHintDismissed(true)
  }, [])

  return (
    <KitchensinkWorkspaceLensControl
      mode={mode}
      onModeChange={setMode}
      suggestedLens={null}
      hintDismissed={hintDismissed}
      onDismissHint={onDismissHint}
      className={className}
      presentation={presentation}
    />
  )
}
