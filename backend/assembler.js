/**
 * 8085/8086 Assembly Language Assembler & Interpreter
 * Supports basic arithmetic and logic operations
 */

class Assembler8085 {
  constructor() {
    this.registers = {
      A: 0x00,   // Accumulator
      B: 0x00,   // B register
      C: 0x00,   // C register
      D: 0x00,   // D register
      E: 0x00,   // E register
      H: 0x00,   // H register
      L: 0x00,   // L register
    };

    this.memory = new Array(256).fill(0x00);
    this.flags = {
      Z: false, // Zero flag
      C: false, // Carry flag
      P: false, // Parity flag
      S: false, // Sign flag
    };

    this.pc = 0;            // Program counter
    this.sp = 0xFF;         // Stack pointer
    this.output = [];
    this.breakpoints = [];
    this.executionState = 'stopped'; // stopped, running, paused
    this.instructionCount = 0;
  }

  /**
   * Parse assembly code into instructions
   */
  parse(code) {
    const lines = code.split('\n');
    const instructions = [];
    const labels = {};

    for (let i = 0; i < lines.length; i++) {
      let line = lines[i].trim();

      // Remove comments
      const commentIdx = line.indexOf(';');
      if (commentIdx !== -1) {
        line = line.substring(0, commentIdx).trim();
      }

      if (!line) continue;

      // Check for labels
      if (line.includes(':')) {
        const [label, rest] = line.split(':');
        labels[label.trim()] = instructions.length;
        line = rest.trim();
        if (!line) continue;
      }

      instructions.push(line);
    }

    return { instructions, labels };
  }

  /**
   * Execute assembly code
   */
  execute(code) {
    this.reset();
    const { instructions, labels } = this.parse(code);

    this.executionState = 'running';
    const steps = [];

    try {
      while (this.pc < instructions.length && this.executionState === 'running') {
        const instruction = instructions[this.pc];
        const before = this.getState();

        this.executeInstruction(instruction);

        const after = this.getState();
        steps.push({
          pc: this.pc,
          instruction,
          before,
          after,
          output: this.output[this.output.length - 1] || null,
        });

        this.pc++;
        this.instructionCount++;
      }

      this.executionState = 'stopped';

      return {
        success: true,
        state: this.getState(),
        steps,
        output: this.output,
        instructionCount: this.instructionCount,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        state: this.getState(),
        steps,
      };
    }
  }

  /**
   * Execute a single instruction
   */
  executeInstruction(line) {
    const parts = line.toUpperCase().split(/\s+/);
    const instruction = parts[0];
    const operands = parts.slice(1).join(' ');

    switch (instruction) {
      // Data movement instructions
      case 'MOV':
        this.MOV(operands);
        break;
      case 'MVI':
        this.MVI(operands);
        break;
      case 'LDA':
        this.LDA(operands);
        break;
      case 'STA':
        this.STA(operands);
        break;

      // Arithmetic instructions
      case 'ADD':
        this.ADD(operands);
        break;
      case 'ADI':
        this.ADI(operands);
        break;
      case 'SUB':
        this.SUB(operands);
        break;
      case 'SUI':
        this.SUI(operands);
        break;
      case 'MUL':
        this.MUL(operands);
        break;
      case 'DIV':
        this.DIV(operands);
        break;
      case 'INR':
        this.INR(operands);
        break;
      case 'DCR':
        this.DCR(operands);
        break;

      // Logical instructions
      case 'ANA':
        this.ANA(operands);
        break;
      case 'ORA':
        this.ORA(operands);
        break;
      case 'XRA':
        this.XRA(operands);
        break;
      case 'CMP':
        this.CMP(operands);
        break;

      // I/O and control
      case 'OUT':
        this.OUT(operands);
        break;
      case 'HLT':
        this.executionState = 'stopped';
        break;
      case 'NOP':
        break;

      default:
        throw new Error(`Unknown instruction: ${instruction}`);
    }
  }

  // ======================== Data Movement Instructions ========================

  MOV(operands) {
    const [dest, src] = operands.split(',').map(x => x.trim());
    const value = this.getRegisterValue(src);
    this.setRegisterValue(dest, value);
  }

  MVI(operands) {
    const [dest, value] = operands.split(',').map(x => x.trim());
    const numValue = this.parseValue(value);
    this.setRegisterValue(dest, numValue);
  }

  LDA(operands) {
    const addr = this.parseValue(operands);
    this.registers.A = this.memory[addr] || 0;
  }

  STA(operands) {
    const addr = this.parseValue(operands);
    this.memory[addr] = this.registers.A;
  }

