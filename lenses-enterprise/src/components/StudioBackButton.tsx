import { useNavigate, useLocation } from 'react-router-dom'
import { useNavigationMode } from '../nav/useNavigationMode'
import { getBackTarget } from '../nav/routeMeta'

/** SPA back control: prefers explicit parent from route meta, else browser history one step. */
export function StudioBackButton() {
  const navigate = useNavigate()
  const location = useLocation()
  const { mode } = useNavigationMode()

  const explicit = getBackTarget(location.pathname, location.search, mode)
  const isHome =
    location.pathname === '/' || location.pathname === ''

  if (isHome && !explicit) {
    return null
  }

  const handleClick = () => {
    if (explicit) {
      navigate(explicit)
      return
    }
    navigate(-1)
  }

  return (
    <button
      type="button"
      className="le-back-btn"
      onClick={handleClick}
      aria-label="Go back"
      title="Back"
    >
      <span className="le-back-btn__icon" aria-hidden="true">
        ←
      </span>
      <span className="le-back-btn__text">Back</span>
    </button>
  )
}
