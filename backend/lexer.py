#!/usr/bin/env python3
"""
Lexer module for 8085/8086 Assembler.

Tokenizes assembly source code into a stream of Token objects using a single
compiled regex pattern with named groups. Supports multiple dialects and
numeric formats.
"""

from __future__ import annotations
import re
import json
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import List, Set, Optional, Dict, Any


class TokenType(Enum):
    """Token type enumeration."""
    LABEL = auto()           # identifier followed by ':'
    MNEMONIC = auto()        # instruction mnemonic from ISA
    REGISTER = auto()        # register name from ISA
    IMMEDIATE = auto()       # numeric literal (decimal, hex, binary, octal, char)
    MEMORY_REF = auto()      # bracket expressions: [BX+SI], [BX+4], (HL)
    DIRECTIVE = auto()       # .org, .db, DB, SEGMENT, etc.
    STRING_LIT = auto()      # "hello" or 'hello'
    IDENTIFIER = auto()      # symbol/label reference (not yet resolved)
    OPERATOR = auto()        # + - * / PTR OFFSET SEG NEAR FAR SHORT
    COMMA = auto()           # ,
    COLON = auto()           # :
    NEWLINE = auto()         # end of line
    COMMENT = auto()         # ; ... or // ...
    UNKNOWN = auto()         # unrecognized token
    EOF = auto()             # end of file


@dataclass
class Token:
    """
    Represents a single token from the source code.
    
    Attributes:
        type: The token type classification
        value: The matched text, case-preserved
        norm: value.upper().strip() for comparisons
        line: 1-indexed line number
        col: 1-indexed column of first character
        col_end: column of last character (for exact underline)
        raw_line: full original source line (for error context)
    """
    type: TokenType
    value: str
    norm: str
    line: int
    col: int
    col_end: int
    raw_line: str
    
    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:{self.col})"


