/**
 * Parser Test Suite
 * Run with: node parser-test.js
 */

const { Parser } = require('./parser.js');

console.log('========================================');
console.log('  8085 Assembly Parser Test Suite');
console.log('========================================\\n');

// Test 1: Simple instruction
console.log('Test 1: Simple Instruction');
const code1 = 'MVI A, 05H';
const parser1 = new Parser(code1);
const result1 = parser1.parse();
parser1.prettyPrint();

// Test 2: With labels
console.log('\\nTest 2: Program with Labels');
const code2 = `LOOP: MVI A, 00H
      INR A
      CMP B
      JNZ LOOP
      HLT`;
const parser2 = new Parser(code2);
const result2 = parser2.parse();
parser2.prettyPrint();

// Test 3: Complete program with comments
console.log('\\nTest 3: Complete Program');
const code3 = `; Addition Program
; Adds two numbers

START: MVI A, 05H       ; Load 5 into A
       MVI B, 03H       ; Load 3 into B
       ADD B            ; Add B to A
       OUT              ; Output result
       HLT              ; Stop execution

; End of program`;

const parser3 = new Parser(code3);
const result3 = parser3.parse();
parser3.prettyPrint();

// Test 4: Multiple number formats
console.log('\\nTest 4: Various Number Formats');
const code4 = `MVI A, 255        ; Decimal
MVI B, 0FFH       ; Hex with leading 0 and H suffix
MVI C, 0xAB       ; Hex with 0x prefix
MVI D, 11111111B  ; Binary with B suffix
MVI E, 0b10101010 ; Binary with 0b prefix`;

const parser4 = new Parser(code4);
const result4 = parser4.parse();
parser4.prettyPrint();

// Display operand details for test 4
console.log('Operand Values:');
result4.instructions.forEach((instr, idx) => {
  if (instr.operands.length > 1) {
    const reg = instr.operands[0].value;
    const val = instr.operands[1].value;
    console.log(`  ${reg} = ${val} (0x${val.toString(16).toUpperCase()}, 0b${val.toString(2)})`);
  }
});
console.log('');
