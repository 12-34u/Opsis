#!/usr/bin/env python3
"""
8086 assembler/interpreter backend for Opsis.
Accepts JSON requests on stdin and emits JSON responses on stdout.
"""

import json
import sys
from copy import deepcopy


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
    def __init__(self, state=None):
        self.load_state(state if state else make_initial_state())
        self.output = []
        self.execution_state = "stopped"
        self.instruction_count = 0

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

    def parse(self, code):
        instructions = []
        labels = {}
        for raw_line in code.split("\n"):
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
        return instructions, labels

    def execute(self, code):
        instructions, labels = self.parse(code)
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
            failed_line = self.pc + 1 if 0 <= self.pc < len(instructions) else None
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
        opcode = parts[0].upper()
        operands = parts[1] if len(parts) > 1 else ""

        if opcode == "MOV":
            dst, src = [x.strip() for x in operands.split(",", 1)]
            self.set_register(dst, self.resolve_operand(src))
        elif opcode == "MVI":
            dst, imm = [x.strip() for x in operands.split(",", 1)]
            self.set_register(dst, self.parse_value(imm))
        elif opcode == "ADD":
            if "," in operands:
                dst, src = self.parse_two_operands(operands)
            else:
                dst, src = "A", operands.strip()
            result = self.resolve_operand(dst) + self.resolve_operand(src)
            self.set_register(dst, result & 0xFFFF)
            self.set_flags(result)
        elif opcode == "SUB":
            if "," in operands:
                dst, src = self.parse_two_operands(operands)
            else:
                dst, src = "A", operands.strip()
            result = self.resolve_operand(dst) - self.resolve_operand(src)
            self.set_register(dst, result & 0xFFFF)
            self.set_flags(result)
        elif opcode == "MUL":
            if "," in operands:
                dst, src = self.parse_two_operands(operands)
            else:
                dst, src = "A", operands.strip()
            result = self.resolve_operand(dst) * self.resolve_operand(src)
            self.set_register(dst, result & 0xFFFF)
            self.set_flags(result)
        elif opcode == "DIV":
            if "," in operands:
                dst, src = self.parse_two_operands(operands)
            else:
                dst, src = "A", operands.strip()
            divisor = self.resolve_operand(src)
            if divisor == 0:
                raise ValueError("Division by zero")
            result = self.resolve_operand(dst) // divisor
            self.set_register(dst, result & 0xFFFF)
            self.set_flags(result)
        elif opcode == "INC":
            reg = operands.strip()
            result = self.resolve_operand(reg) + 1
            self.set_register(reg, result & 0xFFFF)
            self.set_flags(result)
        elif opcode == "DEC":
            reg = operands.strip()
            result = self.resolve_operand(reg) - 1
            self.set_register(reg, result & 0xFFFF)
            self.set_flags(result)
        elif opcode == "CMP":
            if "," in operands:
                left, right = self.parse_two_operands(operands)
            else:
                left, right = "A", operands.strip()
            result = self.resolve_operand(left) - self.resolve_operand(right)
            self.set_flags(result)
        elif opcode == "JMP":
            self.jump_to_label(operands.strip(), labels)
        elif opcode == "JNZ":
            if not self.flags["Z"]:
                self.jump_to_label(operands.strip(), labels)
        elif opcode == "JZ":
            if self.flags["Z"]:
                self.jump_to_label(operands.strip(), labels)
        elif opcode == "LDA":
            addr = self.parse_value(operands.strip())
            self.set_register("AX", self.memory[addr] & 0xFFFF)
        elif opcode == "STA":
            addr = self.parse_value(operands.strip())
            self.memory[addr] = self.resolve_operand("AX") & 0xFFFF
        elif opcode == "OUT":
            value = self.resolve_operand(operands.strip()) if operands.strip() else self.resolve_operand("AX")
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
            self.execution_state = "stopped"
        elif opcode == "NOP":
            pass
        else:
            raise ValueError(f"Unknown instruction: {opcode}")

    def parse_two_operands(self, operands):
        parts = [x.strip() for x in operands.split(",", 1)]
        if len(parts) != 2:
            raise ValueError("Instruction requires two operands")
        return parts[0], parts[1]

    def resolve_operand(self, operand):
        op = operand.upper()
        if op in self.registers:
            return self.registers[op] & 0xFFFF
        return self.parse_value(operand)

    def set_register(self, reg, value):
        reg_u = reg.upper()
        if reg_u not in self.registers:
            raise ValueError(f"Invalid register: {reg}")
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
            return 0
        if val.lower().startswith("0x"):
            return int(val, 16) & 0xFFFF
        if val.lower().endswith("h"):
            return int(val[:-1], 16) & 0xFFFF
        if val.lower().startswith("0b"):
            return int(val, 2) & 0xFFFF
        if val.lower().endswith("b"):
            return int(val[:-1], 2) & 0xFFFF
        return int(val, 10) & 0xFFFF

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
