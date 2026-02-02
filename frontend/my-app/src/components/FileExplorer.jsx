import { useState, useEffect } from 'react';
import './FileExplorer.css';

const FileExplorer = ({ onFileSelect, currentFile, openFiles }) => {
  const [recentFiles, setRecentFiles] = useState([]);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const fileIcons = {
    js: '📜',
    jsx: '⚛️',
    ts: '💙',
    tsx: '⚛️',
    py: '🐍',
    java: '☕',
    html: '🌐',
    css: '🎨',
    json: '📋',
    md: '📝',
    txt: '📄',
    default: '📄'
  };

  const getFileIcon = (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    return fileIcons[ext] || fileIcons.default;
  };

  const getFileState = (file) => {
    if (!file) return '';
    if (file.isModified) return 'modified';
    if (file.isNew) return 'unsaved';
    return 'saved';
  };

  const handleOpenFile = async () => {
    if (window.electronAPI) {
      const file = await window.electronAPI.openFile();
      if (file) {
        onFileSelect(file);
        // Add to recent files
        setRecentFiles(prev => {
          const filtered = prev.filter(f => f.path !== file.path);
          return [file, ...filtered].slice(0, 10);
        });
      }
    }
  };

  const handleOpenFolder = async () => {
    // Placeholder for folder opening
    console.log('Open folder functionality coming soon...');
  };

  return (
    <div className={`file-explorer ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="explorer-header">
        <div className="explorer-title">
          <button 
            className="collapse-btn"
            onClick={() => setIsCollapsed(!isCollapsed)}
          >
            {isCollapsed ? '▶' : '▼'}
          </button>
          <span>EXPLORER</span>
        </div>
        <div className="explorer-actions">
          <button className="icon-btn" onClick={handleOpenFile} title="Open File">
            <span>📄</span>
          </button>
          <button className="icon-btn" onClick={handleOpenFolder} title="Open Folder">
            <span>📁</span>
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <>
          {/* Open Editors Section */}
          {openFiles && openFiles.length > 0 && (
            <div className="explorer-section">
              <div className="section-header">
                <span className="section-arrow">▼</span>
                <span className="section-title">OPEN EDITORS</span>
                <span className="section-badge">{openFiles.length}</span>
              </div>
              <div className="file-list">
                {openFiles.map((file, idx) => (
                  <div
                    key={idx}
                    className={`file-item ${currentFile?.path === file.path ? 'active' : ''} ${getFileState(file)}`}
                    onClick={() => onFileSelect(file)}
                  >
                    <span className="file-icon">{getFileIcon(file.name)}</span>
                    <span className="file-name">{file.name}</span>
                    {file.isModified && <span className="file-indicator">●</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recent Files Section */}
          {recentFiles.length > 0 && (
            <div className="explorer-section">
              <div className="section-header">
                <span className="section-arrow">▼</span>
                <span className="section-title">RECENT</span>
              </div>
              <div className="file-list">
                {recentFiles.map((file, idx) => (
                  <div
                    key={idx}
                    className="file-item"
                    onClick={() => onFileSelect(file)}
                  >
                    <span className="file-icon">{getFileIcon(file.name)}</span>
                    <span className="file-name">{file.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick Actions */}
          <div className="explorer-section">
            <div className="section-header">
              <span className="section-arrow">▼</span>
              <span className="section-title">QUICK ACTIONS</span>
            </div>
            <div className="quick-actions">
              <button className="action-btn" onClick={handleOpenFile}>
                <span className="action-icon">📂</span>
                <span className="action-text">Open File</span>
              </button>
              <button className="action-btn" onClick={handleOpenFolder}>
                <span className="action-icon">📁</span>
                <span className="action-text">Open Folder</span>
              </button>
            </div>
          </div>

          {/* Getting Started */}
          {openFiles.length === 0 && recentFiles.length === 0 && (
            <div className="explorer-empty">
              <p className="empty-message">You have not yet opened a file or folder.</p>
              <button className="primary-btn" onClick={handleOpenFile}>
                Open File
              </button>
              <button className="secondary-btn" onClick={handleOpenFolder}>
                Open Folder
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default FileExplorer;
