import { useState, useEffect } from 'react'
import CodeEditor from './components/CodeEditor'
import LoadingScreen from './components/LoadingScreen'
import './App.css'

const THEME_KEY = 'opsis-app-theme'
const VALID_THEMES = ['tokyo-night', 'doodle-light', 'doodle-dark', 'doodle-white']

function readStoredTheme() {
  try {
    const v = localStorage.getItem(THEME_KEY)
    return VALID_THEMES.includes(v) ? v : 'tokyo-night'
  } catch {
    return 'tokyo-night'
  }
}

function App() {
  const [isLoading, setIsLoading] = useState(true)
  const [appTheme, setAppTheme] = useState(readStoredTheme)

  useEffect(() => {
    document.documentElement.dataset.appTheme = appTheme
    try {
      localStorage.setItem(THEME_KEY, appTheme)
    } catch {
      /* ignore */
    }
  }, [appTheme])

  const handleLoadComplete = () => {
    setIsLoading(false)
  }

  return (
    <div className="App">
      {isLoading ? (
        <LoadingScreen onLoadComplete={handleLoadComplete} />
      ) : (
        <CodeEditor appTheme={appTheme} onAppThemeChange={setAppTheme} />
      )}
    </div>
  )
}

export default App
