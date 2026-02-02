import { useState, useEffect, useRef } from 'react';
import Editor from '@monaco-editor/react';
import MenuBar from './MenuBar';
import Sidebar from './Sidebar';
import FileExplorer from './FileExplorer';
import FileTabs from './FileTabs';
import BottomPanel from './BottomPanel';
import StatusBar from './StatusBar';
import './CodeEditor.css';
import '../theme/tokyoNight.css';

const CodeEditor = () => {
  // File management
  const [openFiles, setOpenFiles] = useState([
    { 
      name: 'welcome.js', 
      content: '// Welcome to Opsis Code Editor!\n// A VS Code-like editor built with Electron\n\nconsole.log("Hello, World!");\n\n// Features:\n// • File Explorer\n// • Multiple Tabs\n// • Code Execution\n// • Tokyo Night Theme\n// • And much more!\n\nfunction greet(name) {\n  return `Hello, ${name}!`;\n}\n\nconsole.log(greet("Developer"));',
      path: null,
      language: 'javascript',
      isModified: false,
      isNew: true
    }
  ]);
  const [activeFileIndex, setActiveFileIndex] = useState(0);
  const [language, setLanguage] = useState('javascript');
  const [output, setOutput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [activeView, setActiveView] = useState('explorer');
  const [cursorPosition, setCursorPosition] = useState({ line: 1, column: 1 });
  const editorRef = useRef(null);

  const currentFile = openFiles[activeFileIndex];

  // Language detection
  const languageMap = {
    'js': 'javascript', 'jsx': 'javascript',
    'ts': 'typescript', 'tsx': 'typescript',
    'py': 'python', 'java': 'java',
    'html': 'html', 'css': 'css',
    'json': 'json', 'md': 'markdown'
  };

  // File operations
  const handleOpenFile = async () => {
    if (window.electronAPI) {
      const file = await window.electronAPI.openFile();
      if (file) {
        const ext = file.name.split('.').pop().toLowerCase();
        const detectedLang = languageMap[ext] || 'javascript';
        
        const newFile = {
          ...file,
          language: detectedLang,
          isModified: false,
          isNew: false
        };

        // Check if file is already open
        const existingIndex = openFiles.findIndex(f => f.path === file.path);
        if (existingIndex !== -1) {
          setActiveFileIndex(existingIndex);
        } else {
          setOpenFiles([...openFiles, newFile]);
          setActiveFileIndex(openFiles.length);
        }
        setLanguage(detectedLang);
        setOutput('');
      }
    }
  };

  const handleSaveFile = async () => {
    if (!currentFile) return;
    
    if (window.electronAPI) {
      if (currentFile.path) {
        const result = await window.electronAPI.saveFile({ 
          path: currentFile.path, 
          content: currentFile.content 
        });
        if (result.success) {
          updateCurrentFile({ isModified: false });
          setOutput('✅ File saved successfully!');
        } else {
          setOutput('❌ Error saving file: ' + result.error);
        }
      } else {
        handleSaveFileAs();
      }
    }
  };

  const handleSaveFileAs = async () => {
    if (!currentFile || !window.electronAPI) return;
    
    const result = await window.electronAPI.saveFileAs({ content: currentFile.content });
    if (result.success) {
      updateCurrentFile({ 
        name: result.name, 
        path: result.path,
        isModified: false,
        isNew: false
      });
      setOutput('✅ File saved successfully!');
    } else if (result.error) {
      setOutput('❌ Error saving file: ' + result.error);
    }
  };

  const handleNewFile = () => {
    const newFile = {
      name: `Untitled-${openFiles.filter(f => f.isNew).length + 1}.js`,
      content: '// New file\n',
      path: null,
      language: 'javascript',
      isModified: false,
      isNew: true
    };
    setOpenFiles([...openFiles, newFile]);
    setActiveFileIndex(openFiles.length);
    setLanguage('javascript');
    setOutput('');
  };

  const handleCloseTab = (fileToClose) => {
    if (openFiles.length === 1) {
      // Don't close the last file, just reset it
      handleNewFile();
      setOpenFiles([openFiles[0]]);
      setActiveFileIndex(0);
      return;
    }

    const indexToClose = openFiles.findIndex(f => f.path === fileToClose.path);
    const newFiles = openFiles.filter((_, idx) => idx !== indexToClose);
    setOpenFiles(newFiles);
    
    // Adjust active index
    if (activeFileIndex >= indexToClose && activeFileIndex > 0) {
      setActiveFileIndex(activeFileIndex - 1);
    }
  };

  const updateCurrentFile = (updates) => {
    const newFiles = [...openFiles];
    newFiles[activeFileIndex] = { ...newFiles[activeFileIndex], ...updates };
    setOpenFiles(newFiles);
  };

  const handleCodeChange = (value) => {
    updateCurrentFile({ 
      content: value || '', 
      isModified: true 
    });
  };

  const handleRunCode = async () => {
    if (!currentFile || !window.electronAPI) return;
    
    setIsRunning(true);
    setOutput('⏳ Running code...\n');
    
    try {
      const result = await window.electronAPI.executeCode({ 
        code: currentFile.content, 
        language: currentFile.language 
      });
      
      if (result.success) {
        let outputText = '✅ Execution completed!\n\n';
        if (result.output) {
          outputText += 'Output:\n' + result.output;
        }
        if (result.error) {
          outputText += '\n\nWarnings/Errors:\n' + result.error;
        }
        setOutput(outputText);
      } else {
        setOutput('❌ Execution failed!\n\n' + (result.error || result.stderr));
      }
    } catch (error) {
      setOutput('❌ Error: ' + error.message);
    } finally {
      setIsRunning(false);
    }
  };

  // Menu actions
  const handleMenuAction = (action) => {
    switch (action) {
      case 'new':
        handleNewFile();
        break;
      case 'open':
        handleOpenFile();
        break;
      case 'save':
        handleSaveFile();
        break;
      case 'saveAs':
        handleSaveFileAs();
        break;
      case 'run':
        handleRunCode();
        break;
      case 'close':
        if (currentFile) handleCloseTab(currentFile);
        break;
      case 'toggleExplorer':
        setActiveView(activeView === 'explorer' ? null : 'explorer');
        break;
      case 'toggleTerminal':
        // Terminal toggle handled by BottomPanel
        break;
      default:
        console.log('Menu action:', action);
    }
  };

  // Editor events
  const handleEditorDidMount = (editor) => {
    editorRef.current = editor;
    editor.onDidChangeCursorPosition((e) => {
      setCursorPosition({
        line: e.position.lineNumber,
        column: e.position.column
      });
    });
  };

  return (
    <div className="vscode-container">
      {/* Top Menu Bar */}
      <MenuBar onAction={handleMenuAction} />
      
      {/* Main Content Area */}
      <div className="vscode-main">
        {/* Activity Bar (Left Icons) */}
        <Sidebar activeView={activeView} onViewChange={setActiveView} />
        
        {/* File Explorer */}
        {activeView === 'explorer' && (
          <FileExplorer 
            onFileSelect={(file) => {
              const existingIndex = openFiles.findIndex(f => f.path === file.path);
              if (existingIndex !== -1) {
                setActiveFileIndex(existingIndex);
              } else {
                setOpenFiles([...openFiles, file]);
                setActiveFileIndex(openFiles.length);
              }
            }}
            currentFile={currentFile}
            openFiles={openFiles}
          />
        )}
        
        {/* Editor Area */}
        <div className="editor-area">
          {/* File Tabs */}
          <FileTabs 
            files={openFiles}
            activeFile={currentFile}
            onTabClick={(file) => {
              const index = openFiles.findIndex(f => f.path === file.path);
              setActiveFileIndex(index);
            }}
            onTabClose={handleCloseTab}
            onNewFile={handleNewFile}
          />
          
          {/* Code Editor */}
          <div className="editor-container">
            <Editor
              height="100%"
              language={currentFile?.language || 'javascript'}
              value={currentFile?.content || ''}
              onChange={handleCodeChange}
              onMount={handleEditorDidMount}
              theme="vs-dark"
              options={{
                fontSize: 14,
                fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace",
                minimap: { enabled: true },
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 2,
                wordWrap: 'on',
                lineNumbers: 'on',
                renderWhitespace: 'selection',
                cursorBlinking: 'smooth',
                cursorSmoothCaretAnimation: 'on',
                smoothScrolling: true,
                padding: { top: 16, bottom: 16 },
                bracketPairColorization: { enabled: true },
                guides: {
                  bracketPairs: true,
                  indentation: true
                }
              }}
            />
          </div>
          
          {/* Bottom Panel (Terminal/Output) */}
          <BottomPanel 
            output={output}
            isRunning={isRunning}
            onClear={() => setOutput('')}
          />
        </div>
      </div>
      
      {/* Status Bar */}
      <StatusBar 
        currentFile={currentFile}
        language={currentFile?.language || 'javascript'}
        lineCount={currentFile?.content?.split('\n').length || 0}
        charCount={currentFile?.content?.length || 0}
        cursorPosition={cursorPosition}
        hasErrors={false}
      />
    </div>
  );
};

export default CodeEditor;
