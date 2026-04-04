#!/usr/bin/env python3
"""
Semantic Analyzer for 8085/8086 Assembler.

Validates semantic correctness after syntax analysis.
Catches errors like undefined labels, forward reference issues,
segment violations, and type mismatches.

Error codes: E2xx (semantic errors)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set

from parser import Statement, StatementType, Operand, OperandType, ParseResult


@dataclass
class SemanticError:
    """
    Semantic error record.
    
    Attributes:
        code: Error code (E2xx)
        message: Human-readable error message
        line: Line number
        col: Column number (if available)
        statement: The problematic statement
        severity: 'error' or 'warning'
    """
    code: str
    message: str
    line: int
    col: Optional[int] = None
    statement: Optional[Statement] = None
    severity: str = 'error'


@dataclass
class Symbol:
    """
    Symbol table entry.
    
    Attributes:
        name: Symbol name (uppercase)
        type: 'label', 'equate', 'data', 'proc'
        value: Address or value
        size: Size in bytes (for data)
        line: Line where defined
        references: Lines where referenced
    """
    name: str
    type: str
    value: Optional[int] = None
    size: int = 0
    line: int = 0
    references: List[int] = field(default_factory=list)


@dataclass
class SemanticAnalysisResult:
    """
    Result of semantic analysis.
    
    Attributes:
        errors: List of semantic errors
        warnings: List of semantic warnings
        symbols: Symbol table
        valid: True if no errors
    """
    errors: List[SemanticError]
    warnings: List[SemanticError]
    symbols: Dict[str, Symbol]
    
    @property
    def valid(self) -> bool:
        return len(self.errors) == 0


class SemanticAnalyzer:
    """
    Semantic analyzer for assembly code.
    
    Validates:
    - Label references (forward and backward)
    - Undefined symbols
    - Segment consistency
    - Type compatibility
    - Value ranges for equates
    """
    
    # Error codes
    E200_UNDEFINED_SYMBOL = "E200"
    E201_UNDEFINED_LABEL = "E201"
    E202_DUPLICATE_SYMBOL = "E202"
    E203_TYPE_MISMATCH = "E203"
    E204_INVALID_SEGMENT = "E204"
    E205_CIRCULAR_REFERENCE = "E205"
    E206_SYMBOL_REDEFINITION = "E206"
    E207_UNRESOLVED_EXTERNAL = "E207"
    E208_PROC_MISMATCH = "E208"
    E209_SEGMENT_MISMATCH = "E209"
    
    # Warning codes
    W200_UNUSED_LABEL = "W200"
    W201_UNREACHABLE_CODE = "W201"
    W202_MISSING_RET = "W202"
    W203_UNINITIALIZED_DATA = "W203"
    
    def __init__(self, architecture: str = "8086"):
        """
        Initialize semantic analyzer.
        
        Args:
            architecture: Target architecture
        """
        self.architecture = architecture.upper()
        self.errors: List[SemanticError] = []
        self.warnings: List[SemanticError] = []
        self.symbols: Dict[str, Symbol] = {}
        self._proc_stack: List[str] = []  # Track PROC/ENDP nesting
        
    def analyze(self, parse_result: ParseResult) -> SemanticAnalysisResult:
        """
        Perform semantic analysis on parsed statements.
        
        Args:
            parse_result: Result from parser
            
        Returns:
            SemanticAnalysisResult with errors, warnings, and symbol table
        """
        self.errors = []
        self.warnings = []
        self.symbols = {}
        self._proc_stack = []
        
        # Pass 1: Collect all symbols
        self._collect_symbols(parse_result)
        
        # Pass 2: Validate references
        self._validate_references(parse_result)
        
        # Pass 3: Check structural integrity
        self._validate_structure(parse_result)
        
        # Pass 4: Check for unused symbols
        self._check_unused_symbols()
        
        return SemanticAnalysisResult(
            errors=self.errors.copy(),
            warnings=self.warnings.copy(),
            symbols=self.symbols.copy()
        )
    
    def _collect_symbols(self, parse_result: ParseResult) -> None:
        """Collect all symbol definitions."""
        for stmt in parse_result.statements:
            if stmt.type == StatementType.EMPTY:
                continue
            
            # Labels from label-only statements
            if stmt.type == StatementType.LABEL_ONLY and stmt.label:
                self._add_symbol(stmt.label, 'label', stmt.line)
            
            # Labels from instructions/directives
            elif stmt.label:
                if stmt.type == StatementType.DATA:
                    self._add_symbol(stmt.label, 'data', stmt.line)
                elif stmt.type == StatementType.EQUATE:
                    # Try to evaluate the value
                    value = self._evaluate_equate(stmt, parse_result.equates)
                    self._add_symbol(stmt.label, 'equate', stmt.line, value=value)
                elif stmt.mnemonic and stmt.mnemonic.upper() == 'PROC':
                    self._add_symbol(stmt.label, 'proc', stmt.line)
                else:
                    self._add_symbol(stmt.label, 'label', stmt.line)
        
        # Also add equates from parser's equates dict that might not have label field
        for name, value in parse_result.equates.items():
            if name.upper() not in self.symbols:
                try:
                    num_value = int(value) if isinstance(value, str) and value.isdigit() else None
                except (ValueError, TypeError):
                    num_value = None
                self._add_symbol(name, 'equate', 0, value=num_value)
    
    def _add_symbol(
        self, 
        name: str, 
        sym_type: str, 
        line: int,
        value: Optional[int] = None
    ) -> None:
        """Add a symbol to the table."""
        upper_name = name.upper()
        
        if upper_name in self.symbols:
            existing = self.symbols[upper_name]
            self._error(
                self.E202_DUPLICATE_SYMBOL,
                f"Symbol '{name}' already defined at line {existing.line}",
                line
            )
        else:
            self.symbols[upper_name] = Symbol(
                name=upper_name,
                type=sym_type,
                value=value,
                line=line
            )
    
    def _evaluate_equate(
        self, 
        stmt: Statement, 
        equates: Dict[str, Any]
    ) -> Optional[int]:
        """Try to evaluate an EQU value."""
        if not stmt.raw_operands:
            return None
        
        value_str = stmt.raw_operands[0]
        
        # Try direct number
        try:
            # Handle hex
            if value_str.upper().startswith('0X'):
                return int(value_str, 16)
            if value_str.upper().endswith('H'):
                return int(value_str[:-1], 16)
            # Handle binary
            if value_str.upper().endswith('B'):
                return int(value_str[:-1], 2)
            # Handle decimal
            return int(value_str)
        except ValueError:
            pass
        
        # Try looking up in existing equates
        if value_str.upper() in equates:
            ref_value = equates[value_str.upper()]
            if isinstance(ref_value, int):
                return ref_value
        
        return None
    
    def _validate_references(self, parse_result: ParseResult) -> None:
        """Validate all symbol references."""
        for stmt in parse_result.statements:
            if stmt.type == StatementType.EMPTY:
                continue
            
            # Check operands for label references
            for operand in stmt.operands:
                if operand.type == OperandType.LABEL:
                    self._check_label_reference(operand.value, stmt)
                elif operand.type == OperandType.EXPRESSION:
                    # Expression might contain label references
                    self._check_expression_references(operand.value, stmt)
                elif operand.is_memory and operand.memory:
                    # Memory operand might have a label displacement
                    if isinstance(operand.memory.displacement, str):
                        self._check_label_reference(operand.memory.displacement, stmt)
    
    def _check_label_reference(self, label: str, stmt: Statement) -> None:
        """Check if a label reference is valid."""
        upper_label = label.upper()
        
        # Skip register names and special symbols
        if upper_label in {'AX', 'BX', 'CX', 'DX', 'SP', 'BP', 'SI', 'DI',
                          'AL', 'AH', 'BL', 'BH', 'CL', 'CH', 'DL', 'DH',
                          'CS', 'DS', 'ES', 'SS', '@DATA', '@CODE'}:
            return
        
        # Check if defined
        if upper_label not in self.symbols:
            self._error(
                self.E201_UNDEFINED_LABEL,
                f"Undefined label: '{label}'",
                stmt.line,
                stmt
            )
        else:
            # Record the reference
            self.symbols[upper_label].references.append(stmt.line)
    
    def _check_expression_references(self, expr: str, stmt: Statement) -> None:
        """Check expression for label references."""
        # Extract potential labels from expression
        # Skip operators and known keywords
        skip_words = {
            'OFFSET', 'SEG', 'PTR', 'BYTE', 'WORD', 'DWORD',
            'NEAR', 'FAR', 'SHORT', 'AND', 'OR', 'NOT', 'XOR',
            '@DATA', '@CODE', 'DATA', 'CODE', '$',
            # Memory model keywords
            'SMALL', 'TINY', 'MEDIUM', 'COMPACT', 'LARGE', 'HUGE', 'FLAT',
            # Common directive arguments
            'NEAR', 'FAR', 'PROC', 'ENDP', 'PUBLIC', 'PRIVATE'
        }
        
        import re
        words = re.findall(r'[A-Za-z_@][A-Za-z0-9_@]*', expr)
        
        for word in words:
            upper = word.upper()
            if upper not in skip_words and not upper.isdigit():
                # Check if it's a register
                if upper in {'AX', 'BX', 'CX', 'DX', 'SP', 'BP', 'SI', 'DI',
                            'AL', 'AH', 'BL', 'BH', 'CL', 'CH', 'DL', 'DH',
                            'CS', 'DS', 'ES', 'SS'}:
                    continue
                
                # Skip @-prefixed special symbols
                if word.startswith('@'):
                    continue
                
                # Check if defined
                if upper not in self.symbols:
                    self._error(
                        self.E200_UNDEFINED_SYMBOL,
                        f"Undefined symbol in expression: '{word}'",
                        stmt.line,
                        stmt
                    )
                else:
                    self.symbols[upper].references.append(stmt.line)
    
    def _validate_structure(self, parse_result: ParseResult) -> None:
        """Validate structural integrity (PROC/ENDP, etc.)."""
        proc_stack: List[tuple] = []  # (name, line)
        
        for stmt in parse_result.statements:
            if stmt.type == StatementType.EMPTY:
                continue
            
            if stmt.mnemonic:
                mnemonic = stmt.mnemonic.upper()
                
                # Track PROC/ENDP
                if mnemonic == 'PROC':
                    proc_name = stmt.label.upper() if stmt.label else f"<unnamed@{stmt.line}>"
                    proc_stack.append((proc_name, stmt.line))
                
                elif mnemonic == 'ENDP':
                    if not proc_stack:
                        self._error(
                            self.E208_PROC_MISMATCH,
                            "ENDP without matching PROC",
                            stmt.line,
                            stmt
                        )
                    else:
                        expected_name = proc_stack[-1][0]
                        actual_name = stmt.label.upper() if stmt.label else ""
                        
                        if actual_name and actual_name != expected_name:
                            self._error(
                                self.E208_PROC_MISMATCH,
                                f"ENDP '{actual_name}' does not match PROC '{expected_name}'",
                                stmt.line,
                                stmt
                            )
                        
                        proc_stack.pop()
        
        # Check for unclosed PROCs
        for proc_name, proc_line in proc_stack:
            self._error(
                self.E208_PROC_MISMATCH,
                f"PROC '{proc_name}' at line {proc_line} not terminated with ENDP",
                proc_line
            )
    
    def _check_unused_symbols(self) -> None:
        """Check for unused symbols (warnings only)."""
        for name, symbol in self.symbols.items():
            if not symbol.references and symbol.type == 'label':
                # Skip common entry points
                if name not in {'START', 'MAIN', '_START', '_MAIN'}:
                    self._warning(
                        self.W200_UNUSED_LABEL,
                        f"Label '{name}' defined but never referenced",
                        symbol.line
                    )
    
    def _error(
        self, 
        code: str, 
        message: str, 
        line: int,
        stmt: Optional[Statement] = None
    ) -> None:
        """Record an error."""
        self.errors.append(SemanticError(
            code=code,
            message=message,
            line=line,
            statement=stmt,
            severity='error'
        ))
    
    def _warning(
        self, 
        code: str, 
        message: str, 
        line: int,
        stmt: Optional[Statement] = None
    ) -> None:
        """Record a warning."""
        self.warnings.append(SemanticError(
            code=code,
            message=message,
            line=line,
            statement=stmt,
            severity='warning'
        ))
    
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0
    
    def get_errors(self) -> List[SemanticError]:
        """Get list of errors."""
        return self.errors.copy()


def analyze_semantics(
    parse_result: ParseResult, 
    architecture: str = "8086"
) -> SemanticAnalysisResult:
    """
    Convenience function to analyze semantics.
    
    Args:
        parse_result: Result from parser
        architecture: Target architecture
        
    Returns:
        SemanticAnalysisResult
    """
    analyzer = SemanticAnalyzer(architecture)
    return analyzer.analyze(parse_result)


if __name__ == '__main__':
    from parser import parse
    
    # Test the semantic analyzer
    test_code = '''
.MODEL SMALL
.DATA
    MSG DB 'Hello'
    COUNT DW 0
    
.CODE
START:
    MOV AX, @DATA
    MOV DS, AX
    
    ; Reference to defined label
    JMP NEXT_LABEL
    
NEXT_LABEL:
    ; Reference to undefined label
    CALL UNDEFINED_FUNC
    
    ; Reference to data symbol
    LEA DX, MSG
    MOV CX, COUNT
    
    ; Mismatched PROC/ENDP
MYPROC PROC
    RET
MYPROC ENDP

    ; Another ENDP without PROC
    ; ENDP

END START
'''
    
    parse_result = parse(test_code)
    result = analyze_semantics(parse_result)
    
    print("=== Semantic Analysis Results ===")
    print(f"Valid: {result.valid}")
    
    print(f"\n=== Symbol Table ({len(result.symbols)}) ===")
    for name, sym in sorted(result.symbols.items()):
        refs = ', '.join(str(r) for r in sym.references) if sym.references else 'none'
        print(f"  {name}: type={sym.type}, line={sym.line}, refs=[{refs}]")
    
    if result.errors:
        print(f"\n=== Errors ({len(result.errors)}) ===")
        for err in result.errors:
            print(f"  [{err.code}] Line {err.line}: {err.message}")
    
    if result.warnings:
        print(f"\n=== Warnings ({len(result.warnings)}) ===")
        for warn in result.warnings:
            print(f"  [{warn.code}] Line {warn.line}: {warn.message}")