  // ======================== Arithmetic Instructions ========================

  ADD(operands) {
    const value = this.getRegisterValue(operands);
    const result = this.registers.A + value;
    this.setFlags(result);
    this.registers.A = result & 0xFF;
  }

  ADI(operands) {
    const value = this.parseValue(operands);
    const result = this.registers.A + value;
    this.setFlags(result);
    this.registers.A = result & 0xFF;
  }

  SUB(operands) {
    const value = this.getRegisterValue(operands);
    const result = this.registers.A - value;
    this.setFlags(result);
    this.registers.A = result & 0xFF;
  }

  SUI(operands) {
    const value = this.parseValue(operands);
    const result = this.registers.A - value;
    this.setFlags(result);
    this.registers.A = result & 0xFF;
  }

  MUL(operands) {
    const value = this.getRegisterValue(operands);
    const result = this.registers.A * value;
    this.setFlags(result);
    this.registers.A = result & 0xFF;
  }

  DIV(operands) {
    const value = this.getRegisterValue(operands);
    if (value === 0) {
      throw new Error('Division by zero');
    }
    const result = Math.floor(this.registers.A / value);
    this.setFlags(result);
    this.registers.A = result & 0xFF;
  }

  INR(operands) {
    const reg = operands.trim();
    const value = this.getRegisterValue(reg);
    const result = value + 1;
    this.setFlags(result);
    this.setRegisterValue(reg, result & 0xFF);
  }

  DCR(operands) {
    const reg = operands.trim();
    const value = this.getRegisterValue(reg);
    const result = value - 1;
    this.setFlags(result);
    this.setRegisterValue(reg, result & 0xFF);
  }

  // ======================== Logical Instructions ========================

  ANA(operands) {
    const value = this.getRegisterValue(operands);
    const result = this.registers.A & value;
    this.setFlags(result);
    this.registers.A = result;
  }

  ORA(operands) {
    const value = this.getRegisterValue(operands);
    const result = this.registers.A | value;
    this.setFlags(result);
    this.registers.A = result;
  }

  XRA(operands) {
    const value = this.getRegisterValue(operands);
    const result = this.registers.A ^ value;
    this.setFlags(result);
    this.registers.A = result;
  }

  CMP(operands) {
    const value = this.getRegisterValue(operands);
    const result = this.registers.A - value;
    this.setFlags(result);
  }

  // ======================== I/O Instructions ========================

  OUT(operands) {
    const value = this.registers.A;
    this.output.push({
      type: 'OUT',
      value: value,
      hex: '0x' + value.toString(16).toUpperCase().padStart(2, '0'),
      decimal: value,
      binary: value.toString(2).padStart(8, '0'),
    });
  }

  // ======================== Helper Methods ========================

  getRegisterValue(reg) {
    const r = reg.trim().toUpperCase();
    if (!(r in this.registers)) {
      throw new Error(`Invalid register: ${r}`);
    }
    return this.registers[r];
  }

  setRegisterValue(reg, value) {
    const r = reg.trim().toUpperCase();
    if (!(r in this.registers)) {
      throw new Error(`Invalid register: ${r}`);
    }
    this.registers[r] = value & 0xFF;
  }

  parseValue(val) {
    const v = val.trim();
    if (v.startsWith('0x') || v.startsWith('0X')) {
      return parseInt(v, 16);
    }
    if (v.endsWith('H') || v.endsWith('h')) {
      return parseInt(v.slice(0, -1), 16);
    }
    if (v.endsWith('B') || v.endsWith('b')) {
      return parseInt(v.slice(0, -1), 2);
    }
    return parseInt(v, 10);
  }

  setFlags(value) {
    value = value & 0xFF;
    this.flags.Z = value === 0;
    this.flags.C = value > 255;
    this.flags.S = (value & 0x80) !== 0;
    this.flags.P = this.countBits(value) % 2 === 0;
  }

  countBits(value) {
    let count = 0;
    while (value) {
      count += value & 1;
      value >>= 1;
    }
    return count;
  }

  getState() {
    return {
      registers: { ...this.registers },
      flags: { ...this.flags },
      memory: [...this.memory],
      pc: this.pc,
      sp: this.sp,
    };
  }

  reset() {
    for (let reg in this.registers) {
      this.registers[reg] = 0;
    }
    this.memory.fill(0);
    this.flags = { Z: false, C: false, P: false, S: false };
    this.pc = 0;
    this.sp = 0xFF;
    this.output = [];
    this.instructionCount = 0;
  }
}

module.exports = Assembler8085;
