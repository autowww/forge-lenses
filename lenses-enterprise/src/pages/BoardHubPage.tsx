import { BoardsArtifactsHub } from '../components/boards'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { useNavigationMode } from '../nav/useNavigationMode'

export function BoardHubPage() {
  useLensesCopilotPage({ route: 'board' })
  const { mode } = useNavigationMode()
  return <BoardsArtifactsHub variant={mode === 'artifacts' ? 'artifacts' : 'flow'} />
}
