import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import '../../kitchensink/css/fs-sticker-board.css'
import { StickerboardGuestApp } from './StickerboardGuestApp'

/** Guest links use ``{public_base}#/{token}`` (hash routing). Legacy path URLs redirect on load. */
function redirectLegacyPathTokenToHash(): void {
  const path = window.location.pathname
  let token = ''
  if (path.startsWith('/stickerboard/')) {
    const rest = path.slice('/stickerboard/'.length).replace(/\/$/, '')
    if (rest && !rest.includes('/')) token = rest
  } else {
    const seg = path.replace(/^\//, '').split('/')[0] ?? ''
    if (seg && !['assets', '__ks', 'api', 'stickerboard', ''].includes(seg)) {
      token = seg
    }
  }
  if (!token || window.location.hash.replace(/^#\/?/, '').split('/')[0]) return
  const basePath = path.startsWith('/stickerboard')
    ? path.split('/').slice(0, 2).join('/') || '/stickerboard'
    : '/'
  window.location.replace(`${basePath}/#/${encodeURIComponent(token)}`)
}

redirectLegacyPathTokenToHash()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HashRouter>
      <Routes>
        <Route path="/:shareToken" element={<StickerboardGuestApp />} />
      </Routes>
    </HashRouter>
  </StrictMode>,
)
