import { useState } from 'react';
import './MenuBar.css';

const MenuBar = ({ onAction }) => {
  const [activeMenu, setActiveMenu] = useState(null);

  const menus = [
    {
      label: 'File',
      items: [
        { label: 'New File', shortcut: 'Ctrl+N', action: 'new' },
        { label: 'Open File...', shortcut: 'Ctrl+O', action: 'open' },
        { label: 'Open Folder...', shortcut: 'Ctrl+K Ctrl+O', action: 'openFolder' },
        { type: 'separator' },
        { label: 'Save', shortcut: 'Ctrl+S', action: 'save' },
        { label: 'Save As...', shortcut: 'Ctrl+Shift+S', action: 'saveAs' },
        { type: 'separator' },
        { label: 'Close Editor', shortcut: 'Ctrl+W', action: 'close' },
      ]
    },
    {
      label: 'Edit',
      items: [
        { label: 'Undo', shortcut: 'Ctrl+Z', action: 'undo' },
        { label: 'Redo', shortcut: 'Ctrl+Y', action: 'redo' },
        { type: 'separator' },
        { label: 'Cut', shortcut: 'Ctrl+X', action: 'cut' },
        { label: 'Copy', shortcut: 'Ctrl+C', action: 'copy' },
        { label: 'Paste', shortcut: 'Ctrl+V', action: 'paste' },
        { type: 'separator' },
        { label: 'Find', shortcut: 'Ctrl+F', action: 'find' },
        { label: 'Replace', shortcut: 'Ctrl+H', action: 'replace' },
      ]
    },
    {
      label: 'Selection',
      items: [
        { label: 'Select All', shortcut: 'Ctrl+A', action: 'selectAll' },
        { label: 'Expand Selection', shortcut: 'Shift+Alt+Right', action: 'expandSelection' },
        { label: 'Shrink Selection', shortcut: 'Shift+Alt+Left', action: 'shrinkSelection' },
      ]
    },
    {
      label: 'View',
      items: [
        { label: 'Command Palette', shortcut: 'Ctrl+Shift+P', action: 'commandPalette' },
        { type: 'separator' },
        { label: 'Explorer', shortcut: 'Ctrl+Shift+E', action: 'toggleExplorer' },
        { label: 'Search', shortcut: 'Ctrl+Shift+F', action: 'toggleSearch' },
        { type: 'separator' },
        { label: 'Terminal', shortcut: 'Ctrl+`', action: 'toggleTerminal' },
        { label: 'Output', shortcut: 'Ctrl+Shift+U', action: 'toggleOutput' },
        { type: 'separator' },
        { label: 'Theme: Tokyo Night', action: 'themeTokyoNight' },
        { label: 'Theme: Doodle Light', action: 'themeDoodleLight' },
        { label: 'Theme: Doodle Dark', action: 'themeDoodleDark' },
        { label: 'Theme: Doodle White', action: 'themeDoodleWhite' },
      ]
    },
    {
      label: 'Go',
      items: [
        { label: 'Go to File...', shortcut: 'Ctrl+P', action: 'goToFile' },
        { label: 'Go to Line...', shortcut: 'Ctrl+G', action: 'goToLine' },
        { label: 'Go to Symbol...', shortcut: 'Ctrl+Shift+O', action: 'goToSymbol' },
      ]
    },
    {
      label: 'Run',
      items: [
        { label: 'Run Code', shortcut: 'F5', action: 'run' },
        { label: 'Run Without Debugging', shortcut: 'Ctrl+F5', action: 'runWithoutDebug' },
        { type: 'separator' },
        { label: 'Stop', shortcut: 'Shift+F5', action: 'stop' },
      ]
    },
    {
      label: 'Terminal',
      items: [
        { label: 'New Terminal', shortcut: 'Ctrl+Shift+`', action: 'newTerminal' },
        { label: 'Split Terminal', shortcut: 'Ctrl+Shift+5', action: 'splitTerminal' },
        { type: 'separator' },
        { label: 'Clear Terminal', action: 'clearTerminal' },
      ]
    },
    {
      label: 'Help',
      items: [
        { label: 'Welcome', action: 'welcome' },
        { label: 'Documentation', action: 'docs' },
        { type: 'separator' },
        { label: 'Guided Tour', action: 'guidedTour' },
        { type: 'separator' },
        { label: 'About', action: 'about' },
      ]
    }
  ];

  const handleMenuClick = (menuLabel) => {
    setActiveMenu(activeMenu === menuLabel ? null : menuLabel);
  };

  const handleItemClick = (action) => {
    setActiveMenu(null);
    if (onAction) {
      onAction(action);
    }
  };

  return (
    <div className="menu-bar">
      <div className="menu-bar-left">
        <div className="app-icon">⚡</div>
        <div className="menu-items">
          {menus.map((menu) => (
            <div key={menu.label} className="menu-item">
              <button
                className={`menu-button ${activeMenu === menu.label ? 'active' : ''}`}
                onClick={() => handleMenuClick(menu.label)}
              >
                {menu.label}
              </button>
              {activeMenu === menu.label && (
                <div className="menu-dropdown">
                  {menu.items.map((item, idx) => (
                    item.type === 'separator' ? (
                      <div key={idx} className="menu-separator" />
                    ) : (
                      <button
                        key={idx}
                        className="menu-dropdown-item"
                        onClick={() => handleItemClick(item.action)}
                      >
                        <span className="menu-item-label">{item.label}</span>
                        {item.shortcut && (
                          <span className="menu-item-shortcut">{item.shortcut}</span>
                        )}
                      </button>
                    )
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="menu-bar-center">
        <span className="app-title">Opsis Code Editor</span>
      </div>
    </div>
  );
};

export default MenuBar;
