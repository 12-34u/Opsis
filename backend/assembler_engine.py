#!/usr/bin/env python3
"""
Dynamic Two-Pass Assembler with Macro Support
==============================================
A fully data-driven assembler supporting:
- JSON-based ISA definition (no hardcoded instructions)
- MASM/NASM/TASM style directives
- Macro definitions and expansion
- Loop instructions (LOOP, LOOPE, LOOPNE)
- Conditional assembly
- Multiple output formats
"""

from __future__ import annotations
import re
import json
import copy
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path
import struct


# =============================================================================
# TOKEN DEFINITIONS
# =============================================================================

class TokenType(Enum):
    LABEL = auto()
    INSTRUCTION = auto()
    REGISTER = auto()
    IMMEDIATE_VALUE = auto()
    MEMORY_REF = auto()
    DIRECTIVE = auto()
    IDENTIFIER = auto()
    STRING = auto()
    COMMA = auto()
    COLON = auto()
    NEWLINE = auto()
    COMMENT = auto()
    EOF = auto()
    OPERATOR = auto()
    SIZE_SPECIFIER = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int
    raw: str = ""
    
    def __repr__(self) -> str:
        return f"Token({self.type.name}, '{self.value}', L{self.line}:C{self.column})"


# =============================================================================
# ERROR HANDLING
# =============================================================================

class AssemblerErrorType(Enum):
    LEXICAL_ERROR = auto()
    SYNTAX_ERROR = auto()
    SEMANTIC_ERROR = auto()
    UNDEFINED_SYMBOL = auto()
    DUPLICATE_SYMBOL = auto()
    INVALID_OPERAND = auto()
    INVALID_INSTRUCTION = auto()
    OPERAND_MISMATCH = auto()
    MACRO_ERROR = auto()


@dataclass
class AssemblerError:
    error_type: AssemblerErrorType
    message: str
    line: int
    column: int
    source_line: str = ""
    suggestion: str = ""
    
    def format(self) -> str:
        indicator = " " * max(0, self.column - 1) + "^"
        parts = [f"[{self.error_type.name}] Line {self.line}, Column {self.column}:", f"  {self.message}"]
        if self.source_line:
            parts.extend([f"  | {self.source_line}", f"  | {indicator}"])
        if self.suggestion:
            parts.append(f"  Suggestion: {self.suggestion}")
        return "\n".join(parts)


class ErrorReporter:
    def __init__(self):
        self.errors: List[AssemblerError] = []
        self.warnings: List[AssemblerError] = []
        self._source_lines: List[str] = []
    
    def set_source(self, source: str) -> None:
        self._source_lines = source.splitlines()
    
    def error(self, error_type: AssemblerErrorType, message: str, line: int, column: int = 1, suggestion: str = "") -> None:
        source_line = self._source_lines[line - 1] if 0 < line <= len(self._source_lines) else ""
        self.errors.append(AssemblerError(error_type, message, line, column, source_line, suggestion))
    
    def warning(self, message: str, line: int, column: int = 1) -> None:
        source_line = self._source_lines[line - 1] if 0 < line <= len(self._source_lines) else ""
        self.warnings.append(AssemblerError(AssemblerErrorType.SEMANTIC_ERROR, f"Warning: {message}", line, column, source_line))
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def clear(self) -> None:
        self.errors = []
        self.warnings = []
    
    def report(self) -> str:
        lines = []
        if self.errors:
            lines.append(f"=== {len(self.errors)} Error(s) Found ===\n")
            for err in self.errors:
                lines.append(err.format())
                lines.append("")
        if self.warnings:
            lines.append(f"=== {len(self.warnings)} Warning(s) ===\n")
            for warn in self.warnings:
                lines.append(warn.format())
                lines.append("")
        return "\n".join(lines)


# =============================================================================
# MACRO SYSTEM
# =============================================================================

@dataclass
class MacroDefinition:
    name: str
    parameters: List[str]
    body: List[str]
    local_labels: List[str] = field(default_factory=list)
    line_defined: int = 0


class MacroProcessor:
    def __init__(self):
        self.macros: Dict[str, MacroDefinition] = {}
        self.errors = ErrorReporter()
        self._expansion_count = 0
    
    def process(self, source: str) -> str:
        self.errors.set_source(source)
        lines = source.splitlines()
        lines = self._collect_macros(lines)
        lines = self._expand_macros(lines)
        return '\n'.join(lines)
    
    def _collect_macros(self, lines: List[str]) -> List[str]:
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            macro_match = re.match(r'^(\w+)\s+MACRO\s*(.*)?$|^MACRO\s+(\w+)\s*(.*)?$', stripped, re.IGNORECASE)
            if macro_match:
                if macro_match.group(1):
                    name = macro_match.group(1).upper()
                    params_str = macro_match.group(2) or ""
                else:
                    name = macro_match.group(3).upper()
                    params_str = macro_match.group(4) or ""
                params = [p.strip() for p in params_str.split(',') if p.strip()]
                body = []
                local_labels = []
                i += 1
                while i < len(lines):
                    body_line = lines[i]
                    body_stripped = body_line.strip().upper()
                    local_match = re.match(r'^LOCAL\s+(.+)$', body_stripped, re.IGNORECASE)
                    if local_match:
                        local_labels.extend([l.strip() for l in local_match.group(1).split(',')])
                        i += 1
                        continue
                    if body_stripped == 'ENDM':
                        break
                    body.append(body_line)
                    i += 1
                self.macros[name] = MacroDefinition(name=name, parameters=params, body=body, local_labels=local_labels, line_defined=i)
            else:
                result.append(line)
            i += 1
        return result
    
    def _expand_macros(self, lines: List[str], depth: int = 0) -> List[str]:
        if depth > 100:
            return lines
        result = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(';'):
                result.append(line)
                continue
            expanded = False
            for macro_name, macro_def in self.macros.items():
                pattern = rf'^{re.escape(macro_name)}(?:\s+(.*))?$'
                match = re.match(pattern, stripped, re.IGNORECASE)
                if match:
                    args_str = match.group(1) or ""
                    args = self._parse_macro_args(args_str)
                    expanded_lines = self._expand_single_macro(macro_def, args)
                    expanded_lines = self._expand_macros(expanded_lines, depth + 1)
                    result.extend(expanded_lines)
                    expanded = True
                    break
            if not expanded:
                result.append(line)
        return result
    
    def _parse_macro_args(self, args_str: str) -> List[str]:
        if not args_str.strip():
            return []
        args = []
        current = ""
        in_quotes = False
        quote_char = None
        for char in args_str:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
                current += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                current += char
                quote_char = None
            elif char == ',' and not in_quotes:
                args.append(current.strip())
                current = ""
            else:
                current += char
        if current.strip():
            args.append(current.strip())
        return args
    
    def _expand_single_macro(self, macro: MacroDefinition, args: List[str]) -> List[str]:
        self._expansion_count += 1
        param_map = {}
        for i, param in enumerate(macro.parameters):
            param_map[param.upper()] = args[i] if i < len(args) else ""
        local_map = {}
        for local in macro.local_labels:
            local_map[local.upper()] = f"@@{local}_{self._expansion_count}"
        result = [f"; --- MACRO {macro.name} ---"]
        for body_line in macro.body:
            expanded_line = body_line
            for param, value in param_map.items():
                expanded_line = re.sub(rf'\b{re.escape(param)}\b', value, expanded_line, flags=re.IGNORECASE)
            for local, unique in local_map.items():
                expanded_line = re.sub(rf'\b{re.escape(local)}\b', unique, expanded_line, flags=re.IGNORECASE)
            result.append(expanded_line)
        result.append(f"; --- END {macro.name} ---")
        return result


