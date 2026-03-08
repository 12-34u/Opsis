const Assembler8086Bridge = require('./assembler');

const assembler = new Assembler8086Bridge();

console.log('Testing MOV instruction...\n');

// Test 1: MOV with 8086 registers
console.log('Test 1: MOV AX, 5');
let result = assembler.execute('MOV AX, 5\nOUT AX\nHLT');
console.log('Success:', result.success);
if (result.success) {
  console.log('Output:', result.output);
  console.log('AX register:', result.state.registers.AX);
} else {
  console.log('ERROR:', result.error);
  console.log('Error Details:', result.errorDetails);
}

console.log('\n---\n');

// Test 2: MOV with 8085-style register (should fail)
assembler.reset();
console.log('Test 2: MOV A, 5 (8085 register - should fail)');
result = assembler.execute('MOV A, 5\nOUT A\nHLT');
console.log('Success:', result.success);
if (result.success) {
  console.log('Output:', result.output);
} else {
  console.log('ERROR:', result.error);
  console.log('Error Details:', result.errorDetails);
}

console.log('\n---\n');

// Test 3: MVI (8085 style)
assembler.reset();
console.log('Test 3: MVI AX, 5');
result = assembler.execute('MVI AX, 5\nOUT AX\nHLT');
console.log('Success:', result.success);
if (result.success) {
  console.log('Output:', result.output);
  console.log('AX register:', result.state.registers.AX);
} else {
  console.log('ERROR:', result.error);
}
