#!/usr/bin/env python3
"""
Assembler Engine - Two-Pass Assembly Orchestrator

This module orchestrates the entire assembly process:
1. Preprocessing (macros, includes, conditionals)
2. Lexical analysis (tokenization)
3. Parsing (AST generation)
4. Analysis (syntax + semantic validation)
5. Pass 1: Symbol table construction + size calculation
6. Pass 2: Code generation with address resolution
7. Output generation (binary, hex, listing)
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from enum import Enum, auto

from lexer import Lexer, Token, TokenType
from preprocessor import Preprocessor, PreprocessorResult
from parser import Parser, ParseResult, Statement, StatementType, Operand, OperandType
from syntax_analyzer import SyntaxAnalyzer
from semantic_analyzer import SemanticAnalyzer
from emitter import Emitter


class AssemblyPhase(Enum):
    """Phases of assembly for error reporting."""
    PREPROCESS = auto()
    LEXING = auto()
    PARSING = auto()
    ANALYSIS = auto()
    PASS1 = auto()
    PASS2 = auto()
    EMIT = auto()


@dataclass
class AssemblyError:
    """Assembly error with location info."""
    phase: AssemblyPhase
    code: str
    message: str
    line: int
    column: int = 0
    source_line: str = ""
    severity: str = "error"


@dataclass
class CodeSection:
    """A code or data section."""
    name: str
    start_address: int
    data: bytearray
    alignment: int = 1


@dataclass
class IRInstruction:
    """Intermediate representation for an instruction."""
    address: int
    statement: Statement
    size: int
    opcode: Optional[bytes] = None
    variant: Optional[Dict[str, Any]] = None
    needs_relocation: bool = False
    relocation_symbol: Optional[str] = None


@dataclass
class AssemblyResult:
    """Result of assembly process."""
    success: bool
    output: Optional[bytes] = None
    errors: List[AssemblyError] = field(default_factory=list)
    warnings: List[AssemblyError] = field(default_factory=list)
    symbols: Dict[str, int] = field(default_factory=dict)
    listing: str = ""
    hex_output: str = ""
    sections: List[CodeSection] = field(default_factory=list)


class ISA:
    """
    Instruction Set Architecture loaded from JSON.
    Provides data-driven opcode lookup without hardcoded dispatch.
    """
    
    def __init__(self, isa_path: Union[str, Path, dict]):
        if isinstance(isa_path, dict):
            self.data = isa_path
        else:
            with open(isa_path) as f:
                self.data = json.load(f)
        
        self.name = self.data.get('name', self.data.get('architecture', 'Unknown'))
        self.endianness = self.data.get('endianness', 'little')
        self.directives = set(self.data.get('directives', []))
        
        # Handle instructions - can be list or dict
        raw_instructions = self.data.get('instructions', [])
        if isinstance(raw_instructions, list):
            # Convert list to dict indexed by mnemonic
            self.instructions = {}
            for instr in raw_instructions:
                mnemonic = instr.get('mnemonic', '').upper()
                if mnemonic:
                    self.instructions[mnemonic] = instr
        else:
            self.instructions = raw_instructions
        
        # Handle registers - can be list or dict
        raw_registers = self.data.get('registers', {})
        if isinstance(raw_registers, list):
            self.registers = {r.get('name', ''): r for r in raw_registers if r.get('name')}
        else:
            self.registers = raw_registers
        
        # Also load register_codes if available
        self.register_codes = self.data.get('register_codes', {})
        
        # Build lookup tables
        self._build_register_lookup()
    
    def _build_register_lookup(self) -> None:
        """Build fast register code lookup."""
        self._reg_codes: Dict[str, int] = {}
        self._reg_sizes: Dict[str, int] = {}
        
        # First use register_codes if available
        for name, code in self.register_codes.items():
            upper = name.upper()
            self._reg_codes[upper] = code
            # Determine size from register name
            if upper in ('AL', 'AH', 'BL', 'BH', 'CL', 'CH', 'DL', 'DH'):
                self._reg_sizes[upper] = 8
            else:
                self._reg_sizes[upper] = 16
        
        # Then add from registers dict
        for name, info in self.registers.items():
            upper = name.upper()
            if isinstance(info, dict):
                self._reg_codes[upper] = info.get('code', self._reg_codes.get(upper, 0))
                self._reg_sizes[upper] = info.get('size', self._reg_sizes.get(upper, 16))
            elif isinstance(info, int):
                self._reg_codes[upper] = info
                if upper not in self._reg_sizes:
                    self._reg_sizes[upper] = 16
    
    def get_instruction(self, mnemonic: str) -> Optional[Dict]:
        """Get instruction definition."""
        return self.instructions.get(mnemonic.upper())
    
    def get_register_code(self, name: str) -> int:
        """Get register encoding."""
        return self._reg_codes.get(name.upper(), 0)
    
    def get_register_size(self, name: str) -> int:
        """Get register size in bits."""
        return self._reg_sizes.get(name.upper(), 16)
    
    def is_register(self, name: str) -> bool:
        """Check if name is a register."""
        return name.upper() in self._reg_codes
    
    def match_variant(
        self, 
        mnemonic: str, 
        operand_types: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Find instruction variant matching operand types.
        """
        instr = self.get_instruction(mnemonic)
        if not instr:
            return None
        
        variants = instr.get('variants', [])
        
        for variant in variants:
            expected = variant.get('operands', [])
            if len(expected) != len(operand_types):
                continue
            
            if self._operands_match(operand_types, expected):
                return variant
        
        # Try relaxed matching for memory/label interchangeability
        for variant in variants:
            expected = variant.get('operands', [])
            if len(expected) != len(operand_types):
                continue
            
            if self._operands_match_relaxed(operand_types, expected):
                return variant
        
        return None
    
    def _operands_match(
        self, 
        actual: List[str], 
        expected: List[str]
    ) -> bool:
        """Strict operand type matching."""
        for act, exp in zip(actual, expected):
            if not self._type_matches(act, exp):
                return False
        return True
    
    def _operands_match_relaxed(
        self, 
        actual: List[str], 
        expected: List[str]
    ) -> bool:
        """Relaxed matching - labels can be memory, etc."""
        for act, exp in zip(actual, expected):
            if not self._type_matches_relaxed(act, exp):
                return False
        return True
    
    def _type_matches(self, actual: str, expected: str) -> bool:
        """Check if actual type matches expected specification."""
        act = actual.upper()
        exp = expected.upper()
        
        # Direct match
        if act == exp:
            return True
        
        # Register groups
        if exp == 'REG' and act in ('REG8', 'REG16', 'R8', 'R16'):
            return True
        if exp in ('R/M8', 'RM8') and act in ('REG8', 'R8', 'MEM', 'MEM8'):
            return True
        if exp in ('R/M16', 'RM16') and act in ('REG16', 'R16', 'MEM', 'MEM16'):
            return True
        if exp in ('R/M', 'RM') and act in ('REG', 'REG8', 'REG16', 'MEM'):
            return True
        
        # Immediate groups
        if exp == 'IMM' and act in ('IMM8', 'IMM16', 'I8', 'I16'):
            return True
        
        return False
    
    def _type_matches_relaxed(self, actual: str, expected: str) -> bool:
        """Relaxed type matching."""
        if self._type_matches(actual, expected):
            return True
        
        act = actual.upper()
        exp = expected.upper()
        
        # Labels can match memory references
        if act == 'LABEL' and exp in ('MEM', 'MEM8', 'MEM16', 'ADDR', 'R/M', 'R/M8', 'R/M16'):
            return True
        
        # Labels can match addresses
        if act == 'LABEL' and exp in ('REL8', 'REL16', 'ADDR', 'PTR'):
            return True
        
        return False


