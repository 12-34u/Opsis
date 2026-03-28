#!/usr/bin/env python3
"""
8086 assembler/interpreter backend for Opsis.
Accepts JSON requests on stdin and emits JSON responses on stdout.
"""

import json
import sys
from copy import deepcopy
from typing import List, Dict, Tuple, Any, Optional


def make_initial_state():
    return {
        "registers": {
            # 8086 registers
            "AX": 0,
            "BX": 0,
            "CX": 0,
            "DX": 0,
            "SI": 0,
            "DI": 0,
            "BP": 0,
            "SP": 0xFFFE,
            "IP": 0,
            # 8085 registers for compatibility
            "A": 0,
            "B": 0,
            "C": 0,
            "D": 0,
            "E": 0,
            "H": 0,
            "L": 0,
            "M": 0,
        },
        "flags": {
            "Z": False,
            "C": False,
            "S": False,
            "P": False,
            "O": False,
        },
        "memory": [0] * 65536,
        "pc": 0,
        "sp": 0xFFFE,
    }


class Assembler8086:
    def __init__(self, state: Optional[Dict[str, Any]] = None):
        self.registers: Dict[str, int] = {}
        self.flags: Dict[str, bool] = {}
        self.memory: List[int] = []
        self.pc: int = 0
        self.sp: int = 0
        self.load_state(state if state else make_initial_state())
        self.output: List[Dict[str, Any]] = []
        self.execution_state: str = "stopped"
        self.instruction_count: int = 0

    def load_state(self, state):
        self.registers = deepcopy(state.get("registers", {}))
        self.flags = deepcopy(state.get("flags", {}))
        self.memory = list(state.get("memory", [0] * 65536))
        self.pc = int(state.get("pc", self.registers.get("IP", 0)))
        self.sp = int(state.get("sp", self.registers.get("SP", 0xFFFE)))
        self.registers["IP"] = self.pc
        self.registers["SP"] = self.sp

    def get_state(self):
        self.registers["IP"] = self.pc & 0xFFFF
        self.registers["SP"] = self.sp & 0xFFFF
        return {
            "registers": deepcopy(self.registers),
            "flags": deepcopy(self.flags),
            "memory": list(self.memory),
            "pc": self.pc & 0xFFFF,
            "sp": self.sp & 0xFFFF,
        }

    def reset(self):
        self.load_state(make_initial_state())
        self.output = []
        self.execution_state = "stopped"
        self.instruction_count = 0

    def parse(self, code: str) -> Tuple[List[str], Dict[str, int], List[int]]:
        instructions: List[str] = []
        labels: Dict[str, int] = {}
        line_mapping: List[int] = []
        for i, raw_line in enumerate(code.split("\n")):
            line = raw_line.strip()
            comment_idx = line.find(";")
            if comment_idx != -1:
                line = line[:comment_idx].strip()
            if not line:
                continue
            if ":" in line:
                label, rest = line.split(":", 1)
                labels[label.strip().upper()] = len(instructions)
                line = rest.strip()
                if not line:
                    continue
            instructions.append(line)
            line_mapping.append(i + 1)
        return instructions, labels, line_mapping

    def execute(self, code):
        instructions, labels, line_mapping = self.parse(code)
        self.pc = 0
        self.registers["IP"] = 0
        self.execution_state = "running"
        self.output = []
        self.instruction_count = 0
        steps = []
        current_instruction = None

        try:
            while self.pc < len(instructions) and self.execution_state == "running":
                line = instructions[self.pc]
                current_instruction = line
                before = self.get_state()
                self.execute_instruction(line, labels)
                after = self.get_state()
                steps.append(
                    {
                        "pc": self.pc,
                        "instruction": line,
                        "before": before,
                        "after": after,
                        "output": self.output[-1] if self.output else None,
                    }
                )
                self.instruction_count += 1
                if self.execution_state == "running":
                    self.pc += 1
                    self.registers["IP"] = self.pc & 0xFFFF

            self.execution_state = "stopped"
            return {
                "success": True,
                "state": self.get_state(),
                "steps": steps,
                "output": self.output,
                "instructionCount": self.instruction_count,
            }
        except Exception as exc:
            failed_line = line_mapping[self.pc] if 0 <= self.pc < len(instructions) else None
            return {
                "success": False,
                "error": str(exc),
                "errorDetails": {
                    "line": failed_line,
                    "pc": self.pc,
                    "instruction": current_instruction,
                },
                "state": self.get_state(),
                "steps": steps,
            }

    def execute_instruction(self, line, labels):
        parts = line.strip().split(None, 1)
        if not parts:
            return
        opcode = parts[0].upper()
        operands = parts[1].strip() if len(parts) > 1 else ""

        if opcode == "MOV":
            dst, src = self.parse_two_operands(operands, opcode)
            self.set_register(dst, self.resolve_operand(src))
        elif opcode == "MVI":
            dst, imm = self.parse_two_operands(operands, opcode)
            self.set_register(dst, self.parse_value(imm))
        elif opcode in ("ADD", "SUB", "MUL", "DIV", "CMP"):
            if not operands:
                raise ValueError(f"Instruction {opcode} requires an operand")
            if "," in operands:
                dst, src = self.parse_two_operands(operands, opcode)
            else:
                dst, src = "A", operands
            
            val_dst = self.resolve_operand(dst)
            val_src = self.resolve_operand(src)
            
            if opcode == "ADD":
                result = val_dst + val_src
            elif opcode == "SUB" or opcode == "CMP":
                result = val_dst - val_src
            elif opcode == "MUL":
                result = val_dst * val_src
            elif opcode == "DIV":
                if val_src == 0:
                    raise ValueError("Division by zero")
                result = val_dst // val_src
                
            if opcode != "CMP":
                self.set_register(dst, result & 0xFFFF)
            self.set_flags(result)
        elif opcode in ("INC", "DEC"):
            if not operands:
                raise ValueError(f"Instruction {opcode} requires a register operand")
            reg = operands.strip().upper()
            if reg not in self.registers:
                raise ValueError(f"Instruction {opcode} requires a valid register, got: '{reg}'")
            val = self.resolve_operand(reg)
            result = val + 1 if opcode == "INC" else val - 1
            self.set_register(reg, result & 0xFFFF)
            self.set_flags(result)
        elif opcode in ("JMP", "JNZ", "JZ"):
            if not operands:
                raise ValueError(f"Instruction {opcode} requires a label operand")
            if opcode == "JMP" or (opcode == "JNZ" and not self.flags["Z"]) or (opcode == "JZ" and self.flags["Z"]):
                self.jump_to_label(operands, labels)
        elif opcode in ("LDA", "STA"):
            if not operands:
                raise ValueError(f"Instruction {opcode} requires a memory address operand")
            addr = self.parse_value(operands)
            if addr < 0 or addr >= len(self.memory):
                raise ValueError(f"Memory address out of range: {addr}")
            if opcode == "LDA":
                self.set_register("AX", self.memory[addr] & 0xFFFF)
            else:
                self.memory[addr] = self.resolve_operand("AX") & 0xFFFF
        elif opcode == "OUT":
            if operands:
                value = self.resolve_operand(operands)
            else:
                value = self.resolve_operand("AX")
            self.output.append(
                {
                    "type": "OUT",
                    "value": value,
                    "hex": f"0x{value:04X}",
                    "decimal": value,
                    "binary": f"{value:016b}",
                }
            )
        elif opcode in ("HLT", "INT"):
            if operands:
                raise ValueError(f"Instruction {opcode} does not take operands")
            self.execution_state = "stopped"
        elif opcode == "NOP":
            if operands:
                raise ValueError(f"Instruction {opcode} does not take operands")
            pass
        else:
            raise ValueError(f"Unknown instruction: '{opcode}'")

    def parse_two_operands(self, operands, opcode=""):
        if not operands:
            raise ValueError(f"Instruction {opcode} requires two operands separated by a comma")
        parts = [x.strip() for x in operands.split(",", 1)]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Instruction {opcode} requires exactly two operands separated by a comma")
        return parts[0], parts[1]

    def resolve_operand(self, operand):
        op = operand.strip()
        if not op:
            raise ValueError("Missing operand")
        op_upper = op.upper()
        if op_upper in self.registers:
            return self.registers[op_upper] & 0xFFFF
        return self.parse_value(op)

    def set_register(self, reg, value):
        reg_u = reg.strip().upper()
        if not reg_u:
            raise ValueError("Missing register")
        if reg_u not in self.registers:
            raise ValueError(f"Invalid register: '{reg}'")
        self.registers[reg_u] = value & 0xFFFF
        # Sync 8085 accumulator A with 8086 accumulator AX
        if reg_u == "A":
            self.registers["AX"] = value & 0xFFFF
        elif reg_u == "AX":
            self.registers["A"] = value & 0xFFFF
        if reg_u == "IP":
            self.pc = self.registers[reg_u]
        if reg_u == "SP":
            self.sp = self.registers[reg_u]

    def parse_value(self, raw):
        val = raw.strip()
        if not val:
            raise ValueError("Missing value/number operand")
        try:
            val_lower = val.lower()
            if val_lower.startswith("0x"):
                return int(val, 16) & 0xFFFF
            if val_lower.endswith("h"):
                return int(val[:-1], 16) & 0xFFFF
            if val_lower.startswith("0b"):
                return int(val, 2) & 0xFFFF
            if val_lower.endswith("b"):
                return int(val[:-1], 2) & 0xFFFF
            
            # If no base prefix/suffix, assume decimal
            return int(val, 10) & 0xFFFF
        except ValueError:
            # Re-raise standard int() casting errors as clean ASM syntax errors
            raise ValueError(f"Invalid operand, number format, or missing 'H'/'B' suffix: '{val}'")

    def jump_to_label(self, label, labels):
        key = label.upper()
        if key not in labels:
            raise ValueError(f"Unknown label: {label}")
        self.pc = labels[key] - 1
        self.registers["IP"] = (self.pc + 1) & 0xFFFF

    def set_flags(self, value):
        v = value & 0xFFFF
        self.flags["Z"] = v == 0
        self.flags["S"] = (v & 0x8000) != 0
        self.flags["P"] = bin(v & 0xFF).count("1") % 2 == 0
        self.flags["C"] = value > 0xFFFF
        self.flags["O"] = False


