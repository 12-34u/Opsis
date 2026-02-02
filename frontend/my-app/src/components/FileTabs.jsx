import { useState } from 'react';
import './FileTabs.css';

const FileTabs = ({ files, activeFile, onTabClick, onTabClose, onNewFile }) => {
  const [hoveredTab, setHoveredTab] = useState(null);

  const getFileIcon = (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    const icons = {
      js: '📜', jsx: '⚛️', ts: '💙', tsx: '⚛️',
      py: '🐍', java: '☕', html: '🌐', css: '🎨',
      json: '📋', md: '📝', txt: '📄'
    };
    return icons[ext] || '📄';
  };

  return (
    <div className="file-tabs">
      <div className="tabs-container">
        {files.map((file, idx) => (
          <div
            key={file.path || idx}
            className={`file-tab ${activeFile?.path === file.path ? 'active' : ''} ${file.isModified ? 'modified' : ''}`}
            onClick={() => onTabClick(file)}
            onMouseEnter={() => setHoveredTab(idx)}
            onMouseLeave={() => setHoveredTab(null)}
          >
            <span className="tab-icon">{getFileIcon(file.name)}</span>
            <span className="tab-name">{file.name}</span>
            {file.isModified && <span className="tab-modified-indicator">●</span>}
            <button
              className={`tab-close ${hoveredTab === idx ? 'visible' : ''}`}
              onClick={(e) => {
                e.stopPropagation();
                onTabClose(file);
              }}
            >
              ×
            </button>
          </div>
        ))}
        <button className="new-tab-btn" onClick={onNewFile} title="New File">
          +
        </button>
      </div>
      <div className="tabs-actions">
        <button className="tab-action-btn" title="Split Editor Right">
          <span>⋮</span>
        </button>
      </div>
    </div>
  );
};

export default FileTabs;
