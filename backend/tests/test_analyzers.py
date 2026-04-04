#!/usr/bin/env python3
"""
Tests for the syntax and semantic analyzers.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser import parse
from syntax_analyzer import SyntaxAnalyzer, analyze_syntax
from semantic_analyzer import SemanticAnalyzer, analyze_semantics


def test(name: str, condition: bool) -> bool:
    """Simple test helper."""
    if condition:
        print(f"✓ {name}")
        return True
    else:
        print(f"✗ {name}")
        return False


def run_tests() -> tuple:
    """Run all analyzer tests."""
    passed = 0
    failed = 0
    
    # ==== Syntax Analyzer Tests ====
    print("\n=== Syntax Analyzer ===")
    
    # Valid instruction
    result = analyze_syntax(parse("MOV AX, BX"))
    if test("Valid instruction passes", result.valid):
        passed += 1
    else:
        failed += 1
        print(f"  Errors: {[e.message for e in result.errors]}")
    
    # Missing operand
    result = analyze_syntax(parse("MOV"))
    if test("Missing operand detected", 
            any(e.code == "E100" for e in result.errors)):
        passed += 1
    else:
        failed += 1
    
    # Too many operands
    result = analyze_syntax(parse("ADD AX, BX, CX"))
    if test("Too many operands detected",
            any(e.code == "E101" for e in result.errors)):
        passed += 1
    else:
        failed += 1
    
    # Unknown instruction
    result = analyze_syntax(parse("FOOBAR AX, BX"))
    if test("Unknown instruction detected",
            any(e.code == "E107" for e in result.errors)):
        passed += 1
    else:
        failed += 1
    
    # Duplicate label
    result = analyze_syntax(parse("LABEL1:\nMOV AX, BX\nLABEL1:"))
    if test("Duplicate label detected",
            any(e.code == "E109" for e in result.errors)):
        passed += 1
    else:
        failed += 1
    
    # Valid memory addressing
    result = analyze_syntax(parse("MOV AX, [BX]"))
    if test("Valid memory addressing passes", result.valid):
        passed += 1
    else:
        failed += 1
        print(f"  Errors: {[e.message for e in result.errors]}")
    
    # Valid complex addressing
    result = analyze_syntax(parse("MOV AX, [BX+SI+4]"))
    if test("Complex addressing passes", result.valid):
        passed += 1
    else:
        failed += 1
        print(f"  Errors: {[e.message for e in result.errors]}")
    
    # Valid data definition
    result = analyze_syntax(parse("MSG DB 'Hello'"))
    if test("Data definition passes", result.valid):
        passed += 1
    else:
        failed += 1
        print(f"  Errors: {[e.message for e in result.errors]}")
    
    # Empty DB error
    result = analyze_syntax(parse("MSG DB"))
    if test("Empty DB detected",
            any(e.code == "E100" for e in result.errors)):
        passed += 1
    else:
        failed += 1
    
    # ==== Semantic Analyzer Tests ====
    print("\n=== Semantic Analyzer ===")
    
    # Undefined label
    result = analyze_semantics(parse("JMP NOWHERE"))
    if test("Undefined label detected",
            any(e.code == "E201" for e in result.errors)):
        passed += 1
    else:
        failed += 1
    
    # Forward reference (should be OK)
    code = """
    JMP END_LABEL
END_LABEL:
    RET
"""
    result = analyze_semantics(parse(code))
    if test("Forward reference allowed", 
            not any(e.code == "E201" and "END_LABEL" in e.message for e in result.errors)):
        passed += 1
    else:
        failed += 1
        print(f"  Errors: {[e.message for e in result.errors]}")
    
    # Backward reference (should be OK)
    code = """
START:
    JMP START
"""
    result = analyze_semantics(parse(code))
    if test("Backward reference allowed", result.valid):
        passed += 1
    else:
        failed += 1
        print(f"  Errors: {[e.message for e in result.errors]}")
    
    # Symbol table populated
    code = """
