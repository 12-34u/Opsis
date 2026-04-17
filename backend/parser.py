#!/usr/bin/env python3
"""
Parser module for 8085/8086 Assembler.

Transforms token streams into structured Statement objects containing
parsed instructions, directives, labels, and operands.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Any, Tuple, Union

from lexer import Token, TokenType, Lexer, parse_immediate
from preprocessor import PreprocessedLine, SourceLocation


class OperandType(Enum):
    """Operand type classification."""
    REGISTER = auto()           # AX, BL, etc.
    IMMEDIATE = auto()          # 42, 0FFh, etc.
    MEMORY_DIRECT = auto()      # [1234h] - direct address
    MEMORY_INDIRECT = auto()    # [BX], [SI] - register indirect
    MEMORY_INDEXED = auto()     # [BX+SI], [BP+DI] - indexed
    MEMORY_BASED = auto()       # [BX+4], [BP+8] - based with displacement
    MEMORY_BASED_INDEXED = auto()  # [BX+SI+4] - based indexed with displacement
    MEMORY_LABEL = auto()       # [label] - symbolic address
    LABEL = auto()              # Label reference (for jumps/calls)
    STRING = auto()             # "hello" - string literal
    EXPRESSION = auto()         # Complex expression: OFFSET label, label+1
    SEGMENT_OVERRIDE = auto()   # ES:, CS:, etc.
    FAR_PTR = auto()           # seg:offset for far calls/jumps


@dataclass 
class MemoryRef:
    """
    Parsed memory reference.
    
    Attributes:
        base: Base register (BX, BP, or None)
        index: Index register (SI, DI, or None)
        displacement: Numeric displacement or label
        segment_override: Segment override (CS, DS, ES, SS, or None)
        size_override: Size override (BYTE, WORD, DWORD, or None)
        raw: Original text
    """
    base: Optional[str] = None
    index: Optional[str] = None
    displacement: Union[int, str, None] = None
    segment_override: Optional[str] = None
    size_override: Optional[str] = None
    raw: str = ""
    
    def is_direct(self) -> bool:
        """True if this is a direct memory access (no registers)."""
        return self.base is None and self.index is None
    
    def is_indirect(self) -> bool:
        """True if this is a simple register indirect."""
        return (self.base is not None or self.index is not None) and self.displacement is None
    
    def needs_displacement(self) -> bool:
        """True if this memory ref has a displacement."""
        return self.displacement is not None


@dataclass
class Operand:
    """
    Parsed operand.
    
    Attributes:
        type: Operand classification
        value: Raw value (string or number)
        register: Register name if register operand
        immediate: Parsed immediate value if immediate
        memory: Parsed memory reference if memory operand
        token: Original token(s)
    """
    type: OperandType
    value: Any
    register: Optional[str] = None
    immediate: Optional[int] = None
    memory: Optional[MemoryRef] = None
    token: Optional[Token] = None
    
    @property
    def is_register(self) -> bool:
        return self.type == OperandType.REGISTER
    
    @property
    def is_immediate(self) -> bool:
        return self.type == OperandType.IMMEDIATE
    
    @property
    def is_memory(self) -> bool:
        return self.type in (
            OperandType.MEMORY_DIRECT, OperandType.MEMORY_INDIRECT,
            OperandType.MEMORY_INDEXED, OperandType.MEMORY_BASED,
            OperandType.MEMORY_BASED_INDEXED, OperandType.MEMORY_LABEL
        )


class StatementType(Enum):
    """Statement type classification."""
    INSTRUCTION = auto()   # CPU instruction (MOV, ADD, etc.)
    DIRECTIVE = auto()     # Assembler directive (DB, ORG, etc.)
    LABEL_ONLY = auto()    # Just a label on a line
    EMPTY = auto()         # Empty or comment-only line
    DATA = auto()          # Data definition (DB, DW, etc.)
    EQUATE = auto()        # EQU or = definition


@dataclass
class Statement:
    """
    Parsed assembly statement.
    
    Attributes:
        type: Statement classification
        label: Label if present (without colon)
        mnemonic: Instruction mnemonic or directive name
        operands: List of parsed operands
        raw_operands: Original operand strings
        line: Source line number
        location: Full source location
        raw_text: Original line text
        comment: Comment text if present
        prefix: Instruction prefix (REP, LOCK, etc.)
        segment_override: Segment override for instruction
    """
    type: StatementType
    label: Optional[str] = None
    mnemonic: Optional[str] = None
    operands: List[Operand] = field(default_factory=list)
    raw_operands: List[str] = field(default_factory=list)
    line: int = 0
    location: Optional[SourceLocation] = None
    raw_text: str = ""
    comment: Optional[str] = None
    prefix: Optional[str] = None
    segment_override: Optional[str] = None


@dataclass
class ParseResult:
    """
    Result of parsing.
    
    Attributes:
        statements: List of parsed statements
        errors: List of parse errors
        labels: Set of defined labels
        equates: Dictionary of EQU/= definitions
    """
    statements: List[Statement]
    errors: List[Dict[str, Any]]
    labels: set
    equates: Dict[str, Any]


class Parser:
    """
    Assembly language parser.
    
    Transforms token streams into structured Statement objects.
    """
    
    # 8086 registers
    REGISTERS_8BIT = {'AL', 'AH', 'BL', 'BH', 'CL', 'CH', 'DL', 'DH'}
    REGISTERS_16BIT = {'AX', 'BX', 'CX', 'DX', 'SP', 'BP', 'SI', 'DI'}
    REGISTERS_SEGMENT = {'CS', 'DS', 'ES', 'SS'}
    
    # 8085 registers
    REGISTERS_8085 = {'A', 'B', 'C', 'D', 'E', 'H', 'L', 'M', 'PSW'}
    
    # Base and index registers for memory addressing
    BASE_REGISTERS = {'BX', 'BP'}
    INDEX_REGISTERS = {'SI', 'DI'}
    
    # Instruction prefixes
    PREFIXES = {'REP', 'REPE', 'REPZ', 'REPNE', 'REPNZ', 'LOCK', 'SEGMENT'}
    
    # Size override keywords
    SIZE_OVERRIDES = {'BYTE', 'WORD', 'DWORD', 'QWORD', 'TBYTE', 'PTR'}
    
    # Data definition directives
    DATA_DIRECTIVES = {'DB', 'DW', 'DD', 'DQ', 'DT', 'RESB', 'RESW', 'RESD', 'RESQ'}
    
    # Segment/section directives
    SEGMENT_DIRECTIVES = {
        '.MODEL', '.DATA', '.CODE', '.STACK', '.BSS',
        'SEGMENT', 'ENDS', 'ASSUME',
        'SECTION', 'BITS',
        '.TEXT', '.RODATA'
    }
    
    # Procedure directives
    PROC_DIRECTIVES = {'PROC', 'ENDP', 'END'}
    
    # Memory reference pattern
    MEM_REF_PATTERN = re.compile(r'''
        (?:(?P<segment>[CDES]S)\s*:\s*)?     # Optional segment override
        (?:(?P<size>BYTE|WORD|DWORD)\s+PTR\s+)?  # Optional size override
        \[
            (?P<contents>[^\]]+)
        \]
    ''', re.VERBOSE | re.IGNORECASE)
    
    def __init__(self, architecture: str = "8086"):
        """
        Initialize parser.
        
        Args:
            architecture: Target architecture ("8085" or "8086")
        """
        self.architecture = architecture.upper()
        self.lexer = Lexer(architecture)
        self.errors: List[Dict[str, Any]] = []
        self.labels: set = set()
        self.equates: Dict[str, Any] = {}
        
    def parse(
        self, 
        source: str, 
        filename: str = "<source>"
    ) -> ParseResult:
        """
        Parse assembly source code.
        
        Args:
            source: Assembly source code or preprocessed lines
            filename: Source filename for error reporting
            
        Returns:
            ParseResult with statements and metadata
        """
        self.errors = []
        self.labels = set()
        self.equates = {}
        
        statements: List[Statement] = []
        
        # Tokenize if source is a string
        lines = source.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            if not line.strip():
                # Empty line
                statements.append(Statement(
                    type=StatementType.EMPTY,
                    line=line_num,
                    raw_text=line
                ))
                continue
            
            # Skip comment-only lines
            stripped = line.strip()
            if stripped.startswith(';') or stripped.startswith('//'):
                statements.append(Statement(
                    type=StatementType.EMPTY,
                    line=line_num,
                    raw_text=line,
                    comment=stripped[1:].strip()
                ))
                continue
            
            # Tokenize line
            tokens = self.lexer.tokenize_line(line, line_num)
            
            # Parse tokens into statement
            stmt = self._parse_statement(tokens, line_num, line)
            if stmt:
                statements.append(stmt)
        
        return ParseResult(
            statements=statements,
            errors=self.errors.copy(),
            labels=self.labels.copy(),
            equates=self.equates.copy()
        )
    
    def parse_preprocessed(
        self, 
        lines: List[PreprocessedLine]
    ) -> ParseResult:
        """
        Parse preprocessed lines.
        
        Args:
            lines: List of PreprocessedLine objects
            
        Returns:
            ParseResult with statements and metadata
        """
        self.errors = []
        self.labels = set()
        self.equates = {}
        
        statements: List[Statement] = []
        
        for pline in lines:
            if pline.is_empty:
                statements.append(Statement(
                    type=StatementType.EMPTY,
                    line=pline.location.line,
                    location=pline.location,
                    raw_text=pline.text
                ))
                continue
            
            # Tokenize
            tokens = self.lexer.tokenize_line(pline.text, pline.location.line)
            
            # Parse
            stmt = self._parse_statement(tokens, pline.location.line, pline.text)
            if stmt:
                stmt.location = pline.location
                statements.append(stmt)
        
        return ParseResult(
            statements=statements,
            errors=self.errors.copy(),
            labels=self.labels.copy(),
            equates=self.equates.copy()
        )
    
    def _parse_statement(
        self, 
        tokens: List[Token], 
        line_num: int,
        raw_text: str
    ) -> Optional[Statement]:
        """
        Parse a list of tokens into a Statement.
        
        Args:
            tokens: List of tokens
            line_num: Line number
            raw_text: Original line text
            
        Returns:
            Statement object or None
        """
        # Filter out newlines, EOF, comments
        comment = None
        filtered: List[Token] = []
        for t in tokens:
            if t.type == TokenType.COMMENT:
                comment = t.value.lstrip(';').lstrip('/').strip()
            elif t.type not in (TokenType.NEWLINE, TokenType.EOF):
                filtered.append(t)
        
        if not filtered:
            return Statement(
                type=StatementType.EMPTY,
                line=line_num,
                raw_text=raw_text,
                comment=comment
            )
        
        # Initialize statement
        label = None
        mnemonic = None
        prefix = None
        segment_override = None
        operands: List[Operand] = []
        raw_operands: List[str] = []
        
        idx = 0
        
        # Check for label
        if len(filtered) > 1 and filtered[1].type == TokenType.COLON:
            label = filtered[0].value
            self.labels.add(label.upper())
            idx = 2
        elif filtered[0].type == TokenType.IDENTIFIER and filtered[0].value.endswith(':'):
            # Label without space before colon
            label = filtered[0].value.rstrip(':')
            self.labels.add(label.upper())
            idx = 1
        
        if idx >= len(filtered):
            # Label-only line
            return Statement(
                type=StatementType.LABEL_ONLY,
                label=label,
                line=line_num,
                raw_text=raw_text,
                comment=comment
            )
        
        # Check for prefix
        if filtered[idx].type == TokenType.MNEMONIC and filtered[idx].norm in self.PREFIXES:
            prefix = filtered[idx].norm
            idx += 1
            if idx >= len(filtered):
                return Statement(
                    type=StatementType.INSTRUCTION,
                    label=label,
                    mnemonic=prefix,
                    line=line_num,
                    raw_text=raw_text,
                    comment=comment
                )
        
        # Check for segment override at instruction level
        if idx < len(filtered) - 1:
            tok = filtered[idx]
            if tok.type == TokenType.REGISTER and tok.norm in self.REGISTERS_SEGMENT:
                if idx + 1 < len(filtered) and filtered[idx + 1].type == TokenType.COLON:
                    segment_override = tok.norm
                    idx += 2
        
        # Get mnemonic or directive
        if idx >= len(filtered):
            return None
        
        tok = filtered[idx]
        
        # Handle IDENTIFIER followed by DIRECTIVE (e.g., "MSG DB 'hello'")
        # This is a data definition with an implicit label
        if tok.type == TokenType.IDENTIFIER and idx + 1 < len(filtered):
            next_tok = filtered[idx + 1]
            
            # Check for EQU definition first: LABEL EQU value
            if next_tok.norm == 'EQU' or next_tok.value == '=':
                # This is: IDENTIFIER EQU value
                label = tok.value
                idx += 2  # Skip IDENTIFIER and EQU/=
                # Rest is the value
                value_tokens = filtered[idx:]
                if value_tokens:
                    value_str = ' '.join(t.value for t in value_tokens 
                                          if t.type not in (TokenType.COMMENT,))
                    self.equates[label.upper()] = value_str
                    return Statement(
                        type=StatementType.EQUATE,
                        label=label,
                        mnemonic='EQU',
                        raw_operands=[value_str],
                        line=line_num,
                        raw_text=raw_text,
                        comment=comment
                    )
            
            # Check if next token is a data directive
            elif next_tok.type == TokenType.DIRECTIVE:
                if next_tok.norm in self.DATA_DIRECTIVES or next_tok.norm.lstrip('.') in self.DATA_DIRECTIVES:
                    # Implicit label for data definition
                    label = tok.value
                    self.labels.add(label.upper())
                    idx += 1
                    tok = filtered[idx]
                # Check for PROC/ENDP
                elif next_tok.norm in self.PROC_DIRECTIVES:
                    label = tok.value
                    if next_tok.norm == 'PROC':
                        self.labels.add(label.upper())
                    idx += 1
                    tok = filtered[idx]
        
        if tok.type == TokenType.MNEMONIC:
            mnemonic = tok.norm
            stmt_type = StatementType.INSTRUCTION
        elif tok.type == TokenType.DIRECTIVE:
            mnemonic = tok.norm
            if mnemonic in self.DATA_DIRECTIVES or mnemonic.lstrip('.') in self.DATA_DIRECTIVES:
                stmt_type = StatementType.DATA
            else:
                stmt_type = StatementType.DIRECTIVE
        elif tok.type == TokenType.IDENTIFIER:
            # Unknown identifier used as instruction (could be macro)
            mnemonic = tok.norm
            stmt_type = StatementType.INSTRUCTION
        else:
            self._error(line_num, tok.col, f"Expected instruction or directive, got {tok.type.name}")
            return None
        
        idx += 1
        
        # Parse operands
        operand_tokens: List[List[Token]] = []
        current_operand: List[Token] = []
        
        while idx < len(filtered):
            tok = filtered[idx]
            if tok.type == TokenType.COMMA:
                if current_operand:
                    operand_tokens.append(current_operand)
                current_operand = []
            elif tok.type != TokenType.COMMENT:
                current_operand.append(tok)
            idx += 1
        
        if current_operand:
            operand_tokens.append(current_operand)
        
        # Parse each operand
        for op_toks in operand_tokens:
            operand = self._parse_operand(op_toks)
            if operand:
                operands.append(operand)
                raw_operands.append(' '.join(t.value for t in op_toks))
        
        return Statement(
            type=stmt_type,
            label=label,
            mnemonic=mnemonic,
            operands=operands,
            raw_operands=raw_operands,
            line=line_num,
            raw_text=raw_text,
            comment=comment,
            prefix=prefix,
            segment_override=segment_override
        )
    
    def _parse_operand(self, tokens: List[Token]) -> Optional[Operand]:
        """
        Parse operand tokens into an Operand object.
        
        Args:
            tokens: List of tokens for this operand
            
        Returns:
            Operand object or None
        """
        if not tokens:
            return None
        
        # Handle single token operands
        if len(tokens) == 1:
            tok = tokens[0]
            
            if tok.type == TokenType.REGISTER:
                return Operand(
                    type=OperandType.REGISTER,
                    value=tok.norm,
                    register=tok.norm,
                    token=tok
                )
            
            if tok.type == TokenType.IMMEDIATE:
                try:
                    val = parse_immediate(tok.value)
                    return Operand(
                        type=OperandType.IMMEDIATE,
                        value=val,
                        immediate=val,
                        token=tok
                    )
                except ValueError:
                    pass
            
            if tok.type == TokenType.MEMORY_REF:
                return self._parse_memory_operand(tok.value, tok)
            
            if tok.type == TokenType.STRING_LIT:
                return Operand(
                    type=OperandType.STRING,
                    value=tok.value,
                    token=tok
                )
            
            if tok.type == TokenType.IDENTIFIER:
                return Operand(
                    type=OperandType.LABEL,
                    value=tok.norm,
                    token=tok
                )
        
        # Handle multi-token operands
        # Check for size override: BYTE PTR [...]
        idx = 0
        size_override = None
        segment_override = None
        
        # Check for segment override: CS:...
        if len(tokens) >= 2 and tokens[0].type == TokenType.REGISTER:
            if tokens[0].norm in self.REGISTERS_SEGMENT:
                if len(tokens) > 1 and tokens[1].type == TokenType.COLON:
                    segment_override = tokens[0].norm
                    idx = 2
        
        # Check for size override
        while idx < len(tokens):
            tok = tokens[idx]
            if tok.norm in self.SIZE_OVERRIDES:
                if tok.norm in ('BYTE', 'WORD', 'DWORD', 'QWORD', 'TBYTE'):
                    size_override = tok.norm
                idx += 1
            else:
                break
        
        # Remaining tokens
        remaining = tokens[idx:]
        
        if not remaining:
            return None
        
        # Check for OFFSET label
        if remaining[0].norm == 'OFFSET' and len(remaining) > 1:
            label_tok = remaining[1]
            return Operand(
                type=OperandType.EXPRESSION,
                value=f"OFFSET {label_tok.value}",
                token=label_tok
            )
        
        # Check for memory reference
        if remaining[0].type == TokenType.MEMORY_REF:
            operand = self._parse_memory_operand(remaining[0].value, remaining[0])
            if operand and operand.memory:
                operand.memory.size_override = size_override
                operand.memory.segment_override = segment_override
            return operand
        
        # Check for [expr] constructed from tokens
        if remaining[0].type == TokenType.OPERATOR and remaining[0].value == '[':
            # Find matching ]
            depth = 1
            end_idx = 1
            while end_idx < len(remaining) and depth > 0:
                if remaining[end_idx].value == '[':
                    depth += 1
                elif remaining[end_idx].value == ']':
                    depth -= 1
                end_idx += 1
            
            if depth == 0:
                mem_tokens = remaining[1:end_idx-1]
                mem_str = '[' + ' '.join(t.value for t in mem_tokens) + ']'
                operand = self._parse_memory_operand(mem_str, remaining[0])
                if operand and operand.memory:
                    operand.memory.size_override = size_override
                    operand.memory.segment_override = segment_override
                return operand
        
        # Check for expression (label + offset, etc.)
        if len(remaining) > 1:
            expr = ' '.join(t.value for t in remaining)
            return Operand(
                type=OperandType.EXPRESSION,
                value=expr,
                token=remaining[0]
            )
        
        # Single remaining token
        tok = remaining[0]
        if tok.type == TokenType.REGISTER:
            return Operand(
                type=OperandType.REGISTER,
                value=tok.norm,
                register=tok.norm,
                token=tok
            )
        
        if tok.type == TokenType.IMMEDIATE:
            try:
                val = parse_immediate(tok.value)
                return Operand(
                    type=OperandType.IMMEDIATE,
                    value=val,
                    immediate=val,
                    token=tok
                )
            except ValueError:
                pass
        
        if tok.type == TokenType.IDENTIFIER:
            return Operand(
                type=OperandType.LABEL,
                value=tok.norm,
                token=tok
            )
        
        return Operand(
            type=OperandType.EXPRESSION,
            value=' '.join(t.value for t in tokens),
            token=tokens[0]
        )
    
    def _parse_memory_operand(
        self, 
        mem_str: str, 
        token: Token
    ) -> Optional[Operand]:
        """
        Parse a memory reference string into an Operand.
        
        Handles:
        - [BX], [SI] - register indirect
        - [BX+SI], [BP+DI] - indexed
        - [BX+4], [BP-8] - based with displacement
        - [BX+SI+4] - based indexed with displacement
        - [1234h] - direct address
        - [label] - symbolic address
        
        Args:
            mem_str: Memory reference string (e.g., "[BX+SI+4]")
            token: Original token
            
        Returns:
            Operand with parsed memory reference
        """
        # Extract contents from brackets
        match = self.MEM_REF_PATTERN.match(mem_str)
        if match:
            segment = match.group('segment')
            size = match.group('size')
            contents = match.group('contents').strip()
        else:
            # Simple extraction
            segment = None
            size = None
            if mem_str.startswith('[') and mem_str.endswith(']'):
                contents = mem_str[1:-1].strip()
            elif mem_str.startswith('(') and mem_str.endswith(')'):
                contents = mem_str[1:-1].strip()
            else:
                contents = mem_str
        
        mem_ref = MemoryRef(raw=mem_str, segment_override=segment, size_override=size)
        
        # Parse contents
        # Split by + and -, keeping the operators
        parts = re.split(r'(\+|-)', contents)
        
        base = None
        index = None
        displacement_parts: List[str] = []
        current_sign = 1
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            if part == '+':
                current_sign = 1
                continue
            elif part == '-':
                current_sign = -1
                continue
            
            upper = part.upper()
            
            # Check for base register
            if upper in self.BASE_REGISTERS:
                base = upper
            # Check for index register
            elif upper in self.INDEX_REGISTERS:
                index = upper
            # Check for other registers (8085 uses different scheme)
            elif upper in self.REGISTERS_16BIT or upper in self.REGISTERS_8085:
                if base is None:
                    base = upper
                else:
                    index = upper
            # Check for numeric displacement
            else:
                # Try to parse as number
                try:
                    val = parse_immediate(part)
                    if current_sign == -1:
                        val = -val
                    displacement_parts.append(str(val))
                except ValueError:
                    # Could be a label or expression
                    if current_sign == -1:
                        displacement_parts.append(f"-{part}")
                    else:
                        displacement_parts.append(part)
        
        mem_ref.base = base
        mem_ref.index = index
        
        # Combine displacement parts
        if displacement_parts:
            try:
                # Try to evaluate as number
                total = sum(int(p) for p in displacement_parts if p.lstrip('-').isdigit())
                non_numeric = [p for p in displacement_parts if not p.lstrip('-').isdigit()]
                if non_numeric:
                    mem_ref.displacement = ' + '.join(non_numeric)
                    if total != 0:
                        mem_ref.displacement += f" + {total}"
                else:
                    mem_ref.displacement = total
            except ValueError:
                mem_ref.displacement = ' + '.join(displacement_parts)
        
        # Determine operand type
        if base is None and index is None:
            if mem_ref.displacement is not None:
                if isinstance(mem_ref.displacement, int):
                    op_type = OperandType.MEMORY_DIRECT
                else:
                    op_type = OperandType.MEMORY_LABEL
            else:
                op_type = OperandType.MEMORY_DIRECT
        elif base is not None and index is not None:
            if mem_ref.displacement is not None:
                op_type = OperandType.MEMORY_BASED_INDEXED
            else:
                op_type = OperandType.MEMORY_INDEXED
        elif base is not None or index is not None:
            if mem_ref.displacement is not None:
                op_type = OperandType.MEMORY_BASED
            else:
                op_type = OperandType.MEMORY_INDIRECT
        else:
            op_type = OperandType.MEMORY_DIRECT
        
        return Operand(
            type=op_type,
            value=mem_str,
            memory=mem_ref,
            token=token
        )
    
    def _error(self, line: int, col: int, message: str) -> None:
        """Record a parse error."""
        self.errors.append({
            'phase': 'PARSER',
            'code': 'E1xx',
            'line': line,
            'col': col,
            'message': message
        })
    
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Get list of errors."""
        return self.errors.copy()


