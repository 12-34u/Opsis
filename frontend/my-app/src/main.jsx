import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

const THEME_KEY = 'opsis-app-theme'
const VALID_THEMES = ['tokyo-night', 'doodle-light', 'doodle-dark', 'doodle-white']
try {
  const stored = localStorage.getItem(THEME_KEY)
  if (stored && VALID_THEMES.includes(stored)) {
    document.documentElement.dataset.appTheme = stored
  }
} catch {
  /* ignore */
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
