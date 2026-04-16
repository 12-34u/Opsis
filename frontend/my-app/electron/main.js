const { app, BrowserWindow, ipcMain, dialog, session } = require('electron');
const path = require('path');
const fs = require('fs').promises;

// Get the Opsis root directory
const opsisRoot = path.resolve(__dirname, '../../..');
const Assembler8085 = require(path.join(opsisRoot, 'backend/assembler'));

let mainWindow;
const assembler = new Assembler8085();

function configureContentSecurityPolicy() {
  const devServerUrl = process.env.VITE_DEV_SERVER_URL;
  const devOrigin = devServerUrl ? new URL(devServerUrl).origin : null;
  const devWsOrigin = devOrigin ? devOrigin.replace('http://', 'ws://').replace('https://', 'wss://') : null;
  const monacoCdnOrigin = 'https://cdn.jsdelivr.net';

  const scriptSrc = ["'self'", monacoCdnOrigin, "https://apis.google.com"];
  const styleSrc = ["'self'", "'unsafe-inline'", monacoCdnOrigin];
  const connectSrc = [
    "'self'", 
    monacoCdnOrigin, 
    "https://*.googleapis.com", 
    "https://*.firebaseapp.com",
    "https://*.firebaseio.com",
    "wss://*.firebaseio.com"
  ];
  const imgSrc = ["'self'", 'data:', 'blob:'];
  const fontSrc = ["'self'", 'data:'];
  const workerSrc = ["'self'", 'blob:'];

  if (devOrigin) {
    // Vite/React dev injects a small inline preamble script.
    scriptSrc.push("'unsafe-inline'");
    scriptSrc.push(devOrigin);
    styleSrc.push(devOrigin);
    connectSrc.push(devOrigin);
    imgSrc.push(devOrigin);
    fontSrc.push(devOrigin);
  }

  if (devWsOrigin) {
    connectSrc.push(devWsOrigin);
  }

  const csp = [
    `default-src 'self'${devOrigin ? ` ${devOrigin}` : ''}`,
    `script-src ${scriptSrc.join(' ')}`,
    `style-src ${styleSrc.join(' ')}`,
    `connect-src ${connectSrc.join(' ')}`,
    `img-src ${imgSrc.join(' ')}`,
    `font-src ${fontSrc.join(' ')}`,
    `worker-src ${workerSrc.join(' ')}`,
    `child-src ${workerSrc.join(' ')}`,
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
  ].join('; ');

  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [csp],
      },
    });
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    frame: true,
    backgroundColor: '#1e1e1e',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    },
    icon: path.join(__dirname, '../public/icon.png')
  });

  // Load the app
  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
    // mainWindow.webContents.openDevTools(); // Uncomment for debugging
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  configureContentSecurityPolicy();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC Handlers for file operations
ipcMain.handle('open-file', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: 'All Files', extensions: ['*'] },
      { name: 'Assembly (8085/8086)', extensions: ['asm', 'asm85', 'asm86', 's'] },
      { name: 'JavaScript', extensions: ['js', 'jsx'] },
      { name: 'TypeScript', extensions: ['ts', 'tsx'] },
      { name: 'Python', extensions: ['py'] },
      { name: 'Java', extensions: ['java'] },
      { name: 'C/C++', extensions: ['c', 'cpp', 'h', 'hpp'] },
      { name: 'HTML', extensions: ['html', 'htm'] },
      { name: 'CSS', extensions: ['css', 'scss', 'sass'] },
      { name: 'JSON', extensions: ['json'] },
      { name: 'Markdown', extensions: ['md'] }
    ]
  });

  if (!result.canceled && result.filePaths.length > 0) {
    const filePath = result.filePaths[0];
    const content = await fs.readFile(filePath, 'utf-8');
    return {
      path: filePath,
      content: content,
      name: path.basename(filePath)
    };
  }
  return null;
});

ipcMain.handle('save-file', async (event, { path: filePath, content }) => {
  try {
    await fs.writeFile(filePath, content, 'utf-8');
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('save-file-as', async (event, { content }) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    filters: [
      { name: 'All Files', extensions: ['*'] },
      { name: 'Assembly (8085/8086)', extensions: ['asm', 'asm85', 'asm86'] },
      { name: 'JavaScript', extensions: ['js'] },
      { name: 'TypeScript', extensions: ['ts'] },
      { name: 'Python', extensions: ['py'] },
      { name: 'Java', extensions: ['java'] },
      { name: 'Text', extensions: ['txt'] }
    ]
  });

  if (!result.canceled && result.filePath) {
    try {
      await fs.writeFile(result.filePath, content, 'utf-8');
      return {
        success: true,
        path: result.filePath,
        name: path.basename(result.filePath)
      };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
  return { success: false };
});

ipcMain.handle('execute-code', async (event, { code, language }) => {
  // Assembly execution
  if (language === 'assembly' || language === 'asm') {
    try {
      const result = assembler.execute(code);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  // Original language execution for backward compatibility
  const { exec } = require('child_process');
  const util = require('util');
  const execPromise = util.promisify(exec);
  
  try {
    let command;
    const tempFile = path.join(app.getPath('temp'), `temp_code_${Date.now()}`);
    
    switch (language) {
      case 'javascript':
        await fs.writeFile(`${tempFile}.js`, code);
        command = `node "${tempFile}.js"`;
        break;
      case 'python':
        await fs.writeFile(`${tempFile}.py`, code);
        command = `python "${tempFile}.py"`;
        break;
      case 'java':
        const className = code.match(/class\s+(\w+)/)?.[1] || 'Main';
        await fs.writeFile(`${tempFile}.java`, code);
        command = `javac "${tempFile}.java" && java -cp "${path.dirname(tempFile)}" ${className}`;
        break;
      default:
        return { success: false, error: 'Unsupported language' };
    }
    
    const { stdout, stderr } = await execPromise(command);
    
    // Clean up temp file
    try {
      await fs.unlink(`${tempFile}.${language === 'javascript' ? 'js' : language === 'python' ? 'py' : 'java'}`);
    } catch (e) {}
    
    return {
      success: true,
      output: stdout,
      error: stderr
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
      output: error.stdout || '',
      stderr: error.stderr || ''
    };
  }
});

// Assembler IPC Handlers
ipcMain.handle('assembler:reset', async (event) => {
  assembler.reset();
  return {
    success: true,
    state: assembler.getState(),
  };
});

ipcMain.handle('assembler:getState', async (event) => {
  return assembler.getState();
});

ipcMain.handle('assembler:setRegister', async (event, register, value) => {
  try {
    assembler.setRegisterValue(register, value);
    return {
      success: true,
      state: assembler.getState(),
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
    };
  }
});

ipcMain.handle('assembler:getMemory', async (event, start = 0, length = 256) => {
  const memory = assembler.memory.slice(start, start + length);
  return {
    success: true,
    memory,
    start,
  };
});

ipcMain.handle('assembler:setMemory', async (event, address, value) => {
  try {
    assembler.memory[address] = value & 0xFF;
    return {
      success: true,
      state: assembler.getState(),
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
    };
  }
});