def handle_request(payload):
    command = payload.get("command")
    state = payload.get("state")
    asm = Assembler8086(state)

    if command == "execute":
        return asm.execute(payload.get("code", ""))
    if command == "reset":
        asm.reset()
        return {"success": True, "state": asm.get_state()}
    if command == "getState":
        return {"success": True, "state": asm.get_state()}
    if command == "setRegister":
        reg = payload.get("register")
        value = payload.get("value", 0)
        asm.set_register(reg, int(value))
        return {"success": True, "state": asm.get_state()}
    if command == "getRegister":
        reg = payload.get("register")
        value = asm.resolve_operand(reg)
        return {"success": True, "value": value, "state": asm.get_state()}
    if command == "getMemory":
        start = int(payload.get("start", 0))
        length = int(payload.get("length", 256))
        mem = asm.memory[start : start + length]
        return {"success": True, "memory": mem, "start": start, "state": asm.get_state()}
    if command == "setMemory":
        address = int(payload.get("address", 0))
        value = int(payload.get("value", 0)) & 0xFFFF
        if address < 0 or address >= len(asm.memory):
            raise ValueError("Memory address out of range")
        asm.memory[address] = value
        return {"success": True, "state": asm.get_state()}

    raise ValueError(f"Unknown command: {command}")


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        result = handle_request(payload)
    except Exception as exc:
        result = {"success": False, "error": str(exc)}
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    main()
