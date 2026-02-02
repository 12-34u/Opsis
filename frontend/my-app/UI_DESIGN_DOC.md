# 🎨 Opsis Code Editor - VS Code UI Design Document

## ✨ Complete UI Redesign - Tokyo Night Theme

The Opsis Code Editor has been completely redesigned to match VS Code's professional interface with a beautiful Tokyo Night color scheme.

---

## 🖥️ Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ ⚡ File  Edit  Selection  View  Go  Run  Terminal  Help    [-][□][×]│  Menu Bar (35px)
├──┬──────────────────────────────────────────────────────────────┤
│📁│ EXPLORER                              📄 📁                  │
│🔍├─────────────────────────────────────────┬──────────────────┤
│⎇ │  ▼ OPEN EDITORS (3)                   │ 📜 welcome.js●   │  File Tabs (35px)
│▶ │    📜 welcome.js ●                     ├──────────────────┤
│⊞ │    🐍 script.py                       │                  │
│  │    ☕ Main.java ●                      │                  │
│  │                                        │   Code Editor    │
│  │  ▼ RECENT                              │    (Monaco)      │
│  │    📜 sample.js                        │                  │
│  │    🐍 test.py                          │                  │
│  │                                        │                  │
│  │  ▼ QUICK ACTIONS                       │                  │
│  │    [📂 Open File]                      ├──────────────────┤
│  │    [📁 Open Folder]                    │⚠️ Problems Output│  Bottom Panel
│  │                                        │                  │  (250px)
│👤│                                        │  Output here...  │
│⚙ │                                        │                  │
├──┴────────────────────────────────────────┴──────────────────┤
│ ⎇ main  ✕ 0  ⚠ 0   📝 JS  LF  UTF-8  Ln 1, Col 1  52 lines 🔔│  Status Bar (22px)
└─────────────────────────────────────────────────────────────────┘

Activity Bar (48px) | Sidebar (280px) | Editor Area (flex) | Status Bar (22px)
```

---

## 🎨 Tokyo Night Color Palette

### Background Colors
- **Primary Background**: `#1a1b26` - Main editor/app background
- **Secondary Background**: `#16161e` - Sidebar, panels
- **Hover**: `#24283b` - Interactive element hover
- **Active**: `#292e42` - Selected items
- **Input**: `#1f2335` - Input fields

### Text Colors
- **Primary Text**: `#c0caf5` - Main text (light blue-white)
- **Secondary Text**: `#7aa2f7` - Links, highlighted text (blue)
- **Muted Text**: `#565f89` - Placeholders, disabled (dark blue)
- **Bright Text**: `#ffffff` - Active selections (white)

### Accent Colors
- **Blue**: `#7aa2f7` - Primary accent, links, active borders
- **Cyan**: `#7dcfff` - Info messages, unsaved indicators
- **Green**: `#9ece6a` - Success messages, terminal prompt
- **Orange**: `#ff9e64` - Modified file indicators, warnings
- **Red**: `#f7768e` - Errors, close buttons
- **Purple**: `#bb9af7` - Special keywords
- **Yellow**: `#e0af68` - Highlights

### File State Colors
- **Saved**: `#c0caf5` - Normal text color
- **Modified**: `#ff9e64` - Orange, with italic style + ● indicator
- **Unsaved**: `#7dcfff` - Cyan for new files
- **Error**: `#f7768e` - Red for files with errors

---

## 📐 Component Breakdown

### 1. Menu Bar (Top - 35px)
**Location**: Very top of the application  
**Components**:
- **Left**: App icon (⚡) + Menu items (File, Edit, Selection, View, Go, Run, Terminal, Help)
- **Center**: App title "Opsis Code Editor"
- **Right**: Window controls (Minimize, Maximize, Close)

**Features**:
- Dropdown menus with keyboard shortcuts
- Hover effects
- Active state highlighting
- Menu items open on click

**Colors**:
- Background: `#16161e`
- Text: `#c0caf5`
- Hover: `#24283b`
- Border: `#292e42`

---