# =============================================================================
# ISA DEFINITION
# =============================================================================

@dataclass
class InstructionVariant:
    operand_types: List[str]
    opcode: Optional[int]
    opcode_template: Optional[str]
    encoding: str
    byte_width: Union[int, List[int]]
    modrm_reg: Optional[str] = None
    relative: bool = False


@dataclass
class InstructionDef:
    mnemonic: str
    description: str
    variants: List[InstructionVariant]


@dataclass
class RegisterDef:
    name: str
    code: str
    width: int
    reg_type: str


@dataclass
class DirectiveDef:
    name: str
    description: str
    operands: List[str]
    byte_width: Optional[int] = None
    no_emit: bool = False
    valid_values: Optional[List[str]] = None


class ISADefinition:
    def __init__(self, isa_json: Union[str, Path, dict]):
        if isinstance(isa_json, dict):
            self._data = isa_json
        elif isinstance(isa_json, Path):
            with open(isa_json) as f:
                self._data = json.load(f)
        elif isinstance(isa_json, str):
            if Path(isa_json).exists():
                with open(isa_json) as f:
                    self._data = json.load(f)
            else:
                self._data = json.loads(isa_json)
        else:
            raise ValueError("ISA must be dict, Path, or JSON string")
        
        self._instructions: Dict[str, InstructionDef] = {}
        self._registers: Dict[str, RegisterDef] = {}
        self._directives: Dict[str, DirectiveDef] = {}
        self._parse_isa()
    
    def _parse_isa(self) -> None:
        for name, reg_data in self._data.get('registers', {}).items():
            self._registers[name.upper()] = RegisterDef(name=name.upper(), code=reg_data['code'], width=reg_data['width'], reg_type=reg_data['type'])
        
        for mnemonic, instr_data in self._data.get('instructions', {}).items():
            variants = []
            for var_data in instr_data.get('variants', []):
                opcode = None
                if 'opcode' in var_data:
                    opcode_str = var_data['opcode']
                    opcode = int(opcode_str, 16) if isinstance(opcode_str, str) else opcode_str
                variants.append(InstructionVariant(
                    operand_types=var_data.get('operands', []),
                    opcode=opcode,
                    opcode_template=var_data.get('opcode_template'),
                    encoding=var_data.get('encoding', 'opcode'),
                    byte_width=var_data.get('byte_width', 1),
                    modrm_reg=var_data.get('modrm_reg'),
                    relative=var_data.get('relative', False)
                ))
            self._instructions[mnemonic.upper()] = InstructionDef(mnemonic=mnemonic.upper(), description=instr_data.get('description', ''), variants=variants)
        
        for name, dir_data in self._data.get('directives', {}).items():
            self._directives[name.upper()] = DirectiveDef(
                name=name.upper(),
                description=dir_data.get('description', ''),
                operands=dir_data.get('operands', []),
                byte_width=dir_data.get('byte_width'),
                no_emit=dir_data.get('no_emit', False),
                valid_values=dir_data.get('valid_values')
            )
    
    def get_instruction(self, mnemonic: str) -> Optional[InstructionDef]:
        return self._instructions.get(mnemonic.upper())
    
    def get_register(self, name: str) -> Optional[RegisterDef]:
        return self._registers.get(name.upper())
    
    def get_directive(self, name: str) -> Optional[DirectiveDef]:
        return self._directives.get(name.upper().lstrip('.'))
    
    def is_directive(self, name: str) -> bool:
        return self.get_directive(name) is not None
    
    def get_instruction_names(self) -> List[str]:
        return list(self._instructions.keys())
    
    def get_register_names(self) -> List[str]:
        return list(self._registers.keys())
    
    def get_directive_names(self) -> List[str]:
        return list(self._directives.keys())
    
    def match_variant(self, mnemonic: str, operand_types: List[str]) -> Optional[InstructionVariant]:
        instr = self.get_instruction(mnemonic)
        if not instr:
            return None
        for variant in instr.variants:
            if self._operands_match(variant.operand_types, operand_types):
                return variant
        return None
    
    def _operands_match(self, expected: List[str], actual: List[str]) -> bool:
        if len(expected) != len(actual):
            return False
        for exp, act in zip(expected, actual):
            exp_norm = exp.lower()
            act_norm = act.lower()
            if exp_norm == act_norm:
                continue
            if exp_norm == 'label' and act_norm in ('imm', 'identifier', 'label'):
                continue
            if exp_norm == 'imm' and act_norm in ('imm', 'immediate', 'label'):
                continue
            return False
        return True


# =============================================================================
# LEXER
# =============================================================================

class Lexer:
    SIZE_SPECIFIERS = {'BYTE', 'WORD', 'DWORD', 'QWORD', 'PTR', 'NEAR', 'FAR', 'SHORT'}
    
    def __init__(self, isa: ISADefinition):
        self.isa = isa
        self.errors = ErrorReporter()
        self._instructions = set(isa.get_instruction_names())
        self._registers = set(isa.get_register_names())
        self._directives = set(isa.get_directive_names())
        self._directives.update({f'.{d}' for d in self._directives})
    
    def tokenize(self, source: str) -> List[Token]:
        self.errors.set_source(source)
        tokens = []
        for line_num, line in enumerate(source.splitlines(), 1):
            tokens.extend(self._tokenize_line(line, line_num))
            tokens.append(Token(TokenType.NEWLINE, "\n", line_num, len(line) + 1))
        tokens.append(Token(TokenType.EOF, "", line_num + 1 if source else 1, 1))
        return tokens
    
    def _tokenize_line(self, line: str, line_num: int) -> List[Token]:
        tokens = []
        pos = 0
        while pos < len(line):
            if line[pos] in ' \t':
                pos += 1
                continue
            if line[pos] == ';':
                tokens.append(Token(TokenType.COMMENT, line[pos:], line_num, pos + 1))
                break
            if line[pos] in '"\'':
                token, end_pos = self._scan_string(line, pos, line_num)
                if token:
                    tokens.append(token)
                pos = end_pos
                continue
            if line[pos] == '[':
                token, end_pos = self._scan_memory_ref(line, pos, line_num)
                if token:
                    tokens.append(token)
                pos = end_pos
                continue
            if line[pos] in '+-*/':
                tokens.append(Token(TokenType.OPERATOR, line[pos], line_num, pos + 1))
                pos += 1
                continue
            if line[pos] == ',':
                tokens.append(Token(TokenType.COMMA, ',', line_num, pos + 1))
                pos += 1
                continue
            if line[pos:pos+2].lower() in ('0x', '0X'):
                match = re.match(r'0[xX][0-9A-Fa-f]+', line[pos:])
                if match:
                    tokens.append(Token(TokenType.IMMEDIATE_VALUE, match.group(0), line_num, pos + 1))
                    pos += len(match.group(0))
                    continue
            if line[pos:pos+2].lower() in ('0b', '0B'):
                match = re.match(r'0[bB][01]+', line[pos:])
                if match:
                    tokens.append(Token(TokenType.IMMEDIATE_VALUE, match.group(0), line_num, pos + 1))
                    pos += len(match.group(0))
                    continue
            if line[pos].isdigit() or (line[pos] == '-' and pos + 1 < len(line) and line[pos+1].isdigit()):
                match = re.match(r'-?\d+[hHbBdDoO]?', line[pos:])
                if match:
                    tokens.append(Token(TokenType.IMMEDIATE_VALUE, match.group(0), line_num, pos + 1))
                    pos += len(match.group(0))
                    continue
            if line[pos].isalpha() or line[pos] in '_@.?':
                match = re.match(r'[A-Za-z_@.?][A-Za-z0-9_@$?]*', line[pos:])
                if match:
                    value = match.group(0)
                    end_pos = pos + len(value)
                    if end_pos < len(line) and line[end_pos] == ':':
                        tokens.append(Token(TokenType.LABEL, value, line_num, pos + 1, value + ':'))
                        pos = end_pos + 1
                        continue
                    token_type = self._classify_identifier(value)
                    tokens.append(Token(token_type, value, line_num, pos + 1, value))
                    pos = end_pos
                    continue
            pos += 1
        return tokens
    
    def _scan_string(self, line: str, start: int, line_num: int) -> Tuple[Optional[Token], int]:
        quote = line[start]
        pos = start + 1
        while pos < len(line) and line[pos] != quote:
            if line[pos] == '\\' and pos + 1 < len(line):
                pos += 2
            else:
                pos += 1
        if pos < len(line):
            return Token(TokenType.STRING, line[start:pos + 1], line_num, start + 1), pos + 1
        return None, len(line)
    
    def _scan_memory_ref(self, line: str, start: int, line_num: int) -> Tuple[Optional[Token], int]:
        pos = start + 1
        depth = 1
        while pos < len(line) and depth > 0:
            if line[pos] == '[':
                depth += 1
            elif line[pos] == ']':
                depth -= 1
            pos += 1
        if depth == 0:
            return Token(TokenType.MEMORY_REF, line[start:pos], line_num, start + 1), pos
        return None, len(line)
    
    def _classify_identifier(self, value: str) -> TokenType:
        upper = value.upper()
        if upper in self.SIZE_SPECIFIERS:
            return TokenType.SIZE_SPECIFIER
        if upper in self._instructions:
            return TokenType.INSTRUCTION
        if upper in self._registers:
            return TokenType.REGISTER
        if upper in self._directives or upper.lstrip('.') in self._directives:
            return TokenType.DIRECTIVE
        return TokenType.IDENTIFIER