class SymbolTable:
    """
    Symbol table for label/variable tracking.
    Supports forward references and multiple passes.
    """
    
    def __init__(self):
        self.symbols: Dict[str, int] = {}
        self.symbol_types: Dict[str, str] = {}
        self.forward_refs: Set[str] = set()
        self.references: Dict[str, List[int]] = {}
    
    def define(
        self, 
        name: str, 
        address: int, 
        sym_type: str = "label"
    ) -> bool:
        """Define a symbol. Returns False if already defined."""
        upper = name.upper()
        if upper in self.symbols:
            return False
        
        self.symbols[upper] = address
        self.symbol_types[upper] = sym_type
        self.forward_refs.discard(upper)
        return True
    
    def resolve(self, name: str) -> Optional[int]:
        """Resolve symbol to address."""
        return self.symbols.get(name.upper())
    
    def is_defined(self, name: str) -> bool:
        """Check if symbol is defined."""
        return name.upper() in self.symbols
    
    def add_reference(self, name: str, address: int) -> None:
        """Track a reference to a symbol."""
        upper = name.upper()
        if upper not in self.references:
            self.references[upper] = []
        self.references[upper].append(address)
        
        if not self.is_defined(upper):
            self.forward_refs.add(upper)
    
    def get_undefined(self) -> Set[str]:
        """Get undefined symbols."""
        return {s for s in self.forward_refs if not self.is_defined(s)}
    
    def clear(self) -> None:
        """Clear the symbol table."""
        self.symbols.clear()
        self.symbol_types.clear()
        self.forward_refs.clear()
        self.references.clear()
    
    def dump(self) -> str:
        """Get formatted symbol table dump."""
        lines = ["Symbol Table:"]
        lines.append("-" * 40)
        lines.append(f"{'Symbol':<20} {'Address':>10} {'Type':<10}")
        lines.append("-" * 40)
        
        for name in sorted(self.symbols.keys()):
            addr = self.symbols[name]
            stype = self.symbol_types.get(name, "unknown")
            lines.append(f"{name:<20} {addr:>10X} {stype:<10}")
        
        return "\n".join(lines)


