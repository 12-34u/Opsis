; 8085/8086 Assembly Language - Opsis Assembler
; Example Programs

; ============================================================================
; EXAMPLE 1: Simple Addition
; ============================================================================

; Load 5 into A, 3 into B, add them, and output result
MVI A, 05H       ; A = 5
MVI B, 03H       ; B = 3
ADD B            ; A = A + B = 8
OUT              ; Output 8
HLT              ; Stop


; ============================================================================
; EXAMPLE 2: Using Multiple Registers
; ============================================================================

; Load values into different registers
MVI A, 10H       ; A = 16
MVI B, 20H       ; B = 32
MVI C, 05H       ; C = 5
ADD B            ; A = A + B = 48
SUB C            ; A = A - C = 43
OUT              ; Output 43
HLT


; ============================================================================
; EXAMPLE 3: Increment and Decrement
; ============================================================================

MVI A, 0AH       ; A = 10
INR A            ; A = A + 1 = 11
INR A            ; A = A + 1 = 12
DCR A            ; A = A - 1 = 11
OUT              ; Output 11
HLT


; ============================================================================
; EXAMPLE 4: Multiplication and Division
; ============================================================================

MVI A, 08H       ; A = 8
MVI B, 04H       ; B = 4
MUL B            ; A = A * B = 32
OUT              ; Output 32
DIV B            ; A = A / B = 8
OUT              ; Output 8
HLT


; ============================================================================
; EXAMPLE 5: Logical Operations
; ============================================================================

MVI A, 0FH       ; A = 15 (binary: 00001111)
MVI B, 03H       ; B = 3  (binary: 00000011)
ANA B            ; A = A AND B = 3
OUT              ; Output 3
MVI A, 0FH       ; Reset A = 15
ORA B            ; A = A OR B = 15
OUT              ; Output 15
HLT


; ============================================================================
; Instruction Set Reference
; ============================================================================
; MOV dest, src     - Move/copy data
; MVI reg, value    - Move immediate value
; ADD reg           - Add register to A
; ADI value         - Add immediate to A
; SUB reg           - Subtract register from A
; SUI value         - Subtract immediate from A
; MUL reg           - Multiply A by register
; DIV reg           - Divide A by register
; INR reg           - Increment register
; DCR reg           - Decrement register
; ANA reg           - Bitwise AND
; ORA reg           - Bitwise OR
; XRA reg           - Bitwise XOR
; CMP reg           - Compare
; LDA addr          - Load from memory
; STA addr          - Store to memory
; OUT               - Output value from A
; HLT               - Halt execution
; NOP               - No operation

; ============================================================================
; Register Names: A, B, C, D, E, H, L
; Number Formats:
;   - Decimal: 10, 255
;   - Hex: 0xAF, AFH, 0xaf
;   - Binary: 11111111B, 0b11111111
; ============================================================================
