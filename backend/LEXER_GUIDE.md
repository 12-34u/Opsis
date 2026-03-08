# Lexer & Parser Implementation Guide

## Overview

This document explains the **lexer** and **parser** implementation for the Opsis 8086 Assembly Language IDE.

## Architecture

```
Source Code (Assembly)
       ↓
   [LEXER] ← Tokenization (lexer.js)
       ↓
   Tokens (stream of meaningful units)
       ↓
   [PARSER] ← Syntax Analysis (parser.js)
       ↓
   AST/Instructions (structured data)
       ↓
   [ASSEMBLER] ← Execution (assembler.js)
       ↓
   Machine Execution
```

---

## 1. LEXER (Tokenizer)

### Purpose
Converts raw source code into **tokens** - the smallest meaningful units.

### Example Transformation

**Input:**
```asm
MVI A, 05H  ; Load 5
```

**Output Tokens:**
```javascript
[
  Token(INSTRUCTION, "MVI", 1:1),
  Token(REGISTER, "A", 1:5),
  Token(COMMA, ",", 1:6),
  Token(NUMBER, 5, 1:8),
  Token(COMMENT, "Load 5", 1:13),
]
```

### Token Types

| Token Type    | Description              | Example           |
|---------------|--------------------------|-------------------|
| INSTRUCTION   | Opcode/mnemonic          | `MVI`, `ADD`      |
| REGISTER      | Register name            | `A`, `B`, `HL`    |
| NUMBER        | Numeric literal          | `5`, `0xFF`, `10B`|
| COMMA         | Operand separator        | `,`               |
| COLON         | Label delimiter          | `:`               |
| LABEL         | Jump target              | `LOOP`            |
| COMMENT       | Documentation            | `; comment`       |
| NEWLINE       | Line terminator          | `\\n`             |
| EOF           | End of file              | -                 |

### Number Format Support

The lexer recognizes multiple number formats:

```asm
255         ; Decimal
0xFF        ; Hexadecimal (0x prefix)
FFH         ; Hexadecimal (H suffix)
11111111B   ; Binary (B suffix)
0b11111111  ; Binary (0b prefix)
```

---

## 2. PARSER

### Purpose
Converts tokens into **structured instructions** with validated syntax.

### Example Transformation

**Tokens:**
```javascript
[INSTRUCTION("MVI"), REGISTER("A"), COMMA, NUMBER(5)]
```

**Output Instruction:**
```javascript
Instruction {
  opcode: "MVI",
  operands: [
    Operand { type: 'register', value: 'A' },
    Operand { type: 'immediate', value: 5 }
  ],
  label: null,
  comment: null,
  line: 1
}
```

### Features

- **Label Resolution**: Maps labels to instruction positions
- **Operand Validation**: Checks operand types and counts
- **Error Reporting**: Provides line and column information
- **Comment Preservation**: Maintains documentation

---

## 3. Integration with Assembler

### Current Assembler (assembler.js)

The current implementation uses basic string splitting:

```javascript
// OLD APPROACH
parse(code) {
  const lines = code.split('\\n');
  // ... simple splitting
}
```

### New Lexer/Parser Approach

Here's how to integrate:

```javascript
const { Parser } = require('./parser.js');

class Assembler8086Bridge {
  // ... existing code ...

  /**
   * Parse assembly code using new lexer/parser
   */
  parseWithLexer(code) {
    try {
      const parser = new Parser(code);
      const result = parser.parse();
      
      return {
        success: true,
        instructions: result.instructions,
        labels: result.labels,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Execute using parsed instructions
   */
  executeWithParser(code) {
    this.reset();
    const parseResult = this.parseWithLexer(code);
    
    if (!parseResult.success) {
      return {
        success: false,
        error: parseResult.error,
      };
    }

    const { instructions, labels } = parseResult;
    this.executionState = 'running';
    const steps = [];

    try {
      while (this.pc < instructions.length && this.executionState === 'running') {
        const instruction = instructions[this.pc];
        const before = this.getState();

        // Execute using structured instruction
        this.executeStructuredInstruction(instruction);

        const after = this.getState();
        steps.push({
          pc: this.pc,
          instruction: instruction.toString(),
          before,
          after,
        });

        this.pc++;
        this.instructionCount++;
      }

      return {
        success: true,
        state: this.getState(),
        steps,
        output: this.output,
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
   * Execute a structured instruction object
   */
  executeStructuredInstruction(instruction) {
    const opcode = instruction.opcode;
    const operands = instruction.operands;

    switch (opcode) {
      case 'MOV':
        if (operands.length !== 2) {
          throw new Error(\`MOV requires 2 operands, got \${operands.length}\`);
        }
        this.setRegisterValue(operands[0].value, this.getRegisterValue(operands[1].value));
        break;

      case 'MVI':
        if (operands.length !== 2) {
          throw new Error(\`MVI requires 2 operands, got \${operands.length}\`);
        }
        this.setRegisterValue(operands[0].value, operands[1].value);
        break;

      case 'ADD':
        if (operands.length !== 1) {
          throw new Error(\`ADD requires 1 operand, got \${operands.length}\`);
        }
        const value = this.getRegisterValue(operands[0].value);
        const result = this.registers.A + value;
        this.setFlags(result);
        this.registers.A = result & 0xFF;
        break;

      case 'HLT':
        this.executionState = 'stopped';
        break;

      // ... more instructions ...

      default:
        throw new Error(\`Unknown instruction: \${opcode}\`);
    }
  }
}
```

