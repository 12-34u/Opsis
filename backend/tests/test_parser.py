#!/usr/bin/env python3
"""
Tests for the parser module.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser import (
    Parser, Statement, StatementType, Operand, OperandType,
    MemoryRef, ParseResult, parse
)


def test(name: str, condition: bool) -> bool:
    """Simple test helper."""
    if condition:
        print(f"✓ {name}")
        return True
    else:
        print(f"✗ {name}")
        return False


def run_tests() -> tuple:
    """Run all parser tests."""
    passed = 0
    failed = 0
    
    # ==== Basic Statement Parsing ====
    print("\n=== Basic Statement Parsing ===")
    
    # Simple instruction
    result = parse("MOV AX, BX")
    stmt = result.statements[0]
    if test("Simple instruction parsed", stmt.type == StatementType.INSTRUCTION):
        passed += 1
    else:
        failed += 1
    
    if test("Mnemonic extracted", stmt.mnemonic == "MOV"):
        passed += 1
    else:
        failed += 1
    
    if test("Two operands", len(stmt.operands) == 2):
        passed += 1
    else:
        failed += 1
    
    # Label parsing
    result = parse("START:\n    MOV AX, BX")
    stmts = [s for s in result.statements if s.type != StatementType.EMPTY]
    if test("Label recognized", any(s.label == "START" for s in stmts)):
        passed += 1
    else:
        failed += 1
    
    # Directive parsing
    result = parse(".DATA")
    stmt = result.statements[0]
    if test("Directive parsed", stmt.type == StatementType.DIRECTIVE):
        passed += 1
    else:
        failed += 1
    
    # ==== Operand Types ====
    print("\n=== Operand Types ===")
    
    # Register operand
    result = parse("MOV AX, BX")
    op1 = result.statements[0].operands[0]
    op2 = result.statements[0].operands[1]
    if test("Register operand type", op1.type == OperandType.REGISTER):
        passed += 1
    else:
        failed += 1
    
    if test("Register name captured", op1.register == "AX"):
        passed += 1
    else:
        failed += 1
    
    # Immediate operand
    result = parse("MOV AX, 1234H")
    op = result.statements[0].operands[1]
    if test("Immediate operand type", op.type == OperandType.IMMEDIATE):
        passed += 1
    else:
        failed += 1
    
    if test("Immediate value parsed", op.immediate == 0x1234):
        passed += 1
    else:
        failed += 1
        print(f"  Got: {op.immediate}")
    
    # Label operand
    result = parse("JMP MYLABEL")
    op = result.statements[0].operands[0]
    if test("Label operand type", op.type == OperandType.LABEL):
        passed += 1
    else:
        failed += 1
        print(f"  Got: {op.type.name}")
    
    # String operand
    result = parse("DB 'Hello'")
    op = result.statements[0].operands[0]
    if test("String operand type", op.type == OperandType.STRING):
        passed += 1
    else:
        failed += 1
    
    # ==== Memory Reference Parsing ====
    print("\n=== Memory Reference Parsing ===")
    
    # Register indirect
    result = parse("MOV AX, [BX]")
    op = result.statements[0].operands[1]
    if test("Memory indirect type", op.type == OperandType.MEMORY_INDIRECT):
        passed += 1
    else:
        failed += 1
    
    if test("Memory base register", op.memory and op.memory.base == "BX"):
        passed += 1
    else:
        failed += 1
    
    # Indexed
    result = parse("MOV AX, [BX+SI]")
    op = result.statements[0].operands[1]
    if test("Memory indexed type", op.type == OperandType.MEMORY_INDEXED):
        passed += 1
    else:
        failed += 1
    
    if test("Memory base+index", op.memory and op.memory.base == "BX" and op.memory.index == "SI"):
        passed += 1
    else:
        failed += 1
    
    # Based with displacement
    result = parse("MOV AX, [BX+4]")
    op = result.statements[0].operands[1]
    if test("Memory based type", op.type == OperandType.MEMORY_BASED):
        passed += 1
    else:
        failed += 1
    
    if test("Memory displacement", op.memory and op.memory.displacement == 4):
        passed += 1
    else:
        failed += 1
    
    # Based indexed with displacement
    result = parse("MOV AX, [BX+SI+8]")
    op = result.statements[0].operands[1]
    if test("Memory based indexed type", op.type == OperandType.MEMORY_BASED_INDEXED):
        passed += 1
    else:
        failed += 1
    
    if test("Full memory ref", 
            op.memory and op.memory.base == "BX" and 
            op.memory.index == "SI" and op.memory.displacement == 8):
        passed += 1
    else:
        failed += 1
    
    # Negative displacement
    result = parse("MOV AX, [BP-4]")
    op = result.statements[0].operands[1]
    if test("Negative displacement", op.memory and op.memory.displacement == -4):
        passed += 1
    else:
        failed += 1
        print(f"  Got: {op.memory.displacement if op.memory else None}")
    
    # Direct address
    result = parse("MOV AX, [1000H]")
    op = result.statements[0].operands[1]
    if test("Direct address type", op.type == OperandType.MEMORY_DIRECT):
        passed += 1
    else:
        failed += 1
    
    # ==== Data Definitions ====
    print("\n=== Data Definitions ===")
    
    # DB with label
    result = parse("MSG DB 'Hello'")
    stmt = result.statements[0]
    if test("Data definition type", stmt.type == StatementType.DATA):
        passed += 1
    else:
        failed += 1
    
    if test("Data label captured", stmt.label == "MSG"):
        passed += 1
    else:
        failed += 1
    
    # DW
    result = parse("COUNT DW 0")
    stmt = result.statements[0]
    if test("DW directive", stmt.mnemonic == "DW"):
        passed += 1
    else:
        failed += 1
    
    # ==== EQU Definitions ====
    print("\n=== EQU Definitions ===")
    
    result = parse("BUFFER_SIZE EQU 256")
    stmt = result.statements[0]
    if test("EQU type", stmt.type == StatementType.EQUATE):
        passed += 1
    else:
        failed += 1
    
    if test("EQU label", stmt.label == "BUFFER_SIZE"):
        passed += 1
    else:
        failed += 1
    
    if test("EQU in equates dict", "BUFFER_SIZE" in result.equates):
        passed += 1
    else:
        failed += 1
    
    # = syntax
    result = parse("MAX_VAL = 100")
    if test("= syntax EQU", result.statements[0].type == StatementType.EQUATE):
        passed += 1
    else:
        failed += 1
    
    # ==== Size Overrides ====
    print("\n=== Size Overrides ===")
    
    result = parse("MOV BYTE PTR [BX], 0")
    op = result.statements[0].operands[0]
    if test("BYTE PTR parsed", op.memory is not None):
        passed += 1
    else:
        failed += 1
    
    # ==== Instruction Prefixes ====
    print("\n=== Instruction Prefixes ===")
    
    result = parse("REP MOVSB")
    stmt = result.statements[0]
    if test("REP prefix", stmt.prefix == "REP" or stmt.mnemonic == "REP"):
        passed += 1
    else:
        failed += 1
        print(f"  prefix={stmt.prefix}, mnemonic={stmt.mnemonic}")
    
    # ==== PROC/ENDP ====
    print("\n=== PROC/ENDP ===")
    
    result = parse("MYPROC PROC")
    stmt = result.statements[0]
    if test("PROC directive", stmt.type == StatementType.DIRECTIVE and stmt.mnemonic == "PROC"):
        passed += 1
    else:
        failed += 1
    
    if test("PROC label", stmt.label == "MYPROC"):
        passed += 1
    else:
        failed += 1
    
    result = parse("MYPROC ENDP")
    stmt = result.statements[0]
    if test("ENDP directive", stmt.type == StatementType.DIRECTIVE and stmt.mnemonic == "ENDP"):
        passed += 1
    else:
        failed += 1
    
    # ==== Comments ====
    print("\n=== Comments ===")
    
    result = parse("MOV AX, BX ; comment here")
    stmt = result.statements[0]
    if test("Comment captured", stmt.comment and "comment" in stmt.comment):
        passed += 1
    else:
        failed += 1
    
    result = parse("; This is a comment line")
    stmt = result.statements[0]
    if test("Comment-only line", stmt.type == StatementType.EMPTY):
        passed += 1
    else:
        failed += 1
    
    # ==== Labels Tracking ====
    print("\n=== Labels Tracking ===")
    
    code = """
