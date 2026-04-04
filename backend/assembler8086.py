#!/usr/bin/env python3
"""
8086 Assembler Backend for Electron App Integration.

This module provides the JSON stdin/stdout interface for the Electron app.
It uses the modular assembler engine with data-driven ISA.
"""

from __future__ import annotations
import json
import sys
import os
from typing import Dict, List, Any, Optional
from copy import deepcopy
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import modular assembler components
from lexer import Lexer, TokenType
from symbol_table import SymbolTable
from emitter import Emitter
from directives import DirectiveHandler
from error_reporter import ErrorReporter, Phase


# Default ISA schema embedded for standalone operation
DEFAULT_ISA = {
    "name": "x86-16",
    "endianness": "little",
    "registers": {
        "AX": {"code": 0, "width": 16, "type": "general"},
        "CX": {"code": 1, "width": 16, "type": "general"},
        "DX": {"code": 2, "width": 16, "type": "general"},
        "BX": {"code": 3, "width": 16, "type": "general"},
        "SP": {"code": 4, "width": 16, "type": "stack"},
        "BP": {"code": 5, "width": 16, "type": "stack"},
        "SI": {"code": 6, "width": 16, "type": "index"},
        "DI": {"code": 7, "width": 16, "type": "index"},
        "AL": {"code": 0, "width": 8, "type": "general"},
        "CL": {"code": 1, "width": 8, "type": "general"},
        "DL": {"code": 2, "width": 8, "type": "general"},
        "BL": {"code": 3, "width": 8, "type": "general"},
        "AH": {"code": 4, "width": 8, "type": "general"},
        "CH": {"code": 5, "width": 8, "type": "general"},
        "DH": {"code": 6, "width": 8, "type": "general"},
        "BH": {"code": 7, "width": 8, "type": "general"},
        "CS": {"code": 1, "width": 16, "type": "segment"},
        "DS": {"code": 3, "width": 16, "type": "segment"},
        "ES": {"code": 0, "width": 16, "type": "segment"},
        "SS": {"code": 2, "width": 16, "type": "segment"}
    },
    "directives": [
        "MODEL", "STACK", "DATA", "CODE", "ASSUME", "SEGMENT", "ENDS",
        "PROC", "ENDP", "END", "ORG", "EQU", "DB", "DW", "DD",
        "PUBLIC", "EXTERN", "EXTRN", "MACRO", "ENDM", "LOCAL",
        "IF", "IFDEF", "IFNDEF", "ELSE", "ENDIF", "INCLUDE"
    ],
    "instructions": {
        "MOV": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,reg", "opcode": "0x89", "byte_width": 2, "modrm": True},
                {"mode": "reg,imm", "opcode": "0xB8", "byte_width": 3, "reg_in_opcode": True, "imm_width": 2},
                {"mode": "reg,mem", "opcode": "0x8B", "byte_width": 4, "modrm": True}
            ]
        },
        "ADD": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,reg", "opcode": "0x01", "byte_width": 2, "modrm": True},
                {"mode": "reg,imm", "opcode": "0x81", "byte_width": 4, "modrm_ext": 0, "imm_width": 2}
            ]
        },
        "SUB": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,reg", "opcode": "0x29", "byte_width": 2, "modrm": True},
                {"mode": "reg,imm", "opcode": "0x81", "byte_width": 4, "modrm_ext": 5, "imm_width": 2}
            ]
        },
        "INC": {
            "operand_count": 1,
            "variants": [
                {"mode": "reg", "opcode": "0x40", "byte_width": 1, "reg_in_opcode": True}
            ]
        },
        "DEC": {
            "operand_count": 1,
            "variants": [
                {"mode": "reg", "opcode": "0x48", "byte_width": 1, "reg_in_opcode": True}
            ]
        },
        "PUSH": {
            "operand_count": 1,
            "variants": [
                {"mode": "reg", "opcode": "0x50", "byte_width": 1, "reg_in_opcode": True}
            ]
        },
        "POP": {
            "operand_count": 1,
            "variants": [
                {"mode": "reg", "opcode": "0x58", "byte_width": 1, "reg_in_opcode": True}
            ]
        },
        "JMP": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0xEB", "byte_width": 2, "relative": True, "rel_width": 1},
                {"mode": "imm", "opcode": "0xEB", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JE": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x74", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JZ": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x74", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JNE": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x75", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JNZ": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x75", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JG": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x7F", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JL": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x7C", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JGE": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x7D", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JLE": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x7E", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "CMP": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,reg", "opcode": "0x39", "byte_width": 2, "modrm": True},
                {"mode": "reg,imm", "opcode": "0x81", "byte_width": 4, "modrm_ext": 7, "imm_width": 2}
            ]
        },
        "CALL": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0xE8", "byte_width": 3, "relative": True, "rel_width": 2}
            ]
        },
        "RET": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xC3", "byte_width": 1}
            ]
        },
        "LOOP": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0xE2", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "LOOPE": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0xE1", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "LOOPNE": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0xE0", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "NOP": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0x90", "byte_width": 1}
            ]
        },
        "HLT": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xF4", "byte_width": 1}
            ]
        },
        "INT": {
            "operand_count": 1,
            "variants": [
                {"mode": "imm", "opcode": "0xCD", "byte_width": 2, "imm_width": 1}
            ]
        },
        "XOR": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,reg", "opcode": "0x31", "byte_width": 2, "modrm": True}
            ]
        },
        "AND": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,reg", "opcode": "0x21", "byte_width": 2, "modrm": True},
                {"mode": "reg,imm", "opcode": "0x81", "byte_width": 4, "modrm_ext": 4, "imm_width": 2}
            ]
        },
        "OR": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,reg", "opcode": "0x09", "byte_width": 2, "modrm": True}
            ]
        },
        "NOT": {
            "operand_count": 1,
            "variants": [
                {"mode": "reg", "opcode": "0xF7", "byte_width": 2, "modrm_ext": 2}
            ]
        },
        "MUL": {
            "operand_count": 1,
            "variants": [
                {"mode": "reg", "opcode": "0xF7", "byte_width": 2, "modrm_ext": 4}
            ]
        },
        "DIV": {
            "operand_count": 1,
            "variants": [
                {"mode": "reg", "opcode": "0xF7", "byte_width": 2, "modrm_ext": 6}
            ]
        },
        "LEA": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,mem", "opcode": "0x8D", "byte_width": 4, "modrm": True}
            ]
        },
        "XCHG": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,reg", "opcode": "0x87", "byte_width": 2, "modrm": True}
            ]
        },
        "NEG": {
            "operand_count": 1,
            "variants": [
                {"mode": "reg", "opcode": "0xF7", "byte_width": 2, "modrm_ext": 3}
            ]
        },
        "SHL": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,imm", "opcode": "0xC1", "byte_width": 3, "modrm_ext": 4, "imm_width": 1},
                {"mode": "reg,reg", "opcode": "0xD3", "byte_width": 2, "modrm_ext": 4}
            ]
        },
        "SAL": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,imm", "opcode": "0xC1", "byte_width": 3, "modrm_ext": 4, "imm_width": 1}
            ]
        },
        "SHR": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,imm", "opcode": "0xC1", "byte_width": 3, "modrm_ext": 5, "imm_width": 1},
                {"mode": "reg,reg", "opcode": "0xD3", "byte_width": 2, "modrm_ext": 5}
            ]
        },
        "SAR": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,imm", "opcode": "0xC1", "byte_width": 3, "modrm_ext": 7, "imm_width": 1}
            ]
        },
        "ROL": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,imm", "opcode": "0xC1", "byte_width": 3, "modrm_ext": 0, "imm_width": 1}
            ]
        },
        "ROR": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,imm", "opcode": "0xC1", "byte_width": 3, "modrm_ext": 1, "imm_width": 1}
            ]
        },
        "RCL": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,imm", "opcode": "0xC1", "byte_width": 3, "modrm_ext": 2, "imm_width": 1}
            ]
        },
        "RCR": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,imm", "opcode": "0xC1", "byte_width": 3, "modrm_ext": 3, "imm_width": 1}
            ]
        },
        "TEST": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,reg", "opcode": "0x85", "byte_width": 2, "modrm": True},
                {"mode": "reg,imm", "opcode": "0xF7", "byte_width": 4, "modrm_ext": 0, "imm_width": 2}
            ]
        },
        "IMUL": {
            "operand_count": 1,
            "variants": [
                {"mode": "reg", "opcode": "0xF7", "byte_width": 2, "modrm_ext": 5}
            ]
        },
        "IDIV": {
            "operand_count": 1,
            "variants": [
                {"mode": "reg", "opcode": "0xF7", "byte_width": 2, "modrm_ext": 7}
            ]
        },
        "CBW": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0x98", "byte_width": 1}
            ]
        },
        "CWD": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0x99", "byte_width": 1}
            ]
        },
        "ADC": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,reg", "opcode": "0x11", "byte_width": 2, "modrm": True},
                {"mode": "reg,imm", "opcode": "0x81", "byte_width": 4, "modrm_ext": 2, "imm_width": 2}
            ]
        },
        "SBB": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,reg", "opcode": "0x19", "byte_width": 2, "modrm": True},
                {"mode": "reg,imm", "opcode": "0x81", "byte_width": 4, "modrm_ext": 3, "imm_width": 2}
            ]
        },
        "JC": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x72", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JB": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x72", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JNAE": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x72", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JNC": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x73", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JNB": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x73", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JAE": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x73", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JA": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x77", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JNBE": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x77", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JBE": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x76", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JNA": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x76", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JNGE": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x7C", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JNLE": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x7F", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JNL": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x7D", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JS": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x78", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JNS": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x79", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JO": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x70", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JNO": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x71", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JP": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x7A", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JPE": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x7A", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JNP": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x7B", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JPO": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0x7B", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "JCXZ": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0xE3", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "LOOPZ": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0xE1", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "LOOPNZ": {
            "operand_count": 1,
            "variants": [
                {"mode": "label", "opcode": "0xE0", "byte_width": 2, "relative": True, "rel_width": 1}
            ]
        },
        "CLC": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xF8", "byte_width": 1}
            ]
        },
        "STC": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xF9", "byte_width": 1}
            ]
        },
        "CMC": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xF5", "byte_width": 1}
            ]
        },
        "CLD": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xFC", "byte_width": 1}
            ]
        },
        "STD": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xFD", "byte_width": 1}
            ]
        },
        "CLI": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xFA", "byte_width": 1}
            ]
        },
        "STI": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xFB", "byte_width": 1}
            ]
        },
        "LAHF": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0x9F", "byte_width": 1}
            ]
        },
        "SAHF": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0x9E", "byte_width": 1}
            ]
        },
        "PUSHF": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0x9C", "byte_width": 1}
            ]
        },
        "POPF": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0x9D", "byte_width": 1}
            ]
        },
        "IN": {
            "operand_count": 2,
            "variants": [
                {"mode": "reg,imm", "opcode": "0xE5", "byte_width": 2, "imm_width": 1}
            ]
        },
        "OUT": {
            "operand_count": 2,
            "variants": [
                {"mode": "imm,reg", "opcode": "0xE7", "byte_width": 2, "imm_width": 1}
            ]
        },
        "MOVSB": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xA4", "byte_width": 1}
            ]
        },
        "MOVSW": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xA5", "byte_width": 1}
            ]
        },
        "CMPSB": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xA6", "byte_width": 1}
            ]
        },
        "CMPSW": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xA7", "byte_width": 1}
            ]
        },
        "SCASB": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xAE", "byte_width": 1}
            ]
        },
        "SCASW": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xAF", "byte_width": 1}
            ]
        },
        "LODSB": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xAC", "byte_width": 1}
            ]
        },
        "LODSW": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xAD", "byte_width": 1}
            ]
        },
        "STOSB": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xAA", "byte_width": 1}
            ]
        },
        "STOSW": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xAB", "byte_width": 1}
            ]
        },
        "REP": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xF3", "byte_width": 1}
            ]
        },
        "REPE": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xF3", "byte_width": 1}
            ]
        },
        "REPZ": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xF3", "byte_width": 1}
            ]
        },
        "REPNE": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xF2", "byte_width": 1}
            ]
        },
        "REPNZ": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xF2", "byte_width": 1}
            ]
        },
        "IRET": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xCF", "byte_width": 1}
            ]
        },
        "AAA": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0x37", "byte_width": 1}
            ]
        },
        "AAS": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0x3F", "byte_width": 1}
            ]
        },
        "AAM": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xD4", "byte_width": 2}
            ]
        },
        "AAD": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xD5", "byte_width": 2}
            ]
        },
        "DAA": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0x27", "byte_width": 1}
            ]
        },
        "DAS": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0x2F", "byte_width": 1}
            ]
        },
        "XLAT": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xD7", "byte_width": 1}
            ]
        },
        "WAIT": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0x9B", "byte_width": 1}
            ]
        },
        "LOCK": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xF0", "byte_width": 1}
            ]
        },
        "RETF": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xCB", "byte_width": 1}
            ]
        },
        "INTO": {
            "operand_count": 0,
            "variants": [
                {"mode": "none", "opcode": "0xCE", "byte_width": 1}
            ]
        }
    }
}


