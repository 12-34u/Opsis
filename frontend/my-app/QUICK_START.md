# Opsis Code Editor - Quick Start Guide

## 🚀 Quick Start

### Option 1: Web Browser (Recommended for testing)
1. Open terminal in `frontend/my-app` directory
2. Run: `npm install` (first time only)
3. Run: `npm run dev`
4. Open browser at: http://localhost:5173

### Option 2: Desktop App (Full Electron Experience)
1. Open terminal in `frontend/my-app` directory
2. Run: `npm install` (first time only)
3. Run: `npm run dev`
4. The Electron window will open automatically

### Option 3: Using start.bat (Windows)
1. Double-click `start.bat` file
2. Wait for the application to start

## 📖 How to Use

### Basic Operations
- **New File**: Click "📄 New" button
- **Open File**: Click "📂 Open" button
- **Save File**: Click "💾 Save" button
- **Save As**: Click "💾 Save As" button
- **Run Code**: Click "▶️ Run" button

### Writing Code
1. Select your programming language from the dropdown (top right)
2. Write your code in the editor
3. Click "Run" to execute (JavaScript, Python, Java supported)
4. View output in the right panel

### Themes
- Click the sun/moon icon (☀️/🌙) in the top right to toggle between light and dark themes

### Font Size
- Adjust the font size using the number input in the toolbar (8-32)

## 💡 Features

✅ **Syntax Highlighting**: Automatic syntax highlighting for all supported languages
✅ **Code Execution**: Run JavaScript, Python, and Java code directly
✅ **File Management**: Open, edit, and save files from your computer
✅ **Multiple Languages**: JavaScript, Python, Java, TypeScript, HTML, CSS, JSON, Markdown
✅ **Professional UI**: VS Code-like interface with dark/light themes
✅ **Line Numbers**: Easy code navigation
✅ **Minimap**: Quick code overview
✅ **Status Bar**: Real-time stats (lines, characters, language)

## ⚙️ Requirements

### For Development
- Node.js 16 or higher
- npm (comes with Node.js)

### For Running Code
- **JavaScript**: Built-in (Node.js)
- **Python**: Install Python 3.x and add to PATH
- **Java**: Install JDK 8+ and add to PATH

## 🐛 Troubleshooting

### Application won't start
- Make sure you're in the correct directory: `frontend/my-app`
- Run `npm install` to ensure all dependencies are installed
- Check that Node.js is installed: `node --version`

### Code execution fails
- **Python**: Ensure Python is installed and in PATH (`python --version`)
- **Java**: Ensure JDK is installed and in PATH (`javac --version`)
- Check the output panel for specific error messages

### Port already in use
- If port 5173 is already in use, close other applications or change the port in `vite.config.js`

## 📚 Supported Languages

### For Editing (Syntax Highlighting)
- JavaScript (.js, .jsx)
- TypeScript (.ts, .tsx)
- Python (.py)
- Java (.java)
- HTML (.html, .htm)
- CSS (.css, .scss, .sass)
- JSON (.json)
- Markdown (.md)

### For Execution (Run Code)
- ✅ JavaScript
- ✅ Python
- ✅ Java

## 🎨 Interface Overview

```
┌─────────────────────────────────────────────────────────┐
│ ⚡ Opsis Code Editor          [filename.js]        ☀️/🌙 │  Menu Bar
├─────────────────────────────────────────────────────────┤
│ 📄New 📂Open 💾Save ▶️Run    [Language▼] [Font: 14]   │  Toolbar
├──────────────────────────┬──────────────────────────────┤
│                          │                              │
│   Editor                 │   Output                     │
│   (Monaco Editor)        │   (Execution Results)        │
│                          │                              │
├──────────────────────────┴──────────────────────────────┤
│ Lines: 25 | Chars: 456          Language: JS | Theme    │  Status Bar
└─────────────────────────────────────────────────────────┘
```

## 🔥 Example Code

### JavaScript
```javascript
console.log("Hello from Opsis!");
const sum = (a, b) => a + b;
console.log("5 + 3 =", sum(5, 3));
```

### Python
```python
print("Hello from Opsis!")
def greet(name):
    return f"Hello, {name}!"
print(greet("World"))
```

### Java
```java
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from Opsis!");
        System.out.println("Sum: " + (5 + 3));
    }
}
```

## 📦 Building for Production

To create a distributable desktop application:

```bash
npm run electron:build
```

This will create installers in the `release` folder for your platform.

## 🤝 Need Help?

- Check the main README_OPSIS.md for detailed documentation
- Review error messages in the output panel
- Ensure all required runtimes are installed (Node.js, Python, Java)

---

**Enjoy coding with Opsis Code Editor! ⚡**
