import './StatusBar.css';

const StatusBar = ({ 
  currentFile, 
  language, 
  lineCount, 
  charCount, 
  cursorPosition,
  hasErrors 
}) => {
  return (
    <div className="status-bar">
      <div className="status-left">
        <button className="status-item clickable" title="Git Branch">
          <span className="status-icon">⎇</span>
          <span>main</span>
        </button>
        {hasErrors && (
          <>
            <button className="status-item clickable error" title="Errors">
              <span className="status-icon">✕</span>
              <span>0</span>
            </button>
            <button className="status-item clickable warning" title="Warnings">
              <span className="status-icon">⚠</span>
              <span>0</span>
            </button>
          </>
        )}
      </div>
      
      <div className="status-right">
        <button className="status-item clickable" title="Select Language Mode">
          <span className="status-icon">📝</span>
          <span>{language || 'Plain Text'}</span>
        </button>
        <span className="status-item" title="Line Ending">
          <span>LF</span>
        </span>
        <span className="status-item" title="Encoding">
          <span>UTF-8</span>
        </span>
        <button className="status-item clickable" title="Go to Line/Column">
          <span>Ln {cursorPosition?.line || 1}, Col {cursorPosition?.column || 1}</span>
        </button>
        <span className="status-item" title="Lines/Characters">
          <span>{lineCount || 0} lines, {charCount || 0} chars</span>
        </span>
        <button className="status-item clickable" title="Notifications">
          <span className="status-icon">🔔</span>
        </button>
      </div>
    </div>
  );
};

export default StatusBar;
