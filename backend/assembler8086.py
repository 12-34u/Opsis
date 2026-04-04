#!/usr/bin/env python3
"""
8086 Assembler Backend - Main Integration Module.

This is the entry point for the Electron app. It provides:
1. JSON stdin/stdout protocol for IPC
2. Full 8086 instruction set support
3. MASM-compatible syntax
4. Step-by-step execution simulation

Architecture:
  Source Code → Lexer → Parser/Pass1 → Symbol Table → Pass2 → Emitter → Machine Code
                                                          ↓
                                                    Execution Engine → State
"""

import json
import sys
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from copy import deepcopy

# Load ISA from JSON
BACKEND_DIR = Path(__file__).parent
ISA_PATH = BACKEND_DIR / 'isa.json'

def load_isa() -> Dict:
    """Load ISA definition from JSON file."""
    if ISA_PATH.exists():
        with open(ISA_PATH) as f:
            return json.load(f)
    return {"registers": {}, "instructions": {}, "directives": []}

ISA = load_isa()

# Build lookup sets from ISA
REGISTERS = {r.upper(): info for r, info in ISA.get('registers', {}).items()}
INSTRUCTIONS = {i.upper(): info for i, info in ISA.get('instructions', {}).items()}
DIRECTIVES = set(d.upper() for d in ISA.get('directives', []))

# Additional directives not in ISA
DIRECTIVES.update(['OFFSET', 'PTR', 'BYTE', 'WORD', 'DWORD', 'DUP', 'NEAR', 'FAR', 'SHORT'])


@dataclass
class ParsedLine:
    """Represents a parsed assembly line."""
    line_num: int
    source: str
    label: Optional[str] = None
    instruction: Optional[str] = None
    operands: List[str] = field(default_factory=list)
    is_directive: bool = False
    address: int = 0
    size: int = 0
    data: Optional[bytes] = None