class Assembler8086:
    """
    8086 Assembler with step-by-step execution for the Electron frontend.
    """
    
    def __init__(self, isa: dict = None):
        """Initialize assembler with ISA."""
        self.isa = isa or DEFAULT_ISA
        self.registers = {name: info for name, info in self.isa['registers'].items()}
        self.directives = set(self.isa.get('directives', []))
        self.instructions = self.isa.get('instructions', {})
        
        self.symbol_table = SymbolTable()
        self.directive_handler = DirectiveHandler(self.symbol_table)
        self.emitter = Emitter('little')
        
        # Execution state
        self.state = {
            'AX': 0, 'BX': 0, 'CX': 0, 'DX': 0,
            'SI': 0, 'DI': 0, 'SP': 0xFFFE, 'BP': 0,
            'IP': 0, 'FLAGS': 0,
            'CS': 0, 'DS': 0, 'ES': 0, 'SS': 0,
            'memory': {},
            'stack': [],
            'halted': False
        }
    
    def parse(self, source: str) -> List[Dict]:
        """
        Parse assembly source into instruction list.
        
        Args:
            source: Assembly source code.
            
        Returns:
            List of parsed instructions.
        """
        parsed = []
        labels = {}
        current_address = 0
        lines = source.strip().split('\n')
        pending_label = None  # Label waiting to be attached to next instruction
        
        for line_num, line in enumerate(lines, 1):
            # Strip comments
            if ';' in line:
                line = line[:line.index(';')]
            line = line.strip()
            
            if not line:
                continue
            
            # Check for label
            label = None
            if ':' in line:
                parts = line.split(':', 1)
                label = parts[0].strip()
                line = parts[1].strip() if len(parts) > 1 else ''
                labels[label.upper()] = current_address
                
                # If this line only had a label, save it for next instruction
                if not line:
                    pending_label = label
                    continue
            
            # Use pending label if we have one
            if pending_label and not label:
                label = pending_label
                pending_label = None
            
            # Tokenize
            parts = line.split(None, 1)
            mnemonic = parts[0].upper()
            operand_str = parts[1].strip() if len(parts) > 1 else ''
            
            # Check for directive
            if mnemonic.startswith('.') or mnemonic in self.directives:
                directive_name = mnemonic.lstrip('.')
                if self.directive_handler.is_no_emit(directive_name):
                    continue
                # Handle data directives
                operands = self._parse_operands(operand_str)
                result = self.directive_handler.process(mnemonic, operands, current_address)
                if result.byte_width > 0:
                    parsed.append({
                        'type': 'directive',
                        'name': mnemonic,
                        'operands': operands,
                        'address': current_address,
                        'line': line_num,
                        'source': line,
                        'label': label,
                        'data': result.data
                    })
                    current_address += result.byte_width
                continue
            
            # Handle NAME EQU VALUE
            if len(parts) > 1:
                rest = parts[1].strip().split(None, 1)
                if rest and rest[0].upper() == 'EQU':
                    value_str = rest[1] if len(rest) > 1 else '0'
                    value = self._parse_value(value_str)
                    labels[mnemonic] = value
                    continue
            
            # Handle NAME DB/DW/DD data definition (e.g., MSG DB 'Hello$')
            if len(parts) > 1:
                rest = parts[1].strip().split(None, 1)
                if rest and rest[0].upper() in ('DB', 'DW', 'DD', 'BYTE', 'WORD', 'DWORD'):
                    # This is a data definition with a label
                    data_label = mnemonic
                    data_directive = rest[0].upper()
                    data_operands = rest[1] if len(rest) > 1 else ''
                    
                    # Store label pointing to current address
                    labels[data_label.upper()] = current_address
                    
                    # Parse data
                    operands = self._parse_operands(data_operands)
                    result = self.directive_handler.process(data_directive, operands, current_address)
                    if result.byte_width > 0:
                        parsed.append({
                            'type': 'directive',
                            'name': data_directive,
                            'operands': operands,
                            'address': current_address,
                            'line': line_num,
                            'source': line,
                            'label': data_label,
                            'data': result.data
                        })
                        current_address += result.byte_width
                    continue
            
            # Instruction
            if mnemonic not in self.instructions:
                raise AssemblyError(f"Unknown instruction: {mnemonic}", line_num, line)
            
            operands = self._parse_operands(operand_str)
            instr_def = self.instructions[mnemonic]
            
            # Get byte width from variant
            operand_types = [self._classify_operand(op) for op in operands]
            variant = self._match_variant(mnemonic, operand_types)
            byte_width = variant.get('byte_width', 1) if variant else 1
            
            parsed.append({
                'type': 'instruction',
                'mnemonic': mnemonic,
                'operands': operands,
                'address': current_address,
                'line': line_num,
                'source': line,
                'label': label,
                'byte_width': byte_width
            })
            current_address += byte_width
        
        # Store labels for resolution
        for entry in parsed:
            entry['labels'] = labels
        
        return parsed
    
    def _parse_operands(self, operand_str: str) -> List[str]:
        """Parse operand string into list."""
        if not operand_str:
            return []
        
        operands = []
        current = []
        in_brackets = 0
        in_string = False
        string_char = None
        
        for char in operand_str:
            if char in '"\'':
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                current.append(char)
            elif in_string:
                current.append(char)
            elif char == '[':
                in_brackets += 1
                current.append(char)
            elif char == ']':
                in_brackets -= 1
                current.append(char)
            elif char == ',' and in_brackets == 0:
                if current:
                    operands.append(''.join(current).strip())
                    current = []
            else:
                current.append(char)
        
        if current:
            operands.append(''.join(current).strip())
        
        return operands
    
    def _classify_operand(self, operand: str) -> str:
        """Classify operand type."""
        operand = operand.strip().upper()
        
        if not operand:
            return 'none'
        
        if operand in self.registers:
            return 'reg'
        
        if operand.startswith('[') and operand.endswith(']'):
            return 'mem'
        
        # OFFSET operator returns an immediate (address)
        if operand.startswith('OFFSET '):
            return 'imm'
        
        # Immediate
        if operand[0].isdigit() or operand[0] == '-':
            return 'imm'
        if operand.startswith('0X') or operand.endswith('H'):
            return 'imm'
        
        return 'label'
    
    def _match_variant(self, mnemonic: str, operand_types: List[str]) -> Optional[dict]:
        """Find matching instruction variant."""
        instr = self.instructions.get(mnemonic)
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
        
        exp_parts = expected.split(',')
        act_parts = actual.split(',')
        
        if len(exp_parts) != len(act_parts):
            return False
        
        for exp, act in zip(exp_parts, act_parts):
            if exp == act:
                continue
            if exp == 'label' and act in ('imm', 'label'):
                continue
            if exp == 'imm' and act == 'label':
                continue
            return False
        
        return True
    
    def _parse_value(self, value: str) -> int:
        """Parse numeric value."""
        value = value.strip().upper()
        if not value:
            return 0
        
        if value.startswith('0X'):
            return int(value, 16)
        if value.endswith('H'):
            return int(value[:-1], 16)
        if value.endswith('B'):
            return int(value[:-1], 2)
        
        try:
            return int(value)
        except ValueError:
            return 0
    
    def execute(self, instructions: List[Dict], initial_state: dict = None) -> dict:
        """
        Execute parsed instructions step by step.
        
        Args:
            instructions: List of parsed instructions.
            initial_state: Initial CPU state.
            
        Returns:
            Execution result with steps.
        """
        if initial_state:
            self.state.update(initial_state)
        
        steps = []
        labels = instructions[0].get('labels', {}) if instructions else {}
        
        # Filter to only instructions (skip directives for execution)
        executable = [i for i in instructions if i['type'] == 'instruction']
        
        # Build label-to-index mapping for jump resolution
        label_to_idx = {}
        for idx, instr in enumerate(executable):
            if instr.get('label'):
                label_to_idx[instr['label'].upper()] = idx
        
        ip = 0
        max_steps = 10000
        step_count = 0
        
        while ip < len(executable) and not self.state['halted'] and step_count < max_steps:
            instr = executable[ip]
            old_state = deepcopy(self.state)
            
            try:
                next_ip = self._execute_instruction(instr, labels, ip, label_to_idx, executable)
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'line': instr['line'],
                    'instruction': instr['source']
                }
            
            step = {
                'line': instr['line'],
                'instruction': instr['source'],
                'mnemonic': instr['mnemonic'],
                'operands': instr['operands'],
                'before': old_state,
                'after': deepcopy(self.state),
                'changes': self._compute_changes(old_state, self.state)
            }
            steps.append(step)
            
            ip = next_ip if next_ip is not None else ip + 1
            step_count += 1
        
        return {
            'success': True,
            'steps': steps,
            'final_state': deepcopy(self.state),
            'step_count': step_count
        }
    
    def _execute_instruction(self, instr: dict, labels: dict, ip: int, 
                              label_to_idx: dict = None, executable: List[dict] = None) -> Optional[int]:
        """Execute a single instruction."""
        mnemonic = instr['mnemonic']
        operands = instr['operands']
        label_to_idx = label_to_idx or {}
        executable = executable or []
        
        def get_value(op: str) -> int:
            op = op.strip().upper()
            # Handle OFFSET operator
            if op.startswith('OFFSET '):
                label_name = op[7:].strip()
                if label_name in labels:
                    return labels[label_name]
                return 0
            if op in self.state:
                return self.state[op] & 0xFFFF
            if op in labels:
                return labels[op]
            return self._parse_value(op)
        
        def set_value(op: str, value: int) -> None:
            op = op.strip().upper()
            if op in self.state:
                self.state[op] = value & 0xFFFF
        
        def update_flags(value: int) -> None:
            self.state['FLAGS'] = 0
            if value == 0:
                self.state['FLAGS'] |= 0x40  # ZF
            if value & 0x8000:
                self.state['FLAGS'] |= 0x80  # SF
        
        # Data movement
        if mnemonic == 'MOV':
            value = get_value(operands[1])
            set_value(operands[0], value)
        
        # Arithmetic
        elif mnemonic == 'ADD':
            result = get_value(operands[0]) + get_value(operands[1])
            set_value(operands[0], result)
            update_flags(result & 0xFFFF)
        
        elif mnemonic == 'SUB':
            result = get_value(operands[0]) - get_value(operands[1])
            set_value(operands[0], result)
            update_flags(result & 0xFFFF)
        
        elif mnemonic == 'INC':
            result = get_value(operands[0]) + 1
            set_value(operands[0], result)
            update_flags(result & 0xFFFF)
        
        elif mnemonic == 'DEC':
            result = get_value(operands[0]) - 1
            set_value(operands[0], result)
            update_flags(result & 0xFFFF)
        
        elif mnemonic == 'MUL':
            # AX = AL * operand (for byte) or DX:AX = AX * operand (for word)
            result = self.state['AX'] * get_value(operands[0])
            self.state['AX'] = result & 0xFFFF
            self.state['DX'] = (result >> 16) & 0xFFFF
        
        elif mnemonic == 'DIV':
            divisor = get_value(operands[0])
            if divisor == 0:
                raise RuntimeError("Division by zero")
            dividend = (self.state['DX'] << 16) | self.state['AX']
            self.state['AX'] = (dividend // divisor) & 0xFFFF
            self.state['DX'] = (dividend % divisor) & 0xFFFF
        
        # Logic
        elif mnemonic == 'AND':
            result = get_value(operands[0]) & get_value(operands[1])
            set_value(operands[0], result)
            update_flags(result)
        
        elif mnemonic == 'OR':
            result = get_value(operands[0]) | get_value(operands[1])
            set_value(operands[0], result)
            update_flags(result)
        
        elif mnemonic == 'XOR':
            result = get_value(operands[0]) ^ get_value(operands[1])
            set_value(operands[0], result)
            update_flags(result)
        
        elif mnemonic == 'NOT':
            result = ~get_value(operands[0]) & 0xFFFF
            set_value(operands[0], result)
        
        elif mnemonic == 'CMP':
            result = get_value(operands[0]) - get_value(operands[1])
            update_flags(result & 0xFFFF)
        
        # Stack
        elif mnemonic == 'PUSH':
            value = get_value(operands[0])
            self.state['SP'] = (self.state['SP'] - 2) & 0xFFFF
            self.state['stack'].append(value)
        
        elif mnemonic == 'POP':
            if self.state['stack']:
                value = self.state['stack'].pop()
                set_value(operands[0], value)
                self.state['SP'] = (self.state['SP'] + 2) & 0xFFFF
        
        # Control flow
        elif mnemonic == 'JMP':
            target = operands[0].strip().upper()
            if target in label_to_idx:
                return label_to_idx[target]
            return ip + 1
        
        elif mnemonic in ('JE', 'JZ'):
            if self.state['FLAGS'] & 0x40:  # ZF
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic in ('JNE', 'JNZ'):
            if not (self.state['FLAGS'] & 0x40):
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic == 'JG':
            if not (self.state['FLAGS'] & 0x40) and not (self.state['FLAGS'] & 0x80):
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic == 'JL':
            if self.state['FLAGS'] & 0x80:
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic == 'JGE':
            if not (self.state['FLAGS'] & 0x80):
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic == 'JLE':
            if (self.state['FLAGS'] & 0x40) or (self.state['FLAGS'] & 0x80):
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic == 'LOOP':
            self.state['CX'] = (self.state['CX'] - 1) & 0xFFFF
            if self.state['CX'] != 0:
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic == 'LOOPE':
            self.state['CX'] = (self.state['CX'] - 1) & 0xFFFF
            if self.state['CX'] != 0 and (self.state['FLAGS'] & 0x40):
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic == 'LOOPNE':
            self.state['CX'] = (self.state['CX'] - 1) & 0xFFFF
            if self.state['CX'] != 0 and not (self.state['FLAGS'] & 0x40):
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic == 'CALL':
            # Push return address
            self.state['stack'].append(ip + 1)
            self.state['SP'] = (self.state['SP'] - 2) & 0xFFFF
            return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic == 'RET':
            if self.state['stack']:
                return self.state['stack'].pop()
            return None
        
        elif mnemonic == 'INT':
            # Simulate interrupt - store in state for frontend
            self.state['last_int'] = get_value(operands[0])
        
        elif mnemonic == 'HLT':
            self.state['halted'] = True
        
        elif mnemonic == 'NOP':
            pass
        
        elif mnemonic == 'XCHG':
            val0 = get_value(operands[0])
            val1 = get_value(operands[1])
            set_value(operands[0], val1)
            set_value(operands[1], val0)
        
        elif mnemonic == 'LEA':
            # Load effective address - simplified
            mem_ref = operands[1]
            if mem_ref.startswith('[') and mem_ref.endswith(']'):
                inner = mem_ref[1:-1].upper()
                value = self._compute_ea(inner)
                set_value(operands[0], value)
        
        # Shift/Rotate operations
        elif mnemonic == 'SHL' or mnemonic == 'SAL':
            count = get_value(operands[1]) if len(operands) > 1 else 1
            result = (get_value(operands[0]) << count) & 0xFFFF
            set_value(operands[0], result)
            update_flags(result)
        
        elif mnemonic == 'SHR':
            count = get_value(operands[1]) if len(operands) > 1 else 1
            result = get_value(operands[0]) >> count
            set_value(operands[0], result)
            update_flags(result)
        
        elif mnemonic == 'SAR':
            count = get_value(operands[1]) if len(operands) > 1 else 1
            val = get_value(operands[0])
            # Arithmetic shift - preserve sign
            if val & 0x8000:
                result = (val >> count) | (0xFFFF << (16 - count))
            else:
                result = val >> count
            result &= 0xFFFF
            set_value(operands[0], result)
            update_flags(result)
        
        elif mnemonic == 'ROL':
            count = get_value(operands[1]) if len(operands) > 1 else 1
            val = get_value(operands[0])
            result = ((val << count) | (val >> (16 - count))) & 0xFFFF
            set_value(operands[0], result)
        
        elif mnemonic == 'ROR':
            count = get_value(operands[1]) if len(operands) > 1 else 1
            val = get_value(operands[0])
            result = ((val >> count) | (val << (16 - count))) & 0xFFFF
            set_value(operands[0], result)
        
        elif mnemonic == 'RCL':
            # Rotate through carry left
            count = get_value(operands[1]) if len(operands) > 1 else 1
            val = get_value(operands[0])
            cf = (self.state['FLAGS'] >> 0) & 1
            for _ in range(count):
                new_cf = (val >> 15) & 1
                val = ((val << 1) | cf) & 0xFFFF
                cf = new_cf
            set_value(operands[0], val)
        
        elif mnemonic == 'RCR':
            # Rotate through carry right
            count = get_value(operands[1]) if len(operands) > 1 else 1
            val = get_value(operands[0])
            cf = (self.state['FLAGS'] >> 0) & 1
            for _ in range(count):
                new_cf = val & 1
                val = ((val >> 1) | (cf << 15)) & 0xFFFF
                cf = new_cf
            set_value(operands[0], val)
        
        # More arithmetic
        elif mnemonic == 'NEG':
            result = (-get_value(operands[0])) & 0xFFFF
            set_value(operands[0], result)
            update_flags(result)
        
        elif mnemonic == 'ADC':
            cf = (self.state['FLAGS'] >> 0) & 1
            result = get_value(operands[0]) + get_value(operands[1]) + cf
            set_value(operands[0], result)
            update_flags(result & 0xFFFF)
        
        elif mnemonic == 'SBB':
            cf = (self.state['FLAGS'] >> 0) & 1
            result = get_value(operands[0]) - get_value(operands[1]) - cf
            set_value(operands[0], result)
            update_flags(result & 0xFFFF)
        
        elif mnemonic == 'TEST':
            result = get_value(operands[0]) & get_value(operands[1])
            update_flags(result)
        
        elif mnemonic == 'IMUL':
            result = self.state['AX'] * get_value(operands[0])
            if result > 32767 or result < -32768:
                result = result & 0xFFFFFFFF
            self.state['AX'] = result & 0xFFFF
            self.state['DX'] = (result >> 16) & 0xFFFF
        
        elif mnemonic == 'IDIV':
            divisor = get_value(operands[0])
            if divisor == 0:
                raise RuntimeError("Division by zero")
            dividend = (self.state['DX'] << 16) | self.state['AX']
            # Handle signed division
            if dividend & 0x80000000:
                dividend = dividend - 0x100000000
            if divisor & 0x8000:
                divisor = divisor - 0x10000
            self.state['AX'] = (dividend // divisor) & 0xFFFF
            self.state['DX'] = (dividend % divisor) & 0xFFFF
        
        elif mnemonic == 'CBW':
            # Extend AL to AX (sign extend)
            al = self.state['AX'] & 0xFF
            if al & 0x80:
                self.state['AX'] = 0xFF00 | al
            else:
                self.state['AX'] = al
        
        elif mnemonic == 'CWD':
            # Extend AX to DX:AX (sign extend)
            if self.state['AX'] & 0x8000:
                self.state['DX'] = 0xFFFF
            else:
                self.state['DX'] = 0
        
        # More conditional jumps
        elif mnemonic in ('JC', 'JB', 'JNAE'):
            if self.state['FLAGS'] & 0x01:  # CF
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic in ('JNC', 'JNB', 'JAE'):
            if not (self.state['FLAGS'] & 0x01):
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic in ('JA', 'JNBE'):
            # Above (CF=0 and ZF=0)
            if not (self.state['FLAGS'] & 0x01) and not (self.state['FLAGS'] & 0x40):
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic in ('JBE', 'JNA'):
            # Below or equal (CF=1 or ZF=1)
            if (self.state['FLAGS'] & 0x01) or (self.state['FLAGS'] & 0x40):
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic in ('JS',):
            if self.state['FLAGS'] & 0x80:  # SF
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic in ('JNS',):
            if not (self.state['FLAGS'] & 0x80):
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic in ('JO',):
            if self.state['FLAGS'] & 0x800:  # OF
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic in ('JNO',):
            if not (self.state['FLAGS'] & 0x800):
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic in ('JP', 'JPE'):
            if self.state['FLAGS'] & 0x04:  # PF
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic in ('JNP', 'JPO'):
            if not (self.state['FLAGS'] & 0x04):
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic == 'JCXZ':
            if self.state['CX'] == 0:
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic in ('LOOPZ', 'LOOPE'):
            self.state['CX'] = (self.state['CX'] - 1) & 0xFFFF
            if self.state['CX'] != 0 and (self.state['FLAGS'] & 0x40):
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        elif mnemonic in ('LOOPNZ', 'LOOPNE'):
            self.state['CX'] = (self.state['CX'] - 1) & 0xFFFF
            if self.state['CX'] != 0 and not (self.state['FLAGS'] & 0x40):
                return self._resolve_jump(operands[0], label_to_idx, ip)
        
        # Flag operations
        elif mnemonic == 'CLC':
            self.state['FLAGS'] &= ~0x01
        
        elif mnemonic == 'STC':
            self.state['FLAGS'] |= 0x01
        
        elif mnemonic == 'CMC':
            self.state['FLAGS'] ^= 0x01
        
        elif mnemonic == 'CLD':
            self.state['FLAGS'] &= ~0x400  # DF
        
        elif mnemonic == 'STD':
            self.state['FLAGS'] |= 0x400
        
        elif mnemonic == 'CLI':
            self.state['FLAGS'] &= ~0x200  # IF
        
        elif mnemonic == 'STI':
            self.state['FLAGS'] |= 0x200
        
        elif mnemonic == 'LAHF':
            # Load AH from flags (low byte)
            self.state['AX'] = (self.state['AX'] & 0x00FF) | ((self.state['FLAGS'] & 0xFF) << 8)
        
        elif mnemonic == 'SAHF':
            # Store AH into flags (low byte)
            ah = (self.state['AX'] >> 8) & 0xFF
            self.state['FLAGS'] = (self.state['FLAGS'] & 0xFF00) | ah
        
        elif mnemonic == 'PUSHF':
            self.state['stack'].append(self.state['FLAGS'])
            self.state['SP'] = (self.state['SP'] - 2) & 0xFFFF
        
        elif mnemonic == 'POPF':
            if self.state['stack']:
                self.state['FLAGS'] = self.state['stack'].pop()
                self.state['SP'] = (self.state['SP'] + 2) & 0xFFFF
        
        # String operations (simplified - single element)
        elif mnemonic == 'MOVSB':
            pass  # Would copy byte [SI] to [DI], increment both
        
        elif mnemonic == 'MOVSW':
            pass  # Would copy word [SI] to [DI], increment both by 2
        
        elif mnemonic == 'STOSB':
            pass  # Would store AL at [DI]
        
        elif mnemonic == 'STOSW':
            pass  # Would store AX at [DI]
        
        elif mnemonic == 'LODSB':
            pass  # Would load byte from [SI] to AL
        
        elif mnemonic == 'LODSW':
            pass  # Would load word from [SI] to AX
        
        # Prefix instructions (no-op in simulation)
        elif mnemonic in ('REP', 'REPE', 'REPZ', 'REPNE', 'REPNZ', 'LOCK'):
            pass
        
        elif mnemonic == 'IRET':
            # Return from interrupt
            if len(self.state['stack']) >= 3:
                self.state['stack'].pop()  # flags
                self.state['stack'].pop()  # cs
                return self.state['stack'].pop()  # ip
        
        elif mnemonic == 'RETF':
            # Far return
            if len(self.state['stack']) >= 2:
                self.state['stack'].pop()  # cs
                return self.state['stack'].pop()  # ip
        
        elif mnemonic == 'INTO':
            # Interrupt on overflow
            if self.state['FLAGS'] & 0x800:
                self.state['last_int'] = 4
        
        elif mnemonic == 'XLAT':
            # Table lookup - AL = [BX + AL]
            addr = (self.state['BX'] + (self.state['AX'] & 0xFF)) & 0xFFFF
            mem = self.state.get('memory', {})
            self.state['AX'] = (self.state['AX'] & 0xFF00) | mem.get(str(addr), 0)
        
        elif mnemonic == 'IN':
            # Input from port - simplified
            pass
        
        elif mnemonic == 'OUT':
            # Output to port - simplified
            pass
        
        elif mnemonic == 'WAIT':
            pass
        
        # BCD operations (simplified)
        elif mnemonic in ('AAA', 'AAS', 'AAM', 'AAD', 'DAA', 'DAS'):
            pass
        
        return None
    
    def _resolve_jump(self, target: str, label_to_idx: dict, ip: int) -> Optional[int]:
        """Resolve jump target to instruction index."""
        target = target.strip().upper()
        if target in label_to_idx:
            return label_to_idx[target]
        return ip + 1
    
    def _compute_ea(self, expr: str) -> int:
        """Compute effective address from expression."""
        # Simple: handle [BX+SI], [BP+DI], [BX+offset], etc.
        value = 0
        for part in expr.replace('-', '+-').split('+'):
            part = part.strip()
            if not part:
                continue
            if part.upper() in self.state:
                value += self.state[part.upper()]
            else:
                value += self._parse_value(part)
        return value & 0xFFFF
    
    def _compute_changes(self, before: dict, after: dict) -> dict:
        """Compute differences between states."""
        changes = {}
        for key in ['AX', 'BX', 'CX', 'DX', 'SI', 'DI', 'SP', 'BP', 'FLAGS']:
            if before.get(key) != after.get(key):
                changes[key] = {'from': before.get(key), 'to': after.get(key)}
        return changes
    
    def reset(self) -> None:
        """Reset assembler state."""
        self.state = {
            'AX': 0, 'BX': 0, 'CX': 0, 'DX': 0,
            'SI': 0, 'DI': 0, 'SP': 0xFFFE, 'BP': 0,
            'IP': 0, 'FLAGS': 0,
            'CS': 0, 'DS': 0, 'ES': 0, 'SS': 0,
            'memory': {},
            'stack': [],
            'halted': False
        }


class AssemblyError(Exception):
    """Assembly error with line information."""
    def __init__(self, message: str, line: int = 0, instruction: str = ''):
        self.message = message
        self.line = line
        self.instruction = instruction
        super().__init__(f"Line {line}: {message}")


def main():
    """Main entry point for Electron integration via stdin/stdout."""
    # Read JSON from stdin
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
            instructions = assembler.parse(code)
            result = assembler.execute(instructions, state)
            print(json.dumps(result))
            return 0 if result['success'] else 1
        except AssemblyError as e:
            print(json.dumps({
                'success': False,
                'error': e.message,
                'line': e.line,
                'instruction': e.instruction
            }))
            return 1
        except Exception as e:
            print(json.dumps({
                'success': False,
                'error': str(e)
            }))
            return 1
    
    elif command == 'parse':
        try:
            instructions = assembler.parse(code)
            print(json.dumps({
                'success': True,
                'instructions': instructions
            }))
            return 0
        except AssemblyError as e:
            print(json.dumps({
                'success': False,
                'error': e.message,
                'line': e.line
            }))
            return 1
    
    elif command == 'reset':
        assembler.reset()
        print(json.dumps({
            'success': True,
            'state': assembler.state
        }))
        return 0
    
    elif command == 'getState':
        print(json.dumps({
            'success': True,
            'state': assembler.state
        }))
        return 0
    
    elif command == 'setRegister':
        register = input_data.get('register', '').upper()
        value = input_data.get('value', 0)
        if register in assembler.state:
            assembler.state[register] = value & 0xFFFF
            print(json.dumps({
                'success': True,
                'state': assembler.state
            }))
        else:
            print(json.dumps({
                'success': False,
                'error': f'Unknown register: {register}'
            }))
        return 0
    
    elif command == 'getRegister':
        register = input_data.get('register', '').upper()
        if register in assembler.state:
            print(json.dumps({
                'success': True,
                'value': assembler.state[register]
            }))
        else:
            print(json.dumps({
                'success': False,
                'error': f'Unknown register: {register}'
            }))
        return 0
    
    elif command == 'setMemory':
        address = input_data.get('address', 0)
        value = input_data.get('value', 0)
        if 'memory' not in assembler.state:
            assembler.state['memory'] = {}
        assembler.state['memory'][str(address)] = value & 0xFF
        print(json.dumps({
            'success': True,
            'state': assembler.state
        }))
        return 0
    
    elif command == 'getMemory':
        start = input_data.get('start', 0)
        length = input_data.get('length', 256)
        memory = assembler.state.get('memory', {})
        result = []
        for i in range(start, start + length):
            result.append(memory.get(str(i), 0))
        print(json.dumps({
            'success': True,
            'memory': result
        }))
        return 0
    
    else:
        print(json.dumps({
            'success': False,
            'error': f'Unknown command: {command}'
        }))
        return 1


if __name__ == '__main__':
    sys.exit(main())
