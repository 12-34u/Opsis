#!/usr/bin/env python3
"""
Directives module for the Dynamic Two-Pass Assembler.
Handles assembly directives like .org, .equ, .db, .dw, etc.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from symbol_table import SymbolTable
    from emitter import Emitter


@dataclass
class DirectiveResult:
    """Result of processing a directive."""
    affects_lc: bool = False        # Does this directive change location counter?
    new_lc: Optional[int] = None    # New LC value if affects_lc is True
    byte_width: int = 0             # Number of bytes this directive emits
    data: Optional[bytes] = None    # Data to emit (for .db, .dw, etc.)
    defines_symbol: bool = False    # Does this define a symbol?
    symbol_name: Optional[str] = None
    symbol_value: Optional[int] = None
    is_constant: bool = False


class DirectiveHandler:
    """
    Handles assembly directives.
    
    Processes directives during Pass 1 (size calculation) and
    Pass 2 (data emission).
    """
    
    # No-emit directives (don't generate code)
    NO_EMIT_DIRECTIVES = {
        'MODEL', 'STACK', 'DATA', 'CODE', 'ASSUME', 'SEGMENT', 'ENDS',
        'PROC', 'ENDP', 'PUBLIC', 'EXTERN', 'EXTRN', 'MACRO', 'ENDM',
        'LOCAL', 'INCLUDE', 'IF', 'IFDEF', 'IFNDEF', 'ELSE', 'ENDIF',
        'END'
    }
    
    def __init__(self, symbol_table: Optional['SymbolTable'] = None):
        """
        Initialize directive handler.
        
        Args:
            symbol_table: Symbol table for EQU and label definitions.
        """
        self.symbol_table = symbol_table
    
    def is_directive(self, name: str) -> bool:
        """
        Check if a name is a known directive.
        
        Args:
            name: Name to check.
            
        Returns:
            True if this is a directive.
        """
        upper = name.upper().lstrip('.')
        return upper in self.NO_EMIT_DIRECTIVES or upper in {
            'ORG', 'EQU', 'DB', 'DW', 'DD', 'ASCII', 'ASCIIZ',
            'BYTE', 'WORD', 'ALIGN', 'EVEN', 'RESB', 'RESW', 'RESD', 'TIMES'
        }
    
    def is_no_emit(self, name: str) -> bool:
        """
        Check if directive doesn't emit code.
        
        Args:
            name: Directive name.
            
        Returns:
            True if directive doesn't emit code.
        """
        return name.upper().lstrip('.') in self.NO_EMIT_DIRECTIVES
    
    def process(self, name: str, operands: List[str], current_lc: int = 0) -> DirectiveResult:
        """
        Process a directive and return result.
        
        Args:
            name: Directive name.
            operands: List of operand strings.
            current_lc: Current location counter.
            
        Returns:
            DirectiveResult with processing outcome.
        """
        upper_name = name.upper().lstrip('.')
        
        # No-emit directives
        if upper_name in self.NO_EMIT_DIRECTIVES:
            return DirectiveResult()
        
        # ORG - set origin
        if upper_name == 'ORG':
            if operands:
                new_lc = self._parse_value(operands[0])
                return DirectiveResult(affects_lc=True, new_lc=new_lc)
            return DirectiveResult()
        
        # EQU - define constant
        if upper_name == 'EQU':
            if len(operands) >= 2:
                name = operands[0]
                value = self._parse_value(operands[1])
                return DirectiveResult(
                    defines_symbol=True,
                    symbol_name=name,
                    symbol_value=value,
                    is_constant=True
                )
            return DirectiveResult()
        
        # DB - define bytes
        if upper_name in ('DB', 'BYTE'):
            data = bytearray()
            for op in operands:
                op = op.strip()
                if op.startswith('"') or op.startswith("'"):
                    # String
                    string = op[1:-1]
                    data.extend(string.encode('ascii', errors='replace'))
                else:
                    # Number
                    value = self._parse_value(op)
                    data.append(value & 0xFF)
            return DirectiveResult(byte_width=len(data), data=bytes(data))
        
        # DW - define words
        if upper_name in ('DW', 'WORD'):
            data = bytearray()
            for op in operands:
                value = self._parse_value(op.strip())
                # Little endian
                data.append(value & 0xFF)
                data.append((value >> 8) & 0xFF)
            return DirectiveResult(byte_width=len(data), data=bytes(data))
        
        # DD - define double words
        if upper_name == 'DD':
            data = bytearray()
            for op in operands:
                value = self._parse_value(op.strip())
                data.append(value & 0xFF)
                data.append((value >> 8) & 0xFF)
                data.append((value >> 16) & 0xFF)
                data.append((value >> 24) & 0xFF)
            return DirectiveResult(byte_width=len(data), data=bytes(data))
        
        # ASCII - define string (no null terminator)
        if upper_name == 'ASCII':
            if operands and (operands[0].startswith('"') or operands[0].startswith("'")):
                string = operands[0][1:-1]
                data = string.encode('ascii', errors='replace')
                return DirectiveResult(byte_width=len(data), data=data)
            return DirectiveResult()
        
        # ASCIIZ - define string with null terminator
        if upper_name == 'ASCIIZ':
            if operands and (operands[0].startswith('"') or operands[0].startswith("'")):
                string = operands[0][1:-1]
                data = string.encode('ascii', errors='replace') + b'\x00'
                return DirectiveResult(byte_width=len(data), data=data)
            return DirectiveResult()
        
        # RESB - reserve bytes
        if upper_name == 'RESB':
            if operands:
                count = self._parse_value(operands[0])
                data = bytes(count)
                return DirectiveResult(byte_width=count, data=data)
            return DirectiveResult()
        
        # RESW - reserve words
        if upper_name == 'RESW':
            if operands:
                count = self._parse_value(operands[0])
                data = bytes(count * 2)
                return DirectiveResult(byte_width=count * 2, data=data)
            return DirectiveResult()
        
        # RESD - reserve double words
        if upper_name == 'RESD':
            if operands:
                count = self._parse_value(operands[0])
                data = bytes(count * 4)
                return DirectiveResult(byte_width=count * 4, data=data)
            return DirectiveResult()
        
        # ALIGN - align to boundary
        if upper_name == 'ALIGN':
            if operands:
                boundary = self._parse_value(operands[0])
                remainder = current_lc % boundary
                if remainder:
                    padding = boundary - remainder
                    data = bytes([0x90] * padding)  # NOP padding
                    return DirectiveResult(byte_width=padding, data=data)
            return DirectiveResult()
        
        # EVEN - align to word boundary
        if upper_name == 'EVEN':
            if current_lc % 2:
                return DirectiveResult(byte_width=1, data=b'\x90')
            return DirectiveResult()
        
        # TIMES - repeat instruction/data
        if upper_name == 'TIMES':
            if len(operands) >= 2:
                count = self._parse_value(operands[0])
                # For simplicity, just handle TIMES n DB value
                if operands[1].upper() == 'DB' and len(operands) >= 3:
                    value = self._parse_value(operands[2])
                    data = bytes([value & 0xFF] * count)
                    return DirectiveResult(byte_width=len(data), data=data)
            return DirectiveResult()
        
        # Unknown directive
        return DirectiveResult()
    
    def _parse_value(self, value: str) -> int:
        """
        Parse a numeric value (hex, binary, decimal).
        
        Args:
            value: String representation of value.
            
        Returns:
            Integer value.
        """
        value = value.strip()
        if not value:
            return 0
        
        # Try to resolve from symbol table first
        if self.symbol_table and not value[0].isdigit() and value[0] != '-':
            try:
                return self.symbol_table.resolve(value)
            except:
                pass
        
        # Hex formats
        if value.lower().startswith('0x'):
            return int(value, 16)
        if value.lower().endswith('h'):
            return int(value[:-1], 16)
        
        # Binary formats
        if value.lower().startswith('0b'):
            return int(value, 2)
        if value.lower().endswith('b') and all(c in '01' for c in value[:-1]):
            return int(value[:-1], 2)
        
        # Octal
        if value.lower().endswith('o'):
            return int(value[:-1], 8)
        
        # Decimal
        try:
            return int(value)
        except ValueError:
            return 0
