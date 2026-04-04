#!/usr/bin/env python3
"""
Symbol Table module for 8086 Assembler.
Manages labels, constants, and forward references.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


class DuplicateLabelError(Exception):
    """Raised when a label is defined more than once."""
    pass


class UndefinedSymbolError(Exception):
    """Raised when a symbol is referenced but not defined."""
    pass


@dataclass
class Symbol:
    """Represents a symbol (label or constant)."""
    name: str
    value: int
    is_constant: bool = False
    line_defined: int = 0
    segment: Optional[str] = None
    size: int = 0  # For data labels


class SymbolTable:
    """
    Symbol table for assembly.
    Tracks labels, constants, and forward references.
    """
    
    def __init__(self):
        """Initialize empty symbol table."""
        self.symbols: Dict[str, Symbol] = {}
        self.forward_refs: Dict[str, List[int]] = {}  # symbol -> [lines where referenced]
    
    def define(self, name: str, value: int, is_constant: bool = False, 
               line: int = 0, segment: str = None, size: int = 0) -> None:
        """
        Define a symbol.
        
        Args:
            name: Symbol name.
            value: Symbol value (address or constant).
            is_constant: True if EQU constant.
            line: Line number where defined.
            segment: Segment name (optional).
            size: Data size in bytes (for data labels).
            
        Raises:
            DuplicateLabelError: If symbol already exists.
        """
        upper_name = name.upper()
        
        if upper_name in self.symbols:
            existing = self.symbols[upper_name]
            raise DuplicateLabelError(
                f"Symbol '{name}' already defined at line {existing.line_defined}"
            )
        
        self.symbols[upper_name] = Symbol(
            name=name,
            value=value,
            is_constant=is_constant,
            line_defined=line,
            segment=segment,
            size=size
        )
        
        # Resolve any forward references
        if upper_name in self.forward_refs:
            del self.forward_refs[upper_name]
    
    def resolve(self, name: str) -> int:
        """
        Get symbol value.
        
        Args:
            name: Symbol name.
            
        Returns:
            Symbol value.
            
        Raises:
            UndefinedSymbolError: If symbol not defined.
        """
        upper_name = name.upper()
        
        if upper_name not in self.symbols:
            raise UndefinedSymbolError(f"Undefined symbol: '{name}'")
        
        return self.symbols[upper_name].value
    
    def is_defined(self, name: str) -> bool:
        """Check if symbol is defined."""
        return name.upper() in self.symbols
    
    def reference(self, name: str, line: int) -> None:
        """
        Record a forward reference.
        
        Args:
            name: Symbol name being referenced.
            line: Line number of reference.
        """
        upper_name = name.upper()
        
        if upper_name not in self.symbols:
            if upper_name not in self.forward_refs:
                self.forward_refs[upper_name] = []
            self.forward_refs[upper_name].append(line)
    
    def get_forward_refs(self) -> List[str]:
        """Get list of unresolved forward references."""
        return list(self.forward_refs.keys())
    
    def get_symbol(self, name: str) -> Optional[Symbol]:
        """Get symbol object."""
        return self.symbols.get(name.upper())
    
    def clear(self) -> None:
        """Clear all symbols."""
        self.symbols.clear()
        self.forward_refs.clear()
    
    def dump(self) -> str:
        """Dump symbol table as formatted string."""
        lines = [
            "Symbol Table",
            "=" * 50,
            f"{'Name':<20} {'Value':<10} {'Type':<10} {'Line':<6}",
            "-" * 50
        ]
        
        for name, sym in sorted(self.symbols.items()):
            sym_type = "CONST" if sym.is_constant else "LABEL"
            lines.append(f"{sym.name:<20} {sym.value:04X}h      {sym_type:<10} {sym.line_defined:<6}")
        
        lines.append("=" * 50)
        return '\n'.join(lines)
    
    def to_dict(self) -> Dict[str, int]:
        """Export as simple name -> value dictionary."""
        return {name: sym.value for name, sym in self.symbols.items()}
