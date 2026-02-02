import { useState } from 'react';
import './BottomPanel.css';

const BottomPanel = ({ output, isRunning, onClear }) => {
  const [activeTab, setActiveTab] = useState('output');
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [panelHeight, setPanelHeight] = useState(250);

  const tabs = [
    { id: 'problems', label: 'Problems', icon: '⚠️', count: 0 },
    { id: 'output', label: 'Output', icon: '📋' },
    { id: 'debug', label: 'Debug Console', icon: '🐛' },
    { id: 'terminal', label: 'Terminal', icon: '❯' },
    { id: 'ports', label: 'Ports', icon: '🔌', count: 0 }
  ];

  return (
    <div 
      className={`bottom-panel ${isCollapsed ? 'collapsed' : ''}`}
      style={{ height: isCollapsed ? '35px' : `${panelHeight}px` }}
    >
      <div className="panel-header">
        <div className="panel-tabs">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`panel-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="tab-icon">{tab.icon}</span>
              <span className="tab-label">{tab.label}</span>
              {tab.count !== undefined && tab.count > 0 && (
                <span className="tab-count">{tab.count}</span>
              )}
            </button>
          ))}
        </div>
        <div className="panel-actions">
          {activeTab === 'output' && (
            <button 
              className="panel-action-btn" 
              onClick={onClear}
              title="Clear Output"
            >
              <span>🗑️</span>
            </button>
          )}
          <button 
            className="panel-action-btn"
            onClick={() => setIsCollapsed(!isCollapsed)}
            title={isCollapsed ? 'Maximize Panel' : 'Minimize Panel'}
          >
            <span>{isCollapsed ? '▲' : '▼'}</span>
          </button>
          <button 
            className="panel-action-btn"
            title="Close Panel"
          >
            <span>×</span>
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <div className="panel-content">
          {activeTab === 'problems' && (
            <div className="panel-view problems-view">
              <div className="empty-state">
                <p>No problems detected in the workspace.</p>
              </div>
            </div>
          )}

          {activeTab === 'output' && (
            <div className="panel-view output-view">
              {isRunning && (
                <div className="output-loading">
                  <span className="spinner">⏳</span>
                  <span>Running code...</span>
                </div>
              )}
              <pre className="output-content">
                {output || 'Output will appear here after running your code...'}
              </pre>
            </div>
          )}

          {activeTab === 'debug' && (
            <div className="panel-view debug-view">
              <div className="empty-state">
                <p>Debug console is ready. Start debugging to see output.</p>
              </div>
            </div>
          )}

          {activeTab === 'terminal' && (
            <div className="panel-view terminal-view">
              <div className="terminal-content">
                <div className="terminal-prompt">
                  <span className="prompt-symbol">❯</span>
                  <span className="prompt-text">Terminal integration coming soon...</span>
                </div>
                <div className="terminal-hint">
                  <p>For now, use the Output tab to see code execution results.</p>
                  <p>Run your code using the Run button or F5.</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'ports' && (
            <div className="panel-view ports-view">
              <div className="empty-state">
                <p>No forwarded ports. Forward a port to access your running services.</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BottomPanel;
