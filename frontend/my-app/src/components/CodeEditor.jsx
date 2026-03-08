import { useState, useEffect, useRef } from 'react';
import Editor from '@monaco-editor/react';
import MenuBar from './MenuBar';
import Sidebar from './Sidebar';
import FileExplorer from './FileExplorer';
import FileTabs from './FileTabs';
import BottomPanel from './BottomPanel';
import StatusBar from './StatusBar';
import RegisterPanel from './RegisterPanel';
import MemoryViewer from './MemoryViewer';
import OutputPanel from './OutputPanel';
import './CodeEditor.css';
import '../theme/tokyoNight.css';

const CodeEditor = () => {
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
  const editorRef = useRef(null);
  const monacoRef = useRef(null);
  const errorDecorationIdsRef = useRef([]);

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
        }
      } else {
        handleSaveFileAs();
      }
    }
  };

  const handleSaveFileAs = async () => {
    if (!currentFile || !window.electronAPI) return;
    
    const result = await window.electronAPI.saveFileAs({ 
      content: currentFile.content 
    });
    
    if (result.success) {
      updateCurrentFile({ 
        path: result.path, 
        name: result.name,
        isModified: false 
      });
    }
  };

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
    clearExecutionHighlights();
    
    try {
      const result = await window.electronAPI.executeCode({ 
        code: currentFile.content, 
        language: currentFile.language 
      });
      
      if (result.success) {
        setAssemblerState(result.state);
        setExecutionOutput(result.output || []);
        setInstructionCount(result.instructionCount || 0);
        setExecutionError(null);
        clearExecutionHighlights();
        
        let outputText = '✅ Assembly execution completed!\n\n';
        outputText += `Instructions executed: ${result.instructionCount}\n`;
        outputText += `Output items: ${result.output?.length || 0}\n`;
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
              language={currentFile?.language || 'assembly'}
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
              }}
            />
          </div>
          
          {/* Assembly-specific panels */}
          <div className="assembly-panels">
            <div className="panel-container">
              <RegisterPanel state={assemblerState} />
            </div>
            <div className="panel-container">
              <MemoryViewer memory={assemblerState?.memory || []} />
            </div>
            <div className="panel-container">
              <OutputPanel 
                output={executionOutput}
                error={executionError}
                instructionCount={instructionCount}
                isRunning={isRunning}
              />
            </div>
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