### 2. Activity Bar (Left Side - 48px width)
**Location**: Far left edge, full height  
**Icons** (Top to Bottom):
1. 📁 Explorer (Ctrl+Shift+E)
2. 🔍 Search (Ctrl+Shift+F)
3. ⎇ Source Control (Ctrl+Shift+G)
4. ▶ Run & Debug (Ctrl+Shift+D)
5. ⊞ Extensions (Ctrl+Shift+X)
6. _[spacer]_
7. 👤 Account
8. ⚙ Settings (Ctrl+,)

**Behavior**:
- Click to toggle views
- Active view shows blue border on left
- Hover shows tooltip with name + shortcut
- Icons are 24px, buttons are 48x48px

**Colors**:
- Background: `#16161e`
- Icon: `#565f89` (inactive)
- Active Icon: `#ffffff`
- Active Border: `#7aa2f7` (2px on left)
- Hover: Icon brightens to `#c0caf5`

---

### 3. Sidebar / File Explorer (280px width)
**Location**: Between Activity Bar and Editor  
**Sections**:

#### Header (35px)
- Title: "EXPLORER" (11px, uppercase, letter-spaced)
- Collapse button (▼/▶)
- Action buttons: 📄 Open File, 📁 Open Folder

#### Open Editors Section
- Shows currently open files
- File icon + name + modified indicator (●)
- Active file highlighted with blue left border
- Click to switch between files
- Shows count badge

#### Recent Files Section
- Recently opened files
- Click to reopen

#### Quick Actions
- Buttons for common tasks
- Open File, Open Folder

**File Item States**:
- **Normal**: Icon + name in `#c0caf5`
- **Active**: Background `#292e42`, blue left border, white text
- **Modified**: Orange text `#ff9e64`, italic, ● indicator
- **Hover**: Background `#24283b`

**Colors**:
- Background: `#16161e`
- Section Header: `#565f89`
- File Text: `#c0caf5`
- Active: `#ffffff` on `#292e42`
- Modified: `#ff9e64` + italic
- Border: `#292e42`

---

### 4. File Tabs (Top of Editor - 35px)
**Location**: Above code editor  
**Components**:
- Multiple tabs (120-200px each)
- Tab: Icon + Filename + Modified indicator (●) + Close (×)
- New tab button (+)
- Actions menu (⋮)

**Tab States**:
- **Inactive**: Background `#1a1b26`, gray text
- **Active**: Background `#24283b`, white text, blue bottom border (2px)
- **Modified**: Orange ● indicator, italic text
- **Hover**: Background lightens, close button appears

**Behavior**:
- Click to switch tabs
- Close button (×) appears on hover
- Modified tabs show ● instead of close button
- New tab button adds blank file
- Horizontal scroll if too many tabs

**Colors**:
- Tab Background: `#1a1b26`
- Active Tab: `#24283b`
- Active Border: `#7aa2f7` (bottom, 2px)
- Text: `#c0caf5`
- Modified: `#ff9e64`
- Border: `#292e42`

---

### 5. Code Editor (Center - Flex)
**Location**: Main center area  
**Features**:
- Monaco Editor (same as VS Code)
- Syntax highlighting
- Line numbers
- Minimap
- Bracket pair colorization
- Smooth scrolling
- Word wrap
- 16px top/bottom padding

**Configuration**:
```javascript
{
  fontSize: 14,
  fontFamily: "'Consolas', 'Monaco', 'Courier New'",
  theme: "vs-dark",
  minimap: { enabled: true },
  tabSize: 2,
  wordWrap: 'on',
  cursorBlinking: 'smooth',
  bracketPairColorization: { enabled: true }
}
```

**Colors**:
- Background: `#1a1b26`
- Text colors: Monaco's Tokyo Night theme
- Selection: `#7aa2f7`

---

### 6. Bottom Panel (Resizable - 250px default)
**Location**: Bottom of editor area  
**Header** (35px):
- Tabs: Problems, Output, Debug Console, Terminal, Ports
- Actions: Clear, Minimize/Maximize, Close

**Tabs**:
- **Problems**: Shows errors/warnings with counts
- **Output**: Code execution results (active by default)
- **Debug Console**: Debug messages
- **Terminal**: Terminal emulator (coming soon)
- **Ports**: Forwarded ports

