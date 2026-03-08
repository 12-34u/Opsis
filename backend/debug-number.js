/**
 * Debug script for testing specific parsing issues
 */

const { Lexer, TokenType } = require('./lexer.js');

// Test the problematic case
console.log('Testing: 11111111B\n');

const lexer = new Lexer('MVI D, 11111111B');
let token;

do {
  token = lexer.getNextToken();
  console.log(token.toString());
} while (token.type !== TokenType.EOF);

// Test individual number
console.log('\n\nTesting just the number:');
const lexer2 = new Lexer('11111111B');
const token2 = lexer2.getNextToken();
console.log('Token:', token2);
console.log('Type:', token2.type);
console.log('Value:', token2.value);

// Test if regex works
const testStr = '11111111';
console.log(`\nRegex test: /^[01]+$/.test("${testStr}") =`, /^[01]+$/.test(testStr));