def parse(
    source: str, 
    architecture: str = "8086",
    filename: str = "<source>"
) -> ParseResult:
    """
    Convenience function to parse assembly source.
    
    Args:
        source: Assembly source code
        architecture: Target architecture
        filename: Source filename
        
    Returns:
        ParseResult
    """
    parser = Parser(architecture)
    return parser.parse(source, filename)


if __name__ == '__main__':
    # Test the parser
    test_code = '''
; Test program
.MODEL SMALL
.STACK 100H

BUFFER_SIZE EQU 256

.DATA
    MSG DB 'Hello, World!$'
    COUNT DW 0
    
.CODE
START:
    MOV AX, @DATA       ; Load data segment
    MOV DS, AX
    
    ; Memory addressing modes
    MOV AX, [BX]        ; Register indirect
    MOV AX, [BX+SI]     ; Based indexed
    MOV AX, [BX+4]      ; Based with displacement
    MOV AX, [BX+SI+8]   ; Based indexed with displacement
    MOV AL, BYTE PTR [SI]  ; Size override
    MOV AX, ES:[BX]     ; Segment override
    
    ; Immediate and register
    MOV AX, 1234H
    MOV BX, AX
    ADD CX, 10
    
    ; Labels
    JMP START
    CALL SUBROUTINE
    
SUBROUTINE PROC
    PUSH AX
    POP AX
    RET
SUBROUTINE ENDP

END START
'''
    
    result = parse(test_code)
    
    print("=== Parsed Statements ===")
    for stmt in result.statements:
        if stmt.type == StatementType.EMPTY:
            continue
        
        label_str = f"{stmt.label}: " if stmt.label else ""
        mnem_str = stmt.mnemonic or ""
        ops_str = ', '.join(stmt.raw_operands) if stmt.raw_operands else ""
        
        print(f"L{stmt.line:3d} [{stmt.type.name:12s}] {label_str}{mnem_str} {ops_str}")
        
        # Show operand details for instructions
        if stmt.type == StatementType.INSTRUCTION and stmt.operands:
            for i, op in enumerate(stmt.operands):
                print(f"        Op{i+1}: {op.type.name}", end="")
                if op.register:
                    print(f" reg={op.register}", end="")
                if op.immediate is not None:
                    print(f" imm={op.immediate}", end="")
                if op.memory:
                    m = op.memory
                    print(f" mem(base={m.base}, idx={m.index}, disp={m.displacement})", end="")
                print()
    
    print(f"\n=== Labels ===")
    print(f"  {result.labels}")
    
    print(f"\n=== Equates ===")
    for name, value in result.equates.items():
        print(f"  {name} = {value}")
    
    if result.errors:
        print(f"\n=== Errors ===")
        for err in result.errors:
            print(f"  Line {err['line']}: {err['message']}")
    else:
        print(f"\n✅ No parse errors")
