# Lexer Implementation - Quick Reference

## What We Built

A complete **Lexer (Tokenizer)** and **Parser** for your Opsis 8085 Assembly Language IDE.

## Files Created

```
backend/
├── lexer.js              # Core lexer/tokenizer
├── parser.js             # Syntax analyzer
├── lexer-test.js         # Lexer unit tests
├── parser-test.js        # Parser unit tests
├── debug-number.js       # Number format debugging
├── integration-example.js # Complete workflow demo
├── LEXER_GUIDE.md        # Comprehensive documentation
└── QUICK_REFERENCE.md    # This file
```

## How It Works

### 1. Lexer (Tokenizer)
Converts source code string → array of tokens

```javascript
const { Lexer } = require('./lexer.js');
const lexer = new Lexer('MVI A, 05H');
const tokens = lexer.tokenize();
// Returns: [INSTRUCTION, REGISTER, COMMA, NUMBER, EOF]
```

### 2. Parser
Converts tokens → structured instructions

```javascript
const { Parser } = require('./parser.js');
const parser = new Parser(assemblyCode);
const { instructions, labels } = parser.parse();
// Returns structured Instruction objects with validated operands
```

## Token Types Supported

| Type | Examples |
|------|----------|
| INSTRUCTION | `MVI`, `ADD`, `MOV`, `HLT` |
| REGISTER | `A`, `B`, `C`, `D`, `E`, `H`, `L` |
| NUMBER | `255`, `0FFH`, `0xAB`, `11111111B`, `0b10101010` |
| COMMA | `,` |
| COLON | `:` |
| IDENTIFIER | Label names like `LOOP`, `START` |
| COMMENT | `; This is a comment` |

## Number Formats

| Format | Example | Value |
|--------|---------|-------|
| Decimal | `255` | 255 |
| Hex (0x) | `0xFF` | 255 |
| Hex (H) | `0FFH` | 255 |
| Binary (B) | `11111111B` | 255 |
| Binary (0b) | `0b11111111` | 255 |

**Important**: Hex numbers starting with A-F must have leading 0: `0FFH` not `FFH`

## Running Tests

```bash
cd backend

# Test lexer
node lexer-test.js

# Test parser
node parser-test.js

# See complete workflow
node integration-example.js

# Debug specific issues
node debug-number.js
```

## Integration with Assembler

### Current assembler.js approach:
```javascript
parse(code) {
  const lines = code.split('\\n');
  // Simple string splitting...
}
```

### New approach (with lexer/parser):
```javascript
const { Parser } = require('./parser.js');

parseWithLexer(code) {
  const parser = new Parser(code);
  return parser.parse();
}

executeWithParser(code) {
  const { instructions, labels } = this.parseWithLexer(code);
  // Execute structured instructions...
}
```

## Benefits

✅ **Better error messages** - Line and column information  
✅ **Cleaner code** - Separation of concerns  
✅ **More features** - Easy to add directives, macros  
✅ **Robust parsing** - Handles edge cases correctly  
✅ **IDE integration** - Ready for syntax highlighting, autocomplete  

## Next Steps

### Phase 1: Integration ✅
- [x] Implement lexer
- [x] Implement parser
- [x] Create comprehensive tests
- [x] Document everything

### Phase 2: Assembler Integration (Next)
- [ ] Update `assembler.js` to use parser
- [ ] Update `ipc-handlers.js` for frontend communication
- [ ] Test with existing frontend
- [ ] Add error reporting to UI

### Phase 3: Enhanced Features
- [ ] Add assembler directives (`.ORG`, `.DB`, `.DW`, `.EQU`)
- [ ] Implement macro support
- [ ] Add 8086-specific instructions
- [ ] Multi-pass assembly for forward references

### Phase 4: IDE Features
- [ ] Real-time syntax highlighting in Monaco Editor
- [ ] Autocomplete for instructions/registers
- [ ] Hover tooltips for instructions
- [ ] Jump-to-definition for labels
- [ ] Real-time error highlighting

## API Usage Examples

### Basic Tokenization
```javascript
const lexer = new Lexer('ADD B');
let token = lexer.getNextToken(); // INSTRUCTION: ADD
token = lexer.getNextToken();     // REGISTER: B
```

### Complete Parsing
```javascript
const parser = new Parser(`
  START: MVI A, 05H
         ADD B
         HLT
`);
const result = parser.parse();
console.log(result.instructions); // Array of Instruction objects
console.log(result.labels);       // Map of label → position
```

### Get Specific Token Info
```javascript
const token = new Token(TokenType.NUMBER, 255, 1, 5);
console.log(token.type);   // 'NUMBER'
console.log(token.value);  // 255
console.log(token.line);   // 1
console.log(token.column); // 5
```

## Error Handling

### Lexer Errors
Returns `ILLEGAL` token type for invalid characters or malformed numbers

### Parser Errors
Throws `ParseError` with line and column information:
```javascript
try {
  const parser = new Parser(code);
  const result = parser.parse();
} catch (error) {
  console.error(\`Error at \${error.line}:\${error.column}: \${error.message}\`);
}
```

## Architecture Diagram

```
Assembly Source Code
        ↓
    [LEXER]
        ↓
   Token Stream → [INSTRUCTION, REGISTER, COMMA, NUMBER, ...]
        ↓
    [PARSER]
        ↓
   Structured Instructions → Instruction { opcode, operands, label }
        ↓
   [ASSEMBLER]
        ↓
   Execution & Output
```

## Key Design Decisions

1. **Token-based parsing**: More maintainable than regex string matching
2. **Separate lexer/parser**: Clean separation of concerns
3. **Structured operands**: Typed operands (register vs immediate vs identifier)
4. **Error recovery**: Parser continues after errors to find all issues
5. **Label resolution**: Single-pass with forward reference support

## Common Patterns

### Check if token is a number
```javascript
if (token.type === TokenType.NUMBER) {
  console.log('Numeric value:', token.value);
}
```

### Iterate through all instructions
```javascript
parseResult.instructions.forEach((instr, index) => {
  console.log(\`\${index}: \${instr.opcode}\`);
  instr.operands.forEach(op => {
    console.log(\`  - \${op.type}: \${op.value}\`);
  });
});
```

### Find instruction by label
```javascript
const labelPos = parseResult.labels.get('LOOP');
const instruction = parseResult.instructions[labelPos];
```

## Performance

- **Lexer**: O(n) - single pass through source
- **Parser**: O(n) - single pass through tokens
- **Memory**: Minimal - only stores structured representation

## Compatibility

- ✅ Node.js (CJS `require`)
- ✅ Browser (global `window` object)
- ✅ Works with existing assembler.js architecture

## Questions?

See [LEXER_GUIDE.md](./LEXER_GUIDE.md) for detailed documentation.

---

**Status**: ✅ Phase 1 Complete - Ready for Integration  
**Last Updated**: March 2026  
**Author**: Opsis Development Team