**Output View**:
- Monospace font (Consolas, 13px)
- Shows running indicator when executing
- Scrollable content
- Clear button

**Tab Features**:
- Icon + Label + Count badge (if applicable)
- Active tab: Background matches panel, blue bottom border
- Hover: Background lightens

**Colors**:
- Background: `#1a1b26`
- Header: `#16161e`
- Tab: `#565f89` (inactive)
- Active Tab: `#c0caf5`, blue border
- Output Text: `#c0caf5`
- Border: `#292e42`

---

### 7. Status Bar (Bottom - 22px)
**Location**: Very bottom of application  
**Left Side**:
- Git branch (⎇ main)
- Errors count (✕ 0) - red
- Warnings count (⚠ 0) - orange

**Right Side**:
- Language mode (📝 JavaScript) - clickable
- Line ending (LF)
- Encoding (UTF-8)
- Cursor position (Ln 1, Col 1) - clickable
- Line/char count
- Notifications (🔔)

**Behavior**:
- All items clickable (show as buttons)
- Hover shows darker background
- Icons 14px, text 12px

**Colors**:
- Background: `#16161e`
- Text: `#c0caf5`
- Hover: `#24283b`
- Error: `#f7768e`
- Warning: `#ff9e64`

---

## 🎯 Visual States & Indicators

### File States
| State | Visual Indicator | Color | Font Style |
|-------|-----------------|-------|------------|
| Saved | Normal | `#c0caf5` | Normal |
| Modified | ● dot | `#ff9e64` | Italic |
| Unsaved (new) | Name | `#7dcfff` | Normal |
| Error | ✕ icon | `#f7768e` | Normal |
| Active | Blue border | `#7aa2f7` | Bold |

### Interactive States
| State | Background | Text | Border |
|-------|-----------|------|--------|
| Normal | Transparent | `#c0caf5` | None |
| Hover | `#24283b` | `#ffffff` | None |
| Active | `#292e42` | `#ffffff` | `#7aa2f7` |
| Focus | Current | Current | `#7aa2f7` |
| Disabled | Same | `#565f89` | None |

### Button Types
1. **Primary**: Blue background `#7aa2f7`, white text
2. **Success**: Green background `#9ece6a`, white text
3. **Danger**: Red background `#f7768e`, white text
4. **Ghost**: Transparent, border `#292e42`, text color

---

## 📱 Responsive Behavior

### Large Screens (> 1024px)
- Sidebar: 280px
- All features visible
- Optimal spacing

### Medium Screens (768px - 1024px)
- Sidebar: 240px
- Status bar condensed
- Panels auto-collapse

### Small Screens (< 768px)
- Sidebar becomes overlay
- Single panel view
- Simplified status bar

---

## ⌨️ Keyboard Shortcuts

### File Operations
- `Ctrl+N` - New File
- `Ctrl+O` - Open File
- `Ctrl+S` - Save File
- `Ctrl+Shift+S` - Save As
- `Ctrl+W` - Close Tab

### View Controls
- `Ctrl+Shift+E` - Toggle Explorer
- `Ctrl+Shift+F` - Toggle Search
- `Ctrl+\`` - Toggle Terminal
- `Ctrl+B` - Toggle Sidebar

### Code Execution
- `F5` - Run Code
- `Ctrl+F5` - Run Without Debugging
- `Shift+F5` - Stop

### Navigation
- `Ctrl+P` - Go to File
- `Ctrl+G` - Go to Line
- `Ctrl+Tab` - Next Tab
- `Ctrl+Shift+Tab` - Previous Tab

---

## 🎭 Animations & Transitions

All transitions: `0.1s` to `0.2s` for smooth feel

- **Hover**: 0.1s background color
- **Tab Switch**: 0.15s background + border
- **Panel Collapse**: 0.2s height
- **Sidebar Toggle**: 0.2s width
- **Menu Dropdown**: Instant (no transition)

---

## 🔍 Accessibility Features