# =============================================================================
# SYMBOL TABLE
# =============================================================================

@dataclass
class Symbol:
    name: str
    address: int
    symbol_type: str = "label"
    defined: bool = True
    line_defined: int = 0
    segment: str = ""


class SymbolTable:
    def __init__(self):
        self._symbols: Dict[str, Symbol] = {}
        self._forward_refs: Dict[str, List[Tuple[int, int]]] = {}
        self._current_segment = ""
    
    def define(self, name: str, address: int, symbol_type: str = "label", line: int = 0) -> bool:
        if name in self._symbols and self._symbols[name].defined:
            return False
        self._symbols[name] = Symbol(name=name, address=address, symbol_type=symbol_type, defined=True, line_defined=line, segment=self._current_segment)
        return True
    
    def reference(self, name: str, from_address: int, line: int = 0) -> None:
        if name not in self._forward_refs:
            self._forward_refs[name] = []
        self._forward_refs[name].append((from_address, line))
    
    def lookup(self, name: str) -> Optional[Symbol]:
        return self._symbols.get(name)
    
    def resolve(self, name: str) -> Optional[int]:
        sym = self._symbols.get(name)
        return sym.address if sym and sym.defined else None
    
    def get_undefined(self) -> List[Tuple[str, int]]:
        undefined = []
        for name, refs in self._forward_refs.items():
            if name not in self._symbols or not self._symbols[name].defined:
                for _, line in refs:
                    undefined.append((name, line))
        return undefined
    
    def set_segment(self, segment: str) -> None:
        self._current_segment = segment
    
    def get_all_symbols(self) -> Dict[str, Symbol]:
        return self._symbols.copy()
    
    def dump(self) -> str:
        lines = ["Symbol Table:", "=" * 60, f"{'Name':<20} {'Address':<12} {'Type':<12} {'Line':<6}", "-" * 60]
        for name, sym in sorted(self._symbols.items()):
            addr_str = f"0x{sym.address:04X}" if sym.defined else "????"
            lines.append(f"{name:<20} {addr_str:<12} {sym.symbol_type:<12} {sym.line_defined:<6}")
        lines.append("=" * 60)
        return "\n".join(lines)


# =============================================================================
# PARSED STRUCTURES
# =============================================================================

@dataclass
class ParsedOperand:
    raw: str
    operand_type: str
    value: Any
    token: Token
    size_override: Optional[str] = None


@dataclass
class ParsedInstruction:
    mnemonic: str
    operands: List[ParsedOperand]
    line: int
    address: int = 0
    byte_width: int = 0
    label: Optional[str] = None


@dataclass
class ParsedDirective:
    directive: str
    operands: List[Any]
    line: int
    address: int = 0
    label: Optional[str] = None


# =============================================================================
# EMITTER
# =============================================================================

class Emitter:
    def __init__(self, endian: str = 'little'):
        self.endian = endian
        self.output: bytearray = bytearray()
        self.current_address = 0
    
    def emit_byte(self, value: int) -> None:
        self.output.append(value & 0xFF)
        self.current_address += 1
    
    def emit_word(self, value: int) -> None:
        if self.endian == 'little':
            self.output.extend(struct.pack('<H', value & 0xFFFF))
        else:
            self.output.extend(struct.pack('>H', value & 0xFFFF))
        self.current_address += 2
    
    def emit_dword(self, value: int) -> None:
        if self.endian == 'little':
            self.output.extend(struct.pack('<I', value & 0xFFFFFFFF))
        else:
            self.output.extend(struct.pack('>I', value & 0xFFFFFFFF))
        self.current_address += 4
    
    def emit_bytes(self, data: bytes) -> None:
        self.output.extend(data)
        self.current_address += len(data)
    
    def emit_immediate(self, value: int, width: int) -> None:
        if width == 1:
            self.emit_byte(value)
        elif width == 2:
            self.emit_word(value)
        elif width == 4:
            self.emit_dword(value)
    
    def emit_signed(self, value: int, width: int) -> None:
        if width == 1:
            if value < 0:
                value = (256 + value) & 0xFF
            self.emit_byte(value)
        elif width == 2:
            if value < 0:
                value = (65536 + value) & 0xFFFF
            self.emit_word(value)
        else:
            self.emit_immediate(value, width)
    
    def emit_modrm(self, mod: int, reg: int, rm: int) -> None:
        modrm = ((mod & 0x3) << 6) | ((reg & 0x7) << 3) | (rm & 0x7)
        self.emit_byte(modrm)
    
    def get_hex_string(self) -> str:
        return self.output.hex().upper()
    
    def get_formatted_hex(self, bytes_per_line: int = 16) -> str:
        lines = []
        for i in range(0, len(self.output), bytes_per_line):
            chunk = self.output[i:i + bytes_per_line]
            hex_part = ' '.join(f'{b:02X}' for b in chunk)
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            lines.append(f"{i:04X}: {hex_part:<{bytes_per_line*3}} {ascii_part}")
        return '\n'.join(lines)
    
    def get_binary(self) -> bytes:
        return bytes(self.output)
    
    def write_binary_file(self, path: Union[str, Path]) -> None:
        with open(path, 'wb') as f:
            f.write(self.output)
    
    def write_intel_hex(self, path: Union[str, Path]) -> None:
        with open(path, 'w') as f:
            addr = 0
            for i in range(0, len(self.output), 16):
                chunk = self.output[i:i + 16]
                length = len(chunk)
                record = f':{length:02X}{addr:04X}00'
                for b in chunk:
                    record += f'{b:02X}'
                checksum = (length + (addr >> 8) + (addr & 0xFF) + sum(chunk)) & 0xFF
                checksum = (~checksum + 1) & 0xFF
                record += f'{checksum:02X}'
                f.write(record + '\n')
                addr += 16
            f.write(':00000001FF\n')
    
    def reset(self, origin: int = 0) -> None:
        self.output = bytearray()
        self.current_address = origin


