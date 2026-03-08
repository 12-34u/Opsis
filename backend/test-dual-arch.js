const Assembler8086Bridge = require('./assembler');

const assembler = new Assembler8086Bridge();

console.log('=== 8085 + 8086 Dual Architecture Test ===\n');

// Test both architectures in same program
const code = `
; 8085-style code
MOV A, 10
MOV B, 20
ADD A, B
OUT A

; 8086-style code  
MOV AX, 100
MOV BX, 200
ADD AX, BX
OUT AX

HLT
`;

const result = assembler.execute(code);

if (result.success) {
  console.log('✅ Execution successful!\n');
  console.log('8085 Registers:');
  console.log('  A =', result.state.registers.A);
  console.log('  B =', result.state.registers.B);
  console.log('\n8086 Registers:');
  console.log('  AX =', result.state.registers.AX);
  console.log('  BX =', result.state.registers.BX);
  console.log('\nOutput:');
  result.output.forEach((out, i) => {
    console.log(`  ${i + 1}. ${out.value} (${out.hex})`);
  });
} else {
  console.log('❌ Error:', result.error);
  console.log('Error Details:', result.errorDetails);
}