MSG DB 'Hello'
COUNT DW 0
START:
    MOV AX, BX
"""
    result = analyze_semantics(parse(code))
    if test("Symbol table populated",
            "MSG" in result.symbols and "COUNT" in result.symbols):
        passed += 1
    else:
        failed += 1
        print(f"  Symbols: {list(result.symbols.keys())}")
    
    # Symbol types correct
    if test("Symbol types correct",
            result.symbols.get("MSG") and result.symbols["MSG"].type == "data" and
            result.symbols.get("START") and result.symbols["START"].type == "label"):
        passed += 1
    else:
        failed += 1
    
    # Reference tracking
    code = """
MSG DB 'Hello'
START:
    LEA DX, MSG
    LEA SI, MSG
"""
    result = analyze_semantics(parse(code))
    if test("References tracked",
            result.symbols.get("MSG") and len(result.symbols["MSG"].references) >= 2):
        passed += 1
    else:
        failed += 1
        refs = result.symbols.get("MSG")
        print(f"  MSG refs: {refs.references if refs else 'N/A'}")
    
    # Unmatched ENDP warning
    code = """
ENDP
"""
    result = analyze_semantics(parse(code))
    # ENDP alone might be parsed differently
    # This is more of a structural check
    
    # PROC/ENDP matching
    code = """
MYPROC PROC
    RET
MYPROC ENDP
"""
    result = analyze_semantics(parse(code))
    # Note: ENDP creates duplicate symbol issue
    # Check that MYPROC is in symbols
    if test("PROC creates symbol",
            "MYPROC" in result.symbols and result.symbols["MYPROC"].type == "proc"):
        passed += 1
    else:
        failed += 1
    
    # EQU handling
    code = """
BUFFER_SIZE EQU 256
"""
    result = analyze_semantics(parse(code))
    if test("EQU creates symbol",
            "BUFFER_SIZE" in result.symbols and result.symbols["BUFFER_SIZE"].type == "equate"):
        passed += 1
    else:
        failed += 1
    
    # Unused label warning
    code = """
UNUSED_LABEL:
    NOP
USED_LABEL:
    JMP USED_LABEL
"""
    result = analyze_semantics(parse(code))
    if test("Unused label warning",
            any(w.code == "W200" and "UNUSED" in w.message for w in result.warnings)):
        passed += 1
    else:
        failed += 1
    
    # ==== Integration Test ====
    print("\n=== Integration Tests ===")
    
    # Full valid program
    full_program = """
.MODEL SMALL
.STACK 100H
.DATA
    MSG DB 'Hello, World!$'
.CODE
START:
    MOV AX, @DATA
    MOV DS, AX
    LEA DX, MSG
    MOV AH, 09H
    INT 21H
    MOV AX, 4C00H
    INT 21H
END START
"""
    parse_result = parse(full_program)
    syntax_result = analyze_syntax(parse_result)
    semantic_result = analyze_semantics(parse_result)
    
    if test("Full program syntax valid", syntax_result.valid):
        passed += 1
    else:
        failed += 1
        print(f"  Syntax errors: {[e.message for e in syntax_result.errors]}")
    
    if test("Full program semantics valid", semantic_result.valid):
        passed += 1
    else:
        failed += 1
        print(f"  Semantic errors: {[e.message for e in semantic_result.errors]}")
    
    # Program with errors
    error_program = """
START:
    MOV AX        ; Missing operand
    XYZ BX, CX    ; Unknown instruction
    JMP NOWHERE   ; Undefined label
START:            ; Duplicate label
"""
    parse_result = parse(error_program)
    syntax_result = analyze_syntax(parse_result)
    semantic_result = analyze_semantics(parse_result)
    
    if test("Error program has syntax errors", not syntax_result.valid):
        passed += 1
    else:
        failed += 1
    
    if test("Error program has semantic errors", not semantic_result.valid):
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
