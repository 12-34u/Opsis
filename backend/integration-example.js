/**
 * Integration Example: Complete Workflow
 * Demonstrates lexer → parser → assembler integration
 */

const { Lexer, TokenType } = require('./lexer.js');
const { Parser } = require('./parser.js');

console.log('='.repeat(60));
console.log('  Opsis Assembly Language - Complete Workflow');
console.log('='.repeat(60));

// Sample assembly program
const assemblyCode = `
; Fibonacci-like sequence generator
; Computes: 1, 1, 2, 3, 5, 8...

START: MVI A, 01H      ; First number = 1
       MVI B, 01H      ; Second number = 1
       OUT             ; Output first number

LOOP:  MOV C, A        ; Save A to C
       ADD B           ; A = A + B
       OUT             ; Output result
       MOV A, B        ; A = B (previous second)
       MOV B, C        ; B = C (previous first)
       HLT             ; Stop (in real code, would loop)

; End of program
`;

console.log('\n1. SOURCE CODE');
console.log('-'.repeat(60));
console.log(assemblyCode);

// STEP 1: LEXICAL ANALYSIS (Tokenization)
console.log('\n2. LEXICAL ANALYSIS (Tokenization)');
console.log('-'.repeat(60));
const lexer = new Lexer(assemblyCode);
const tokens = lexer.tokenize();

let tokenCount = { instructions: 0, registers: 0, numbers: 0, labels: 0 };
tokens.forEach(token => {
  if (token.type === TokenType.INSTRUCTION) tokenCount.instructions++;
  if (token.type === TokenType.REGISTER) tokenCount.registers++;
  if (token.type === TokenType.NUMBER) tokenCount.numbers++;
  if (token.type === TokenType.IDENTIFIER) tokenCount.labels++;
});

console.log(`✓ Tokenization complete`);
console.log(`  Total tokens: ${tokens.length}`);
console.log(`  Instructions: ${tokenCount.instructions}`);
console.log(`  Registers: ${tokenCount.registers}`);
console.log(`  Numbers: ${tokenCount.numbers}`);
console.log(`  Labels/Identifiers: ${tokenCount.labels}`);

// STEP 2: SYNTAX ANALYSIS (Parsing)
console.log('\n3. SYNTAX ANALYSIS (Parsing)');
console.log('-'.repeat(60));
const parser = new Parser(assemblyCode);
const parseResult = parser.parse();

console.log(`✓ Parsing complete`);
console.log(`  Instructions: ${parseResult.instructions.length}`);
console.log(`  Labels: ${parseResult.labels.size}`);

// Display parsed program
parser.prettyPrint();

// STEP 3: STRUCTURED INSTRUCTION DETAILS
console.log('\n4. INSTRUCTION DETAILS');
console.log('-'.repeat(60));
parseResult.instructions.forEach((instr, idx) => {
  let detail = `${idx.toString().padStart(2)}: ${instr.opcode.padEnd(6)}`;
  
  if (instr.operands.length > 0) {
    detail += instr.operands.map(op => {
      if (op.type === 'immediate') {
        return `${op.value} (0x${op.value.toString(16).toUpperCase()})`;
      }
      return op.value;
    }).join(', ');
  }
  
  if (instr.label) {
    detail = `[${instr.label}] ` + detail;
  }
  
  console.log(detail);
});

// STEP 4: LABEL RESOLUTION
console.log('\n5. LABEL RESOLUTION');
console.log('-'.repeat(60));
parseResult.labels.forEach((position, name) => {
  console.log(`  ${name.padEnd(10)} → Instruction ${position} (Address: 0x${(position * 2).toString(16).toUpperCase()})`);
});

// STEP 5: READY FOR EXECUTION
console.log('\n6. READY FOR EXECUTION');
console.log('-'.repeat(60));
console.log('✓ Code is syntax-valid and ready to execute');
console.log('✓ Labels resolved');
console.log('✓ Operands validated');
console.log('\nTo execute:');
console.log('  const assembler = new Assembler8085();');
console.log('  const result = assembler.executeWithParser(parseResult);');

console.log('\n' + '='.repeat(60));
console.log('  Lexer & Parser Integration Complete');
console.log('='.repeat(60) + '\n');
