#!/usr/bin/env python3
"""
Lexer module for 8086 Assembler.
Tokenizes assembly source code using regex-based pattern matching.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Dict, Any


class TokenType(Enum):
    """Token types for assembly language."""
    LABEL = auto()
    INSTRUCTION = auto()
    DIRECTIVE = auto()
    REGISTER = auto()
    IMMEDIATE = auto()
    MEMORY_REF = auto()
    STRING_LIT = auto()
    IDENTIFIER = auto()
    COMMA = auto()
    COLON = auto()
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    NEWLINE = auto()
    COMMENT = auto()
    EOF = auto()
    OPERATOR = auto()


@dataclass
class Token:
    """Represents a single token."""
    type: TokenType
    value: str
    line: int
    col: int
    
    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:{self.col})"


class Lexer:
    """
    Assembly language lexer.
    Tokenizes source code into a stream of tokens.
    """
    
    # Master regex pattern with named groups
    PATTERN = re.compile(r'''
        (?P<COMMENT>;[^\n]*)                           |  # Comments
        (?P<STRING>"[^"]*"|'[^']*')                    |  # String literals
        (?P<MEMORY>\[[^\]]+\])                         |  # Memory references [BX+SI]
        (?P<HEX>0[xX][0-9A-Fa-f]+|[0-9][0-9A-Fa-f]*[hH]) |  # Hex: 0xFF or FFh
        (?P<BINARY>[01]+[bB])                          |  # Binary: 1010b
        (?P<OCTAL>[0-7]+[oOqQ])                        |  # Octal: 77o or 77q
        (?P<DECIMAL>-?[0-9]+)                          |  # Decimal numbers
        (?P<IDENTIFIER>[A-Za-z_@?][A-Za-z0-9_@?]*)     |  # Identifiers/keywords
        (?P<COLON>:)                                   |  # Label separator
        (?P<COMMA>,)                                   |  # Operand separator
        (?P<PLUS>\+)                                   |  # Addition
        (?P<MINUS>-)                                   |  # Subtraction
        (?P<MULTIPLY>\*)                               |  # Multiplication
        (?P<LBRACKET>\[)                               |  # Memory bracket
        (?P<RBRACKET>\])                               |  # Memory bracket
        (?P<NEWLINE>\n)                                |  # Newlines
        (?P<WHITESPACE>[ \t]+)                         |  # Whitespace (skip)
        (?P<INVALID>.)                                    # Catch-all for errors
    ''', re.VERBOSE | re.IGNORECASE)
    
    def __init__(self, isa: Dict[str, Any] = None):
        """
        Initialize lexer with ISA definitions.
        
        Args:
            isa: ISA dictionary containing registers, instructions, directives.
        """
        self.isa = isa or {}
        self.registers = set(r.upper() for r in self.isa.get('registers', {}).keys())
        self.instructions = set(i.upper() for i in self.isa.get('instructions', {}).keys())
        self.directives = set(d.upper() for d in self.isa.get('directives', []))
        
        # Add common directives and operators
        self.directives.update(['OFFSET', 'PTR', 'BYTE', 'WORD', 'DWORD', 'NEAR', 'FAR', 'SHORT'])
        self.operators = {'OFFSET', 'PTR', 'BYTE', 'WORD', 'DWORD', 'NEAR', 'FAR', 'SHORT',
                          'SEG', 'TYPE', 'SIZE', 'LENGTH', 'HIGH', 'LOW', 'DUP'}
    
    def tokenize(self, source: str) -> List[Token]:
        """
        Tokenize assembly source code.
        
        Args:
            source: Assembly source code string.
            
        Returns:
            List of tokens.
        """
        tokens = []
        line_num = 1
        line_start = 0
        
        for match in self.PATTERN.finditer(source):
            kind = match.lastgroup
            value = match.group()
            col = match.start() - line_start + 1
            
            if kind == 'WHITESPACE':
                continue
            
            if kind == 'NEWLINE':
                tokens.append(Token(TokenType.NEWLINE, value, line_num, col))
                line_num += 1
                line_start = match.end()
                continue
            
            if kind == 'COMMENT':
                tokens.append(Token(TokenType.COMMENT, value, line_num, col))
                continue
            
            if kind == 'STRING':
                tokens.append(Token(TokenType.STRING_LIT, value, line_num, col))
                continue
            
            if kind == 'MEMORY':
                tokens.append(Token(TokenType.MEMORY_REF, value, line_num, col))
                continue
            
            if kind in ('HEX', 'BINARY', 'OCTAL', 'DECIMAL'):
                tokens.append(Token(TokenType.IMMEDIATE, value, line_num, col))
                continue
            
            if kind == 'IDENTIFIER':
                upper_val = value.upper()
                if upper_val in self.registers:
                    tokens.append(Token(TokenType.REGISTER, value, line_num, col))
                elif upper_val in self.instructions:
                    tokens.append(Token(TokenType.INSTRUCTION, value, line_num, col))
                elif upper_val in self.directives:
                    tokens.append(Token(TokenType.DIRECTIVE, value, line_num, col))
                elif upper_val in self.operators:
                    tokens.append(Token(TokenType.OPERATOR, value, line_num, col))
                else:
                    tokens.append(Token(TokenType.IDENTIFIER, value, line_num, col))
                continue
            
            if kind == 'COLON':
                # Convert previous IDENTIFIER to LABEL
                if tokens and tokens[-1].type == TokenType.IDENTIFIER:
                    prev = tokens.pop()
                    tokens.append(Token(TokenType.LABEL, prev.value, prev.line, prev.col))
                tokens.append(Token(TokenType.COLON, value, line_num, col))
                continue
            
            if kind == 'COMMA':
                tokens.append(Token(TokenType.COMMA, value, line_num, col))
                continue
            
            if kind == 'PLUS':
                tokens.append(Token(TokenType.PLUS, value, line_num, col))
                continue
            
            if kind == 'MINUS':
                tokens.append(Token(TokenType.MINUS, value, line_num, col))
                continue
            
            if kind == 'MULTIPLY':
                tokens.append(Token(TokenType.MULTIPLY, value, line_num, col))
                continue
            
            if kind in ('LBRACKET', 'RBRACKET'):
                tt = TokenType.LBRACKET if kind == 'LBRACKET' else TokenType.RBRACKET
                tokens.append(Token(tt, value, line_num, col))
                continue
            
            if kind == 'INVALID':
                # Skip invalid characters silently or raise error
                continue
        
        tokens.append(Token(TokenType.EOF, '', line_num, 0))
        return tokens
    
    def tokenize_line(self, line: str, line_num: int = 1) -> List[Token]:
        """Tokenize a single line."""
        return [t for t in self.tokenize(line) if t.type != TokenType.EOF]
