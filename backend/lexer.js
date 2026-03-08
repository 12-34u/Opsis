/**
 * Lexer (Tokenizer) for 8085/8086 Assembly Language
 * Converts source code into a stream of tokens
 */

// Token types
const TokenType = {
  // Instructions
  INSTRUCTION: 'INSTRUCTION',
  
  // Identifiers & Registers
  REGISTER: 'REGISTER',
  LABEL: 'LABEL',
  IDENTIFIER: 'IDENTIFIER',
  
  // Literals
  NUMBER: 'NUMBER',
  
  // Operators & Punctuation
  COMMA: 'COMMA',
  COLON: 'COLON',
  
  // Special
  COMMENT: 'COMMENT',
  NEWLINE: 'NEWLINE',
  EOF: 'EOF',
  
  // Error
  ILLEGAL: 'ILLEGAL',
};

// Instruction set keywords for 8086 + legacy compatibility
const INSTRUCTIONS = new Set([
  // Core 8086 flow/data
  'MOV', 'LEA', 'PUSH', 'POP', 'XCHG',
  'ADD', 'ADC', 'SUB', 'SBB', 'INC', 'DEC', 'CMP', 'NEG',
  'AND', 'OR', 'XOR', 'NOT', 'TEST',
  'JMP', 'JE', 'JNE', 'JZ', 'JNZ', 'JC', 'JNC', 'JO', 'JNO', 'JS', 'JNS',
  'CALL', 'RET', 'INT', 'NOP', 'HLT',

  // Compatibility mnemonics already used by existing samples/tests
  'MOV', 'MVI', 'LDA', 'STA', 'LHLD', 'SHLD', 'LXI', 'LDAX', 'STAX',
  'XCHG', 'PUSH', 'POP', 'XTHL', 'SPHL',
  'ADD', 'ADI', 'ADC', 'ACI', 'SUB', 'SUI', 'SBB', 'SBI',
  'INR', 'DCR', 'INX', 'DCX', 'DAD', 'MUL', 'DIV',
  'ANA', 'ANI', 'ORA', 'ORI', 'XRA', 'XRI', 'CMP', 'CPI',
  'RLC', 'RRC', 'RAL', 'RAR', 'CMA', 'CMC', 'STC',
  'JMP', 'JC', 'JNC', 'JZ', 'JNZ', 'JP', 'JM', 'JPE', 'JPO',
  'CALL', 'CC', 'CNC', 'CZ', 'CNZ', 'CP', 'CM', 'CPE', 'CPO',
  'RET', 'RC', 'RNC', 'RZ', 'RNZ', 'RP', 'RM', 'RPE', 'RPO',
  'RST', 'PCHL', 
  'IN', 'OUT',
  'HLT', 'NOP', 'EI', 'DI', 'RIM', 'SIM',
]);

// Register names (8086 + legacy)
const REGISTERS = new Set([
  // 8086 general + segment + pointers
  'AX', 'BX', 'CX', 'DX', 'AH', 'AL', 'BH', 'BL', 'CH', 'CL', 'DH', 'DL',
  'SI', 'DI', 'BP', 'SP', 'IP',
  'CS', 'DS', 'ES', 'SS',
  // Legacy 8085 registers retained for backwards compatibility
  'A', 'B', 'C', 'D', 'E', 'H', 'L', 'M', 'PSW',
]);

// Register pairs
const REGISTER_PAIRS = new Set(['BC', 'DE', 'HL', 'PSW']);

class Token {
  constructor(type, value, line, column) {
    this.type = type;
    this.value = value;
    this.line = line;
    this.column = column;
  }
  
  toString() {
    return `Token(${this.type}, "${this.value}", ${this.line}:${this.column})`;
  }
}

class Lexer {
  constructor(source) {
    this.source = source;
    this.position = 0;
    this.line = 1;
    this.column = 1;
    this.currentChar = this.source[0] || null;
  }

  /**
   * Advance to the next character
   */
  advance() {
    if (this.currentChar === '\n') {
      this.line++;
      this.column = 1;
    } else {
      this.column++;
    }
    
    this.position++;
    this.currentChar = this.position < this.source.length ? this.source[this.position] : null;
  }

  /**
   * Peek at the next character without advancing
   */
  peek(offset = 1) {
    const peekPos = this.position + offset;
    return peekPos < this.source.length ? this.source[peekPos] : null;
  }

  /**
   * Skip whitespace (except newlines)
   */
  skipWhitespace() {
    while (this.currentChar !== null && 
           this.currentChar !== '\n' &&
           /\s/.test(this.currentChar)) {
      this.advance();
    }
  }

  /**
   * Read a comment starting with ';'
   */
  readComment() {
    const startColumn = this.column;
    let comment = '';
    
    // Skip the ';'
    this.advance();
    
    // Read until end of line
    while (this.currentChar !== null && this.currentChar !== '\n') {
      comment += this.currentChar;
      this.advance();
    }
    
    return new Token(TokenType.COMMENT, comment.trim(), this.line, startColumn);
  }

  /**
   * Read an identifier or keyword
   */
  readIdentifier() {
    const startColumn = this.column;
    let identifier = '';
    
    // First character is letter or underscore
    while (this.currentChar !== null && 
           /[a-zA-Z0-9_]/.test(this.currentChar)) {
      identifier += this.currentChar;
      this.advance();
    }
    
    const upperIdent = identifier.toUpperCase();
    
    // Check if it's an instruction
    if (INSTRUCTIONS.has(upperIdent)) {
      return new Token(TokenType.INSTRUCTION, upperIdent, this.line, startColumn);
    }
    
    // Check if it's a register
    if (REGISTERS.has(upperIdent) || REGISTER_PAIRS.has(upperIdent)) {
      return new Token(TokenType.REGISTER, upperIdent, this.line, startColumn);
    }
    
    // Otherwise it's an identifier (could be a label reference)
    return new Token(TokenType.IDENTIFIER, identifier, this.line, startColumn);
  }

