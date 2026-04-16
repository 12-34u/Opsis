import { useState, useEffect, useRef, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import MenuBar from './MenuBar';
import Sidebar from './Sidebar';
import FileExplorer from './FileExplorer';
import FileTabs from './FileTabs';
import BottomPanel from './BottomPanel';
import StatusBar from './StatusBar';
import OutputPanel from './OutputPanel';
import UserGuide from './UserGuide';
import CloudModal from './CloudModal';
import AIPanel from './AIPanel';
import './CodeEditor.css';

const CodeEditor = ({ appTheme = 'tokyo-night', onAppThemeChange, isGuest = false, userEmail = '' }) => {
  // File management
  const [openFiles, setOpenFiles] = useState([
    { 
      name: 'example.asm', 
      content: `; 8085/8086 Assembly Example
; Add two numbers and output result

MVI A, 05H       ; Load 5 into Register A
MVI B, 03H       ; Load 3 into Register B
ADD B            ; Add B to A (A = A + B)
OUT              ; Output the result
HLT              ; Halt execution`,
      path: null,
      language: 'assembly',
      isModified: false,
      isNew: true
    }
  ]);
  const [activeFileIndex, setActiveFileIndex] = useState(0);
  const [language, setLanguage] = useState('assembly');
  const [output, setOutput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [activeView, setActiveView] = useState('explorer');
  const [cursorPosition, setCursorPosition] = useState({ line: 1, column: 1 });
  const [assemblerState, setAssemblerState] = useState(null);
  const [executionOutput, setExecutionOutput] = useState([]);
  const [executionError, setExecutionError] = useState(null);
  const [instructionCount, setInstructionCount] = useState(0);
  const [executionSteps, setExecutionSteps] = useState([]);
  const editorRef = useRef(null);
  const monacoRef = useRef(null);
  const errorDecorationIdsRef = useRef([]);
  const saveFileRef = useRef(null);
  const saveFileAsRef = useRef(null);
  const [panelHeight, setPanelHeight] = useState(300);
  const isDraggingRef = useRef(false);
  const dragStartYRef = useRef(0);
  const dragStartHeightRef = useRef(0);
  const [tourState, setTourState] = useState({ run: false, startIndex: 0, key: 0 });
  const [cloudModalConfig, setCloudModalConfig] = useState({ isOpen: false, mode: 'load' });
  const [isAIPanelOpen, setIsAIPanelOpen] = useState(false);

  // Auto-trigger tour for guests vs users
  useEffect(() => {
    if (isGuest) {
      // Small delay helps UI settle
      setTimeout(() => setTourState(prev => ({ run: true, startIndex: 0, key: prev.key + 1 })), 500);
    } else if (userEmail) {
      const seenKey = `opsis-tour-seen-${userEmail}`;
      if (!localStorage.getItem(seenKey)) {
         localStorage.setItem(seenKey, 'true');
         setTimeout(() => setTourState(prev => ({ run: true, startIndex: 0, key: prev.key + 1 })), 500);
      }
    }
  }, [isGuest, userEmail]);

  // Panel resize handlers
  const handlePanelDragStart = useCallback((e) => {
    e.preventDefault();
    isDraggingRef.current = true;
    dragStartYRef.current = e.clientY;
    dragStartHeightRef.current = panelHeight;
    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';
  }, [panelHeight]);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isDraggingRef.current) return;
      const delta = dragStartYRef.current - e.clientY;
      const newHeight = Math.max(100, Math.min(window.innerHeight * 0.7, dragStartHeightRef.current + delta));
      setPanelHeight(newHeight);
    };
    const handleMouseUp = () => {
      if (isDraggingRef.current) {
        isDraggingRef.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const currentFile = openFiles[activeFileIndex];

  // Language detection
  const languageMap = {
    'js': 'javascript', 'jsx': 'javascript',
    'ts': 'typescript', 'tsx': 'typescript',
    'py': 'python', 'java': 'java',
    'html': 'html', 'css': 'css',
    'json': 'json', 'md': 'markdown',
    'asm': 'assembly', 'asm85': 'assembly', 'asm86': 'assembly', 's': 'assembly'
  };

  // Register assembly language in Monaco
  useEffect(() => {
    if (window.monaco) {
      window.monaco.languages.register({ id: 'assembly' });
      window.monaco.languages.setMonarchTokensProvider('assembly', {
        tokenizer: {
          root: [
            [/;.*/, 'comment'],
            [/\b(MOV|MVI|ADD|SUB|MUL|DIV|ADI|SUI|INR|DCR|ANA|ORA|XRA|CMP|LDA|STA|OUT|HLT|NOP)\b/i, 'keyword'],
            [/\b(A|B|C|D|E|H|L)\b/i, 'variable'],
            [/0[xX][0-9a-fA-F]+|[0-9]+[hH]|[0-9]+[bB]|[0-9]+/, 'number'],
            [/[a-zA-Z_:][a-zA-Z0-9_:]*/, 'identifier'],
          ]
        }
      });
    }
  }, []);

  // File operations
  const handleOpenFile = async () => {
    if (!isGuest && userEmail) {
      setCloudModalConfig({ isOpen: true, mode: 'load' });
      return;
    }

    if (window.electronAPI) {
      const file = await window.electronAPI.openFile();
      if (file) {
        const ext = file.name.split('.').pop().toLowerCase();
        const detectedLang = languageMap[ext] || 'javascript';
        
        const newFile = {
          ...file,
          language: detectedLang,
          isModified: false,
          isNew: false,
          isCloudFile: false
        };

        const existingIndex = openFiles.findIndex(f => f.path === file.path && !f.isCloudFile);
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
    
    if (!isGuest && userEmail) {
      if (currentFile.isCloudFile && currentFile.name && !currentFile.name.startsWith('untitled_')) {
        // Just trigger save modal securely
        setCloudModalConfig({ isOpen: true, mode: 'save' });
      } else {
        handleSaveFileAs();
      }
      return;
    }

    if (window.electronAPI) {
      if (currentFile.path) {
        const result = await window.electronAPI.saveFile({ 
          path: currentFile.path, 
          content: currentFile.content 
        });
        if (result.success) {
          updateCurrentFile({ isModified: false });
        }
      } else {
        handleSaveFileAs();
      }
    }
  };

  const handleSaveFileAs = async () => {
    if (!currentFile) return;

    if (!isGuest && userEmail) {
      setCloudModalConfig({ isOpen: true, mode: 'save' });
      return;
    }

    if (!window.electronAPI) return;
    const result = await window.electronAPI.saveFileAs({ 
      content: currentFile.content 
    });
    
    if (result.success) {
      updateCurrentFile({ 
        path: result.path, 
        name: result.name,
        isModified: false,
        isCloudFile: false
      });
    }
  };

  const handleCloudLoadComplete = (fileData) => {
    setCloudModalConfig({ isOpen: false, mode: 'load' });
    const newFile = {
      name: fileData.name,
      content: fileData.content,
      language: fileData.language || 'assembly',
      path: null,
      isCloudFile: true,
      isModified: false,
      isNew: false
    };

    const existingIndex = openFiles.findIndex(f => f.name === newFile.name && f.isCloudFile);
    if (existingIndex !== -1) {
      updateCurrentFile({ content: newFile.content, isModified: false });
      setActiveFileIndex(existingIndex);
    } else {
      setOpenFiles([...openFiles, newFile]);
      setActiveFileIndex(openFiles.length);
    }
    setLanguage(newFile.language);
    setOutput('');
  };

  const handleCloudSaveComplete = (fileName) => {
    setCloudModalConfig({ isOpen: false, mode: 'save' });
    updateCurrentFile({ 
      name: fileName,
      isCloudFile: true,
      isModified: false,
      isNew: false
    });
  };

  // Keep refs up to date so Monaco closures always call the latest version
  saveFileRef.current = handleSaveFile;
  saveFileAsRef.current = handleSaveFileAs;

  const handleNewFile = () => {
    const newFile = {
      name: `untitled_${Date.now()}.asm`,
      content: `; New Assembly File
; 8085/8086 Assembly

MVI A, 00H
HLT`,
      path: null,
      language: 'assembly',
      isModified: false,
      isNew: true
    };
    
    setOpenFiles([...openFiles, newFile]);
    setActiveFileIndex(openFiles.length);
  };

  const handleCloseTab = (fileToClose) => {
    const index = openFiles.findIndex(f => f === fileToClose);
    if (index === -1) return;

    const newFiles = openFiles.filter(f => f !== fileToClose);
    setOpenFiles(newFiles);
    
    if (newFiles.length === 0) {
      handleNewFile();
    } else if (activeFileIndex >= newFiles.length) {
      setActiveFileIndex(newFiles.length - 1);
    }
  };

  const updateCurrentFile = (updates) => {
    const newFiles = [...openFiles];
    newFiles[activeFileIndex] = { ...newFiles[activeFileIndex], ...updates };
    setOpenFiles(newFiles);
  };

  const clearExecutionHighlights = () => {
    if (!editorRef.current || !monacoRef.current) return;

    const model = editorRef.current.getModel();
    if (!model) return;

    monacoRef.current.editor.setModelMarkers(model, 'assembly-execution', []);
    errorDecorationIdsRef.current = editorRef.current.deltaDecorations(
      errorDecorationIdsRef.current,
      []
    );
  };

  const highlightExecutionError = (lineNumber, message) => {
    if (!editorRef.current || !monacoRef.current || !lineNumber) return;

    const model = editorRef.current.getModel();
    if (!model) return;

    const safeLine = Math.max(1, Math.min(lineNumber, model.getLineCount()));
    const endColumn = model.getLineMaxColumn(safeLine);

    monacoRef.current.editor.setModelMarkers(model, 'assembly-execution', [
      {
        startLineNumber: safeLine,
        startColumn: 1,
        endLineNumber: safeLine,
        endColumn,
        message,
        severity: monacoRef.current.MarkerSeverity.Error,
      },
    ]);

    errorDecorationIdsRef.current = editorRef.current.deltaDecorations(
      errorDecorationIdsRef.current,
      [
        {
          range: new monacoRef.current.Range(safeLine, 1, safeLine, endColumn),
          options: {
            isWholeLine: true,
            className: 'execution-error-line',
            glyphMarginClassName: 'execution-error-glyph',
          },
        },
      ]
    );

    editorRef.current.revealLineInCenter(safeLine);
  };

  const handleCodeChange = (value) => {
    clearExecutionHighlights();
    updateCurrentFile({ 
      content: value || '', 
      isModified: true 
    });
  };

  const handleRunCode = async () => {
    if (!currentFile || !window.electronAPI) return;
    
    setIsRunning(true);
    setOutput('⏳ Assembling and executing...\n');
    setExecutionError(null);
    setExecutionOutput([]);
    setExecutionSteps([]);
    clearExecutionHighlights();
    
    try {
      const result = await window.electronAPI.executeCode({ 
        code: currentFile.content, 
        language: currentFile.language 
      });
      
      if (result.success) {
        setAssemblerState(result.state);
        setExecutionOutput(result.output || []);
        setExecutionSteps(result.steps || []);
        setInstructionCount(result.instructionCount || 0);
        setExecutionError(null);
        clearExecutionHighlights();
        
        let outputText = '✅ Assembly execution completed!\n\n';
        outputText += `Instructions executed: ${result.instructionCount}\n`;
        if (result.output && result.output.length > 0) {
          outputText += `\nProgram Output:\n`;
          result.output.forEach((item, idx) => {
            outputText += `  ${item.decimal != null ? item.decimal : item.value}`;
            if (item.hex) outputText += `  (${item.hex})`;
            outputText += `\n`;
          });
        }
        setOutput(outputText);
      } else {
        const details = result.errorDetails || {};
        const errorLines = ['❌ Assembly execution failed!'];

        if (details.line !== undefined && details.line !== null) {
          errorLines.push(`Line: ${details.line}`);
        }
        if (details.instruction) {
          errorLines.push(`Instruction: ${details.instruction}`);
        }
        if (result.error) {
          errorLines.push(`Reason: ${result.error}`);
        }

        const formattedError = errorLines.join('\n');
        setExecutionError(formattedError);
        setOutput(formattedError);
        setInstructionCount(result.instructionCount || 0);

        if (details.line !== undefined && details.line !== null) {
          highlightExecutionError(details.line, formattedError);
        }
      }
    } catch (error) {
      setExecutionError(error.message);
      setOutput('❌ Error: ' + error.message);
      clearExecutionHighlights();
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
      case 'themeTokyoNight':
        onAppThemeChange?.('tokyo-night');
        break;
      case 'themeDoodleLight':
        onAppThemeChange?.('doodle-light');
        break;
      case 'themeDoodleDark':
        onAppThemeChange?.('doodle-dark');
        break;
      case 'themeDoodleWhite':
        onAppThemeChange?.('doodle-white');
        break;
      case 'guidedTour':
        setTourState(prev => ({ run: false, startIndex: 1, key: prev.key + 1 }));
        setTimeout(() => setTourState(prev => ({ ...prev, run: true })), 50);
        break;
      case 'aiAnalyze':
        setIsAIPanelOpen(true);
        break;
      default:
        console.log('Menu action:', action);
    }
  };

  // Editor events
  const handleEditorDidMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    editor.onDidChangeCursorPosition((e) => {
      setCursorPosition({
        line: e.position.lineNumber,
        column: e.position.column
      });
    });

    // Override Ctrl+S in Monaco to prevent browser save dialog
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      saveFileRef.current?.();
    });
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyS, () => {
      saveFileAsRef.current?.();
    });
  };

  // Global keyboard shortcuts
  useEffect(() => {
    const onKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (e.shiftKey) {
          handleSaveFileAs();
        } else {
          handleSaveFile();
        }
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [openFiles, activeFileIndex]);

  return (
    <div className="vscode-container">
      <CloudModal 
        isOpen={cloudModalConfig.isOpen}
        mode={cloudModalConfig.mode}
        userEmail={userEmail}
        currentContent={currentFile?.content || ''}
        currentFileName={currentFile?.name || ''}
        onClose={() => setCloudModalConfig({ ...cloudModalConfig, isOpen: false })}
        onLoadComplete={handleCloudLoadComplete}
        onSaveComplete={handleCloudSaveComplete}
      />
      <AIPanel
        code={currentFile?.content || ''}
        isOpen={isAIPanelOpen}
        onClose={() => setIsAIPanelOpen(false)}
      />
      <UserGuide 
        key={`tour-${tourState.key}`}
        run={tourState.run} 
        setRun={(val) => setTourState(prev => ({ ...prev, run: val }))} 
        startIndex={tourState.startIndex}
        appTheme={appTheme}
      />
      {/* Top Menu Bar */}
      <MenuBar onAction={handleMenuAction} isGuest={isGuest} />
      
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
            onTabClick={(file, idx) => {
              setActiveFileIndex(idx);
            }}
            onTabClose={handleCloseTab}
            onNewFile={handleNewFile}
          />
          
          {/* Code Editor */}
          <div className="editor-container">
            <Editor
              height="100%"
              language={currentFile?.language || 'assembly'}
              value={currentFile?.content || ''}
              onChange={handleCodeChange}
              onMount={handleEditorDidMount}
              theme={(appTheme === 'doodle-light' || appTheme === 'doodle-white') ? 'vs' : 'vs-dark'}
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
              }}
            />
          </div>
          
          {/* Assembly-specific panels */}
          <div className="panel-resize-handle" onMouseDown={handlePanelDragStart}>
            <div className="resize-grip" />
          </div>
          <div className="assembly-panels" style={{ height: panelHeight }}>
            <OutputPanel 
              output={executionOutput}
              error={executionError}
              instructionCount={instructionCount}
              isRunning={isRunning}
              steps={executionSteps}
              assemblerState={assemblerState}
            />
          </div>
        </div>
      </div>
      
      {/* Status Bar */}
      <StatusBar 
        currentFile={currentFile}
        language={currentFile?.language || 'assembly'}
        lineCount={currentFile?.content?.split('\n').length || 0}
        charCount={currentFile?.content?.length || 0}
        cursorPosition={cursorPosition}
        hasErrors={executionError ? true : false}
      />
    </div>
  );
};

export default CodeEditor;

