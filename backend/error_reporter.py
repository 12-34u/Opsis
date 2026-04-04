#!/usr/bin/env python3
"""
Error Reporter module for the Dynamic Two-Pass Assembler.
Collects and reports assembly errors with detailed context.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Phase(Enum):
    """Assembly phase where error occurred."""
    LEXER = "LEXER"
    PASS1 = "PASS1"
    PASS2 = "PASS2"


@dataclass
class AssemblerError:
    """Represents an assembly error."""
    phase: Phase
    code: str
    line: int
    col: int
    message: str
    source_line: str = ""
    
    def format(self) -> str:
        """Format error for display."""
        parts = [
            f"[{self.phase.value}:{self.code}] Line {self.line}, Column {self.col}:",
            f"  {self.message}"
        ]
        if self.source_line:
            parts.append(f"  | {self.source_line.rstrip()}")
            parts.append(f"  | {' ' * (self.col - 1)}^")
        return "\n".join(parts)


class ErrorReporter:
    """
    Collects and reports assembly errors.
    
    Accumulates errors during assembly and provides formatted output.
    """
    
    # Error code definitions
    CODES = {
        # Lexer errors (E001-E019)
        "E001": "Invalid character",
        "E002": "Unterminated string",
        "E003": "Invalid number format",
        
        # Pass 1 errors (E020-E039)
        "E020": "Duplicate label definition",
        "E021": "Invalid directive",
        "E022": "Missing operand",
        "E023": "Invalid label name",
        
        # Pass 2 errors (E040-E059)
        "E040": "Undefined symbol",
        "E041": "Invalid operand type",
        "E042": "Operand out of range",
        "E043": "Unknown instruction",
        "E044": "Wrong number of operands",
        "E045": "No matching instruction variant",
        
        # General errors (E060-E099)
        "E060": "Internal assembler error",
        "E061": "File not found",
        "E062": "ISA loading error",
    }
    
    def __init__(self):
        """Initialize error reporter."""
        self.errors: List[AssemblerError] = []
        self.warnings: List[AssemblerError] = []
        self._source_lines: List[str] = []
    
    def set_source(self, source: str) -> None:
        """
        Set source code for error context.
        
        Args:
            source: Assembly source code.
        """
        self._source_lines = source.splitlines()
    
    def error(self, phase: Phase, code: str, message: str, 
              line: int, col: int = 1) -> None:
        """
        Record an error.
        
        Args:
            phase: Assembly phase (LEXER, PASS1, PASS2).
            code: Error code (E001-E099).
            message: Error message.
            line: Source line number.
            col: Column number.
        """
        source_line = ""
        if 0 < line <= len(self._source_lines):
            source_line = self._source_lines[line - 1]
        
        self.errors.append(AssemblerError(
            phase=phase,
            code=code,
            line=line,
            col=col,
            message=message,
            source_line=source_line
        ))
    
    def warning(self, phase: Phase, message: str, line: int, col: int = 1) -> None:
        """
        Record a warning.
        
        Args:
            phase: Assembly phase.
            message: Warning message.
            line: Source line number.
            col: Column number.
        """
        source_line = ""
        if 0 < line <= len(self._source_lines):
            source_line = self._source_lines[line - 1]
        
        self.warnings.append(AssemblerError(
            phase=phase,
            code="W001",
            line=line,
            col=col,
            message=f"Warning: {message}",
            source_line=source_line
        ))
    
    def has_errors(self) -> bool:
        """Check if any errors have been recorded."""
        return len(self.errors) > 0
    
    def clear(self) -> None:
        """Clear all errors and warnings."""
        self.errors.clear()
        self.warnings.clear()
    
    def report(self) -> str:
        """
        Generate formatted error report.
        
        Returns:
            Formatted string with all errors and warnings.
        """
        # Sort by line number
        sorted_errors = sorted(self.errors, key=lambda e: (e.line, e.col))
        sorted_warnings = sorted(self.warnings, key=lambda e: (e.line, e.col))
        
        lines = []
        
        if sorted_errors:
            lines.append(f"\n=== {len(sorted_errors)} Error(s) ===\n")
            for err in sorted_errors:
                lines.append(err.format())
                lines.append("")
        
        if sorted_warnings:
            lines.append(f"\n=== {len(sorted_warnings)} Warning(s) ===\n")
            for warn in sorted_warnings:
                lines.append(warn.format())
                lines.append("")
        
        return "\n".join(lines)
    
    def get_exit_code(self) -> int:
        """Get process exit code (1 if errors, 0 otherwise)."""
        return 1 if self.errors else 0