  /**
   * Read a number in various formats:
   * - Decimal: 123, 255
   * - Hexadecimal: 0xFF, FFH, 0xab
   * - Binary: 11110000B, 0b11110000
   */
  readNumber() {
    const startColumn = this.column;
    let number = '';
    let value = 0;
    
    // Check for 0x or 0b prefix
    if (this.currentChar === '0' && this.peek()) {
      const next = this.peek();
      
      if (next === 'x' || next === 'X') {
        // Hexadecimal with 0x prefix
        this.advance(); // skip '0'
        this.advance(); // skip 'x'
        number = this.readHexDigits();
        value = parseInt(number, 16);
        return new Token(TokenType.NUMBER, value, this.line, startColumn);
      } else if (next === 'b' || next === 'B') {
        // Binary with 0b prefix
        this.advance(); // skip '0'
        this.advance(); // skip 'b'
        number = this.readBinaryDigits();
        value = parseInt(number, 2);
        return new Token(TokenType.NUMBER, value, this.line, startColumn);
      }
    }
    
    // Read number - could be hex, binary, or decimal
    // Strategy: read digits first, then check for suffix or hex letters
    const startPosition = this.position;
    
    // Read decimal digits first
    while (this.currentChar !== null && /[0-9]/.test(this.currentChar)) {
      number += this.currentChar;
      this.advance();
    }
    
    // Check what comes next
    if (this.currentChar !== null) {
      const nextChar = this.currentChar.toUpperCase();
      
      // Check for H or B suffix
      if (nextChar === 'H' || nextChar === 'B') {
        // This is a suffixed number
        const suffix = nextChar;
        this.advance(); // consume the suffix
        
        if (suffix === 'H') {
          // Hexadecimal
          value = parseInt(number, 16);
          return new Token(TokenType.NUMBER, value, this.line, startColumn);
        } else if (suffix === 'B') {
          // Binary - validate
          if (!/^[01]+$/.test(number)) {
            // Invalid binary number
            return new Token(TokenType.ILLEGAL, number + 'B', this.line, startColumn);
          }
          value = parseInt(number, 2);
          return new Token(TokenType.NUMBER, value, this.line, startColumn);
        }
      } else if (/[A-Fa-f]/.test(nextChar)) {
        // Has hex letters after digits - continue reading as potential hex
        while (this.currentChar !== null && /[0-9A-Fa-f]/.test(this.currentChar)) {
          number += this.currentChar;
          this.advance();
        }
        
        // Must have H suffix for hex numbers with A-F
        if (this.currentChar !== null && this.currentChar.toUpperCase() === 'H') {
          this.advance();
          value = parseInt(number, 16);
          return new Token(TokenType.NUMBER, value, this.line, startColumn);
        } else {
          // Hex letters without H suffix - illegal
          return new Token(TokenType.ILLEGAL, number, this.line, startColumn);
        }
      }
    }
    
    // No suffix - must be decimal
    value = parseInt(number, 10);
    return new Token(TokenType.NUMBER, value, this.line, startColumn);
  }

  /**
   * Read hexadecimal digits
   */
  readHexDigits() {
    let hex = '';
    while (this.currentChar !== null && /[0-9A-Fa-f]/.test(this.currentChar)) {
      hex += this.currentChar;
      this.advance();
    }
    return hex;
  }

  /**
   * Read binary digits
   */
  readBinaryDigits() {
    let binary = '';
    while (this.currentChar !== null && /[01]/.test(this.currentChar)) {
      binary += this.currentChar;
      this.advance();
    }
    return binary;
  }

  /**
   * Get the next token
   */
  getNextToken() {
    while (this.currentChar !== null) {
      const startColumn = this.column;
      
      // Skip whitespace (but not newlines)
      if (this.currentChar !== '\n' && /\s/.test(this.currentChar)) {
        this.skipWhitespace();
        continue;
      }
      
      // Newline
      if (this.currentChar === '\n') {
        this.advance();
        return new Token(TokenType.NEWLINE, '\\n', this.line - 1, startColumn);
      }
      
      // Comment
      if (this.currentChar === ';') {
        return this.readComment();
      }
      
      // Colon (for labels)
      if (this.currentChar === ':') {
        this.advance();
        return new Token(TokenType.COLON, ':', this.line, startColumn);
      }
      
      // Comma (operand separator)
      if (this.currentChar === ',') {
        this.advance();
        return new Token(TokenType.COMMA, ',', this.line, startColumn);
      }
      
      // Identifier or keyword
      if (/[a-zA-Z_]/.test(this.currentChar)) {
        return this.readIdentifier();
      }
      
      // Number
      if (/[0-9]/.test(this.currentChar)) {
        return this.readNumber();
      }
      
      // Unknown character
      const illegalChar = this.currentChar;
      this.advance();
      return new Token(TokenType.ILLEGAL, illegalChar, this.line, startColumn);
    }
    
    return new Token(TokenType.EOF, null, this.line, this.column);
  }

  /**
   * Tokenize the entire source code
   */
  tokenize() {
    const tokens = [];
    let token;
    
    do {
      token = this.getNextToken();
      tokens.push(token);
    } while (token.type !== TokenType.EOF);
    
    return tokens;
  }
}

// Export for use in Node.js and browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { Lexer, Token, TokenType };
} else {
  window.Lexer = Lexer;
  window.Token = Token;
  window.TokenType = TokenType;
}
