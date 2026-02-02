# Opsis Code Editor

A VS Code-like desktop code editor and compiler built with Electron.js, React, and Monaco Editor.

## Features

- 🎨 **VS Code-like Interface**: Professional code editor with syntax highlighting
- 📝 **Multiple Language Support**: JavaScript, Python, Java, TypeScript, HTML, CSS, JSON, Markdown
- ▶️ **Code Execution**: Run JavaScript, Python, and Java code directly in the app
- 💾 **File Operations**: Open, Save, and Save As functionality
- 🌙 **Theme Toggle**: Switch between Dark and Light themes
- 📏 **Customizable**: Adjust font size and preferences
- 🖥️ **Desktop Application**: Full desktop app experience with Electron

## Technologies Used

- **Electron.js**: Desktop application framework
- **React**: UI library
- **Vite**: Build tool and dev server
- **Monaco Editor**: The code editor that powers VS Code
- **Node.js**: Backend for file operations and code execution

## Installation

1. Install dependencies:
```bash
cd frontend/my-app
npm install
```

## Running the Application

### Development Mode (Web Browser)
```bash
npm run dev
```
Then open http://localhost:5173 in your browser.

### Development Mode (Electron Desktop App)
```bash
npm run electron:dev
```
Then in another terminal:
```bash
npm run electron:start
```

### Build for Production
```bash
npm run electron:build
```
This will create a distributable desktop application in the `release` folder.

## Usage

### Opening Files
1. Click the "Open" button in the toolbar
2. Select a file from your system
3. The file content will load in the editor

### Saving Files
1. Click "Save" to save to the current file
2. Click "Save As" to save to a new location

### Running Code
1. Write your code in the editor
2. Select the appropriate language from the dropdown
3. Click the "Run" button
4. View the output in the right panel

### Supported Languages for Execution
- **JavaScript**: Executes with Node.js
- **Python**: Requires Python installed on your system
- **Java**: Requires JDK installed on your system

### Keyboard Shortcuts
- `Ctrl+O`: Open file (platform-specific)
- `Ctrl+S`: Save file (platform-specific)
- Monaco Editor shortcuts work as in VS Code

## Project Structure

```
my-app/
├── electron/
│   ├── main.js          # Electron main process
│   └── preload.js       # Preload script for IPC
├── src/
│   ├── components/
│   │   ├── CodeEditor.jsx
│   │   └── CodeEditor.css
│   ├── App.jsx
│   ├── App.css
│   ├── main.jsx
│   └── index.css
├── public/
├── package.json
└── vite.config.js
```

## Features in Detail

### Code Editor
- Syntax highlighting for multiple languages
- Line numbers
- Minimap for navigation
- Word wrap
- Auto-indentation
- Smart bracket matching

### File Management
- Open files from your system
- Save changes to existing files
- Save new files with custom names
- Auto-detect language from file extension

### Code Execution
- Run code directly in the application
- View output and errors in real-time
- Support for multiple programming languages
- Clean error messages

## Requirements

- Node.js 16 or higher
- For Python execution: Python 3.x
- For Java execution: JDK 8 or higher

## Troubleshooting

### Code doesn't execute
- Ensure the required runtime (Node.js, Python, or Java) is installed and in your PATH
- Check the output panel for error messages

### App doesn't start in Electron mode
- Make sure you run `npm run electron:dev` first to start the Vite dev server
- Then run `npm run electron:start` in a separate terminal

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