# =============================================================================
# ASSEMBLER ENGINE
# =============================================================================

class AssemblerEngine:
    def __init__(self, isa: ISADefinition):
        self.isa = isa
        self.lexer = Lexer(isa)
        self.macro_processor = MacroProcessor()
        self.symbol_table = SymbolTable()
        self.emitter = Emitter()
        self.errors = ErrorReporter()
        self._origin = 0
        self._location_counter = 0
        self._parsed_lines: List[Union[ParsedInstruction, ParsedDirective]] = []
        self._model = "SMALL"
        self._entry_point: Optional[str] = None
    
    def assemble(self, source: str) -> Optional[bytes]:
        self.errors = ErrorReporter()
        self.errors.set_source(source)
        self.symbol_table = SymbolTable()
        self.emitter.reset()
        self._parsed_lines = []
        self._origin = 0
        self._location_counter = 0
        
        try:
            processed_source = self.macro_processor.process(source)
            if self.macro_processor.errors.has_errors():
                self.errors.errors.extend(self.macro_processor.errors.errors)
                return None
        except Exception as e:
            self.errors.error(AssemblerErrorType.MACRO_ERROR, f"Macro processing failed: {str(e)}", 1)
            return None
        
        tokens = self.lexer.tokenize(processed_source)
        if self.lexer.errors.has_errors():
            self.errors.errors.extend(self.lexer.errors.errors)
            return None
        
        if not self._pass1(tokens):
            return None
        
        undefined = self.symbol_table.get_undefined()
        for sym, line in undefined:
            self.errors.error(AssemblerErrorType.UNDEFINED_SYMBOL, f"Undefined symbol: '{sym}'", line)
        
        if self.errors.has_errors():
            return None
        
        if not self._pass2():
            return None
        
        return self.emitter.get_binary()
    
    def _pass1(self, tokens: List[Token]) -> bool:
        self._location_counter = self._origin
        lines = self._group_by_line(tokens)
        
        for line_tokens in lines:
            if not line_tokens:
                continue
            line_num = line_tokens[0].line
            current_label = None
            idx = 0
            
            if line_tokens[idx].type == TokenType.LABEL:
                label_name = line_tokens[idx].value
                if not self.symbol_table.define(label_name, self._location_counter, "label", line_num):
                    self.errors.error(AssemblerErrorType.DUPLICATE_SYMBOL, f"Duplicate label: '{label_name}'", line_num, line_tokens[idx].column)
                current_label = label_name
                idx += 1
            
            remaining = [t for t in line_tokens[idx:] if t.type not in (TokenType.NEWLINE, TokenType.EOF, TokenType.COMMENT)]
            if not remaining:
                continue
            
            token = remaining[0]
            
            if token.type == TokenType.DIRECTIVE:
                parsed = self._parse_directive(remaining, line_num)
                if parsed:
                    parsed.address = self._location_counter
                    parsed.label = current_label
                    self._handle_directive_pass1(parsed)
                    self._parsed_lines.append(parsed)
                continue
            
            if token.type == TokenType.INSTRUCTION:
                parsed = self._parse_instruction(remaining, line_num)
                if parsed:
                    parsed.address = self._location_counter
                    parsed.label = current_label
                    size = self._calculate_instruction_size(parsed)
                    parsed.byte_width = size
                    self._location_counter += size
                    self._parsed_lines.append(parsed)
                continue
            
            if token.type == TokenType.IDENTIFIER:
                if len(remaining) >= 3 and remaining[1].value.upper() in ('EQU', '.EQU'):
                    name = token.value
                    value = self._evaluate_expression(remaining[2:], line_num)
                    self.symbol_table.define(name, value, "constant", line_num)
                    self._parsed_lines.append(ParsedDirective(directive='EQU', operands=[name, value], line=line_num, label=current_label))
                    continue
                if len(remaining) >= 2 and remaining[1].value.upper() in ('SEGMENT', 'PROC'):
                    # Handle MASM-style segment/proc definitions
                    continue
            
            # Handle unknown - might be MASM directive without dot
            self._handle_unknown(remaining, line_num, current_label)
        
        return not self.errors.has_errors()
    
    def _handle_unknown(self, tokens: List[Token], line_num: int, label: Optional[str]) -> None:
        if not tokens:
            return
        first = tokens[0].value.upper()
        # MASM directives that don't generate code
        no_emit = {'TITLE', 'SUBTITLE', 'PAGE', 'NAME', '.186', '.286', '.386', '.486', '.8086', 'DOSSEG', 'IDEAL', 'MASM', 'JUMPS', 'NOJUMPS', 'LOCALS', 'NOLOCALS', '.RADIX'}
        if first.lstrip('.') in no_emit or first in no_emit:
            return
        # If it starts with a dot and we don't recognize it, just ignore it
        if first.startswith('.'):
            return
    
    def _pass2(self) -> bool:
        self.emitter.reset(self._origin)
        for item in self._parsed_lines:
            if isinstance(item, ParsedDirective):
                self._emit_directive(item)
            elif isinstance(item, ParsedInstruction):
                self._emit_instruction(item)
        return not self.errors.has_errors()
    
    def _group_by_line(self, tokens: List[Token]) -> List[List[Token]]:
        lines = []
        current_line = []
        for token in tokens:
            if token.type == TokenType.NEWLINE:
                if current_line:
                    lines.append(current_line)
                    current_line = []
            elif token.type == TokenType.COMMENT:
                continue
            elif token.type == TokenType.EOF:
                if current_line:
                    lines.append(current_line)
                break
            else:
                current_line.append(token)
        return lines
    
    def _parse_instruction(self, tokens: List[Token], line: int) -> Optional[ParsedInstruction]:
        if not tokens or tokens[0].type != TokenType.INSTRUCTION:
            return None
        mnemonic = tokens[0].value.upper()
        operands = []
        idx = 1
        size_override = None
        while idx < len(tokens):
            token = tokens[idx]
            if token.type == TokenType.COMMA:
                idx += 1
                continue
            if token.type in (TokenType.NEWLINE, TokenType.EOF, TokenType.COMMENT):
                break
            if token.type == TokenType.SIZE_SPECIFIER:
                size_override = token.value.upper()
                idx += 1
                continue
            operand = self._parse_operand(token, size_override)
            if operand:
                operands.append(operand)
                size_override = None
            idx += 1
        
        instr_def = self.isa.get_instruction(mnemonic)
        if instr_def:
            valid_counts = set(len(v.operand_types) for v in instr_def.variants)
            if len(operands) not in valid_counts:
                expected = ', '.join(str(c) for c in sorted(valid_counts))
                self.errors.error(AssemblerErrorType.OPERAND_MISMATCH, f"'{mnemonic}' expects {expected} operand(s), got {len(operands)}", line, tokens[0].column)
                return None
        else:
            self.errors.error(AssemblerErrorType.INVALID_INSTRUCTION, f"Unknown instruction: '{mnemonic}'", line, tokens[0].column)
            return None
        
        return ParsedInstruction(mnemonic=mnemonic, operands=operands, line=line)
    
    def _parse_operand(self, token: Token, size_override: Optional[str] = None) -> Optional[ParsedOperand]:
        if token.type == TokenType.REGISTER:
            return ParsedOperand(raw=token.value, operand_type='reg', value=token.value.upper(), token=token, size_override=size_override)
        elif token.type == TokenType.IMMEDIATE_VALUE:
            value = self._parse_immediate_value(token.value)
            return ParsedOperand(raw=token.value, operand_type='imm', value=value, token=token, size_override=size_override)
        elif token.type == TokenType.MEMORY_REF:
            return ParsedOperand(raw=token.value, operand_type='mem', value=token.value, token=token, size_override=size_override)
        elif token.type == TokenType.IDENTIFIER:
            return ParsedOperand(raw=token.value, operand_type='label', value=token.value, token=token, size_override=size_override)
        return None
    
    def _parse_immediate_value(self, value: str) -> int:
        value = value.strip()
        if value.lower().startswith('0x'):
            return int(value, 16)
        if value.lower().startswith('0b'):
            return int(value, 2)
        if value.lower().endswith('h'):
            return int(value[:-1], 16)
        if value.lower().endswith('b') and all(c in '01' for c in value[:-1]):
            return int(value[:-1], 2)
        if value.lower().endswith('o'):
            return int(value[:-1], 8)
        if value.lower().endswith('d'):
            return int(value[:-1])
        return int(value)
    
    def _evaluate_expression(self, tokens: List[Token], line: int) -> int:
        if not tokens:
            return 0
        if len(tokens) == 1:
            if tokens[0].type == TokenType.IMMEDIATE_VALUE:
                return self._parse_immediate_value(tokens[0].value)
            elif tokens[0].type == TokenType.IDENTIFIER:
                sym = self.symbol_table.lookup(tokens[0].value)
                return sym.address if sym else 0
        return 0
    
    def _parse_directive(self, tokens: List[Token], line: int) -> Optional[ParsedDirective]:
        if not tokens or tokens[0].type != TokenType.DIRECTIVE:
            return None
        directive = tokens[0].value.upper().lstrip('.')
        operands = []
        idx = 1
        while idx < len(tokens):
            token = tokens[idx]
            if token.type in (TokenType.NEWLINE, TokenType.EOF, TokenType.COMMENT):
                break
            if token.type == TokenType.COMMA:
                idx += 1
                continue
            if token.type == TokenType.IMMEDIATE_VALUE:
                operands.append(self._parse_immediate_value(token.value))
            elif token.type == TokenType.STRING:
                operands.append(token.value[1:-1])
            elif token.type == TokenType.IDENTIFIER:
                operands.append(token.value)
            else:
                operands.append(token.value)
            idx += 1
        return ParsedDirective(directive=directive, operands=operands, line=line)
    
    def _handle_directive_pass1(self, directive: ParsedDirective) -> None:
        if directive.directive == 'ORG':
            if directive.operands:
                val = directive.operands[0]
                if isinstance(val, int):
                    self._origin = val
                    self._location_counter = val
        elif directive.directive == 'MODEL':
            if directive.operands:
                self._model = str(directive.operands[0]).upper()
        elif directive.directive in ('DATA', 'CODE', 'STACK'):
            pass  # Segment directives - no emit
        elif directive.directive == 'DB':
            for op in directive.operands:
                if isinstance(op, str):
                    self._location_counter += len(op)
                else:
                    self._location_counter += 1
        elif directive.directive == 'DW':
            self._location_counter += len(directive.operands) * 2
        elif directive.directive == 'DD':
            self._location_counter += len(directive.operands) * 4
        elif directive.directive == 'RESB':
            if directive.operands:
                self._location_counter += directive.operands[0]
        elif directive.directive == 'RESW':
            if directive.operands:
                self._location_counter += directive.operands[0] * 2
        elif directive.directive == 'ALIGN':
            if directive.operands:
                boundary = directive.operands[0]
                remainder = self._location_counter % boundary
                if remainder:
                    self._location_counter += boundary - remainder
        elif directive.directive == 'EVEN':
            if self._location_counter % 2:
                self._location_counter += 1
        elif directive.directive == 'EQU':
            pass  # Already handled
        elif directive.directive == 'END':
            if directive.operands:
                self._entry_point = str(directive.operands[0])
    
    def _calculate_instruction_size(self, instr: ParsedInstruction) -> int:
        operand_types = [op.operand_type for op in instr.operands]
        variant = self.isa.match_variant(instr.mnemonic, operand_types)
        if variant:
            if isinstance(variant.byte_width, list):
                return variant.byte_width[0]
            return variant.byte_width
        base = 1
        for op in instr.operands:
            if op.operand_type in ('imm', 'mem', 'label'):
                base += 2
        return max(base, 2)
    
    def _emit_instruction(self, instr: ParsedInstruction) -> None:
        operand_types = [op.operand_type for op in instr.operands]
        variant = self.isa.match_variant(instr.mnemonic, operand_types)
        if not variant:
            self.errors.error(AssemblerErrorType.INVALID_OPERAND, f"No variant for {instr.mnemonic} with {operand_types}", instr.line)
            return
        
        if variant.opcode is not None:
            self.emitter.emit_byte(variant.opcode)
        elif variant.opcode_template:
            opcode = self._resolve_opcode_template(variant.opcode_template, instr.operands)
            self.emitter.emit_byte(opcode)
        
        encoding = variant.encoding.lower()
        if 'modrm' in encoding:
            self._emit_modrm(instr, variant)
        if 'imm8' in encoding:
            self._emit_immediate_byte(instr)
        elif 'immediate' in encoding:
            self._emit_immediate_operand(instr, variant)
        if 'rel' in encoding:
            self._emit_relative_address(instr, variant)
    
    def _resolve_opcode_template(self, template: str, operands: List[ParsedOperand]) -> int:
        if '{reg_code}' in template:
            reg_name = operands[0].value
            reg_def = self.isa.get_register(reg_name)
            if reg_def:
                base_str = template.split('{')[0]
                base = int(base_str, 16) if base_str.startswith('0x') else int(base_str, 16) << 4
                reg_code = int(reg_def.code, 2)
                return (base & 0xF8) | reg_code
        if '{reg_code+8}' in template:
            reg_name = operands[0].value
            reg_def = self.isa.get_register(reg_name)
            if reg_def:
                base_str = template.split('{')[0]
                base = int(base_str, 16) if base_str.startswith('0x') else int(base_str, 16) << 4
                reg_code = int(reg_def.code, 2)
                return (base & 0xF8) | (reg_code + 8)
        return int(template, 16)
    
    def _emit_modrm(self, instr: ParsedInstruction, variant: InstructionVariant) -> None:
        mod = 0b11
        reg = 0
        rm = 0
        if len(instr.operands) >= 2:
            if instr.operands[0].operand_type == 'reg':
                rm_reg = self.isa.get_register(instr.operands[0].value)
                if rm_reg:
                    rm = int(rm_reg.code, 2)
            if instr.operands[1].operand_type == 'reg':
                reg_def = self.isa.get_register(instr.operands[1].value)
                if reg_def:
                    reg = int(reg_def.code, 2)
        elif len(instr.operands) == 1:
            if instr.operands[0].operand_type == 'reg':
                rm_reg = self.isa.get_register(instr.operands[0].value)
                if rm_reg:
                    rm = int(rm_reg.code, 2)
        if variant.modrm_reg:
            reg = int(variant.modrm_reg, 2)
        self.emitter.emit_modrm(mod, reg, rm)
    
    def _emit_immediate_byte(self, instr: ParsedInstruction) -> None:
        for op in instr.operands:
            if op.operand_type == 'imm':
                self.emitter.emit_byte(op.value & 0xFF)
                break
    
    def _emit_immediate_operand(self, instr: ParsedInstruction, variant: InstructionVariant) -> None:
        for op in instr.operands:
            if op.operand_type == 'imm':
                width = variant.byte_width if isinstance(variant.byte_width, int) else variant.byte_width[0]
                imm_width = width - 1
                if 'modrm' in variant.encoding.lower():
                    imm_width -= 1
                imm_width = max(1, min(imm_width, 2))
                self.emitter.emit_immediate(op.value, imm_width)
                break
    
    def _emit_relative_address(self, instr: ParsedInstruction, variant: InstructionVariant) -> None:
        for op in instr.operands:
            if op.operand_type == 'label':
                target_addr = self.symbol_table.resolve(op.value)
                if target_addr is not None:
                    width = variant.byte_width if isinstance(variant.byte_width, int) else variant.byte_width[0]
                    offset = target_addr - (instr.address + width)
                    offset_width = width - 1
                    self.emitter.emit_signed(offset, offset_width)
                else:
                    self.errors.error(AssemblerErrorType.UNDEFINED_SYMBOL, f"Undefined label: '{op.value}'", instr.line)
                break
            elif op.operand_type == 'imm':
                width = variant.byte_width if isinstance(variant.byte_width, int) else variant.byte_width[0]
                self.emitter.emit_immediate(op.value, width - 1)
                break
    
    def _emit_directive(self, directive: ParsedDirective) -> None:
        if directive.directive == 'DB':
            for op in directive.operands:
                if isinstance(op, str):
                    self.emitter.emit_bytes(op.encode('ascii'))
                elif isinstance(op, int):
                    self.emitter.emit_byte(op)
        elif directive.directive == 'DW':
            for op in directive.operands:
                if isinstance(op, int):
                    self.emitter.emit_word(op)
                elif isinstance(op, str):
                    sym = self.symbol_table.lookup(op)
                    self.emitter.emit_word(sym.address if sym else 0)
        elif directive.directive == 'DD':
            for op in directive.operands:
                if isinstance(op, int):
                    self.emitter.emit_dword(op)
        elif directive.directive == 'RESB':
            if directive.operands:
                for _ in range(directive.operands[0]):
                    self.emitter.emit_byte(0)
        elif directive.directive == 'RESW':
            if directive.operands:
                for _ in range(directive.operands[0] * 2):
                    self.emitter.emit_byte(0)
        elif directive.directive == 'ALIGN':
            if directive.operands:
                boundary = directive.operands[0]
                while self.emitter.current_address % boundary:
                    self.emitter.emit_byte(0x90)
        elif directive.directive == 'EVEN':
            if self.emitter.current_address % 2:
                self.emitter.emit_byte(0x90)
    
    def get_listing(self) -> str:
        lines = ["Assembly Listing", "=" * 70, f"{'Addr':<8} {'Machine Code':<20} {'Source':<40}", "-" * 70]
        for item in self._parsed_lines:
            if isinstance(item, ParsedInstruction):
                addr = f"{item.address:04X}"
                ops = ', '.join(op.raw for op in item.operands)
                src = f"{item.mnemonic:<8} {ops}"
                if item.label:
                    src = f"{item.label}: {src}"
                lines.append(f"{addr:<8} {'---':<20} {src:<40}")
            elif isinstance(item, ParsedDirective):
                addr = f"{item.address:04X}"
                ops = ', '.join(str(op) for op in item.operands[:3])
                src = f"{item.directive:<8} {ops}"
                lines.append(f"{addr:<8} {'---':<20} {src:<40}")
        lines.append("=" * 70)
        return '\n'.join(lines)
    
    def get_statistics(self) -> str:
        return f"""
Assembly Statistics:
====================
Code Size:     {len(self.emitter.output)} bytes
Symbols:       {len(self.symbol_table.get_all_symbols())}
Macros:        {len(self.macro_processor.macros)}
Origin:        0x{self._origin:04X}
Entry Point:   {self._entry_point or 'Not specified'}
Memory Model:  {self._model}
"""


