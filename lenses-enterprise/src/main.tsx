import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { StudioErrorBoundary } from './components/StudioErrorBoundary'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <StudioErrorBoundary>
      <App />
    </StudioErrorBoundary>
  </StrictMode>,
)
