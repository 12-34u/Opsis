#!/usr/bin/env python3
"""
Syntax Analyzer for 8085/8086 Assembler.

Validates parsed statements against the ISA specification.
Catches errors like missing operands, invalid addressing modes,
and malformed instructions.

Error codes: E1xx (syntax errors)
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any, Set, Tuple

from parser import Statement, StatementType, Operand, OperandType, ParseResult


@dataclass
class SyntaxError:
    """
    Syntax error record.
    
    Attributes:
        code: Error code (E1xx)
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
class SyntaxAnalysisResult:
    """
    Result of syntax analysis.
    
    Attributes:
        errors: List of syntax errors found
        warnings: List of syntax warnings
        valid: True if no errors (warnings OK)
    """
    errors: List[SyntaxError]
    warnings: List[SyntaxError]
    
    @property
    def valid(self) -> bool:
        return len(self.errors) == 0


class SyntaxAnalyzer:
    """
    Syntax analyzer for assembly code.
    
    Validates:
    - Operand count matches instruction specification
    - Operand types are valid for instruction
    - Addressing modes are valid
    - Register sizes match
    - Immediate values are in range
    """
    
    # Error codes
    E100_MISSING_OPERAND = "E100"
    E101_TOO_MANY_OPERANDS = "E101"
    E102_INVALID_OPERAND_TYPE = "E102"
    E103_INVALID_REGISTER = "E103"
    E104_INVALID_ADDRESSING_MODE = "E104"
    E105_REGISTER_SIZE_MISMATCH = "E105"
    E106_IMMEDIATE_OUT_OF_RANGE = "E106"
    E107_INVALID_INSTRUCTION = "E107"
    E108_INVALID_DIRECTIVE_SYNTAX = "E108"
    E109_DUPLICATE_LABEL = "E109"
    E110_INVALID_MEMORY_OPERAND = "E110"
    
    # Warning codes
    W100_REDUNDANT_SIZE_OVERRIDE = "W100"
    W101_IMPLICIT_SIZE_ASSUMPTION = "W101"
    
    def __init__(self, architecture: str = "8086"):
        """
        Initialize syntax analyzer.
        
        Args:
            architecture: Target architecture ("8085" or "8086")
        """
        self.architecture = architecture.upper()
        self.isa = self._load_isa()
        self.errors: List[SyntaxError] = []
        self.warnings: List[SyntaxError] = []
        self._defined_labels: Set[str] = set()
        
    def _load_isa(self) -> Dict[str, Any]:
        """Load ISA definition from JSON."""
        backend_dir = Path(__file__).parent
        isa_file = backend_dir / f'isa_{self.architecture.lower()}.json'
        
        if isa_file.exists():
            with open(isa_file) as f:
                return json.load(f)
        
        return {'instructions': [], 'registers': {}}
    
    def analyze(self, parse_result: ParseResult) -> SyntaxAnalysisResult:
        """
        Analyze parsed statements for syntax errors.
        
        Args:
            parse_result: Result from parser
            
        Returns:
            SyntaxAnalysisResult with errors and warnings
        """
        self.errors = []
        self.warnings = []
        self._defined_labels = set()
        
        # First pass: collect labels
        for stmt in parse_result.statements:
            if stmt.label:
                if stmt.label.upper() in self._defined_labels:
                    self._error(
                        self.E109_DUPLICATE_LABEL,
                        f"Duplicate label: '{stmt.label}'",
                        stmt
                    )
                else:
                    self._defined_labels.add(stmt.label.upper())
        
        # Second pass: validate statements
        for stmt in parse_result.statements:
            if stmt.type == StatementType.EMPTY:
                continue
            elif stmt.type == StatementType.INSTRUCTION:
                self._validate_instruction(stmt)
            elif stmt.type == StatementType.DATA:
                self._validate_data(stmt)
            elif stmt.type == StatementType.DIRECTIVE:
                self._validate_directive(stmt)
            elif stmt.type == StatementType.EQUATE:
                self._validate_equate(stmt)
        
        return SyntaxAnalysisResult(
            errors=self.errors.copy(),
            warnings=self.warnings.copy()
        )
    
    def _validate_instruction(self, stmt: Statement) -> None:
        """Validate an instruction statement."""
        if not stmt.mnemonic:
            return
        
        mnemonic = stmt.mnemonic.upper()
        
        # Find instruction in ISA
        instr_def = self._find_instruction(mnemonic)
        if not instr_def:
            self._error(
                self.E107_INVALID_INSTRUCTION,
                f"Unknown instruction: '{mnemonic}'",
                stmt
            )
            return
        
        # Check operand count against variants
        variants = instr_def.get('variants', [])
        if not variants:
            # No variants defined - allow any operands
            return
        
        # Find matching variant
        matching_variant = self._find_matching_variant(stmt, variants)
        
        if not matching_variant:
            # Try to give a helpful error
            expected_counts = set()
            for v in variants:
                ops = v.get('operands')
                if ops is None or ops == '' or ops == []:
                    op_count = 0
                elif isinstance(ops, list):
                    op_count = len(ops)
                elif isinstance(ops, str):
                    op_count = len(ops.split(',')) if ops.strip() else 0
                else:
                    op_count = 0
                expected_counts.add(op_count)
            
            actual_count = len(stmt.operands)
            
            if actual_count < min(expected_counts):
                self._error(
                    self.E100_MISSING_OPERAND,
                    f"'{mnemonic}' requires at least {min(expected_counts)} operand(s), got {actual_count}",
                    stmt
                )
            elif actual_count > max(expected_counts):
                self._error(
                    self.E101_TOO_MANY_OPERANDS,
                    f"'{mnemonic}' accepts at most {max(expected_counts)} operand(s), got {actual_count}",
                    stmt
                )
            else:
                # Count matches but types don't
                self._error(
                    self.E102_INVALID_OPERAND_TYPE,
                    f"Invalid operand combination for '{mnemonic}'",
                    stmt
                )
        else:
            # Validate operand details
            self._validate_operand_details(stmt, matching_variant)
    
    def _find_instruction(self, mnemonic: str) -> Optional[Dict[str, Any]]:
        """Find instruction definition in ISA."""
        for instr in self.isa.get('instructions', []):
            if instr.get('mnemonic', '').upper() == mnemonic.upper():
                return instr
        return None
    
    def _find_matching_variant(
        self, 
        stmt: Statement, 
        variants: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find a variant that matches the operands."""
        for variant in variants:
            operand_spec = variant.get('operands', '')
            if self._operands_match(stmt.operands, operand_spec):
                return variant
        return None
    
    def _operands_match(
        self, 
        operands: List[Operand], 
        spec: Any
    ) -> bool:
        """Check if operands match a specification."""
        # Handle both list and string formats
        if spec is None:
            return len(operands) == 0
        
        if isinstance(spec, list):
            spec_parts = spec
        elif isinstance(spec, str):
            if not spec or spec.strip() == '':
                return len(operands) == 0
            spec_parts = [p.strip() for p in spec.split(',')]
        else:
            return False
        
        if len(operands) != len(spec_parts):
            return False
        
        for operand, spec_part in zip(operands, spec_parts):
            if not self._operand_matches_spec(operand, spec_part):
                return False
        
        return True
    
    def _operand_matches_spec(self, operand: Operand, spec: str) -> bool:
        """Check if an operand matches a specification."""
        spec = spec.upper()
        
        # Register specifications
        if spec in ('REG8', 'R8'):
            return operand.is_register and operand.register in {
                'AL', 'AH', 'BL', 'BH', 'CL', 'CH', 'DL', 'DH'
            }
        
        if spec in ('REG16', 'R16'):
            return operand.is_register and operand.register in {
                'AX', 'BX', 'CX', 'DX', 'SP', 'BP', 'SI', 'DI'
            }
        
        if spec in ('SEGREG', 'SREG'):
            return operand.is_register and operand.register in {
                'CS', 'DS', 'ES', 'SS'
            }
        
        if spec == 'REG':
            return operand.is_register
        
        # Immediate specifications
        if spec in ('IMM8', 'I8'):
            if not operand.is_immediate:
                return False
            val = operand.immediate or 0
            return -128 <= val <= 255
        
        if spec in ('IMM16', 'I16'):
            if not operand.is_immediate:
                return False
            val = operand.immediate or 0
            return -32768 <= val <= 65535
        
        if spec == 'IMM':
            return operand.is_immediate
        
        # Memory specifications - labels are valid memory references
        if spec in ('MEM', 'M', 'MEM8', 'MEM16'):
            return operand.is_memory or operand.type == OperandType.LABEL
        
        if spec == 'R/M8':
            return (operand.is_register and operand.register in {
                'AL', 'AH', 'BL', 'BH', 'CL', 'CH', 'DL', 'DH'
            }) or operand.is_memory
        
        if spec == 'R/M16':
            return (operand.is_register and operand.register in {
                'AX', 'BX', 'CX', 'DX', 'SP', 'BP', 'SI', 'DI'
            }) or operand.is_memory
        
        if spec == 'R/M':
            return operand.is_register or operand.is_memory
        
        # Specific registers
        if spec == 'AL':
            return operand.is_register and operand.register == 'AL'
        if spec == 'AX':
            return operand.is_register and operand.register == 'AX'
        if spec == 'CL':
            return operand.is_register and operand.register == 'CL'
        if spec == 'DX':
            return operand.is_register and operand.register == 'DX'
        
        # Label/address
        if spec in ('REL8', 'REL16', 'ADDR', 'LABEL'):
            return operand.type in (OperandType.LABEL, OperandType.IMMEDIATE, OperandType.EXPRESSION)
        
        # 8085 specific
        if spec in ('RST', 'PSW'):
            return True  # Accept any for RST vectors
        
        # Accept any if not a specific spec
        return True
    
    def _validate_operand_details(
        self, 
        stmt: Statement, 
        variant: Dict[str, Any]
    ) -> None:
        """Validate detailed operand constraints."""
        for i, operand in enumerate(stmt.operands):
            # Check immediate range
            if operand.is_immediate and operand.immediate is not None:
                byte_width = variant.get('byte_width', 2)
                val = operand.immediate
                
                if byte_width == 1:
                    if not (-128 <= val <= 255):
                        self._error(
                            self.E106_IMMEDIATE_OUT_OF_RANGE,
                            f"Immediate value {val} out of range for 8-bit operand",
                            stmt
                        )
                elif byte_width == 2:
                    if not (-32768 <= val <= 65535):
                        self._error(
                            self.E106_IMMEDIATE_OUT_OF_RANGE,
                            f"Immediate value {val} out of range for 16-bit operand",
                            stmt
                        )
            
            # Check memory operand validity
            if operand.is_memory and operand.memory:
                mem = operand.memory
                
                # Validate base register
                if mem.base and mem.base not in {'BX', 'BP', 'SI', 'DI'}:
                    # 8085 allows different registers
                    if self.architecture == "8086":
                        self._error(
                            self.E110_INVALID_MEMORY_OPERAND,
                            f"Invalid base register in memory operand: {mem.base}",
                            stmt
                        )
                
                # Validate index register
                if mem.index and mem.index not in {'SI', 'DI'}:
                    if self.architecture == "8086":
                        self._error(
                            self.E110_INVALID_MEMORY_OPERAND,
                            f"Invalid index register in memory operand: {mem.index}",
                            stmt
                        )
                
                # Check for invalid combinations (BP requires segment override for direct)
                if mem.base == 'BP' and mem.displacement is None and mem.index is None:
                    self._warning(
                        self.W101_IMPLICIT_SIZE_ASSUMPTION,
                        "[BP] requires displacement; will be encoded as [BP+0]",
                        stmt
                    )
    
    def _validate_data(self, stmt: Statement) -> None:
        """Validate a data definition statement."""
        if not stmt.mnemonic:
            return
        
        directive = stmt.mnemonic.upper()
        
        # Check operand presence
        if not stmt.operands and not stmt.raw_operands:
            self._error(
                self.E100_MISSING_OPERAND,
                f"'{directive}' requires at least one value",
                stmt
            )
            return
        
        # Validate values for directive type
        if directive in ('DB', 'BYTE'):
            for operand in stmt.operands:
                if operand.is_immediate and operand.immediate is not None:
                    if not (-128 <= operand.immediate <= 255):
                        self._error(
                            self.E106_IMMEDIATE_OUT_OF_RANGE,
                            f"Value {operand.immediate} out of range for DB (byte)",
                            stmt
                        )
        
        elif directive in ('DW', 'WORD'):
            for operand in stmt.operands:
                if operand.is_immediate and operand.immediate is not None:
                    if not (-32768 <= operand.immediate <= 65535):
                        self._error(
                            self.E106_IMMEDIATE_OUT_OF_RANGE,
                            f"Value {operand.immediate} out of range for DW (word)",
                            stmt
                        )
    
    def _validate_directive(self, stmt: Statement) -> None:
        """Validate an assembler directive."""
        if not stmt.mnemonic:
            return
        
        directive = stmt.mnemonic.upper().lstrip('.')
        
        # ORG requires an address
        if directive == 'ORG':
            if not stmt.operands:
                self._error(
                    self.E100_MISSING_OPERAND,
                    "ORG requires an address operand",
                    stmt
                )
        
        # END can have an optional start label
        # MODEL requires a model type
        if directive == 'MODEL':
            if not stmt.raw_operands:
                self._error(
                    self.E100_MISSING_OPERAND,
                    ".MODEL requires a memory model (SMALL, MEDIUM, etc.)",
                    stmt
                )
    
    def _validate_equate(self, stmt: Statement) -> None:
        """Validate an EQU definition."""
        if not stmt.raw_operands:
            self._error(
                self.E100_MISSING_OPERAND,
                "EQU requires a value",
                stmt
            )
    
    def _error(self, code: str, message: str, stmt: Statement) -> None:
        """Record an error."""
        self.errors.append(SyntaxError(
            code=code,
            message=message,
            line=stmt.line,
            statement=stmt,
            severity='error'
        ))
    
    def _warning(self, code: str, message: str, stmt: Statement) -> None:
        """Record a warning."""
        self.warnings.append(SyntaxError(
            code=code,
            message=message,
            line=stmt.line,
            statement=stmt,
            severity='warning'
        ))
    
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0
    
    def get_errors(self) -> List[SyntaxError]:
        """Get list of errors."""
        return self.errors.copy()


def analyze_syntax(
    parse_result: ParseResult, 
    architecture: str = "8086"
) -> SyntaxAnalysisResult:
    """
    Convenience function to analyze syntax.
    
    Args:
        parse_result: Result from parser
        architecture: Target architecture
        
    Returns:
        SyntaxAnalysisResult
    """
    analyzer = SyntaxAnalyzer(architecture)
    return analyzer.analyze(parse_result)


if __name__ == '__main__':
    from parser import parse
    
    # Test the syntax analyzer
    test_code = '''
; Test code with various errors
.MODEL SMALL
.DATA
    MSG DB 'Hello'
    
.CODE
START:
    MOV AX, BX      ; Valid
    MOV AL, 1234H   ; E106: immediate too large for AL
    MOV             ; E100: missing operands
    ADD AX, BX, CX  ; E101: too many operands
    XYZ AX, BX      ; E107: unknown instruction
    
START:              ; E109: duplicate label
    JMP END_LABEL   ; Forward reference (OK for syntax)
    
END_LABEL:
    RET
END START
'''
    
    parse_result = parse(test_code)
    result = analyze_syntax(parse_result)
    
    print("=== Syntax Analysis Results ===")
    print(f"Valid: {result.valid}")
    
    if result.errors:
        print(f"\n=== Errors ({len(result.errors)}) ===")
        for err in result.errors:
            print(f"  [{err.code}] Line {err.line}: {err.message}")
    
    if result.warnings:
        print(f"\n=== Warnings ({len(result.warnings)}) ===")
        for warn in result.warnings:
            print(f"  [{warn.code}] Line {warn.line}: {warn.message}")
