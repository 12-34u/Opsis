/**
 * Assembly Assembler IPC Handlers
 * Handles communication between Electron main process and renderer
 */

const { ipcMain } = require('electron');
const Assembler8086Bridge = require('./assembler');

const assembler = new Assembler8086Bridge();

function initializeAssemblerHandlers() {
  /**
   * Execute assembly code
   */
  ipcMain.handle('assembler:execute', async (event, code) => {
    try {
      const result = assembler.execute(code);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  });

  /**
   * Reset assembler state
   */
  ipcMain.handle('assembler:reset', async (event) => {
    assembler.reset();
    return {
      success: true,
      state: assembler.getState(),
    };
  });

  /**
   * Get current assembler state
   */
  ipcMain.handle('assembler:getState', async (event) => {
    return assembler.getState();
  });

  /**
   * Set register value
   */
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

  /**
   * Get register value
   */
  ipcMain.handle('assembler:getRegister', async (event, register) => {
    try {
      const value = assembler.getRegisterValue(register);
      return {
        success: true,
        value,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  });

  /**
   * Get memory
   */
  ipcMain.handle('assembler:getMemory', async (event, start = 0, length = 256) => {
    try {
      const memory = assembler.getMemory(start, length);
      return {
        success: true,
        memory,
        start,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  });

  /**
   * Set memory value
   */
  ipcMain.handle('assembler:setMemory', async (event, address, value) => {
    try {
      assembler.setMemoryValue(address, value);
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
}

module.exports = { initializeAssemblerHandlers };