class Lexer:
    """
    Assembly language lexer.
    
    Tokenizes source code using a single compiled regex pattern with named groups.
    Supports Intel 8085, 8086, and multiple assembler dialects (NASM, TASM, MASM, GAS).
    """
    
    # Load ISA data for mnemonic/register recognition
    _isa_8085: Optional[Dict[str, Any]] = None
    _isa_8086: Optional[Dict[str, Any]] = None
    _isa_loaded: bool = False
    
    # Architecture-specific sets
    _mnemonics_8085: Set[str] = set()
    _mnemonics_8086: Set[str] = set()
    _registers_8085: Set[str] = set()
    _registers_8086: Set[str] = set()
    
    # Common directives
    _directives: Set[str] = set()
    
    # Operators recognized as separate tokens
    OPERATORS = {
        'PTR', 'OFFSET', 'SEG', 'NEAR', 'FAR', 'SHORT', 'BYTE', 'WORD', 
        'DWORD', 'QWORD', 'TBYTE', 'DUP', 'EQ', 'NE', 'LT', 'LE', 'GT', 'GE',
        'AND', 'OR', 'XOR', 'NOT', 'SHL', 'SHR', 'MOD', 'HIGH', 'LOW', 'LENGTH',
        'SIZE', 'TYPE', 'THIS', 'MASK', 'WIDTH', '$', '+'
    }
    
    # Master regex pattern with named groups
    # Order matters: more specific patterns must come before general ones
    PATTERN = re.compile(r'''
        # Comments (must come early to avoid partial matches)
        (?P<COMMENT>;[^\n]*|//[^\n]*)
        
        # String literals (single or double quoted)
        |(?P<STRING_LIT>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')
        
        # Memory references with brackets (Intel syntax)
        |(?P<MEMORY_REF_BRACKET>\[
            (?:[^\[\]]+|\[(?:[^\[\]]+|\[[^\[\]]*\])*\])*
        \])
        
        # Memory references with parentheses (8085 style or GAS)
        |(?P<MEMORY_REF_PAREN>\(
            (?:[A-Za-z_][A-Za-z0-9_]*(?:\s*[+\-]\s*[A-Za-z0-9_]+)*)
        \))
        
        # Hex numbers: 0xFF, 0FFh, $FF, 0FFH
        |(?P<HEX_0X>0[xX][0-9A-Fa-f]+)
        |(?P<HEX_H>[0-9][0-9A-Fa-f]*[hH])
        |(?P<HEX_DOLLAR>\$[0-9A-Fa-f]+)
        
        # Binary numbers: 0b1010, 1010b (0b prefix MUST come before decimal)
        |(?P<BIN_0B>0[bB][01]+)
        |(?P<BIN_B>[01]+[bB])
        
        # Octal numbers: 77o, 77q
        |(?P<OCTAL>[0-7]+[oOqQ])
        
        # Character literals: 'A', "A"
        |(?P<CHAR_LIT>'(?:[^'\\]|\\.)'|"(?:[^"\\]|\\.)")
        
        # Decimal numbers (including negative)
        |(?P<DECIMAL>-?[0-9]+)
        
        # Identifiers (labels, registers, mnemonics, directives)
        # Allow leading dot for directives (.org, .db)
        # Allow leading % for GAS registers (%eax)
        # Allow leading @ for MASM special symbols (@data)
        |(?P<IDENTIFIER>[.%@]?[A-Za-z_][A-Za-z0-9_]*)
        
        # Punctuation and operators
        |(?P<COLON>:)
        |(?P<COMMA>,)
        |(?P<PLUS>\+)
        |(?P<MINUS>-)
        |(?P<STAR>\*)
        |(?P<SLASH>/)
        |(?P<LPAREN>\()
        |(?P<RPAREN>\))
        |(?P<LBRACKET>\[)
        |(?P<RBRACKET>\])
        |(?P<DOLLAR>\$)
        
        # Newlines
        |(?P<NEWLINE>\n)
        
        # Whitespace (skip)
        |(?P<WHITESPACE>[ \t\r]+)
        
        # Unknown character
        |(?P<UNKNOWN>.)
    ''', re.VERBOSE | re.MULTILINE)
    
    def __init__(self, architecture: str = "8086"):
        """
        Initialize lexer.
        
        Args:
            architecture: Target architecture ("8085" or "8086")
        """
        self.architecture = architecture.upper()
        self._load_isa()
        self.errors: List[Dict[str, Any]] = []
        
        # Select architecture-specific sets
        if self.architecture == "8085":
            self._mnemonics = self._mnemonics_8085
            self._registers = self._registers_8085
        else:
            self._mnemonics = self._mnemonics_8086
            self._registers = self._registers_8086
    
    @classmethod
    def _load_isa(cls) -> None:
        """Load ISA definitions from JSON files."""
        if cls._isa_loaded:
            return  # Already loaded
        
        backend_dir = Path(__file__).parent
        
        # Load 8085 ISA
        isa_8085_path = backend_dir / 'isa_8085.json'
        if isa_8085_path.exists():
            with open(isa_8085_path) as f:
                cls._isa_8085 = json.load(f)
                for instr in cls._isa_8085.get('instructions', []):
                    cls._mnemonics_8085.add(instr['mnemonic'].upper())
                for reg_list in cls._isa_8085.get('registers', {}).values():
                    if isinstance(reg_list, list):
                        cls._registers_8085.update(r.upper() for r in reg_list)
                cls._directives.update(d.upper() for d in cls._isa_8085.get('directives', []))
        
        # Load 8086 ISA
        isa_8086_path = backend_dir / 'isa_8086.json'
        if isa_8086_path.exists():
            with open(isa_8086_path) as f:
                cls._isa_8086 = json.load(f)
                for instr in cls._isa_8086.get('instructions', []):
                    cls._mnemonics_8086.add(instr['mnemonic'].upper())
                for reg_list in cls._isa_8086.get('registers', {}).values():
                    if isinstance(reg_list, list):
                        cls._registers_8086.update(r.upper() for r in reg_list)
                cls._directives.update(d.upper() for d in cls._isa_8086.get('directives', []))
        
        # Add common directives not in ISA files
        # Note: DS is removed as directive - it's the segment register in 8086
        cls._directives.update([
            'ORG', 'EQU', 'DB', 'DW', 'DD', 'DQ', 'DT', 'RESB', 'RESW', 'RESD',
            'TIMES', 'SEGMENT', 'ENDS', 'PROC', 'ENDP', 'END', 'ASSUME',
            'MODEL', 'STACK', 'DATA', 'CODE', 'PUBLIC', 'EXTERN', 'EXTRN',
            'MACRO', 'ENDM', 'IF', 'IFDEF', 'IFNDEF', 'ELSE', 'ENDIF', 'ELSEIF',
            'ALIGN', 'EVEN', 'INCLUDE', 'GLOBAL', 'SECTION', 'BITS',
            'SMALL', 'TINY', 'MEDIUM', 'COMPACT', 'LARGE', 'HUGE', 'FLAT',
            'IDEAL', 'MASM', 'QUIRKS', 'NOSMART', 'SMART',
            'STRUC', 'STRUCT', 'UNION', 'RECORD', 'TYPEDEF',
            'LOCAL', 'INVOKE', 'PROTO', 'USES', 'ARG', 'LOCALS',
            'ASCII', 'ASCIZ', 'ASCIIZ', 'BYTE', 'WORD', 'DWORD',
            'SET', 'GLOBL', 'TEXT', 'BSS', 'RODATA',
            '%DEFINE', '%MACRO', '%ENDMACRO', '%INCLUDE', '%IF', '%ENDIF',
            '%IFDEF', '%IFNDEF', '%ELSE', '%ELIF', '%REP', '%ENDREP'
        ])
        
        # Add 8085 special registers
        cls._registers_8085.add('M')
        cls._registers_8085.add('PSW')
        
        cls._isa_loaded = True
    
    def tokenize(self, source: str) -> List[Token]:
        """
        Tokenize assembly source code.
        
        Args:
            source: Assembly source code string
            
        Returns:
            List of Token objects
        """
        self.errors = []
        tokens: List[Token] = []
        
        # Split source into lines for raw_line tracking
        lines = source.split('\n')
        
        # Track position
        line_num = 1
        line_start = 0
        
        for match in self.PATTERN.finditer(source):
            kind = match.lastgroup
            value = match.group()
            start = match.start()
            end = match.end()
            
            # Calculate line and column
            # Count newlines before this position
            while line_start + len(lines[line_num - 1]) < start and line_num <= len(lines):
                line_start += len(lines[line_num - 1]) + 1  # +1 for newline
                line_num += 1
            
            col = start - line_start + 1
            col_end = col + len(value) - 1
            raw_line = lines[line_num - 1] if line_num <= len(lines) else ""
            
            # Skip whitespace
            if kind == 'WHITESPACE':
                continue
            
            # Create token based on type
            token = self._create_token(kind, value, line_num, col, col_end, raw_line)
            if token:
                tokens.append(token)
                
                # Track newlines for line counting
                if kind == 'NEWLINE':
                    line_num += 1
                    line_start = end
        
        # Add EOF token
        raw_line = lines[-1] if lines else ""
        tokens.append(Token(
            type=TokenType.EOF,
            value='',
            norm='',
            line=line_num,
            col=len(raw_line) + 1 if raw_line else 1,
            col_end=len(raw_line) + 1 if raw_line else 1,
            raw_line=raw_line
        ))
        
        return tokens
    
    def _create_token(
        self, 
        kind: str, 
        value: str, 
        line: int, 
        col: int, 
        col_end: int, 
        raw_line: str
    ) -> Optional[Token]:
        """
        Create a Token object from regex match.
        
        Args:
            kind: Regex group name
            value: Matched text
            line: Line number
            col: Start column
            col_end: End column
            raw_line: Full source line
            
        Returns:
            Token object or None for skipped tokens
        """
        norm = value.upper().strip()
        
        # Comments
        if kind == 'COMMENT':
            return Token(TokenType.COMMENT, value, norm, line, col, col_end, raw_line)
        
        # String literals
        if kind == 'STRING_LIT':
            return Token(TokenType.STRING_LIT, value, norm, line, col, col_end, raw_line)
        
        # Memory references
        if kind in ('MEMORY_REF_BRACKET', 'MEMORY_REF_PAREN'):
            return Token(TokenType.MEMORY_REF, value, norm, line, col, col_end, raw_line)
        
        # Numeric literals
        if kind in ('HEX_0X', 'HEX_H', 'HEX_DOLLAR', 'BIN_B', 'BIN_0B', 'OCTAL', 'DECIMAL', 'CHAR_LIT'):
            return Token(TokenType.IMMEDIATE, value, norm, line, col, col_end, raw_line)
        
        # Identifiers - classify as register, directive, mnemonic, or identifier
        if kind == 'IDENTIFIER':
            upper = value.upper().lstrip('.%@')
            
            # Special case: @-prefixed tokens are pseudo-variables or user labels
            # They should be IDENTIFIER, not DIRECTIVE/MNEMONIC/REGISTER
            if value.startswith('@'):
                return Token(TokenType.IDENTIFIER, value, norm, line, col, col_end, raw_line)
            
            # Check if it's a register FIRST (registers take highest priority)
            # This handles ambiguous cases like DS (segment register, but also GAS directive)
            if upper in self._registers:
                return Token(TokenType.REGISTER, value, norm, line, col, col_end, raw_line)
            
            # Check if it's a directive (with or without leading dot)
            if upper in self._directives or value.upper() in self._directives:
                return Token(TokenType.DIRECTIVE, value, norm, line, col, col_end, raw_line)
            
            # Check if it's a mnemonic
            if upper in self._mnemonics:
                return Token(TokenType.MNEMONIC, value, norm, line, col, col_end, raw_line)
            
            # Check if it's an operator keyword
            if upper in self.OPERATORS:
                return Token(TokenType.OPERATOR, value, norm, line, col, col_end, raw_line)
            
            # Otherwise it's an identifier (label reference)
            return Token(TokenType.IDENTIFIER, value, norm, line, col, col_end, raw_line)
        
        # Punctuation
        if kind == 'COLON':
            return Token(TokenType.COLON, value, norm, line, col, col_end, raw_line)
        if kind == 'COMMA':
            return Token(TokenType.COMMA, value, norm, line, col, col_end, raw_line)
        if kind in ('PLUS', 'MINUS', 'STAR', 'SLASH', 'LPAREN', 'RPAREN', 
                    'LBRACKET', 'RBRACKET', 'DOLLAR'):
            return Token(TokenType.OPERATOR, value, norm, line, col, col_end, raw_line)
        
        # Newlines
        if kind == 'NEWLINE':
            return Token(TokenType.NEWLINE, value, norm, line, col, col_end, raw_line)
        
        # Unknown tokens - record error
        if kind == 'UNKNOWN':
            self.errors.append({
                'phase': 'LEXER',
                'code': 'E001',
                'line': line,
                'col': col,
                'col_end': col_end,
                'raw_line': raw_line,
                'message': f"Unrecognized character: {value!r}"
            })
            return Token(TokenType.UNKNOWN, value, norm, line, col, col_end, raw_line)
        
        return None
    
    def tokenize_line(self, line: str, line_num: int = 1) -> List[Token]:
        """
        Tokenize a single line of assembly.
        
        Args:
            line: Single line of assembly code
            line_num: Line number for token metadata
            
        Returns:
            List of Token objects
        """
        # Add newline if not present to properly terminate
        if not line.endswith('\n'):
            line = line + '\n'
        
        tokens = self.tokenize(line)
        
        # Adjust line numbers
        for token in tokens:
            token.line = line_num
        
        return tokens
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Get list of lexer errors."""
        return self.errors.copy()
    
    def has_errors(self) -> bool:
        """Check if any errors occurred during tokenization."""
        return len(self.errors) > 0


def parse_immediate(value: str) -> int:
    """
    Parse an immediate value string to integer.
    
    Supports:
    - Decimal: 42, -10
    - Hex: 0xFF, 0FFh, $FF
    - Binary: 1010b, 0b1010
    - Octal: 77o, 77q
    - Character: 'A'
    
    Args:
        value: Immediate value string
        
    Returns:
        Integer value
        
    Raises:
        ValueError: If value cannot be parsed
    """
    value = value.strip()
    
    if not value:
        raise ValueError("Empty value")
    
    # Character literal
    if len(value) >= 3 and value[0] in '"\'':
        char = value[1:-1]
        if char.startswith('\\'):
            escapes = {'n': '\n', 't': '\t', 'r': '\r', '0': '\0', '\\': '\\', "'": "'", '"': '"'}
            return ord(escapes.get(char[1], char[1]))
        return ord(char[0]) if char else 0
    
    upper = value.upper()
    
    # Hex: 0xFF
    if upper.startswith('0X'):
        return int(value[2:], 16)
    
    # Hex: $FF (NASM/6502 style)
    if value.startswith('$'):
        return int(value[1:], 16)
    
    # Hex: 0FFh
    if upper.endswith('H'):
        return int(value[:-1], 16)
    
    # Binary: 0b1010
    if upper.startswith('0B'):
        return int(value[2:], 2)
    
    # Binary: 1010b
    if upper.endswith('B') and all(c in '01' for c in value[:-1]):
        return int(value[:-1], 2)
    
    # Octal: 77o or 77q
    if upper.endswith('O') or upper.endswith('Q'):
        return int(value[:-1], 8)
    
    # Decimal
    return int(value)


# Module-level convenience function
def tokenize(source: str, architecture: str = "8086") -> List[Token]:
    """
    Tokenize assembly source code.
    
    Args:
        source: Assembly source code
        architecture: Target architecture ("8085" or "8086")
        
    Returns:
        List of Token objects
    """
    lexer = Lexer(architecture)
    return lexer.tokenize(source)


if __name__ == '__main__':
    # Test the lexer
    test_code = '''
; Hello World for 8086
.MODEL SMALL
.STACK 100H
.DATA
    MSG DB 'Hello, World!$'
    COUNT EQU 10
.CODE
START:
    MOV AX, @DATA       ; Load data segment
    MOV DS, AX
    LEA DX, MSG         ; Load address of message
    MOV AH, 09H         ; DOS print string function
    INT 21H             ; Call DOS
    MOV AX, 4C00H       ; Exit program
    INT 21H
END START
'''
    
    lexer = Lexer("8086")
    tokens = lexer.tokenize(test_code)
    
    print("=== Tokens ===")
    for token in tokens:
        if token.type not in (TokenType.NEWLINE, TokenType.COMMENT, TokenType.EOF):
            print(f"  {token}")
    
    if lexer.has_errors():
        print("\n=== Errors ===")
        for err in lexer.get_errors():
            print(f"  Line {err['line']}: {err['message']}")
