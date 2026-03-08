/**
 * Test file for the Assembly Language Lexer
 * Run with: node lexer-test.js
 */

const { Lexer, TokenType } = require('./lexer.js');

// Test cases
const testCases = [
  {
    name: 'Simple Instruction',
    code: 'MVI A, 05H',
    expected: ['INSTRUCTION', 'REGISTER', 'COMMA', 'NUMBER', 'EOF'],
  },
  {
    name: 'Instruction with Comment',
    code: 'ADD B            ; Add B to A',
    expected: ['INSTRUCTION', 'REGISTER', 'COMMENT', 'EOF'],
  },
  {
    name: 'Label Definition',
    code: 'LOOP: MVI A, 10',
    expected: ['IDENTIFIER', 'COLON', 'INSTRUCTION', 'REGISTER', 'COMMA', 'NUMBER', 'EOF'],
  },
  {
    name: 'Multiple Number Formats',
    code: 'MVI A, 0xFF\\nMVI B, 255\\nMVI C, 11111111B',
    expected: null, // Just visual test
  },
  {
    name: 'Complete Program',
    code: `; Example program
MVI A, 05H       ; Load 5
MVI B, 03H       ; Load 3
ADD B            ; Add them
OUT              ; Output
HLT              ; Stop`,
    expected: null,
  },
];

console.log('========================================');
console.log('  8085 Assembly Lexer Test Suite');
console.log('========================================\\n');

testCases.forEach((test, index) => {
  console.log(`Test ${index + 1}: ${test.name}`);
  console.log('Code:');
  console.log('  ' + test.code.replace(/\\n/g, '\\n  '));
  console.log('\\nTokens:');
  
  const lexer = new Lexer(test.code);
  const tokens = lexer.tokenize();
  
  tokens.forEach(token => {
    if (token.type !== TokenType.NEWLINE) {
      console.log(`  ${token.toString()}`);
    }
  });
  
  if (test.expected) {
    const actualTypes = tokens.map(t => t.type);
    const match = JSON.stringify(actualTypes) === JSON.stringify(test.expected);
    console.log(`\\n✓ Expected: ${test.expected.join(', ')}`);
    console.log(`  Actual:   ${actualTypes.join(', ')}`);
    console.log(`  Result:   ${match ? '✓ PASS' : '✗ FAIL'}\\n`);
  }
  
  console.log('----------------------------------------\\n');
});

// Interactive test
console.log('\\n========================================');
console.log('  Number Format Tests');
console.log('========================================\\n');

const numberTests = [
  { code: '255', desc: 'Decimal' },
  { code: '0xFF', desc: 'Hex with 0x' },
  { code: 'FFH', desc: 'Hex with H suffix' },
  { code: '0xAB', desc: 'Hex lowercase' },
  { code: '11111111B', desc: 'Binary with B suffix' },
  { code: '0b11111111', desc: 'Binary with 0b prefix' },
];

numberTests.forEach(test => {
  const lexer = new Lexer(test.code);
  const token = lexer.getNextToken();
  console.log(`${test.desc.padEnd(25)} "${test.code.padEnd(15)}" => ${token.value} (0x${token.value.toString(16).toUpperCase()})`);
});
