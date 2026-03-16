const { spawnSync } = require('child_process');
const path = require('path');

class Assembler8086Bridge {
  constructor() {
    this.pythonScript = path.join(__dirname, 'assembler8086.py');
    this.state = {
      registers: {
        // 8086 registers
        AX: 0,
        BX: 0,
        CX: 0,
        DX: 0,
        SI: 0,
        DI: 0,
        BP: 0,
        SP: 0xFFFE,
        IP: 0,
        // 8085 registers for compatibility
        A: 0,
        B: 0,
        C: 0,
        D: 0,
        E: 0,
        H: 0,
        L: 0,
        M: 0,
      },
      flags: {
        Z: false,
        C: false,
        S: false,
        P: false,
        O: false,
      },
      memory: new Array(65536).fill(0),
      pc: 0,
      sp: 0xFFFE,
    };
    this.memory = this.state.memory;
    this.output = [];
    this.instructionCount = 0;
  }

  runPython(command, payload = {}) {
    const request = {
      command,
      state: this.state,
      ...payload,
    };

    const pythonCmd = process.platform === "win32" ? "python" : "python3";

    const result = spawnSync(pythonCmd, [this.pythonScript], {
      input: JSON.stringify(request),
      encoding: "utf-8",
      maxBuffer: 10 * 1024 * 1024,
      shell: true
    });

    if (result.error) {
      throw new Error(`Python execution failed: ${result.error.message}`);
    }

    if (result.status !== 0) {
      throw new Error((result.stderr || 'Python process failed').trim());
    }

    let parsed;
    try {
      parsed = JSON.parse(result.stdout || '{}');
    } catch (error) {
      throw new Error(`Invalid Python response: ${error.message}`);
    }

    if (parsed.state) {
      this.state = parsed.state;
      this.memory = this.state.memory;
    }

    if (Array.isArray(parsed.output)) {
      this.output = parsed.output;
    }

    if (typeof parsed.instructionCount === 'number') {
      this.instructionCount = parsed.instructionCount;
    }

    return parsed;
  }

  execute(code) {
    return this.runPython('execute', { code });
  }

  reset() {
    return this.runPython('reset');
  }

  getState() {
    const result = this.runPython('getState');
    return result.state || this.state;
  }

  setRegisterValue(register, value) {
    const result = this.runPython('setRegister', { register, value });
    if (!result.success) {
      throw new Error(result.error || 'Failed to set register');
    }
  }

  getRegisterValue(register) {
    const result = this.runPython('getRegister', { register });
    if (!result.success) {
      throw new Error(result.error || 'Failed to get register');
    }
    return result.value;
  }

  setMemoryValue(address, value) {
    const result = this.runPython('setMemory', { address, value });
    if (!result.success) {
      throw new Error(result.error || 'Failed to set memory');
    }
  }

  getMemory(start = 0, length = 256) {
    const result = this.runPython('getMemory', { start, length });
    if (!result.success) {
      throw new Error(result.error || 'Failed to get memory');
    }
    return result.memory;
  }
}

module.exports = Assembler8086Bridge;