---

## 4. Benefits of Lexer/Parser

### ✅ Advantages

1. **Better Error Messages**
   - Line and column information
   - Specific error types (syntax, operand count, etc.)

2. **Cleaner Code**
   - Separation of concerns (tokenization vs. parsing vs. execution)
   - Easier to maintain and extend

3. **More Features**
   - Macro support (future)
   - Directives (.ORG, .DB, .DW)
   - Better label resolution

4. **Robust Parsing**
   - Handles edge cases (whitespace, comments, formats)
   - Validates syntax before execution

5. **IDE Integration**
   - Syntax highlighting
   - Autocomplete
   - Real-time error checking

---

## 5. Testing

### Run Lexer Tests
```bash
cd backend
node lexer-test.js
```

### Run Parser Tests
```bash
cd backend
node parser-test.js
```

### Example Output
```
========== Parsed Program ==========

Labels:
  LOOP -> instruction 0

Instructions:
    0: LOOP: MVI A, 00H
    1: INR A
    2: CMP B
    3: JNZ LOOP
    4: HLT
```

---

## 6. Next Steps

### Phase 1: Basic Integration ✅
- [x] Implement lexer
- [x] Implement parser
- [x] Create tests

### Phase 2: Integration (Next)
- [ ] Integrate parser into assembler.js
- [ ] Update IPC handlers
- [ ] Test with existing frontend

### Phase 3: Enhanced Features
- [ ] Add directives (.ORG, .DB, .DW, .EQU)
- [ ] Implement macros
- [ ] Add 8086-specific instructions
- [ ] Syntax validation in editor

### Phase 4: IDE Features
- [ ] Real-time error highlighting
- [ ] Autocomplete for instructions/registers
- [ ] Hover documentation
- [ ] Symbol navigation

---

## 7. File Structure

```
backend/
├── lexer.js           # Tokenizer implementation
├── parser.js          # Parser implementation
├── lexer-test.js      # Lexer tests
├── parser-test.js     # Parser tests
├── assembler.js       # Main assembler (to be updated)
└── LEXER_GUIDE.md     # This file
```

---

## 8. API Reference

### Lexer API

```javascript
const { Lexer, TokenType } = require('./lexer.js');

const lexer = new Lexer(sourceCode);
const tokens = lexer.tokenize(); // Returns array of tokens

// Or get tokens one by one
let token;
do {
  token = lexer.getNextToken();
  console.log(token);
} while (token.type !== TokenType.EOF);
```

### Parser API

```javascript
const { Parser } = require('./parser.js');

const parser = new Parser(sourceCode);
const result = parser.parse();

console.log(result.instructions); // Array of Instruction objects
console.log(result.labels);       // Map of label names to positions

parser.prettyPrint(); // Pretty print the parsed program
```

---

## 9. Example: Complete Workflow

```javascript
// 1. Write assembly code
const code = \`
LOOP: MVI A, 00H    ; Initialize A
      INR A         ; Increment A
      CMP B         ; Compare with B
      JNZ LOOP      ; Loop if not zero
      HLT           ; Stop
\`;

// 2. Tokenize with Lexer
const lexer = new Lexer(code);
const tokens = lexer.tokenize();
console.log('Tokens:', tokens);

// 3. Parse into Instructions
const parser = new Parser(code);
const { instructions, labels } = parser.parse();
console.log('Instructions:', instructions);
console.log('Labels:', labels);

// 4. Execute with Assembler
const assembler = new Assembler8086Bridge();
const result = assembler.executeWithParser(code);
console.log('Result:', result);
```

---

## Resources

- **8086 Instruction Set**: See backend/README.md
- **Number Formats**: Decimal, Hex (0x/H), Binary (0b/B)
- **Token Types**: See TokenType enum in lexer.js

---

**Author**: Opsis Development Team  
**Last Updated**: March 2026