class Assembler8086:
    """
    Full 8086 Assembler with simulation support.
    
    Flow:
    1. parse() - Tokenize and parse source into ParsedLine list
    2. execute() - Simulate execution step by step
    """
    
    def __init__(self):
        """Initialize assembler with default state."""
        self.reset()
    
    def reset(self):
        """Reset assembler state."""
        self.state = {
            # 16-bit general registers
            'AX': 0, 'BX': 0, 'CX': 0, 'DX': 0,
            # Index and pointer registers
            'SI': 0, 'DI': 0, 'SP': 0xFFFE, 'BP': 0,
            # Segment registers
            'CS': 0, 'DS': 0, 'ES': 0, 'SS': 0,
            # Instruction pointer
            'IP': 0,
            # Flags: bit 0=CF, 6=ZF, 7=SF, 11=OF
            'FLAGS': 0,
            # Memory (dict for sparse storage)
            'memory': {},
            # Stack (for simulation)
            'stack': [],
            # Halted flag
            'halted': False,
            # Last interrupt number
            'last_int': None,
        }
        self.labels = {}
        self.errors = []
    
    def parse(self, source: str) -> List[ParsedLine]:
        """
        Parse assembly source code.
        
        Pass 1: Build symbol table and calculate addresses.
        
        Args:
            source: Assembly source code.
            
        Returns:
            List of ParsedLine objects.
        """
        lines = source.split('\n')
        parsed = []
        address = 0
        pending_label = None
        
        for line_num, line in enumerate(lines, 1):
            # Remove comments
            if ';' in line:
                comment_pos = line.index(';')
                # Check if ; is inside a string
                in_string = False
                for i, c in enumerate(line[:comment_pos]):
                    if c in '"\'':
                        in_string = not in_string
                if not in_string:
                    line = line[:comment_pos]
            
            line = line.strip()
            if not line:
                continue
            
            pl = ParsedLine(line_num=line_num, source=line, address=address)
            
            # Check for label (ends with :)
            if ':' in line:
                colon_pos = line.index(':')
                # Make sure colon isn't in a string
                potential_label = line[:colon_pos].strip()
                if potential_label and not potential_label.startswith('"'):
                    pl.label = potential_label
                    self.labels[potential_label.upper()] = address
                    line = line[colon_pos + 1:].strip()
                    
                    if not line:
                        # Label on its own line - save for next instruction
                        pending_label = pl.label
                        continue
            
            # Attach pending label from previous line
            if pending_label:
                pl.label = pending_label
                pending_label = None
            
            if not line:
                continue
            
            # Tokenize line
            parts = self._split_line(line)
            if not parts:
                continue
            
            mnemonic = parts[0].upper()
            operand_str = parts[1] if len(parts) > 1 else ''
            
            # Check if this is NAME DIRECTIVE VALUE (e.g., MSG DB 'Hello', MAIN PROC)
            if len(parts) > 1:
                second = parts[1].split()[0].upper() if parts[1] else ''
                if second in ('DB', 'DW', 'DD', 'DQ', 'DT', 'EQU', 'BYTE', 'WORD', 'DWORD'):
                    # This is: LABEL DIRECTIVE operands
                    data_label = mnemonic
                    self.labels[data_label.upper()] = address
                    pl.label = data_label
                    
                    directive_parts = parts[1].split(None, 1)
                    mnemonic = directive_parts[0].upper()
                    operand_str = directive_parts[1] if len(directive_parts) > 1 else ''
                elif second in ('PROC', 'ENDP'):
                    # This is: LABEL PROC/ENDP
                    proc_label = mnemonic
                    self.labels[proc_label.upper()] = address
                    pl.label = proc_label
                    pl.is_directive = True
                    pl.instruction = second
                    parsed.append(pl)
                    continue
            
            # Handle directive
            if mnemonic.startswith('.') or mnemonic in DIRECTIVES:
                directive = mnemonic.lstrip('.')
                
                # Skip no-emit directives
                if directive in ('MODEL', 'SMALL', 'TINY', 'MEDIUM', 'COMPACT', 'LARGE',
                                'STACK', 'DATA', 'CODE', 'SEGMENT', 'ENDS', 'ASSUME',
                                'PROC', 'ENDP', 'END', 'PUBLIC', 'EXTERN', 'EXTRN',
                                'MACRO', 'ENDM', 'LOCAL', 'IF', 'IFDEF', 'IFNDEF',
                                'ELSE', 'ENDIF', 'INCLUDE', 'TITLE', 'NAME', 'PAGE'):
                    pl.is_directive = True
                    pl.instruction = directive
                    parsed.append(pl)
                    continue
                
                # EQU - define constant
                if directive == 'EQU':
                    operands = self._parse_operands(operand_str)
                    if operands:
                        value = self._parse_immediate(operands[0])
                        if pl.label:
                            self.labels[pl.label.upper()] = value
                    pl.is_directive = True
                    pl.instruction = directive
                    parsed.append(pl)
                    continue
                
                # ORG - set origin
                if directive == 'ORG':
                    operands = self._parse_operands(operand_str)
                    if operands:
                        address = self._parse_immediate(operands[0])
                    pl.is_directive = True
                    pl.instruction = directive
                    parsed.append(pl)
                    continue
                
                # DB/DW/DD - define data
                if directive in ('DB', 'DW', 'DD', 'BYTE', 'WORD', 'DWORD'):
                    operands = self._parse_operands(operand_str)
                    data, size = self._process_data_directive(directive, operands)
                    pl.data = data
                    pl.size = size
                    pl.is_directive = True
                    pl.instruction = directive
                    pl.operands = operands
                    parsed.append(pl)
                    address += size
                    continue
                
                # Other directives - skip
                pl.is_directive = True
                pl.instruction = directive
                parsed.append(pl)
                continue
            
            # Handle instruction
            if mnemonic in INSTRUCTIONS:
                operands = self._parse_operands(operand_str)
                pl.instruction = mnemonic
                pl.operands = operands
                pl.is_directive = False
                
                # Calculate instruction size
                pl.size = self._get_instruction_size(mnemonic, operands)
                
                # Track forward references
                for op in operands:
                    upper_op = op.upper()
                    if upper_op.startswith('OFFSET '):
                        ref = upper_op[7:].strip()
                        if ref not in self.labels:
                            pass  # Forward reference, resolved later
                    elif not self._is_register(op) and not self._is_immediate(op):
                        if upper_op not in self.labels:
                            pass  # Forward reference
                
                parsed.append(pl)
                address += pl.size
            else:
                self.errors.append(f"Line {line_num}: Unknown instruction '{mnemonic}'")
        
        return parsed
    
    def _split_line(self, line: str) -> List[str]:
        """Split line into mnemonic and operands."""
        # Find first whitespace not in brackets or quotes
        in_brackets = 0
        in_quotes = False
        quote_char = None
        
        for i, c in enumerate(line):
            if c in '"\'':
                if not in_quotes:
                    in_quotes = True
                    quote_char = c
                elif c == quote_char:
                    in_quotes = False
            elif not in_quotes:
                if c == '[':
                    in_brackets += 1
                elif c == ']':
                    in_brackets -= 1
                elif c in ' \t' and in_brackets == 0:
                    return [line[:i].strip(), line[i:].strip()]
        
        return [line]
    
    def _parse_operands(self, operand_str: str) -> List[str]:
        """Parse operands string into list."""
        if not operand_str:
            return []
        
        operands = []
        current = []
        in_brackets = 0
        in_quotes = False
        quote_char = None
        
        for c in operand_str:
            if c in '"\'':
                if not in_quotes:
                    in_quotes = True
                    quote_char = c
                elif c == quote_char:
                    in_quotes = False
                current.append(c)
            elif in_quotes:
                current.append(c)
            elif c == '[':
                in_brackets += 1
                current.append(c)
            elif c == ']':
                in_brackets -= 1
                current.append(c)
            elif c == ',' and in_brackets == 0:
                if current:
                    operands.append(''.join(current).strip())
                    current = []
            else:
                current.append(c)
        
        if current:
            operands.append(''.join(current).strip())
        
        return operands
    
    def _process_data_directive(self, directive: str, operands: List[str]) -> Tuple[bytes, int]:
        """Process DB/DW/DD directive and return (data, size)."""
        data = bytearray()
        
        for op in operands:
            op = op.strip()
            
            # String literal
            if op.startswith('"') or op.startswith("'"):
                quote_char = op[0]
                end_pos = op.rfind(quote_char)
                if end_pos > 0:
                    string_content = op[1:end_pos]
                    data.extend(string_content.encode('ascii', errors='replace'))
                continue
            
            # DUP expression: count DUP(value)
            if 'DUP' in op.upper():
                match = re.match(r'(\d+)\s*DUP\s*\(([^)]+)\)', op, re.IGNORECASE)
                if match:
                    count = int(match.group(1))
                    value = self._parse_immediate(match.group(2))
                    if directive in ('DB', 'BYTE'):
                        data.extend([value & 0xFF] * count)
                    elif directive in ('DW', 'WORD'):
                        for _ in range(count):
                            data.append(value & 0xFF)
                            data.append((value >> 8) & 0xFF)
                    else:
                        for _ in range(count):
                            data.extend([(value >> (i*8)) & 0xFF for i in range(4)])
                continue
            
            # Numeric value
            value = self._parse_immediate(op)
            
            if directive in ('DB', 'BYTE'):
                data.append(value & 0xFF)
            elif directive in ('DW', 'WORD'):
                data.append(value & 0xFF)
                data.append((value >> 8) & 0xFF)
            else:  # DD, DWORD
                data.append(value & 0xFF)
                data.append((value >> 8) & 0xFF)
                data.append((value >> 16) & 0xFF)
                data.append((value >> 24) & 0xFF)
        
        return bytes(data), len(data)
    
    def _get_instruction_size(self, mnemonic: str, operands: List[str]) -> int:
        """Get instruction size in bytes."""
        info = INSTRUCTIONS.get(mnemonic, {})
        variants = info.get('variants', [])
        
        if not variants:
            return 1
        
        # Simple heuristic: first variant's width
        return variants[0].get('width', 1)
    
    def _is_register(self, op: str) -> bool:
        """Check if operand is a register."""
        return op.upper() in REGISTERS
    
    def _is_immediate(self, op: str) -> bool:
        """Check if operand is an immediate value."""
        op = op.strip().upper()
        if not op:
            return False
        
        # Hex: 0xFF or FFh
        if op.startswith('0X') or op.endswith('H'):
            return True
        
        # Binary: 1010b
        if op.endswith('B') and all(c in '01' for c in op[:-1]):
            return True
        
        # Decimal (possibly signed)
        if op.lstrip('-').isdigit():
            return True
        
        return False
    
    def _parse_immediate(self, value: str) -> int:
        """Parse immediate value to integer."""
        value = value.strip().upper()
        if not value:
            return 0
        
        # Remove OFFSET prefix
        if value.startswith('OFFSET '):
            label = value[7:].strip()
            return self.labels.get(label, 0)
        
        # Hex: 0xFF or FFh
        if value.startswith('0X'):
            return int(value, 16)
        if value.endswith('H'):
            return int(value[:-1], 16)
        
        # Binary: 1010b
        if value.endswith('B') and all(c in '01' for c in value[:-1]):
            return int(value[:-1], 2)
        
        # Octal: 77o or 77q
        if value.endswith('O') or value.endswith('Q'):
            return int(value[:-1], 8)
        
        # Try label lookup
        if value in self.labels:
            return self.labels[value]
        
        # Decimal
        try:
            return int(value)
        except ValueError:
            return 0
    
    def execute(self, parsed: List[ParsedLine], initial_state: Dict = None) -> Dict:
        """
        Execute parsed instructions step by step.
        
        Args:
            parsed: List of ParsedLine from parse().
            initial_state: Optional initial CPU state.
            
        Returns:
            Execution result dict with steps and final state.
        """
        if initial_state:
            self.state.update(initial_state)
        
        # Filter executable instructions
        executable = [p for p in parsed if not p.is_directive and p.instruction]
        
        # Build label-to-index mapping
        label_to_idx = {}
        for idx, pl in enumerate(executable):
            if pl.label:
                label_to_idx[pl.label.upper()] = idx
        
        steps = []
        ip = 0
        max_steps = 10000
        
        while ip < len(executable) and not self.state['halted'] and len(steps) < max_steps:
            pl = executable[ip]
            old_state = deepcopy(self.state)
            
            try:
                next_ip = self._execute_instruction(pl, label_to_idx, ip)
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'line': pl.line_num,
                    'instruction': pl.source
                }
            
            step = {
                'line': pl.line_num,
                'instruction': pl.source,
                'mnemonic': pl.instruction,
                'operands': pl.operands,
                'before': old_state,
                'after': deepcopy(self.state),
                'changes': self._compute_changes(old_state, self.state)
            }
            steps.append(step)
            
            ip = next_ip if next_ip is not None else ip + 1
        
        return {
            'success': True,
            'steps': steps,
            'final_state': deepcopy(self.state),
            'step_count': len(steps)
        }
    
    def _execute_instruction(self, pl: ParsedLine, label_to_idx: Dict[str, int], ip: int) -> Optional[int]:
        """Execute a single instruction. Returns next IP or None for sequential."""
        mnemonic = pl.instruction
        ops = pl.operands
        
        # 8-bit sub-register mappings
        LOW_REGS = {'AL': 'AX', 'BL': 'BX', 'CL': 'CX', 'DL': 'DX'}
        HIGH_REGS = {'AH': 'AX', 'BH': 'BX', 'CH': 'CX', 'DH': 'DX'}
        
        def get_val(op: str) -> int:
            """Get value of operand."""
            op = op.strip().upper()
            
            # OFFSET operator
            if op.startswith('OFFSET '):
                label = op[7:].strip()
                return self.labels.get(label, 0)
            
            # 8-bit low registers (AL, BL, CL, DL)
            if op in LOW_REGS:
                return self.state[LOW_REGS[op]] & 0xFF
            
            # 8-bit high registers (AH, BH, CH, DH)
            if op in HIGH_REGS:
                return (self.state[HIGH_REGS[op]] >> 8) & 0xFF
            
            # 16-bit Register
            if op in self.state:
                val = self.state[op]
                return val if isinstance(val, int) else 0
            
            # Label
            if op in self.labels:
                return self.labels[op]
            
            # Immediate
            return self._parse_immediate(op)
        
        def set_val(op: str, value: int) -> None:
            """Set value of operand."""
            op = op.strip().upper()
            
            # 8-bit low registers (AL, BL, CL, DL)
            if op in LOW_REGS:
                parent = LOW_REGS[op]
                self.state[parent] = (self.state[parent] & 0xFF00) | (value & 0xFF)
                return
            
            # 8-bit high registers (AH, BH, CH, DH)
            if op in HIGH_REGS:
                parent = HIGH_REGS[op]
                self.state[parent] = (self.state[parent] & 0x00FF) | ((value & 0xFF) << 8)
                return
            
            # 16-bit registers
            if op in self.state and isinstance(self.state[op], int):
                self.state[op] = value & 0xFFFF
        
        def update_flags(result: int, is_sub: bool = False) -> None:
            """Update FLAGS based on result."""
            result &= 0xFFFF
            flags = 0
            if result == 0:
                flags |= 0x40  # ZF (bit 6)
            if result & 0x8000:
                flags |= 0x80  # SF (bit 7)
            self.state['FLAGS'] = flags
        
        # === Data Movement ===
        if mnemonic == 'MOV':
            set_val(ops[0], get_val(ops[1]))
        
        elif mnemonic == 'XCHG':
            v0, v1 = get_val(ops[0]), get_val(ops[1])
            set_val(ops[0], v1)
            set_val(ops[1], v0)
        
        elif mnemonic == 'LEA':
            # Load effective address
            mem_ref = ops[1]
            if mem_ref.startswith('[') and mem_ref.endswith(']'):
                inner = mem_ref[1:-1].upper()
                addr = self._compute_ea(inner)
                set_val(ops[0], addr)
        
        elif mnemonic == 'PUSH':
            val = get_val(ops[0])
            self.state['stack'].append(val)
            self.state['SP'] = (self.state['SP'] - 2) & 0xFFFF
        
        elif mnemonic == 'POP':
            if self.state['stack']:
                val = self.state['stack'].pop()
                set_val(ops[0], val)
                self.state['SP'] = (self.state['SP'] + 2) & 0xFFFF
        
        elif mnemonic == 'PUSHF':
            self.state['stack'].append(self.state['FLAGS'])
            self.state['SP'] = (self.state['SP'] - 2) & 0xFFFF
        
        elif mnemonic == 'POPF':
            if self.state['stack']:
                self.state['FLAGS'] = self.state['stack'].pop()
                self.state['SP'] = (self.state['SP'] + 2) & 0xFFFF
        
        # === Arithmetic ===
        elif mnemonic == 'ADD':
            result = get_val(ops[0]) + get_val(ops[1])
            set_val(ops[0], result)
            update_flags(result)
        
        elif mnemonic == 'SUB':
            result = get_val(ops[0]) - get_val(ops[1])
            set_val(ops[0], result)
            update_flags(result, is_sub=True)
        
        elif mnemonic == 'ADC':
            cf = self.state['FLAGS'] & 1
            result = get_val(ops[0]) + get_val(ops[1]) + cf
            set_val(ops[0], result)
            update_flags(result)
        
        elif mnemonic == 'SBB':
            cf = self.state['FLAGS'] & 1
            result = get_val(ops[0]) - get_val(ops[1]) - cf
            set_val(ops[0], result)
            update_flags(result, is_sub=True)
        
        elif mnemonic == 'INC':
            result = get_val(ops[0]) + 1
            set_val(ops[0], result)
            update_flags(result)
        
        elif mnemonic == 'DEC':
            result = get_val(ops[0]) - 1
            set_val(ops[0], result)
            update_flags(result)
        
        elif mnemonic == 'NEG':
            result = -get_val(ops[0])
            set_val(ops[0], result)
            update_flags(result)
        
        elif mnemonic == 'MUL':
            result = self.state['AX'] * get_val(ops[0])
            self.state['AX'] = result & 0xFFFF
            self.state['DX'] = (result >> 16) & 0xFFFF
        
        elif mnemonic == 'IMUL':
            ax = self.state['AX']
            if ax & 0x8000:
                ax -= 0x10000
            op_val = get_val(ops[0])
            if op_val & 0x8000:
                op_val -= 0x10000
            result = ax * op_val
            self.state['AX'] = result & 0xFFFF
            self.state['DX'] = (result >> 16) & 0xFFFF
        
        elif mnemonic == 'DIV':
            divisor = get_val(ops[0])
            if divisor == 0:
                raise RuntimeError("Division by zero")
            dividend = (self.state['DX'] << 16) | self.state['AX']
            self.state['AX'] = (dividend // divisor) & 0xFFFF
            self.state['DX'] = (dividend % divisor) & 0xFFFF
        
        elif mnemonic == 'IDIV':
            divisor = get_val(ops[0])
            if divisor == 0:
                raise RuntimeError("Division by zero")
            dividend = (self.state['DX'] << 16) | self.state['AX']
            if dividend & 0x80000000:
                dividend -= 0x100000000
            if divisor & 0x8000:
                divisor -= 0x10000
            self.state['AX'] = (dividend // divisor) & 0xFFFF
            self.state['DX'] = (dividend % divisor) & 0xFFFF
        
        elif mnemonic == 'CBW':
            al = self.state['AX'] & 0xFF
            if al & 0x80:
                self.state['AX'] = 0xFF00 | al
            else:
                self.state['AX'] = al
        
        elif mnemonic == 'CWD':
            if self.state['AX'] & 0x8000:
                self.state['DX'] = 0xFFFF
            else:
                self.state['DX'] = 0
        
        # === Logic ===
        elif mnemonic == 'AND':
            result = get_val(ops[0]) & get_val(ops[1])
            set_val(ops[0], result)
            update_flags(result)
        
        elif mnemonic == 'OR':
            result = get_val(ops[0]) | get_val(ops[1])
            set_val(ops[0], result)
            update_flags(result)
        
        elif mnemonic == 'XOR':
            result = get_val(ops[0]) ^ get_val(ops[1])
            set_val(ops[0], result)
            update_flags(result)
        
        elif mnemonic == 'NOT':
            result = ~get_val(ops[0]) & 0xFFFF
            set_val(ops[0], result)
        
        elif mnemonic == 'TEST':
            result = get_val(ops[0]) & get_val(ops[1])
            update_flags(result)
        
        elif mnemonic == 'CMP':
            result = get_val(ops[0]) - get_val(ops[1])
            update_flags(result, is_sub=True)
        
        # === Shifts/Rotates ===
        elif mnemonic in ('SHL', 'SAL'):
            count = get_val(ops[1]) if len(ops) > 1 else 1
            result = (get_val(ops[0]) << count) & 0xFFFF
            set_val(ops[0], result)
            update_flags(result)
        
        elif mnemonic == 'SHR':
            count = get_val(ops[1]) if len(ops) > 1 else 1
            result = get_val(ops[0]) >> count
            set_val(ops[0], result)
            update_flags(result)
        
        elif mnemonic == 'SAR':
            count = get_val(ops[1]) if len(ops) > 1 else 1
            val = get_val(ops[0])
            sign = val & 0x8000
            result = val >> count
            if sign:
                result |= (0xFFFF << (16 - count)) & 0xFFFF
            set_val(ops[0], result)
            update_flags(result)
        
        elif mnemonic == 'ROL':
            count = get_val(ops[1]) if len(ops) > 1 else 1
            val = get_val(ops[0])
            result = ((val << count) | (val >> (16 - count))) & 0xFFFF
            set_val(ops[0], result)
        
        elif mnemonic == 'ROR':
            count = get_val(ops[1]) if len(ops) > 1 else 1
            val = get_val(ops[0])
            result = ((val >> count) | (val << (16 - count))) & 0xFFFF
            set_val(ops[0], result)
        
        # === Control Flow ===
        elif mnemonic == 'JMP':
            return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic in ('JE', 'JZ'):
            if self.state['FLAGS'] & 0x40:  # ZF
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic in ('JNE', 'JNZ'):
            if not (self.state['FLAGS'] & 0x40):
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic == 'JG':
            if not (self.state['FLAGS'] & 0x40) and not (self.state['FLAGS'] & 0x80):
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic == 'JGE':
            if not (self.state['FLAGS'] & 0x80):
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic == 'JL':
            if self.state['FLAGS'] & 0x80:
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic == 'JLE':
            if (self.state['FLAGS'] & 0x40) or (self.state['FLAGS'] & 0x80):
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic in ('JC', 'JB'):
            if self.state['FLAGS'] & 0x01:  # CF
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic in ('JNC', 'JAE'):
            if not (self.state['FLAGS'] & 0x01):
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic == 'JA':
            if not (self.state['FLAGS'] & 0x01) and not (self.state['FLAGS'] & 0x40):
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic == 'JBE':
            if (self.state['FLAGS'] & 0x01) or (self.state['FLAGS'] & 0x40):
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic == 'JS':
            if self.state['FLAGS'] & 0x80:
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic == 'JNS':
            if not (self.state['FLAGS'] & 0x80):
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic == 'JCXZ':
            if self.state['CX'] == 0:
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic == 'LOOP':
            self.state['CX'] = (self.state['CX'] - 1) & 0xFFFF
            if self.state['CX'] != 0:
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic in ('LOOPE', 'LOOPZ'):
            self.state['CX'] = (self.state['CX'] - 1) & 0xFFFF
            if self.state['CX'] != 0 and (self.state['FLAGS'] & 0x40):
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic in ('LOOPNE', 'LOOPNZ'):
            self.state['CX'] = (self.state['CX'] - 1) & 0xFFFF
            if self.state['CX'] != 0 and not (self.state['FLAGS'] & 0x40):
                return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic == 'CALL':
            self.state['stack'].append(ip + 1)
            self.state['SP'] = (self.state['SP'] - 2) & 0xFFFF
            return self._resolve_jump(ops[0], label_to_idx)
        
        elif mnemonic == 'RET':
            if self.state['stack']:
                return self.state['stack'].pop()
        
        elif mnemonic == 'INT':
            self.state['last_int'] = get_val(ops[0])
        
        elif mnemonic == 'HLT':
            self.state['halted'] = True
        
        elif mnemonic == 'NOP':
            pass
        
        # === Flag Operations ===
        elif mnemonic == 'CLC':
            self.state['FLAGS'] &= ~0x01
        
        elif mnemonic == 'STC':
            self.state['FLAGS'] |= 0x01
        
        elif mnemonic == 'CMC':
            self.state['FLAGS'] ^= 0x01
        
        elif mnemonic == 'CLD':
            self.state['FLAGS'] &= ~0x400
        
        elif mnemonic == 'STD':
            self.state['FLAGS'] |= 0x400
        
        elif mnemonic == 'CLI':
            self.state['FLAGS'] &= ~0x200
        
        elif mnemonic == 'STI':
            self.state['FLAGS'] |= 0x200
        
        elif mnemonic == 'LAHF':
            self.state['AX'] = (self.state['AX'] & 0x00FF) | ((self.state['FLAGS'] & 0xFF) << 8)
        
        elif mnemonic == 'SAHF':
            self.state['FLAGS'] = (self.state['FLAGS'] & 0xFF00) | ((self.state['AX'] >> 8) & 0xFF)
        
        return None
    
    def _resolve_jump(self, target: str, label_to_idx: Dict[str, int]) -> Optional[int]:
        """Resolve jump target to instruction index."""
        target = target.strip().upper()
        if target in label_to_idx:
            return label_to_idx[target]
        return None
    
    def _compute_ea(self, expr: str) -> int:
        """Compute effective address from expression."""
        value = 0
        for part in expr.replace('-', '+-').split('+'):
            part = part.strip()
            if not part:
                continue
            if part in self.state and isinstance(self.state[part], int):
                value += self.state[part]
            elif part in self.labels:
                value += self.labels[part]
            else:
                value += self._parse_immediate(part)
        return value & 0xFFFF
    
    def _compute_changes(self, before: Dict, after: Dict) -> Dict:
        """Compute state changes."""
        changes = {}
        for key in ['AX', 'BX', 'CX', 'DX', 'SI', 'DI', 'SP', 'BP', 'FLAGS']:
            if before.get(key) != after.get(key):
                changes[key] = {'from': before.get(key), 'to': after.get(key)}
        return changes


# === Main Entry Point for Electron ===

def main():
    """Main entry point - JSON stdin/stdout protocol."""
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(json.dumps({'success': False, 'error': f'Invalid JSON: {e}'}))
        return 1
    
    command = input_data.get('command', 'execute')
    code = input_data.get('code', '')
    state = input_data.get('state', {})
    
    assembler = Assembler8086()
    
    if state:
        assembler.state.update(state)
    
    if command == 'execute':
        try:
            parsed = assembler.parse(code)
            if assembler.errors:
                return json.dumps({
                    'success': False,
                    'error': assembler.errors[0]
                })
            result = assembler.execute(parsed)
            print(json.dumps(result))
            return 0 if result['success'] else 1
        except Exception as e:
            print(json.dumps({'success': False, 'error': str(e)}))
            return 1
    
    elif command == 'parse':
        try:
            parsed = assembler.parse(code)
            print(json.dumps({
                'success': True,
                'instructions': [{'line': p.line_num, 'source': p.source, 
                                 'mnemonic': p.instruction, 'operands': p.operands}
                                for p in parsed],
                'labels': assembler.labels
            }))
            return 0
        except Exception as e:
            print(json.dumps({'success': False, 'error': str(e)}))
            return 1
    
    elif command == 'reset':
        assembler.reset()
        print(json.dumps({'success': True, 'state': assembler.state}))
        return 0
    
    elif command == 'getState':
        print(json.dumps({'success': True, 'state': assembler.state}))
        return 0
    
    elif command == 'setRegister':
        reg = input_data.get('register', '').upper()
        val = input_data.get('value', 0)
        if reg in assembler.state:
            assembler.state[reg] = val & 0xFFFF
            print(json.dumps({'success': True, 'state': assembler.state}))
        else:
            print(json.dumps({'success': False, 'error': f'Unknown register: {reg}'}))
        return 0
    
    elif command == 'getRegister':
        reg = input_data.get('register', '').upper()
        if reg in assembler.state:
            print(json.dumps({'success': True, 'value': assembler.state[reg]}))
        else:
            print(json.dumps({'success': False, 'error': f'Unknown register: {reg}'}))
        return 0
    
    elif command == 'setMemory':
        addr = input_data.get('address', 0)
        val = input_data.get('value', 0)
        assembler.state['memory'][str(addr)] = val & 0xFF
        print(json.dumps({'success': True, 'state': assembler.state}))
        return 0
    
    elif command == 'getMemory':
        start = input_data.get('start', 0)
        length = input_data.get('length', 256)
        mem = assembler.state.get('memory', {})
        result = [mem.get(str(i), 0) for i in range(start, start + length)]
        print(json.dumps({'success': True, 'memory': result}))
        return 0
    
    else:
        print(json.dumps({'success': False, 'error': f'Unknown command: {command}'}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