- **Focus Indicators**: 2px blue outline
- **Keyboard Navigation**: Full support
- **Screen Readers**: ARIA labels on all buttons
- **Contrast**: WCAG AA compliant
- **Font Sizes**: Minimum 12px, optimal 13-14px

---

## 📊 Spacing System

- **Extra Small**: 4px - Icon gaps, inline elements
- **Small**: 8px - Button padding, list items
- **Medium**: 12px - Section padding, gaps
- **Large**: 16px - Content padding
- **Extra Large**: 24px - Major sections

---

## 🎨 Icon System

### File Type Icons
- 📜 JavaScript (.js, .jsx)
- ⚛️ React (.jsx, .tsx)
- 💙 TypeScript (.ts, .tsx)
- 🐍 Python (.py)
- ☕ Java (.java)
- 🌐 HTML (.html)
- 🎨 CSS (.css)
- 📋 JSON (.json)
- 📝 Markdown (.md)
- 📄 Text (.txt)

### Action Icons
- ▶ Run/Play
- ⏸ Pause
- ⏹ Stop
- 📁 Folder
- 📄 File
- 💾 Save
- 🔍 Search
- ⚙ Settings
- 👤 Account
- 🔔 Notifications

---

## ✨ Special Effects

### Syntax Highlighting Colors (Monaco)
- **Keywords**: `#bb9af7` (purple)
- **Strings**: `#9ece6a` (green)
- **Numbers**: `#ff9e64` (orange)
- **Functions**: `#7aa2f7` (blue)
- **Comments**: `#565f89` (muted)
- **Variables**: `#c0caf5` (white-blue)

### Scrollbar Styling
- **Track**: Transparent
- **Thumb**: `#444b6a` (visible on scroll)
- **Thumb Hover**: `#565f89` (brighter)
- **Width**: 10px
- **Border Radius**: 5px

---

## 🎬 UI Behavior Details

### File Explorer
- Click file → Opens in new tab
- Click open file → Switches to that tab
- Double-click → Opens and focuses
- Right-click → Context menu (future)

### Tabs
- Click → Switch to tab
- Middle-click → Close tab (future)
- Drag → Reorder tabs (future)
- Modified tab → Shows ● , ask on close

### Bottom Panel
- Drag top edge → Resize height
- Double-click header → Toggle collapse
- Tab switch → Persists size
- Close button → Hides panel

### Status Bar
- Click items → Opens related panels
- Hover → Shows tooltips
- Always visible → No collapse

---

## 🚀 Performance Optimizations

- **Virtual Scrolling**: For large file lists
- **Lazy Loading**: Monaco editor loaded on demand
- **Debounced Updates**: File change tracking
- **Memoized Components**: Prevents re-renders
- **CSS Transitions**: GPU-accelerated
- **Smooth Scrolling**: Native smooth scroll

---

## 📐 Exact Measurements

```css
Menu Bar Height: 35px
Activity Bar Width: 48px
Sidebar Width: 280px (collapsible)
File Tab Height: 35px
Bottom Panel Height: 250px (resizable: 150-600px)
Status Bar Height: 22px
Border Width: 1px
Active Border Width: 2px
Button Border Radius: 3-4px
Scrollbar Width: 10px
Font Size (UI): 12-13px
Font Size (Editor): 14px
Line Height: 1.5-1.6
```

---

## 🎨 Design Principles

1. **Consistency**: All components follow same patterns
2. **Clarity**: Clear visual hierarchy
3. **Efficiency**: Minimal clicks to common actions
4. **Feedback**: Visual response to all interactions
5. **Beauty**: Professional Tokyo Night aesthetic
6. **Performance**: Smooth 60fps animations

---

## ✅ VS Code Parity Achieved

✅ Menu bar with dropdowns  
✅ Activity bar with view switching  
✅ File explorer with sections  
✅ Multi-tab file editing  
✅ File state indicators (saved/modified)  
✅ Bottom panel with multiple views  
✅ Status bar with contextual info  
✅ Tokyo Night color scheme  
✅ Professional typography  
✅ Smooth animations  
✅ Keyboard shortcuts  
✅ Responsive layout  

---

**This is a true VS Code clone with professional UI design! 🎉**
