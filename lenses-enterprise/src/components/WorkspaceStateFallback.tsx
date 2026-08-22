import { useWorkspace } from '../context/WorkspaceContext'
import { StatePanel } from './page'

/** Shown when the shell is visible but workspace state is unexpectedly missing. */
export function WorkspaceStateFallback() {
  const { refresh } = useWorkspace()
  return (
    <StatePanel
      variant="error"
      title="Workspace data is not available"
      description="The workspace scan did not return a payload yet, or the connection was interrupted."
      actions={
        <button type="button" className="le-btn le-btn--primary" onClick={() => void refresh()}>
          Reload workspace
        </button>
      }
    />
  )
}
