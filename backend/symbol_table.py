#!/usr/bin/env python3
"""
Symbol Table module for the Dynamic Two-Pass Assembler.
Handles label definitions, constants, and forward reference tracking.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


class DuplicateLabelError(Exception):
    """Raised when attempting to redefine an existing label."""
    def __init__(self, name: str, line: int):
        self.name = name
        self.line = line
        super().__init__(f"Duplicate label '{name}' at line {line}")


class UndefinedSymbolError(Exception):
    """Raised when referencing an undefined symbol."""
    def __init__(self, name: str, line: int = 0):
        self.name = name
        self.line = line
        super().__init__(f"Undefined symbol '{name}'" + (f" at line {line}" if line else ""))


@dataclass
class Symbol:
    """Represents a symbol table entry."""
    name: str
    value: int
    is_constant: bool = False
    is_defined: bool = True
    line_defined: int = 0
    references: List[int] = field(default_factory=list)


class SymbolTable:
    """
    Symbol table for tracking labels, constants, and forward references.
    
    Provides methods to define symbols, resolve addresses, and track
    forward references for validation after Pass 1.
    """
    
    def __init__(self):
        """Initialize empty symbol table."""
        self._symbols: Dict[str, Symbol] = {}
        self._forward_refs: Set[str] = set()
    
    def define(self, name: str, value: int, is_constant: bool = False, line: int = 0) -> None:
        """
        Define a symbol with a value.
        
        Args:
            name: Symbol name.
            value: Symbol value (address or constant).
            is_constant: True if this is a constant (EQU), not a label.
            line: Source line number where defined.
            
        Raises:
            DuplicateLabelError: If symbol is already defined.
        """
        upper_name = name.upper()
        if upper_name in self._symbols and self._symbols[upper_name].is_defined:
            raise DuplicateLabelError(name, line)
        
        # Remove from forward refs if it was referenced before definition
        self._forward_refs.discard(upper_name)
        
        self._symbols[upper_name] = Symbol(
            name=name,
            value=value,
            is_constant=is_constant,
            is_defined=True,
            line_defined=line
        )
    
    def reference(self, name: str, from_line: int = 0) -> None:
        """
        Record a reference to a symbol (for forward reference tracking).
        
        Args:
            name: Symbol name being referenced.
            from_line: Line number where the reference occurs.
        """
        upper_name = name.upper()
        if upper_name not in self._symbols:
            self._forward_refs.add(upper_name)
            # Create placeholder
            self._symbols[upper_name] = Symbol(
                name=name,
                value=0,
                is_defined=False,
                references=[from_line]
            )
        elif not self._symbols[upper_name].is_defined:
            self._symbols[upper_name].references.append(from_line)
    
    def resolve(self, name: str) -> int:
        """
        Resolve a symbol to its value.
        
        Args:
            name: Symbol name to resolve.
            
        Returns:
            Symbol value.
            
        Raises:
            UndefinedSymbolError: If symbol is not defined.
        """
        upper_name = name.upper()
        if upper_name not in self._symbols:
            raise UndefinedSymbolError(name)
        symbol = self._symbols[upper_name]
        if not symbol.is_defined:
            raise UndefinedSymbolError(name)
        return symbol.value
    
    def is_defined(self, name: str) -> bool:
        """
        Check if a symbol is defined.
        
        Args:
            name: Symbol name.
            
        Returns:
            True if symbol is defined, False otherwise.
        """
        upper_name = name.upper()
        return upper_name in self._symbols and self._symbols[upper_name].is_defined
    
    def get_forward_refs(self) -> List[str]:
        """
        Get list of symbols referenced but not yet defined.
        
        Returns:
            List of undefined symbol names.
        """
        return [
            name for name, sym in self._symbols.items()
            if not sym.is_defined
        ]
    
    def get_all_symbols(self) -> Dict[str, Symbol]:
        """
        Get all defined symbols.
        
        Returns:
            Dictionary of symbol name to Symbol object.
        """
        return {k: v for k, v in self._symbols.items() if v.is_defined}
    
    def dump(self) -> str:
        """
        Generate human-readable symbol table dump.
        
        Returns:
            Formatted string representation.
        """
        lines = [
            "Symbol Table",
            "=" * 60,
            f"{'Name':<20} {'Value':<12} {'Type':<10} {'Line':<6}",
            "-" * 60
        ]
        
        for name, sym in sorted(self._symbols.items()):
            if sym.is_defined:
                sym_type = "CONSTANT" if sym.is_constant else "LABEL"
                val_str = f"0x{sym.value:04X}"
                lines.append(f"{sym.name:<20} {val_str:<12} {sym_type:<10} {sym.line_defined:<6}")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def clear(self) -> None:
        """Clear all symbols and forward references."""
        self._symbols.clear()
        self._forward_refs.clear()
