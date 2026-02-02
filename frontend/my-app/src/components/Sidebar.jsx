import './Sidebar.css';

const Sidebar = ({ activeView, onViewChange }) => {
  const views = [
    { id: 'explorer', icon: '📁', label: 'Explorer', shortcut: 'Ctrl+Shift+E' },
    { id: 'search', icon: '🔍', label: 'Search', shortcut: 'Ctrl+Shift+F' },
    { id: 'git', icon: '⎇', label: 'Source Control', shortcut: 'Ctrl+Shift+G' },
    { id: 'debug', icon: '▶', label: 'Run and Debug', shortcut: 'Ctrl+Shift+D' },
    { id: 'extensions', icon: '⊞', label: 'Extensions', shortcut: 'Ctrl+Shift+X' }
  ];

  const bottomViews = [
    { id: 'account', icon: '👤', label: 'Account' },
    { id: 'settings', icon: '⚙', label: 'Settings', shortcut: 'Ctrl+,' }
  ];

  return (
    <div className="activity-bar">
      <div className="activity-bar-top">
        {views.map(view => (
          <button
            key={view.id}
            className={`activity-btn ${activeView === view.id ? 'active' : ''}`}
            onClick={() => onViewChange(view.id)}
            title={`${view.label} (${view.shortcut})`}
          >
            <span className="activity-icon">{view.icon}</span>
          </button>
        ))}
      </div>
      <div className="activity-bar-bottom">
        {bottomViews.map(view => (
          <button
            key={view.id}
            className={`activity-btn ${activeView === view.id ? 'active' : ''}`}
            onClick={() => onViewChange(view.id)}
            title={view.shortcut ? `${view.label} (${view.shortcut})` : view.label}
          >
            <span className="activity-icon">{view.icon}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default Sidebar;
