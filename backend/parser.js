/**
 * Parser for 8085/8086 Assembly Language
 * Converts tokens from the lexer into structured instructions
 */

const { Lexer, TokenType } = require('./lexer.js');

class Instruction {
  constructor(opcode, operands, label = null, comment = null, line = 1) {
    this.opcode = opcode;          // Instruction mnemonic (e.g., 'MVI', 'ADD')
    this.operands = operands;      // Array of operands
    this.label = label;            // Optional label
    this.comment = comment;        // Optional comment
    this.line = line;              // Source line number
  }
  
  toString() {
    let str = '';
    if (this.label) str += `${this.label}: `;
    str += this.opcode;
    if (this.operands.length > 0) {
      str += ' ' + this.operands.map(op => op.toString()).join(', ');
    }
    if (this.comment) str += `  ; ${this.comment}`;
    return str;
  }
}

class Operand {
  constructor(type, value) {
    this.type = type;    // 'register', 'immediate', 'identifier', 'address'
    this.value = value;  // The actual value
  }
  
  toString() {
    return `${this.value}`;
  }
}

class ParseError extends Error {
  constructor(message, line, column) {
    super(`Parse Error at ${line}:${column}: ${message}`);
    this.line = line;
    this.column = column;
  }
}

class Parser {
  constructor(source) {
    this.lexer = new Lexer(source);
    this.tokens = this.lexer.tokenize();
    this.position = 0;
    this.currentToken = this.tokens[0];
    this.labels = new Map();
    this.instructions = [];
  }

  /**
   * Advance to the next token
   */
  advance() {
    this.position++;
    if (this.position < this.tokens.length) {
      this.currentToken = this.tokens[this.position];
    }
  }

  /**
   * Peek at the next token without advancing
   */
  peek(offset = 1) {
    const peekPos = this.position + offset;
    return peekPos < this.tokens.length ? this.tokens[peekPos] : null;
  }

  /**
   * Skip newlines and comments
   */
  skipNewlinesAndComments() {
    while (this.currentToken.type === TokenType.NEWLINE ||
           this.currentToken.type === TokenType.COMMENT) {
      this.advance();
    }
  }

  /**
   * Expect a specific token type
   */
  expect(tokenType) {
    if (this.currentToken.type !== tokenType) {
      throw new ParseError(
        `Expected ${tokenType}, got ${this.currentToken.type}`,
        this.currentToken.line,
        this.currentToken.column
      );
    }
    const token = this.currentToken;
    this.advance();
    return token;
  }

  /**
   * Parse an operand
   */
  parseOperand() {
    const token = this.currentToken;
    
    switch (token.type) {
      case TokenType.REGISTER:
        this.advance();
        return new Operand('register', token.value);
      
      case TokenType.NUMBER:
        this.advance();
        return new Operand('immediate', token.value);
      
      case TokenType.IDENTIFIER:
        this.advance();
        return new Operand('identifier', token.value);
      
      default:
        throw new ParseError(
          `Unexpected token in operand: ${token.type}`,
          token.line,
          token.column
        );
    }
  }

  /**
   * Parse operands (comma-separated)
   */
  parseOperands() {
    const operands = [];
    
    // Check if there are any operands
    if (this.currentToken.type === TokenType.NEWLINE ||
        this.currentToken.type === TokenType.COMMENT ||
        this.currentToken.type === TokenType.EOF) {
      return operands;
    }
    
    // Parse first operand
    operands.push(this.parseOperand());
    
    // Parse additional operands
    while (this.currentToken.type === TokenType.COMMA) {
      this.advance(); // skip comma
      
      // Skip optional whitespace (handled by lexer)
      operands.push(this.parseOperand());
    }
    
    return operands;
  }

  /**
   * Parse a single line (label, instruction, comment)
   */
  parseLine() {
    let label = null;
    let comment = null;
    let instruction = null;
    
    const startLine = this.currentToken.line;
    
    // Check for label
    if (this.currentToken.type === TokenType.IDENTIFIER &&
        this.peek() && this.peek().type === TokenType.COLON) {
      label = this.currentToken.value;
      this.advance(); // skip identifier
      this.advance(); // skip colon
    }
    
    // Check for instruction
    if (this.currentToken.type === TokenType.INSTRUCTION) {
      const opcode = this.currentToken.value;
      this.advance();
      
      const operands = this.parseOperands();
      
      instruction = new Instruction(opcode, operands, label, null, startLine);
    }
    
    // Check for comment
    if (this.currentToken.type === TokenType.COMMENT) {
      comment = this.currentToken.value;
      if (instruction) {
        instruction.comment = comment;
      }
      this.advance();
    }
    
    // Store label if present
    if (label && instruction) {
      this.labels.set(label, this.instructions.length);
    }
    
    return instruction;
  }

  /**
   * Parse the entire program
   */
  parse() {
    this.skipNewlinesAndComments();
    
    while (this.currentToken.type !== TokenType.EOF) {
      try {
        const instruction = this.parseLine();
        
        if (instruction) {
          this.instructions.push(instruction);
        }
        
        this.skipNewlinesAndComments();
      } catch (error) {
        // Collect error and try to continue parsing
        console.error(error.message);
        
        // Skip to next line
        while (this.currentToken.type !== TokenType.NEWLINE &&
               this.currentToken.type !== TokenType.EOF) {
          this.advance();
        }
        this.skipNewlinesAndComments();
      }
    }
    
    return {
      instructions: this.instructions,
      labels: this.labels,
    };
  }

  /**
   * Pretty print the parsed program
   */
  prettyPrint() {
    console.log('\\n========== Parsed Program ==========\\n');
    
    if (this.labels.size > 0) {
      console.log('Labels:');
      this.labels.forEach((position, name) => {
        console.log(`  ${name} -> instruction ${position}`);
      });
      console.log('');
    }
    
    console.log('Instructions:');
    this.instructions.forEach((instruction, index) => {
      console.log(`  ${index.toString().padStart(3)}: ${instruction.toString()}`);
    });
    
    console.log('\\n====================================\\n');
  }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { Parser, Instruction, Operand, ParseError };
} else {
  window.Parser = Parser;
  window.Instruction = Instruction;
  window.Operand = Operand;
  window.ParseError = ParseError;
}
