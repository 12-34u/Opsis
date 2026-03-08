# Opsis Assembly Assembler IDE

An educational 8086-focused assembly language assembler and interpreter built into Opsis Code Editor.

## Features

### Assembler Support
- **8086 Microprocessor** - Primary architecture
- **Complete Instruction Set**:
  - Data Movement: MOV, MVI, LDA, STA
  - Arithmetic: ADD, ADI, SUB, SUI, MUL, DIV, INR, DCR
  - Logical: ANA, ORA, XRA, CMP
  - I/O & Control: OUT, HLT, NOP

### Execution Engine
- **Python-backed Assembly Interpretation** - Electron invokes a Python 8086 engine
- **Register State Display** - View key 8086 registers (AX, BX, CX, DX, SI, DI, BP, SP, IP)
- **Flag Visualization** - Zero, Carry, Parity, Sign flags
- **Memory Inspector** - Hexadecimal memory dump with navigation
- **Output Panel** - View execution results in Hex/Decimal/Binary

### IDE Features
- **Monaco Editor** - Professional code editing with syntax highlighting
- **File Management** - Create, open, save assembly files
- **Multi-file Tabs** - Work with multiple assembly files
- **Tokyo Night Theme** - Beautiful dark color scheme
- **Error Reporting** - Clear error messages with execution info

## Usage

### Creating a New Assembly Program

1. **File → New** or press the new file button
2. Write assembly code:
   ```asm
   MVI A, 05H       ; Load 5 into A
   MVI B, 03H       ; Load 3 into B
   ADD B            ; Add B to A
   OUT              ; Output result
   HLT              ; Stop
   ```
3. **Run → Execute** or press Ctrl+Shift+R
4. View results in the Register, Memory, and Output panels

### Number Formats

- **Decimal**: `10`, `255`
- **Hexadecimal**: `0xAF`, `AFH`, `0Ah`
- **Binary**: `11111111B`, `0b11111111`

### Instruction Reference

#### Data Movement
```asm
MOV A, B         ; Copy B to A
MVI A, 0x05      ; Load immediate value
LDA 0x50         ; Load from memory address
STA 0x50         ; Store to memory address
```

#### Arithmetic
```asm
ADD B            ; A = A + B
ADI 0x10         ; A = A + 0x10
SUB C            ; A = A - C
MUL D            ; A = A * D
DIV E            ; A = A / E
INR A            ; A = A + 1
DCR B            ; B = B - 1
```

#### Logical Operations
```asm
ANA B            ; A = A AND B
ORA C            ; A = A OR C
XRA D            ; A = A XOR D
CMP B            ; Compare A with B (sets flags)
```

#### I/O and Control
```asm
OUT              ; Output A register
HLT              ; Halt execution
NOP              ; No operation
```

## Register Details

### General Purpose Registers
- **A (Accumulator)** - Main working register
- **B, C, D, E** - General purpose
- **H, L** - Usually used for memory addressing

### Flags
- **Z (Zero)** - Set when result is 0
- **C (Carry)** - Set when result > 255
- **P (Parity)** - Set when result has even parity
- **S (Sign)** - Set when result bit 7 is 1

### Special Registers
- **PC (Program Counter)** - Points to next instruction
- **SP (Stack Pointer)** - Points to stack top

## Example Programs

### Example 1: Basic Arithmetic
```asm
MVI A, 08H       ; A = 8
MVI B, 04H       ; B = 4
MUL B            ; A = 8 * 4 = 32
OUT              ; Output 32
DIV B            ; A = 32 / 4 = 8
OUT              ; Output 8
HLT
```

### Example 2: Using Multiple Registers
```asm
MVI A, 10H       ; A = 16
MVI B, 20H       ; B = 32
MVI C, 05H       ; C = 5
ADD B            ; A = 16 + 32 = 48
SUB C            ; A = 48 - 5 = 43
OUT              ; Output 43
HLT
```

### Example 3: Logical Operations
```asm
MVI A, 0FH       ; A = 15 (binary: 00001111)
MVI B, 03H       ; B = 3  (binary: 00000011)
ANA B            ; A = 15 AND 3 = 3
OUT              ; Output 3
HLT
```

## Output Format

The Output Panel displays execution results in three formats:
- **HEX**: `0x05` - Hexadecimal notation
- **DEC**: `5` - Decimal value
- **BIN**: `00000101` - Binary representation (8-bit)

## Memory Layout

The memory viewer shows a 256-byte address space:
- Addresses from `0x00` to `0xFF`
- Display in 16x16 grid (16 rows × 16 columns)
- Navigate with arrow buttons or direct address input
- Green highlight shows non-zero memory locations

## Troubleshooting

### "Division by zero" Error
```asm
MVI A, 10H
MVI B, 00H
DIV B            ; ERROR: Cannot divide by zero
```
Solution: Ensure divisor is not zero

### "Invalid register" Error
Check register names are valid: AX, BX, CX, DX, SI, DI, BP, SP, IP (case-insensitive)

### "Unknown instruction" Error
Verify instruction spelling and format. See Instruction Reference above.

## Future Enhancements

- [ ] Looping and branching (JMP, JNZ, JZ)
- [ ] Subroutines (CALL, RET)
- [ ] Stack operations (PUSH, POP)
- [ ] Memory addressing modes
- [ ] Breakpoints and step-through debugging
- [ ] Visual data flow diagrams
- [ ] 8086 extended instructions
- [ ] Reverse disassembly

## Education

This assembler is designed for:
- Learning microprocessor architecture
- Understanding low-level programming
- Computer science education
- Assembly language fundamentals
- Microcontroller programming basics

---

**Opsis Assembler** - Building understanding through code execution
