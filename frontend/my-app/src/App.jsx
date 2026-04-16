import { useState, useEffect } from 'react';
import { HashRouter, Routes, Route, useLocation } from 'react-router-dom';
import CodeEditor from './components/CodeEditor';
import LandingPage from './components/LandingPage';
import AuthPage from './components/AuthPage';
import LoadingScreen from './components/LoadingScreen';
import './App.css';

const THEME_KEY = 'opsis-app-theme';
const VALID_THEMES = ['tokyo-night', 'doodle-light', 'doodle-dark', 'doodle-white'];

function readStoredTheme() {
  try {
    const v = localStorage.getItem(THEME_KEY);
    return VALID_THEMES.includes(v) ? v : 'tokyo-night';
  } catch {
    return 'tokyo-night';
  }
}

// A wrapper for the Editor that receives router navigation state
const EditorWrapper = ({ appTheme, setAppTheme }) => {
  const location = useLocation();
  // We can pass down the isGuest flag based on location state. 
  // It defaults to false unless explicitly set to true.
  const isGuest = location.state?.isGuest || false;
  const userEmail = location.state?.userEmail || '';

  return (
    <CodeEditor 
      appTheme={appTheme} 
      onAppThemeChange={setAppTheme} 
      isGuest={isGuest} 
      userEmail={userEmail}
    />
  );
};

function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [appTheme, setAppTheme] = useState(readStoredTheme);

  useEffect(() => {
    document.documentElement.dataset.appTheme = appTheme;
    try {
      localStorage.setItem(THEME_KEY, appTheme);
    } catch {
      /* ignore */
    }
  }, [appTheme]);

  const handleLoadComplete = () => {
    setIsLoading(false);
  };

  if (isLoading) {
    return (
      <div className="App">
        <LoadingScreen onLoadComplete={handleLoadComplete} />
      </div>
    );
  }

  return (
    <div className="App">
      <HashRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route 
            path="/editor" 
            element={<EditorWrapper appTheme={appTheme} setAppTheme={setAppTheme} />} 
          />
        </Routes>
      </HashRouter>
    </div>
  );
}

export default App;
