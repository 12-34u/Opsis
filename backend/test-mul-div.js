const Assembler8086Bridge = require('./assembler');

const assembler = new Assembler8086Bridge();

console.log('Testing MUL and DIV instructions...\n');

// Test 1: MUL with implicit A register
console.log('Test 1: MUL B (8 * 4 = 32)');
let result = assembler.execute(`
MVI A, 08H
MVI B, 04H
MUL B
OUT
HLT
`);
console.log('Success:', result.success);
if (result.success) {
  console.log('Output:', result.output);
  console.log('A register:', result.state.registers.A);
} else {
  console.log('ERROR:', result.error);
}

console.log('\n---\n');

// Test 2: DIV with implicit A register
assembler.reset();
console.log('Test 2: DIV B (32 / 4 = 8)');
result = assembler.execute(`
MVI A, 20H
MVI B, 04H
DIV B
OUT
HLT
`);
console.log('Success:', result.success);
if (result.success) {
  console.log('Output:', result.output);
  console.log('A register:', result.state.registers.A);
} else {
  console.log('ERROR:', result.error);
}

console.log('\n---\n');

// Test 3: MUL with explicit registers (8086 style)
assembler.reset();
console.log('Test 3: MUL AX, BX (5 * 3 = 15)');
result = assembler.execute(`
MVI AX, 05H
MVI BX, 03H
MUL AX, BX
OUT AX
HLT
`);
console.log('Success:', result.success);
if (result.success) {
  console.log('Output:', result.output);
  console.log('AX register:', result.state.registers.AX);
} else {
  console.log('ERROR:', result.error);
}

console.log('\n---\n');

// Test 4: Division by zero
assembler.reset();
console.log('Test 4: DIV by zero (should fail)');
result = assembler.execute(`
MVI A, 0AH
MVI B, 00H
DIV B
OUT
HLT
`);
console.log('Success:', result.success);
if (result.success) {
  console.log('Unexpected success!');
} else {
  console.log('Expected ERROR:', result.error);
}
