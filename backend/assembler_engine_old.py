#!/usr/bin/env python3
"""
Assembler Engine for the Dynamic Two-Pass Assembler.
Orchestrates the two-pass assembly process using data-driven ISA.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from copy import deepcopy

from lexer import Lexer, Token, TokenType
from symbol_table import SymbolTable, DuplicateLabelError
from emitter import Emitter
from directives import DirectiveHandler, DirectiveResult
from error_reporter import ErrorReporter, Phase


@dataclass
class IRNode:
    """Intermediate Representation node for an instruction."""
    address: int
    mnemonic: str
    raw_operands: List[str]
    source_line: str
    line_num: int
    byte_width: int = 0
    is_directive: bool = False
    directive_result: Optional[DirectiveResult] = None
    label: Optional[str] = None


class ISA:
    """
    Instruction Set Architecture loaded from JSON.
    
    Provides opcode lookups and variant matching without hardcoded dispatch.
    """
    
    def __init__(self, isa_path: Union[str, Path, dict]):
        """
        Load ISA from JSON file or dictionary.
        
        Args:
            isa_path: Path to isa.json or ISA dictionary.
        """
        if isinstance(isa_path, dict):
            self.data = isa_path
        else:
            with open(isa_path) as f:
                self.data = json.load(f)
        
        self.instructions = self.data.get('instructions', {})
        self.registers = self.data.get('registers', {})
        self.directives = set(self.data.get('directives', []))
        self.endianness = self.data.get('endianness', 'little')
    
    def get_instruction(self, mnemonic: str) -> Optional[dict]:
        """Get instruction definition by mnemonic."""
        return self.instructions.get(mnemonic.upper())
    
    def get_register(self, name: str) -> Optional[dict]:
        """Get register definition by name."""
        return self.registers.get(name.upper())
    
    def get_register_code(self, name: str) -> int:
        """Get register encoding code."""
        reg = self.get_register(name)
        return reg['code'] if reg else 0
    
    def is_register(self, name: str) -> bool:
        """Check if name is a register."""
        return name.upper() in self.registers
    
    def is_instruction(self, name: str) -> bool:
        """Check if name is an instruction."""
        return name.upper() in self.instructions
    
    def is_directive(self, name: str) -> bool:
        """Check if name is a directive."""
        upper = name.upper().lstrip('.')
        return upper in self.directives or f'.{upper}' in self.directives
    
    def match_variant(self, mnemonic: str, operand_types: List[str]) -> Optional[dict]:
        """
        Find instruction variant matching operand types.
        
        Args:
            mnemonic: Instruction mnemonic.
            operand_types: List of operand type strings.
            
        Returns:
            Matching variant dict or None.
        """
        instr = self.get_instruction(mnemonic)
        if not instr:
            return None
        
        mode_str = ','.join(operand_types) if operand_types else 'none'
        
        for variant in instr.get('variants', []):
            variant_mode = variant.get('mode', 'none')
            if self._modes_match(variant_mode, mode_str):
                return variant
        
        return None
    
    def _modes_match(self, expected: str, actual: str) -> bool:
        """Check if operand modes match."""
        if expected == actual:
            return True
        
        # Handle wildcards and aliases
        exp_parts = expected.split(',')
        act_parts = actual.split(',')
        
        if len(exp_parts) != len(act_parts):
            return False
        
        for exp, act in zip(exp_parts, act_parts):
            if exp == act:
                continue
            # label can match imm
            if exp == 'label' and act in ('imm', 'label', 'identifier'):
                continue
            if exp == 'imm' and act in ('imm', 'label', 'identifier'):
                continue
            return False
        
        return True


class AssemblerEngine:
    """
    Two-Pass Assembler Engine.
    
    Pass 1: Build symbol table and IR nodes with address assignment.
    Pass 2: Generate machine code using ISA definitions.
    """
    
    def __init__(self, isa_path: Union[str, Path, dict] = 'isa.json'):
        """
        Initialize assembler with ISA.
        
        Args:
            isa_path: Path to ISA JSON file or ISA dictionary.
        """
        if isinstance(isa_path, dict):
            self.isa = ISA(isa_path)
        else:
            self.isa = ISA(isa_path)
        
        self.symbol_table = SymbolTable()
        self.emitter = Emitter(self.isa.endianness)
        self.errors = ErrorReporter()
        self.directive_handler = DirectiveHandler(self.symbol_table)
        self.lexer = Lexer(self.isa.data)
        
        self.ir_nodes: List[IRNode] = []
        self.origin = 0
        self.location_counter = 0
    
    def assemble(self, source: str, origin: int = 0) -> Optional[bytes]:
        """
        Assemble source code to machine code.
        
        Args:
            source: Assembly source code.
            origin: Base address.
            
        Returns:
            Machine code bytes or None if errors.
        """
        self.origin = origin
        self.location_counter = origin
        self.errors.set_source(source)
        self.errors.clear()
        self.symbol_table.clear()
        self.ir_nodes = []
        self.emitter.reset(origin)
        
        # Tokenize
        tokens = self.lexer.tokenize(source)
        
        # Pass 1: Build symbol table and IR
        if not self._pass1(tokens, source):
            return None
        
        # Check for undefined symbols
        undefined = self.symbol_table.get_forward_refs()
        for sym in undefined:
            self.errors.error(Phase.PASS2, "E040", f"Undefined symbol: '{sym}'", 0)
        
        if self.errors.has_errors():
            return None
        
        # Pass 2: Generate machine code
        if not self._pass2():
            return None
        
        return self.emitter.to_binary()
    
    def _pass1(self, tokens: List[Token], source: str) -> bool:
        """
        Pass 1: Build symbol table and IR nodes.
        
        Args:
            tokens: List of tokens from lexer.
            source: Original source code.
            
        Returns:
            True if successful, False if errors.
        """
        lines = source.splitlines()
        token_lines = self._group_tokens_by_line(tokens)
        
        for line_num, line_tokens in token_lines.items():
            if not line_tokens:
                continue
            
            source_line = lines[line_num - 1] if line_num <= len(lines) else ""
            self._process_line(line_tokens, source_line, line_num)
        
        return not self.errors.has_errors()
    
    def _group_tokens_by_line(self, tokens: List[Token]) -> Dict[int, List[Token]]:
        """Group tokens by line number."""
        groups: Dict[int, List[Token]] = {}
        for token in tokens:
            if token.type in (TokenType.NEWLINE, TokenType.EOF, TokenType.COMMENT):
                continue
            if token.line not in groups:
                groups[token.line] = []
            groups[token.line].append(token)
        return groups
    
    def _process_line(self, tokens: List[Token], source_line: str, line_num: int) -> None:
        """Process a single line of tokens."""
        if not tokens:
            return
        
        idx = 0
        current_label = None
        
        # Check for label
        if tokens[idx].type == TokenType.LABEL:
            label_name = tokens[idx].value
            try:
                self.symbol_table.define(label_name, self.location_counter, line=line_num)
            except DuplicateLabelError as e:
                self.errors.error(Phase.PASS1, "E020", str(e), line_num, tokens[idx].col)
            current_label = label_name
            idx += 1
            # Skip colon if present
            if idx < len(tokens) and tokens[idx].type == TokenType.COLON:
                idx += 1
        
        # Check for identifier followed by colon (alternate label syntax)
        elif tokens[idx].type == TokenType.IDENTIFIER:
            if idx + 1 < len(tokens) and tokens[idx + 1].type == TokenType.COLON:
                label_name = tokens[idx].value
                try:
                    self.symbol_table.define(label_name, self.location_counter, line=line_num)
                except DuplicateLabelError as e:
                    self.errors.error(Phase.PASS1, "E020", str(e), line_num, tokens[idx].col)
                current_label = label_name
                idx += 2
        
        # Nothing more on line?
        if idx >= len(tokens):
            return
        
        token = tokens[idx]
        
        # Directive?
        if token.type == TokenType.DIRECTIVE or self.directive_handler.is_directive(token.value):
            operands = self._extract_operands(tokens[idx + 1:])
            result = self.directive_handler.process(token.value, operands, self.location_counter)
            
            if result.affects_lc and result.new_lc is not None:
                self.origin = result.new_lc
                self.location_counter = result.new_lc
                self.emitter.reset(result.new_lc)
            
            if result.defines_symbol and result.symbol_name:
                try:
                    self.symbol_table.define(
                        result.symbol_name, 
                        result.symbol_value or 0,
                        is_constant=result.is_constant,
                        line=line_num
                    )
                except DuplicateLabelError as e:
                    self.errors.error(Phase.PASS1, "E020", str(e), line_num)
            
            if result.byte_width > 0:
                node = IRNode(
                    address=self.location_counter,
                    mnemonic=token.value.upper(),
                    raw_operands=operands,
                    source_line=source_line,
                    line_num=line_num,
                    byte_width=result.byte_width,
                    is_directive=True,
                    directive_result=result,
                    label=current_label
                )
                self.ir_nodes.append(node)
                self.location_counter += result.byte_width
            return
        
        # Instruction
        if token.type in (TokenType.INSTRUCTION, TokenType.IDENTIFIER):
            mnemonic = token.value.upper()
            
            # Check if it's a valid instruction
            if not self.isa.is_instruction(mnemonic):
                # Could be EQU with name before it
                if idx + 1 < len(tokens) and tokens[idx + 1].value.upper() == 'EQU':
                    name = mnemonic
                    operands = self._extract_operands(tokens[idx + 2:])
                    if operands:
                        value = self._parse_immediate(operands[0])
                        try:
                            self.symbol_table.define(name, value, is_constant=True, line=line_num)
                        except DuplicateLabelError as e:
                            self.errors.error(Phase.PASS1, "E020", str(e), line_num)
                    return
                
                # Check if it's a directive without dot
                if self.directive_handler.is_directive(mnemonic):
                    operands = self._extract_operands(tokens[idx + 1:])
                    result = self.directive_handler.process(mnemonic, operands, self.location_counter)
                    # Handle as directive...
                    return
                
                # Unknown - might be forward reference, skip for now
                return
            
            operands = self._extract_operands(tokens[idx + 1:])
            operand_types = [self._classify_operand(op) for op in operands]
            
            # Find matching variant to get byte width
            variant = self.isa.match_variant(mnemonic, operand_types)
            if variant:
                byte_width = variant.get('byte_width', 1)
            else:
                # Estimate
                byte_width = self._estimate_instruction_size(mnemonic, operands)
            
            # Track forward references
            for op in operands:
                if self._is_label_reference(op):
                    self.symbol_table.reference(op, line_num)
            
            node = IRNode(
                address=self.location_counter,
                mnemonic=mnemonic,
                raw_operands=operands,
                source_line=source_line,
                line_num=line_num,
                byte_width=byte_width,
                label=current_label
            )
            self.ir_nodes.append(node)
            self.location_counter += byte_width
    
    def _extract_operands(self, tokens: List[Token]) -> List[str]:
        """Extract operand strings from tokens."""
        operands = []
        current = []
        
        for token in tokens:
            if token.type == TokenType.COMMA:
                if current:
                    operands.append(''.join(current).strip())
                    current = []
            elif token.type in (TokenType.NEWLINE, TokenType.EOF, TokenType.COMMENT):
                break
            else:
                current.append(token.value)
        
        if current:
            operands.append(''.join(current).strip())
        
        return operands
    
    def _classify_operand(self, operand: str) -> str:
        """Classify operand type."""
        operand = operand.strip()
        
        if not operand:
            return 'none'
        
        if self.isa.is_register(operand):
            return 'reg'
        
        if operand.startswith('[') and operand.endswith(']'):
            return 'mem'
        
        if operand[0].isdigit() or operand[0] == '-':
            return 'imm'
        
        if operand.lower().startswith('0x') or operand.lower().endswith('h'):
            return 'imm'
        
        # Assume it's a label/identifier
        return 'label'
    
    def _is_label_reference(self, operand: str) -> bool:
        """Check if operand is a label reference."""
        operand = operand.strip()
        if not operand:
            return False
        if self.isa.is_register(operand):
            return False
        if operand[0].isdigit() or operand[0] == '-':
            return False
        if operand.lower().startswith('0x') or operand.lower().endswith('h'):
            return False
        if operand.startswith('['):
            return False
        return True
    
    def _estimate_instruction_size(self, mnemonic: str, operands: List[str]) -> int:
        """Estimate instruction size."""
        instr = self.isa.get_instruction(mnemonic)
        if not instr:
            return 1
        
        # Get first variant's byte width as estimate
        variants = instr.get('variants', [])
        if variants:
            return variants[0].get('byte_width', 1)
        
        return 1
    
    def _pass2(self) -> bool:
        """
        Pass 2: Generate machine code.
        
        Returns:
            True if successful, False if errors.
        """
        for node in self.ir_nodes:
            if node.is_directive and node.directive_result:
                # Emit directive data
                if node.directive_result.data:
                    self.emitter.emit_bytes(node.directive_result.data)
            else:
                # Emit instruction
                self._emit_instruction(node)
        
        return not self.errors.has_errors()
    
    def _emit_instruction(self, node: IRNode) -> None:
        """Emit machine code for an instruction."""
        mnemonic = node.mnemonic
        operands = node.raw_operands
        operand_types = [self._classify_operand(op) for op in operands]
        
        variant = self.isa.match_variant(mnemonic, operand_types)
        if not variant:
            self.errors.error(
                Phase.PASS2, "E045",
                f"No matching variant for {mnemonic} with operands {operand_types}",
                node.line_num
            )
            return
        
        opcode = int(variant.get('opcode', '0x00'), 16)
        
        # Handle register-in-opcode
        if variant.get('reg_in_opcode') and operands:
            reg_code = self.isa.get_register_code(operands[0])
            opcode = (opcode & 0xF8) | reg_code
            self.emitter.emit_byte(opcode)
            return
        
        # Emit opcode
        self.emitter.emit_byte(opcode)
        
        # Handle ModR/M
        if variant.get('modrm'):
            self._emit_modrm(node, variant)
        elif variant.get('modrm_ext') is not None:
            self._emit_modrm_ext(node, variant)
        
        # Handle immediate/relative
        if variant.get('relative'):
            self._emit_relative(node, variant)
        elif variant.get('imm_width'):
            self._emit_immediate(node, variant)
    
    def _emit_modrm(self, node: IRNode, variant: dict) -> None:
        """Emit ModR/M byte for reg,reg or reg,mem."""
        operands = node.raw_operands
        if len(operands) < 2:
            return
        
        # Assume mod=11 (register direct) for now
        mod = 0b11
        
        if self.isa.is_register(operands[0]):
            rm = self.isa.get_register_code(operands[0])
        else:
            rm = 0
        
        if self.isa.is_register(operands[1]):
            reg = self.isa.get_register_code(operands[1])
        else:
            reg = 0
        
        self.emitter.emit_modrm(mod, reg, rm)
    
    def _emit_modrm_ext(self, node: IRNode, variant: dict) -> None:
        """Emit ModR/M with opcode extension."""
        ext = variant['modrm_ext']
        operands = node.raw_operands
        
        if operands and self.isa.is_register(operands[0]):
            rm = self.isa.get_register_code(operands[0])
        else:
            rm = 0
        
        self.emitter.emit_modrm(0b11, ext, rm)
    
    def _emit_relative(self, node: IRNode, variant: dict) -> None:
        """Emit relative address for jumps/calls."""
        rel_width = variant.get('rel_width', 1)
        operands = node.raw_operands
        
        if not operands:
            return
        
        target_name = operands[0].strip()
        
        if self.symbol_table.is_defined(target_name):
            target_addr = self.symbol_table.resolve(target_name)
        else:
            target_addr = self._parse_immediate(target_name)
        
        # Calculate relative offset
        # Offset is from end of instruction
        current_end = node.address + node.byte_width
        offset = target_addr - current_end
        
        if rel_width == 1:
            self.emitter.emit_signed_byte(offset)
        else:
            self.emitter.emit_signed_word(offset)
    
    def _emit_immediate(self, node: IRNode, variant: dict) -> None:
        """Emit immediate value."""
        imm_width = variant.get('imm_width', 2)
        operands = node.raw_operands
        
        # Find immediate operand
        imm_value = 0
        for op in operands:
            if self._classify_operand(op) in ('imm', 'label'):
                if self.symbol_table.is_defined(op):
                    imm_value = self.symbol_table.resolve(op)
                else:
                    imm_value = self._parse_immediate(op)
                break
        
        if imm_width == 1:
            self.emitter.emit_byte(imm_value)
        elif imm_width == 2:
            self.emitter.emit_word(imm_value)
        else:
            self.emitter.emit_dword(imm_value)
    
    def _parse_immediate(self, value: str) -> int:
        """Parse immediate value."""
        value = value.strip()
        if not value:
            return 0
        
        # Hex
        if value.lower().startswith('0x'):
            return int(value, 16)
        if value.lower().endswith('h'):
            return int(value[:-1], 16)
        
        # Binary
        if value.lower().startswith('0b'):
            return int(value, 2)
        if value.lower().endswith('b') and all(c in '01' for c in value[:-1]):
            return int(value[:-1], 2)
        
        # Decimal
        try:
            return int(value)
        except ValueError:
            return 0
    
    def get_listing(self) -> str:
        """Get assembly listing."""
        return self.emitter.to_listing(self.ir_nodes)
    
    def get_symbol_table(self) -> str:
        """Get symbol table dump."""
        return self.symbol_table.dump()
    
    def get_hex_dump(self) -> str:
        """Get hex dump."""
        return self.emitter.to_hex_dump()
    
    def get_intel_hex(self) -> str:
        """Get Intel HEX output."""
        return self.emitter.to_intel_hex()
