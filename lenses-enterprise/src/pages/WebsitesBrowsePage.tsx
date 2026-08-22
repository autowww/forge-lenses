import { useParams } from 'react-router-dom'
import { SitePreviewShell } from '../components/sites/SitePreviewShell'

/** Published site preview — canonical Studio route for static /local-site output. */
export function WebsitesBrowsePage() {
  const { site = '', '*': tail = '' } = useParams()
  return <SitePreviewShell siteName={site} subpath={tail} validateWorkspace />
}