# =============================================================================
# ISA FACTORY
# =============================================================================

def create_full_isa() -> dict:
    return {
        "registers": {
            "AX": {"code": "000", "width": 16, "type": "general"},
            "BX": {"code": "011", "width": 16, "type": "general"},
            "CX": {"code": "001", "width": 16, "type": "general"},
            "DX": {"code": "010", "width": 16, "type": "general"},
            "SP": {"code": "100", "width": 16, "type": "pointer"},
            "BP": {"code": "101", "width": 16, "type": "pointer"},
            "SI": {"code": "110", "width": 16, "type": "index"},
            "DI": {"code": "111", "width": 16, "type": "index"},
            "AL": {"code": "000", "width": 8, "type": "general"},
            "AH": {"code": "100", "width": 8, "type": "general"},
            "BL": {"code": "011", "width": 8, "type": "general"},
            "BH": {"code": "111", "width": 8, "type": "general"},
            "CL": {"code": "001", "width": 8, "type": "general"},
            "CH": {"code": "101", "width": 8, "type": "general"},
            "DL": {"code": "010", "width": 8, "type": "general"},
            "DH": {"code": "110", "width": 8, "type": "general"},
            "CS": {"code": "001", "width": 16, "type": "segment"},
            "DS": {"code": "011", "width": 16, "type": "segment"},
            "ES": {"code": "000", "width": 16, "type": "segment"},
            "SS": {"code": "010", "width": 16, "type": "segment"},
        },
        "instructions": {
            "MOV": {"description": "Move", "variants": [
                {"operands": ["reg", "reg"], "opcode": "0x89", "encoding": "opcode + modrm", "byte_width": 2},
                {"operands": ["reg", "imm"], "opcode": "0xB8", "encoding": "opcode + immediate", "byte_width": 3},
            ]},
            "ADD": {"description": "Add", "variants": [
                {"operands": ["reg", "reg"], "opcode": "0x01", "encoding": "opcode + modrm", "byte_width": 2},
                {"operands": ["reg", "imm"], "opcode": "0x81", "modrm_reg": "000", "encoding": "opcode + modrm + immediate", "byte_width": 4},
            ]},
            "SUB": {"description": "Subtract", "variants": [
                {"operands": ["reg", "reg"], "opcode": "0x29", "encoding": "opcode + modrm", "byte_width": 2},
                {"operands": ["reg", "imm"], "opcode": "0x81", "modrm_reg": "101", "encoding": "opcode + modrm + immediate", "byte_width": 4},
            ]},
            "INC": {"description": "Increment", "variants": [
                {"operands": ["reg"], "opcode_template": "0x40", "encoding": "opcode", "byte_width": 1},
            ]},
            "DEC": {"description": "Decrement", "variants": [
                {"operands": ["reg"], "opcode_template": "0x48", "encoding": "opcode", "byte_width": 1},
            ]},
            "MUL": {"description": "Multiply", "variants": [
                {"operands": ["reg"], "opcode": "0xF7", "modrm_reg": "100", "encoding": "opcode + modrm", "byte_width": 2},
            ]},
            "DIV": {"description": "Divide", "variants": [
                {"operands": ["reg"], "opcode": "0xF7", "modrm_reg": "110", "encoding": "opcode + modrm", "byte_width": 2},
            ]},
            "AND": {"description": "AND", "variants": [
                {"operands": ["reg", "reg"], "opcode": "0x21", "encoding": "opcode + modrm", "byte_width": 2},
            ]},
            "OR": {"description": "OR", "variants": [
                {"operands": ["reg", "reg"], "opcode": "0x09", "encoding": "opcode + modrm", "byte_width": 2},
            ]},
            "XOR": {"description": "XOR", "variants": [
                {"operands": ["reg", "reg"], "opcode": "0x31", "encoding": "opcode + modrm", "byte_width": 2},
            ]},
            "NOT": {"description": "NOT", "variants": [
                {"operands": ["reg"], "opcode": "0xF7", "modrm_reg": "010", "encoding": "opcode + modrm", "byte_width": 2},
            ]},
            "CMP": {"description": "Compare", "variants": [
                {"operands": ["reg", "reg"], "opcode": "0x39", "encoding": "opcode + modrm", "byte_width": 2},
                {"operands": ["reg", "imm"], "opcode": "0x81", "modrm_reg": "111", "encoding": "opcode + modrm + immediate", "byte_width": 4},
            ]},
            "JMP": {"description": "Jump", "variants": [
                {"operands": ["label"], "opcode": "0xE9", "encoding": "opcode + rel16", "byte_width": 3, "relative": True},
            ]},
            "JZ": {"description": "Jump if zero", "variants": [
                {"operands": ["label"], "opcode": "0x74", "encoding": "opcode + rel8", "byte_width": 2, "relative": True},
            ]},
            "JNZ": {"description": "Jump if not zero", "variants": [
                {"operands": ["label"], "opcode": "0x75", "encoding": "opcode + rel8", "byte_width": 2, "relative": True},
            ]},
            "JE": {"description": "Jump if equal", "variants": [
                {"operands": ["label"], "opcode": "0x74", "encoding": "opcode + rel8", "byte_width": 2, "relative": True},
            ]},
            "JNE": {"description": "Jump if not equal", "variants": [
                {"operands": ["label"], "opcode": "0x75", "encoding": "opcode + rel8", "byte_width": 2, "relative": True},
            ]},
            "JL": {"description": "Jump if less", "variants": [
                {"operands": ["label"], "opcode": "0x7C", "encoding": "opcode + rel8", "byte_width": 2, "relative": True},
            ]},
            "JG": {"description": "Jump if greater", "variants": [
                {"operands": ["label"], "opcode": "0x7F", "encoding": "opcode + rel8", "byte_width": 2, "relative": True},
            ]},
            "JLE": {"description": "Jump if <=", "variants": [
                {"operands": ["label"], "opcode": "0x7E", "encoding": "opcode + rel8", "byte_width": 2, "relative": True},
            ]},
            "JGE": {"description": "Jump if >=", "variants": [
                {"operands": ["label"], "opcode": "0x7D", "encoding": "opcode + rel8", "byte_width": 2, "relative": True},
            ]},
            "LOOP": {"description": "Loop CX times", "variants": [
                {"operands": ["label"], "opcode": "0xE2", "encoding": "opcode + rel8", "byte_width": 2, "relative": True},
            ]},
            "LOOPE": {"description": "Loop while equal", "variants": [
                {"operands": ["label"], "opcode": "0xE1", "encoding": "opcode + rel8", "byte_width": 2, "relative": True},
            ]},
            "LOOPNE": {"description": "Loop while not equal", "variants": [
                {"operands": ["label"], "opcode": "0xE0", "encoding": "opcode + rel8", "byte_width": 2, "relative": True},
            ]},
            "LOOPZ": {"description": "Loop while zero", "variants": [
                {"operands": ["label"], "opcode": "0xE1", "encoding": "opcode + rel8", "byte_width": 2, "relative": True},
            ]},
            "LOOPNZ": {"description": "Loop while not zero", "variants": [
                {"operands": ["label"], "opcode": "0xE0", "encoding": "opcode + rel8", "byte_width": 2, "relative": True},
            ]},
            "CALL": {"description": "Call", "variants": [
                {"operands": ["label"], "opcode": "0xE8", "encoding": "opcode + rel16", "byte_width": 3, "relative": True},
            ]},
            "RET": {"description": "Return", "variants": [
                {"operands": [], "opcode": "0xC3", "encoding": "opcode", "byte_width": 1},
            ]},
            "PUSH": {"description": "Push", "variants": [
                {"operands": ["reg"], "opcode_template": "0x50", "encoding": "opcode", "byte_width": 1},
            ]},
            "POP": {"description": "Pop", "variants": [
                {"operands": ["reg"], "opcode_template": "0x58", "encoding": "opcode", "byte_width": 1},
            ]},
            "INT": {"description": "Interrupt", "variants": [
                {"operands": ["imm"], "opcode": "0xCD", "encoding": "opcode + imm8", "byte_width": 2},
            ]},
            "NOP": {"description": "No op", "variants": [
                {"operands": [], "opcode": "0x90", "encoding": "opcode", "byte_width": 1},
            ]},
            "HLT": {"description": "Halt", "variants": [
                {"operands": [], "opcode": "0xF4", "encoding": "opcode", "byte_width": 1},
            ]},
            "CLI": {"description": "Clear IF", "variants": [
                {"operands": [], "opcode": "0xFA", "encoding": "opcode", "byte_width": 1},
            ]},
            "STI": {"description": "Set IF", "variants": [
                {"operands": [], "opcode": "0xFB", "encoding": "opcode", "byte_width": 1},
            ]},
            "CLC": {"description": "Clear CF", "variants": [
                {"operands": [], "opcode": "0xF8", "encoding": "opcode", "byte_width": 1},
            ]},
            "STC": {"description": "Set CF", "variants": [
                {"operands": [], "opcode": "0xF9", "encoding": "opcode", "byte_width": 1},
            ]},
            "CLD": {"description": "Clear DF", "variants": [
                {"operands": [], "opcode": "0xFC", "encoding": "opcode", "byte_width": 1},
            ]},
            "STD": {"description": "Set DF", "variants": [
                {"operands": [], "opcode": "0xFD", "encoding": "opcode", "byte_width": 1},
            ]},
            "PUSHF": {"description": "Push flags", "variants": [
                {"operands": [], "opcode": "0x9C", "encoding": "opcode", "byte_width": 1},
            ]},
            "POPF": {"description": "Pop flags", "variants": [
                {"operands": [], "opcode": "0x9D", "encoding": "opcode", "byte_width": 1},
            ]},
            "CBW": {"description": "Convert byte to word", "variants": [
                {"operands": [], "opcode": "0x98", "encoding": "opcode", "byte_width": 1},
            ]},
            "CWD": {"description": "Convert word to dword", "variants": [
                {"operands": [], "opcode": "0x99", "encoding": "opcode", "byte_width": 1},
            ]},
            "XCHG": {"description": "Exchange", "variants": [
                {"operands": ["reg", "reg"], "opcode": "0x87", "encoding": "opcode + modrm", "byte_width": 2},
            ]},
            "IRET": {"description": "Interrupt return", "variants": [
                {"operands": [], "opcode": "0xCF", "encoding": "opcode", "byte_width": 1},
            ]},
        },
        "directives": {
            "ORG": {"description": "Set origin", "operands": ["imm"]},
            "DB": {"description": "Define byte", "operands": ["data"], "byte_width": 1},
            "DW": {"description": "Define word", "operands": ["data"], "byte_width": 2},
            "DD": {"description": "Define dword", "operands": ["data"], "byte_width": 4},
            "EQU": {"description": "Equate", "operands": ["value"], "no_emit": True},
            "RESB": {"description": "Reserve bytes", "operands": ["count"]},
            "RESW": {"description": "Reserve words", "operands": ["count"], "byte_width": 2},
            "ALIGN": {"description": "Align", "operands": ["boundary"]},
            "EVEN": {"description": "Align even", "operands": []},
            "MODEL": {"description": "Memory model", "operands": ["type"], "no_emit": True, "valid_values": ["TINY", "SMALL", "MEDIUM", "COMPACT", "LARGE", "HUGE", "FLAT"]},
            "STACK": {"description": "Stack size", "operands": ["size"], "no_emit": True},
            "DATA": {"description": "Data segment", "operands": [], "no_emit": True},
            "CODE": {"description": "Code segment", "operands": [], "no_emit": True},
            "SEGMENT": {"description": "Segment", "operands": ["name"], "no_emit": True},
            "ENDS": {"description": "End segment", "operands": [], "no_emit": True},
            "PROC": {"description": "Procedure", "operands": ["name"], "no_emit": True},
            "ENDP": {"description": "End procedure", "operands": [], "no_emit": True},
            "ASSUME": {"description": "Assume", "operands": ["regs"], "no_emit": True},
            "PUBLIC": {"description": "Public", "operands": ["symbols"], "no_emit": True},
            "EXTERN": {"description": "External", "operands": ["symbols"], "no_emit": True},
            "EXTRN": {"description": "External", "operands": ["symbols"], "no_emit": True},
            "GLOBAL": {"description": "Global", "operands": ["symbols"], "no_emit": True},
            "INCLUDE": {"description": "Include", "operands": ["filename"], "no_emit": True},
            "MACRO": {"description": "Macro", "operands": ["name"], "no_emit": True},
            "ENDM": {"description": "End macro", "operands": [], "no_emit": True},
            "LOCAL": {"description": "Local", "operands": ["labels"], "no_emit": True},
            "IF": {"description": "If", "operands": ["cond"], "no_emit": True},
            "IFDEF": {"description": "If defined", "operands": ["symbol"], "no_emit": True},
            "IFNDEF": {"description": "If not defined", "operands": ["symbol"], "no_emit": True},
            "ELSE": {"description": "Else", "operands": [], "no_emit": True},
            "ENDIF": {"description": "End if", "operands": [], "no_emit": True},
            "END": {"description": "End", "operands": ["entry"], "no_emit": True},
            "SECTION": {"description": "Section", "operands": ["name"], "no_emit": True},
        }
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 70)
    print("DYNAMIC TWO-PASS ASSEMBLER WITH MACRO SUPPORT")
    print("=" * 70)
    
    isa = ISADefinition(create_full_isa())
    assembler = AssemblerEngine(isa)
    
    # Test 1: MASM-style
    print("\n" + "=" * 70)
    print("TEST 1: MASM-Style Program")
    print("=" * 70)
    
    masm_source = """; MASM-style
.MODEL SMALL
.STACK 100h
.DATA
    msg DB "Hello", 0
.CODE
main:
    MOV AX, 0x1234
    MOV BX, AX
    ADD AX, BX
    INT 0x21
    RET
END main
"""
    print("Source:", masm_source)
    result = assembler.assemble(masm_source)
    if result:
        print("✓ Assembly SUCCESSFUL")
        print(assembler.symbol_table.dump())
        print(f"Machine Code: {assembler.emitter.get_hex_string()}")
        print(f"Hex Dump:\n{assembler.emitter.get_formatted_hex()}")
    else:
        print("✗ Assembly FAILED")
        print(assembler.errors.report())
    
    # Test 2: Loop
    print("\n" + "=" * 70)
    print("TEST 2: Loop Example")
    print("=" * 70)
    
    loop_source = """start:
    MOV CX, 10
    XOR AX, AX
loop_start:
    ADD AX, CX
    DEC CX
    LOOP loop_start
done:
    RET
"""
    print("Source:", loop_source)
    result = assembler.assemble(loop_source)
    if result:
        print("✓ Assembly SUCCESSFUL")
        print(assembler.symbol_table.dump())
        print(f"Machine Code: {assembler.emitter.get_hex_string()}")
        print(f"Hex Dump:\n{assembler.emitter.get_formatted_hex()}")
    else:
        print("✗ Assembly FAILED")
        print(assembler.errors.report())
    
    # Test 3: Macro
    print("\n" + "=" * 70)
    print("TEST 3: Macro Example")
    print("=" * 70)
    
    macro_source = """PUSHREG MACRO
    PUSH AX
    PUSH BX
    PUSH CX
ENDM

ADDVAL MACRO reg, val
    ADD reg, val
ENDM

start:
    PUSHREG
    MOV AX, 5
    ADDVAL AX, 10
    POP CX
    POP BX
    POP AX
    RET
"""
    print("Source:", macro_source)
    result = assembler.assemble(macro_source)
    if result:
        print("✓ Assembly SUCCESSFUL")
        print(assembler.symbol_table.dump())
        print(f"Machine Code: {assembler.emitter.get_hex_string()}")
        print(f"Hex Dump:\n{assembler.emitter.get_formatted_hex()}")
        print(assembler.get_listing())
    else:
        print("✗ Assembly FAILED")
        print(assembler.errors.report())
    
    # Test 4: Conditional jumps
    print("\n" + "=" * 70)
    print("TEST 4: Conditional Jumps")
    print("=" * 70)
    
    branch_source = """start:
    MOV AX, 10
    MOV BX, 5
    CMP AX, BX
    JG greater
    JL lesser
    JMP equal
greater:
    MOV CX, 1
    JMP done
lesser:
    MOV CX, 2
    JMP done
equal:
    MOV CX, 0
done:
    RET
"""
    print("Source:", branch_source)
    result = assembler.assemble(branch_source)
    if result:
        print("✓ Assembly SUCCESSFUL")
        print(assembler.symbol_table.dump())
        print(f"Machine Code: {assembler.emitter.get_hex_string()}")
        print(f"Hex Dump:\n{assembler.emitter.get_formatted_hex()}")
        print(assembler.get_statistics())
    else:
        print("✗ Assembly FAILED")
        print(assembler.errors.report())
    
    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()