class AssemblerEngine:
    """
    Two-pass assembler engine.
    
    Pass 1: Build symbol table, calculate instruction sizes
    Pass 2: Generate machine code with resolved addresses
    """
    
    def __init__(
        self, 
        architecture: str = "8086",
        isa_path: Optional[Union[str, Path]] = None
    ):
        self.architecture = architecture.upper()
        
        # Load ISA
        if isa_path:
            self.isa = ISA(isa_path)
        else:
            default_path = Path(__file__).parent / f"isa_{architecture.lower()}.json"
            if default_path.exists():
                self.isa = ISA(default_path)
            else:
                raise FileNotFoundError(f"ISA file not found: {default_path}")
        
        # Initialize components
        self.preprocessor = Preprocessor()
        self.lexer = Lexer(architecture)
        self.parser = Parser(architecture)
        self.syntax_analyzer = SyntaxAnalyzer(architecture)
        self.semantic_analyzer = SemanticAnalyzer()
        self.symbol_table = SymbolTable()
        self.emitter = Emitter(self.isa.endianness)
        
        # State
        self.errors: List[AssemblyError] = []
        self.warnings: List[AssemblyError] = []
        self.ir: List[IRInstruction] = []
        self.origin = 0
        self.current_section = "CODE"
    
    def assemble(
        self, 
        source: str, 
        origin: int = 0,
        dialect: Optional[str] = None
    ) -> AssemblyResult:
        """
        Assemble source code to machine code.
        
        Args:
            source: Assembly source code
            origin: Base address
            dialect: Force specific dialect (NASM, MASM, etc.)
            
        Returns:
            AssemblyResult with output or errors
        """
        self.origin = origin
        self.errors = []
        self.warnings = []
        self.ir = []
        self.symbol_table.clear()
        self.emitter.reset(origin)
        
        # Phase 1: Preprocess
        preprocessed_source = self._preprocess(source, dialect)
        if not preprocessed_source:
            return self._make_result(False)
        
        # Phase 2: Lex
        tokens = self._lex(preprocessed_source)
        if tokens is None:
            return self._make_result(False)
        
        # Phase 3: Parse
        parse_result = self._parse(tokens, preprocessed_source)
        if not parse_result:
            return self._make_result(False)
        
        # Phase 4: Analyze
        if not self._analyze(parse_result, preprocessed_source):
            return self._make_result(False)
        
        # Phase 5: Pass 1 - Symbol table & sizes
        if not self._pass1(parse_result.statements):
            return self._make_result(False)
        
        # Check for undefined symbols
        undefined = self.symbol_table.get_undefined()
        for sym in undefined:
            self._error(
                AssemblyPhase.PASS1,
                "E040",
                f"Undefined symbol: '{sym}'",
                0
            )
        
        if self.errors:
            return self._make_result(False)
        
        # Phase 6: Pass 2 - Code generation
        if not self._pass2():
            return self._make_result(False)
        
        return self._make_result(True)
    
    def _preprocess(
        self, 
        source: str, 
        dialect: Optional[str]
    ) -> Optional[str]:
        """Run preprocessor, return preprocessed source string."""
        try:
            result = self.preprocessor.preprocess(source)
            
            # Handle errors from result
            for err in result.errors:
                if isinstance(err, dict):
                    msg = err.get('message', str(err))
                    line = err.get('line', 0)
                else:
                    msg = str(err)
                    line = 0
                self._error(AssemblyPhase.PREPROCESS, "E001", msg, line)
            
            if result.errors:
                return None
            
            # Reconstruct source from preprocessed lines
            output_lines = [line.text for line in result.lines]
            return '\n'.join(output_lines)
        except Exception as e:
            self._error(AssemblyPhase.PREPROCESS, "E000", str(e), 0)
            return None
    
    def _lex(self, source: str) -> Optional[List[Token]]:
        """Run lexer."""
        try:
            return self.lexer.tokenize(source)
        except Exception as e:
            self._error(AssemblyPhase.LEXING, "E010", str(e), 0)
            return None
    
    def _parse(
        self, 
        tokens: List[Token], 
        source: str
    ) -> Optional[ParseResult]:
        """Run parser."""
        try:
            result = self.parser.parse(source)
            
            for err in result.errors:
                self._error(
                    AssemblyPhase.PARSING, 
                    err.code,
                    err.message, 
                    err.line
                )
            
            if result.errors:
                return None
            
            return result
        except Exception as e:
            self._error(AssemblyPhase.PARSING, "E020", str(e), 0)
            return None
    
    def _analyze(self, parse_result: ParseResult, source: str) -> bool:
        """Run syntax and semantic analyzers."""
        # Syntax analysis
        syntax_result = self.syntax_analyzer.analyze(parse_result)
        
        for err in syntax_result.errors:
            self._error(
                AssemblyPhase.ANALYSIS,
                err.code,
                err.message,
                err.line
            )
        
        for warn in syntax_result.warnings:
            self._warning(
                AssemblyPhase.ANALYSIS,
                warn.code,
                warn.message,
                warn.line
            )
        
        # Semantic analysis
        semantic_result = self.semantic_analyzer.analyze(parse_result)
        
        for err in semantic_result.errors:
            self._error(
                AssemblyPhase.ANALYSIS,
                err.code,
                err.message,
                err.line
            )
        
        for warn in semantic_result.warnings:
            self._warning(
                AssemblyPhase.ANALYSIS,
                warn.code,
                warn.message,
                warn.line
            )
        
        return not bool([e for e in self.errors if e.phase == AssemblyPhase.ANALYSIS])
    
    def _pass1(self, statements: List[Statement]) -> bool:
        """
        Pass 1: Build symbol table and calculate instruction sizes.
        """
        lc = self.origin  # Location counter
        
        for stmt in statements:
            # Handle labels
            if stmt.label:
                if not self.symbol_table.define(stmt.label, lc):
                    self._error(
                        AssemblyPhase.PASS1,
                        "E041",
                        f"Duplicate label: '{stmt.label}'",
                        stmt.line
                    )
            
            # Calculate size and add to IR
            size = self._calculate_size(stmt)
            
            if stmt.type == StatementType.INSTRUCTION:
                variant = self._find_variant(stmt)
                
                ir_instr = IRInstruction(
                    address=lc,
                    statement=stmt,
                    size=size,
                    variant=variant
                )
                self.ir.append(ir_instr)
                lc += size
            
            elif stmt.type == StatementType.DIRECTIVE:
                self._handle_directive_pass1(stmt, lc)
                lc += size
            
            elif stmt.type == StatementType.DATA:
                lc += size
        
        return not self.errors
    
    def _pass2(self) -> bool:
        """
        Pass 2: Generate machine code with resolved addresses.
        """
        for ir_instr in self.ir:
            stmt = ir_instr.statement
            
            if stmt.type == StatementType.INSTRUCTION:
                self._generate_instruction(ir_instr)
            elif stmt.type == StatementType.DATA:
                self._generate_data(ir_instr)
        
        return not self.errors
    
    def _calculate_size(self, stmt: Statement) -> int:
        """Calculate byte size of a statement."""
        if stmt.type == StatementType.INSTRUCTION:
            return self._instruction_size(stmt)
        elif stmt.type == StatementType.DIRECTIVE:
            return self._directive_size(stmt)
        elif stmt.type == StatementType.DATA:
            return self._data_size(stmt)
        return 0
    
    def _instruction_size(self, stmt: Statement) -> int:
        """Calculate instruction byte size."""
        mnemonic = stmt.mnemonic.upper()
        instr = self.isa.get_instruction(mnemonic)
        
        if not instr:
            return 1  # Default for unknown
        
        # Find matching variant
        operand_types = self._get_operand_types(stmt)
        variant = self.isa.match_variant(mnemonic, operand_types)
        
        if variant:
            return variant.get('size', variant.get('bytes', 1))
        
        # Estimate from instruction properties
        base_size = 1  # Opcode
        
        # Add ModR/M if needed
        if stmt.operands:
            has_memory = any(op.is_memory for op in stmt.operands)
            has_register = any(op.is_register for op in stmt.operands)
            if has_memory or (has_register and len(stmt.operands) > 1):
                base_size += 1
        
        # Add immediate
        for op in stmt.operands:
            if op.is_immediate:
                val = op.immediate or 0
                if -128 <= val <= 255:
                    base_size += 1
                else:
                    base_size += 2
        
        return base_size
    
    def _directive_size(self, stmt: Statement) -> int:
        """Calculate directive size contribution."""
        directive = stmt.mnemonic.upper()
        
        # ORG changes location but no bytes
        if directive == 'ORG':
            return 0
        
        # Data definition directives
        if directive == 'DB':
            return sum(self._data_item_size(op, 1) for op in stmt.operands)
        if directive == 'DW':
            return sum(self._data_item_size(op, 2) for op in stmt.operands)
        if directive == 'DD':
            return sum(self._data_item_size(op, 4) for op in stmt.operands)
        
        # Reserve directives
        if directive in ('RESB', 'RES'):
            if stmt.operands and stmt.operands[0].is_immediate:
                return stmt.operands[0].immediate or 0
            return 1
        if directive == 'RESW':
            if stmt.operands and stmt.operands[0].is_immediate:
                return (stmt.operands[0].immediate or 0) * 2
            return 2
        
        return 0
    
    def _data_item_size(self, operand: Operand, unit_size: int) -> int:
        """Calculate size of a data item."""
        if operand.type == OperandType.STRING:
            # String literal
            return len(operand.raw.strip("'\""))
        if operand.type == OperandType.IMMEDIATE:
            return unit_size
        if operand.type == OperandType.EXPRESSION:
            # DUP expression: count DUP (value)
            raw = operand.raw.upper()
            if 'DUP' in raw:
                parts = raw.split('DUP')
                try:
                    count = int(parts[0].strip())
                    return count * unit_size
                except:
                    pass
            return unit_size
        return unit_size
    
    def _data_size(self, stmt: Statement) -> int:
        """Calculate data definition size."""
        return self._directive_size(stmt)
    
    def _find_variant(self, stmt: Statement) -> Optional[Dict[str, Any]]:
        """Find matching instruction variant."""
        operand_types = self._get_operand_types(stmt)
        return self.isa.match_variant(stmt.mnemonic, operand_types)
    
    def _get_operand_types(self, stmt: Statement) -> List[str]:
        """Get operand type strings for variant matching."""
        types = []
        
        for op in stmt.operands:
            if op.is_register:
                reg = op.register.upper()
                size = self.isa.get_register_size(reg)
                if size == 8:
                    types.append('REG8')
                else:
                    types.append('REG16')
            elif op.is_memory:
                types.append('MEM')
            elif op.is_immediate:
                val = op.immediate or 0
                if -128 <= val <= 255:
                    types.append('IMM8')
                else:
                    types.append('IMM16')
            elif op.type == OperandType.LABEL:
                types.append('LABEL')
            else:
                types.append('UNKNOWN')
        
        return types
    
    def _handle_directive_pass1(self, stmt: Statement, lc: int) -> None:
        """Handle directive in pass 1."""
        directive = stmt.mnemonic.upper()
        
        if directive == 'EQU':
            if stmt.label and stmt.operands:
                val = self._evaluate_expression(stmt.operands[0])
                self.symbol_table.define(stmt.label, val, "constant")
        
        elif directive == 'ORG':
            if stmt.operands:
                new_origin = self._evaluate_expression(stmt.operands[0])
                self.origin = new_origin
    
    def _evaluate_expression(self, operand: Operand) -> int:
        """Evaluate an expression operand."""
        if operand.is_immediate:
            return operand.immediate or 0
        
        if operand.type == OperandType.LABEL:
            addr = self.symbol_table.resolve(operand.raw)
            if addr is not None:
                return addr
        
        # Try parsing raw value
        raw = operand.raw.strip()
        
        # Hex
        if raw.lower().startswith('0x'):
            return int(raw, 16)
        if raw.lower().endswith('h'):
            return int(raw[:-1], 16)
        
        # Binary  
        if raw.lower().startswith('0b'):
            return int(raw, 2)
        
        # Decimal
        try:
            return int(raw)
        except:
            return 0
    
    def _generate_instruction(self, ir_instr: IRInstruction) -> None:
        """Generate machine code for an instruction."""
        stmt = ir_instr.statement
        variant = ir_instr.variant
        
        if not variant:
            # Try to find variant again with resolved symbols
            variant = self._find_variant(stmt)
        
        if not variant:
            self._error(
                AssemblyPhase.PASS2,
                "E050",
                f"No encoding for: {stmt.mnemonic} with given operands",
                stmt.line
            )
            return
        
        # Emit opcode byte(s)
        opcode = variant.get('opcode')
        if isinstance(opcode, int):
            self.emitter.emit_byte(opcode)
        elif isinstance(opcode, list):
            for b in opcode:
                self.emitter.emit_byte(b)
        elif isinstance(opcode, str):
            # Parse hex string
            opcode_int = int(opcode, 16)
            if opcode_int > 255:
                self.emitter.emit_byte((opcode_int >> 8) & 0xFF)
            self.emitter.emit_byte(opcode_int & 0xFF)
        
        # Emit ModR/M if needed
        if variant.get('modrm') or variant.get('has_modrm'):
            self._emit_modrm(stmt, variant)
        
        # Emit immediate
        if variant.get('imm_width') or variant.get('has_immediate'):
            self._emit_immediate(stmt, variant)
        
        # Emit displacement/relative
        if variant.get('rel_width') or variant.get('has_relative'):
            self._emit_relative(ir_instr, variant)
    
    def _emit_modrm(self, stmt: Statement, variant: Dict) -> None:
        """Emit ModR/M byte."""
        operands = stmt.operands
        
        if not operands:
            return
        
        # Determine mod, reg, rm fields
        mod = 0b11  # Register mode default
        reg = variant.get('modrm_ext', 0)  # Opcode extension or register
        rm = 0
        
        if len(operands) >= 2:
            # Two operands: reg field from first, rm from second
            if operands[0].is_register:
                reg = self.isa.get_register_code(operands[0].register)
            
            if operands[1].is_register:
                rm = self.isa.get_register_code(operands[1].register)
                mod = 0b11
            elif operands[1].is_memory:
                mod = 0b00  # Memory mode
                rm = 0b110  # Direct address mode
        elif len(operands) == 1:
            if operands[0].is_register:
                rm = self.isa.get_register_code(operands[0].register)
                mod = 0b11
        
        modrm = (mod << 6) | (reg << 3) | rm
        self.emitter.emit_byte(modrm)
    
    def _emit_immediate(self, stmt: Statement, variant: Dict) -> None:
        """Emit immediate value."""
        imm_width = variant.get('imm_width', 2)
        
        # Find immediate operand
        for op in stmt.operands:
            if op.is_immediate or op.type == OperandType.LABEL:
                value = self._evaluate_expression(op)
                
                if imm_width == 1:
                    self.emitter.emit_byte(value)
                elif imm_width == 2:
                    self.emitter.emit_word(value)
                else:
                    self.emitter.emit_dword(value)
                break
    
    def _emit_relative(self, ir_instr: IRInstruction, variant: Dict) -> None:
        """Emit relative address for jumps/calls."""
        stmt = ir_instr.statement
        rel_width = variant.get('rel_width', 1)
        
        if not stmt.operands:
            return
        
        target_op = stmt.operands[0]
        target_addr = self._evaluate_expression(target_op)
        
        # Calculate offset from instruction end
        instr_end = ir_instr.address + ir_instr.size
        offset = target_addr - instr_end
        
        if rel_width == 1:
            self.emitter.emit_signed_byte(offset)
        else:
            self.emitter.emit_signed_word(offset)
    
    def _generate_data(self, ir_instr: IRInstruction) -> None:
        """Generate data bytes."""
        stmt = ir_instr.statement
        directive = stmt.mnemonic.upper()
        
        unit_size = {'DB': 1, 'DW': 2, 'DD': 4}.get(directive, 1)
        
        for op in stmt.operands:
            if op.type == OperandType.STRING:
                # String literal
                text = op.raw.strip("'\"")
                self.emitter.emit_string(text)
            elif op.is_immediate:
                value = op.immediate or 0
                if unit_size == 1:
                    self.emitter.emit_byte(value)
                elif unit_size == 2:
                    self.emitter.emit_word(value)
                else:
                    self.emitter.emit_dword(value)
            elif op.type == OperandType.LABEL:
                value = self._evaluate_expression(op)
                if unit_size == 1:
                    self.emitter.emit_byte(value)
                elif unit_size == 2:
                    self.emitter.emit_word(value)
    
    def _error(
        self, 
        phase: AssemblyPhase, 
        code: str, 
        message: str, 
        line: int
    ) -> None:
        """Record an error."""
        self.errors.append(AssemblyError(
            phase=phase,
            code=code,
            message=message,
            line=line
        ))
    
    def _warning(
        self, 
        phase: AssemblyPhase, 
        code: str, 
        message: str, 
        line: int
    ) -> None:
        """Record a warning."""
        self.warnings.append(AssemblyError(
            phase=phase,
            code=code,
            message=message,
            line=line,
            severity="warning"
        ))
    
    def _make_result(self, success: bool) -> AssemblyResult:
        """Create assembly result."""
        return AssemblyResult(
            success=success,
            output=bytes(self.emitter.buffer) if success else None,
            errors=self.errors,
            warnings=self.warnings,
            symbols=dict(self.symbol_table.symbols),
            listing=self.get_listing() if success else "",
            hex_output=self.emitter.to_hex_string() if success else ""
        )
    
    def get_listing(self) -> str:
        """Generate assembly listing."""
        lines = []
        lines.append("Assembly Listing")
        lines.append("=" * 60)
        lines.append(f"{'Addr':>6}  {'Hex':<16}  Source")
        lines.append("-" * 60)
        
        buffer = self.emitter.buffer
        
        for ir_instr in self.ir:
            addr = ir_instr.address
            size = ir_instr.size
            stmt = ir_instr.statement
            
            # Get bytes
            start = addr - self.origin
            end = start + size
            if 0 <= start < len(buffer):
                code_bytes = buffer[start:end]
                hex_str = ' '.join(f'{b:02X}' for b in code_bytes)
            else:
                hex_str = ""
            
            # Format source
            source = f"{stmt.mnemonic}"
            if stmt.operands:
                ops = ', '.join(op.raw for op in stmt.operands)
                source += f" {ops}"
            if stmt.label:
                source = f"{stmt.label}: {source}"
            
            lines.append(f"{addr:06X}  {hex_str:<16}  {source}")
        
        lines.append("-" * 60)
        lines.append("")
        lines.append(self.symbol_table.dump())
        
        return "\n".join(lines)


# Entry point for testing
if __name__ == "__main__":
    # Test code
    test_code = """
; Simple test program
ORG 100h

START:
    MOV AX, 1234h
    MOV BX, AX  
    ADD AX, BX
    JMP DONE
    
NEXT:
    NOP
    
DONE:
    HLT
"""
    
    engine = AssemblerEngine("8086")
    result = engine.assemble(test_code, origin=0x100)
    
    print("Assembly Result:")
    print(f"  Success: {result.success}")
    
    if result.success:
        print(f"  Output: {result.hex_output}")
        print(f"\n{result.listing}")
    else:
        print("\nErrors:")
        for err in result.errors:
            print(f"  [{err.code}] Line {err.line}: {err.message}")