START:
    MOV AX, BX
LOOP:
    JMP LOOP
MSG DB 'test'
"""
    result = parse(code)
    if test("Labels collected", {"START", "LOOP", "MSG"}.issubset(result.labels)):
        passed += 1
    else:
        failed += 1
        print(f"  Got: {result.labels}")
    
    # ==== 8085 Support ====
    print("\n=== 8085 Support ===")
    
    parser = Parser("8085")
    result = parser.parse("MVI A, 0FFH")
    stmt = result.statements[0]
    if test("8085 instruction", stmt.mnemonic == "MVI"):
        passed += 1
    else:
        failed += 1
    
    # ==== Edge Cases ====
    print("\n=== Edge Cases ===")
    
    # Empty line
    result = parse("")
    if test("Empty line", len(result.statements) == 1 and result.statements[0].type == StatementType.EMPTY):
        passed += 1
    else:
        failed += 1
    
    # Multiple operands (for DB)
    result = parse("DB 1, 2, 3, 4")
    stmt = result.statements[0]
    # Note: operands might be parsed differently - check raw_operands
    if test("Multiple operands", len(stmt.raw_operands) >= 1):
        passed += 1
    else:
        failed += 1
    
    # OFFSET operator
    result = parse("MOV DX, OFFSET MSG")
    op = result.statements[0].operands[1]
    if test("OFFSET expression", op.type == OperandType.EXPRESSION and "OFFSET" in op.value):
        passed += 1
    else:
        failed += 1
    
    # ==== Full Program ====
    print("\n=== Full Program ===")
    
    full_program = """
.MODEL SMALL
.STACK 100H
.DATA
    MSG DB 'Hello$'
.CODE
START:
    MOV AX, @DATA
    MOV DS, AX
    LEA DX, MSG
    MOV AH, 09H
    INT 21H
END START
"""
    result = parse(full_program)
    instr_count = len([s for s in result.statements if s.type == StatementType.INSTRUCTION])
    if test("Full program parses", instr_count >= 5):
        passed += 1
    else:
        failed += 1
        print(f"  Instruction count: {instr_count}")
    
    if test("No parse errors", len(result.errors) == 0):
        passed += 1
    else:
        failed += 1
        print(f"  Errors: {result.errors}")
    
    # ==== Error Tracking ====
    print("\n=== Error Tracking ===")
    
    # Parser should handle bad input gracefully
    result = parse("??? invalid")
    # Should not crash, may have errors
    if test("Graceful error handling", result is not None):
        passed += 1
    else:
        failed += 1
    
    return passed, failed


if __name__ == '__main__':
    passed, failed = run_tests()
    
    print(f"\n{'='*40}")
    print(f"Results: {passed}/{passed+failed} tests passed")
    
    if failed == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ {failed} test(s) failed")
        sys.exit(1)
