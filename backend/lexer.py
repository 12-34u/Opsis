#!/usr/bin/env python3
"""
Lexer module for the Dynamic Two-Pass Assembler.
Tokenizes assembly source using regex with named groups.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional


class TokenType(Enum):
    """Token type enumeration."""
    LABEL = auto()
    INSTRUCTION = auto()
    REGISTER = auto()
    IMMEDIATE = auto()
    MEMORY_REF = auto()
    DIRECTIVE = auto()
    STRING_LIT = auto()
    COMMENT = auto()
    IDENTIFIER = auto()
    COMMA = auto()
    COLON = auto()
    NEWLINE = auto()
    EOF = auto()


@dataclass
class Token:
    """Represents a lexical token."""
    type: TokenType
    value: str
    line: int
    col: int
    
    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:C{self.col})"


class Lexer:
    """
    Assembly language lexer using compiled regex patterns.
    
    Tokenizes source into: LABEL, INSTRUCTION, REGISTER, IMMEDIATE,
    MEMORY_REF, DIRECTIVE, STRING_LIT, COMMENT, IDENTIFIER.
    """
    
    # Combined regex pattern with named groups
    PATTERN = re.compile(r'''
        (?P<COMMENT>;[^\n]*)                              |  # Comments
        (?P<STRING_LIT>"[^"]*"|'[^']*')                   |  # String literals
        (?P<MEMORY_REF>\[[^\]]+\])                        |  # Memory references
        (?P<HEX>0[xX][0-9A-Fa-f]+|[0-9][0-9A-Fa-f]*[hH])  |  # Hex numbers
        (?P<BINARY>0[bB][01]+|[01]+[bB])                  |  # Binary numbers
        (?P<DECIMAL>-?\d+)                                |  # Decimal numbers
        (?P<DIRECTIVE>\.[A-Za-z_][A-Za-z0-9_]*)           |  # Directives with dot
        (?P<WORD>[A-Za-z_@?][A-Za-z0-9_@$?]*)             |  # Words (instructions, registers, labels)
        (?P<COMMA>,)                                      |  # Comma
        (?P<COLON>:)                                      |  # Colon
        (?P<NEWLINE>\n)                                   |  # Newline
        (?P<WHITESPACE>[ \t]+)                            |  # Whitespace (skip)
        (?P<ERROR>.)                                         # Any other character
    ''', re.VERBOSE | re.MULTILINE)
    
    # Known registers (loaded from ISA or hardcoded set)
    REGISTERS = {
        'AX', 'BX', 'CX', 'DX', 'SI', 'DI', 'BP', 'SP',
        'AL', 'BL', 'CL', 'DL', 'AH', 'BH', 'CH', 'DH',
        'CS', 'DS', 'ES', 'SS', 'IP',
        # 8085 compatibility
        'A', 'B', 'C', 'D', 'E', 'H', 'L', 'M'
    }
    
    # Known directives (no-emit and data)
    DIRECTIVES = {
        'MODEL', 'STACK', 'DATA', 'CODE', 'ORG', 'EQU', 'DB', 'DW', 'DD',
        'ASCII', 'ASCIIZ', 'BYTE', 'WORD', 'END', 'ASSUME', 'SEGMENT', 
        'ENDS', 'PROC', 'ENDP', 'PUBLIC', 'EXTERN', 'EXTRN', 'MACRO', 
        'ENDM', 'LOCAL', 'INCLUDE', 'IF', 'IFDEF', 'IFNDEF', 'ELSE', 
        'ENDIF', 'ALIGN', 'EVEN', 'RESB', 'RESW', 'RESD', 'TIMES'
    }
    
    def __init__(self, isa_data: Optional[dict] = None):
        """
        Initialize lexer, optionally with ISA data for instruction recognition.
        
        Args:
            isa_data: Optional ISA dictionary with instruction definitions.
        """
        self.instructions = set()
        if isa_data:
            self.instructions = set(isa_data.get('instructions', {}).keys())
            # Add registers from ISA
            for reg in isa_data.get('registers', {}):
                self.REGISTERS.add(reg.upper())
            # Add directives from ISA
            for directive in isa_data.get('directives', []):
                self.DIRECTIVES.add(directive.upper().lstrip('.'))
    
    def tokenize(self, source: str) -> List[Token]:
        """
        Tokenize assembly source code.
        
        Args:
            source: Assembly source code string.
            
        Returns:
            List of Token objects.
        """
        tokens: List[Token] = []
        line = 1
        line_start = 0
        
        for match in self.PATTERN.finditer(source):
            kind = match.lastgroup
            value = match.group()
            col = match.start() - line_start + 1
            
            if kind == 'WHITESPACE':
                continue
            elif kind == 'NEWLINE':
                tokens.append(Token(TokenType.NEWLINE, value, line, col))
                line += 1
                line_start = match.end()
            elif kind == 'ERROR':
                # Skip unknown characters silently for now
                continue
            elif kind == 'COMMENT':
                tokens.append(Token(TokenType.COMMENT, value, line, col))
            elif kind == 'STRING_LIT':
                tokens.append(Token(TokenType.STRING_LIT, value, line, col))
            elif kind == 'MEMORY_REF':
                tokens.append(Token(TokenType.MEMORY_REF, value, line, col))
            elif kind in ('HEX', 'BINARY', 'DECIMAL'):
                tokens.append(Token(TokenType.IMMEDIATE, value, line, col))
            elif kind == 'DIRECTIVE':
                tokens.append(Token(TokenType.DIRECTIVE, value.upper(), line, col))
            elif kind == 'COMMA':
                tokens.append(Token(TokenType.COMMA, value, line, col))
            elif kind == 'COLON':
                # Mark previous token as LABEL if it was an identifier
                if tokens and tokens[-1].type == TokenType.IDENTIFIER:
                    tokens[-1] = Token(TokenType.LABEL, tokens[-1].value, tokens[-1].line, tokens[-1].col)
                tokens.append(Token(TokenType.COLON, value, line, col))
            elif kind == 'WORD':
                upper_val = value.upper()
                if upper_val in self.REGISTERS:
                    tokens.append(Token(TokenType.REGISTER, upper_val, line, col))
                elif upper_val in self.DIRECTIVES:
                    tokens.append(Token(TokenType.DIRECTIVE, upper_val, line, col))
                elif upper_val in self.instructions:
                    tokens.append(Token(TokenType.INSTRUCTION, upper_val, line, col))
                else:
                    # Could be instruction, label reference, or identifier
                    tokens.append(Token(TokenType.IDENTIFIER, value, line, col))
        
        tokens.append(Token(TokenType.EOF, '', line, 1))
        return tokens
    
    def classify_identifier(self, value: str) -> TokenType:
        """
        Classify an identifier as instruction, register, directive, or identifier.
        
        Args:
            value: The identifier string.
            
        Returns:
            Appropriate TokenType.
        """
        upper = value.upper()
        if upper in self.REGISTERS:
            return TokenType.REGISTER
        elif upper in self.DIRECTIVES:
            return TokenType.DIRECTIVE
        elif upper in self.instructions:
            return TokenType.INSTRUCTION
        return TokenType.IDENTIFIER
