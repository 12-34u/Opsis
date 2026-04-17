#!/usr/bin/env python3
"""
Tests for the preprocessor module.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from preprocessor import (
    Preprocessor, Dialect, SourceLocation, PreprocessedLine, 
    Macro, PreprocessorResult, preprocess
)


def check(name: str, condition: bool) -> bool:
    """Simple test helper."""
    if condition:
        print(f"✓ {name}")
        return True
    else:
        print(f"✗ {name}")
        return False


def run_tests() -> tuple:
    """Run all preprocessor tests."""
    passed = 0
    failed = 0
    
    # ==== Dialect Detection Tests ====
    print("\n=== Dialect Detection ===")
    
    # MASM detection
    masm_code = """
.MODEL SMALL
.STACK 100H
.DATA
.CODE
END START
"""
    result = preprocess(masm_code)
    if test("Detect MASM dialect", result.dialect == Dialect.MASM):
        passed += 1
    else:
        failed += 1
    
    # NASM detection
    nasm_code = """
section .text
global _start
%macro TEST 1
%endmacro
"""
    result = preprocess(nasm_code)
    if test("Detect NASM dialect", result.dialect == Dialect.NASM):
        passed += 1
    else:
        failed += 1
    
    # GAS detection
    gas_code = """
.globl _start
.text
.ascii "hello"
movl $1, %eax
"""
    result = preprocess(gas_code)
    if test("Detect GAS dialect", result.dialect == Dialect.GAS):
        passed += 1
    else:
        failed += 1
    
    # TASM detection (IDEAL mode)
    tasm_code = """
IDEAL
MODEL SMALL
CODESEG
"""
    result = preprocess(tasm_code)
    if test("Detect TASM dialect", result.dialect == Dialect.TASM):
        passed += 1
    else:
        failed += 1
    
    # Force dialect
    pp = Preprocessor(dialect=Dialect.NASM)
    result = pp.preprocess(masm_code)
    if test("Force dialect override", result.dialect == Dialect.NASM):
        passed += 1
    else:
        failed += 1
    
    # ==== EQU/Symbol Definition Tests ====
    print("\n=== Symbol Definition ===")
    
    code = """
VALUE1 EQU 100
VALUE2 = 0FFh
VALUE3 EQU 1010b
"""
    result = preprocess(code)
    if test("EQU decimal", result.symbols.get('VALUE1') == 100):
        passed += 1
    else:
        failed += 1
        print(f"  Got: {result.symbols.get('VALUE1')}")
    
    if test("= hex", result.symbols.get('VALUE2') == 255):
        passed += 1
    else:
        failed += 1
        print(f"  Got: {result.symbols.get('VALUE2')}")
    
    if test("EQU binary", result.symbols.get('VALUE3') == 10):
        passed += 1
    else:
        failed += 1
        print(f"  Got: {result.symbols.get('VALUE3')}")
    
    # ==== MASM Macro Tests ====
    print("\n=== MASM Macros ===")
    
    masm_macro = """
PRINT_CHAR MACRO char
    MOV AL, char
    MOV AH, 0EH
    INT 10H
ENDM

START:
    PRINT_CHAR 'A'
    PRINT_CHAR 'B'
"""
    result = preprocess(masm_macro, dialect=Dialect.MASM)
    
    if test("Macro defined", 'PRINT_CHAR' in result.macros):
        passed += 1
    else:
        failed += 1
    
    if test("Macro has 1 param", len(result.macros.get('PRINT_CHAR', Macro('', [], [], SourceLocation('', 0))).params) == 1):
        passed += 1
    else:
        failed += 1
    
    if test("Macro has 3 body lines", len(result.macros.get('PRINT_CHAR', Macro('', [], [], SourceLocation('', 0))).body) == 3):
        passed += 1
    else:
        failed += 1
    
    # Check macro expansion
    expanded_lines = [l.text.strip() for l in result.lines if l.location.macro_name == 'PRINT_CHAR']
    if test("Macro expanded twice", len(expanded_lines) == 6):  # 3 lines x 2 invocations
        passed += 1
    else:
        failed += 1
        print(f"  Got {len(expanded_lines)} lines")
    
    # Check parameter substitution
    has_a = any("'A'" in l for l in expanded_lines)
    has_b = any("'B'" in l for l in expanded_lines)
    if test("Macro params substituted", has_a and has_b):
        passed += 1
    else:
        failed += 1
    
    # ==== NASM Macro Tests ====
    print("\n=== NASM Macros ===")
    
    nasm_macro = """
%macro PUSHALL 0
    PUSH AX
    PUSH BX
    PUSH CX
    PUSH DX
%endmacro

section .text
    PUSHALL
"""
    result = preprocess(nasm_macro, dialect=Dialect.NASM)
    
    if test("NASM macro defined", 'PUSHALL' in result.macros):
        passed += 1
    else:
        failed += 1
    
    expanded = [l.text.strip() for l in result.lines if l.location.macro_name == 'PUSHALL']
    if test("NASM macro expanded", len(expanded) == 4):
        passed += 1
    else:
        failed += 1
    
    # ==== LOCAL Labels ====
    print("\n=== LOCAL Labels ===")
    
    local_macro = """
LOOP_N MACRO count
    LOCAL loop_start, loop_end
    MOV CX, count
loop_start:
    DEC CX
    JNZ loop_start
loop_end:
ENDM

    LOOP_N 10
    LOOP_N 20
"""
    result = preprocess(local_macro, dialect=Dialect.MASM)
    
    macro = result.macros.get('LOOP_N')
    if test("LOCAL labels declared", macro and 'LOOP_START' in macro.local_labels):
        passed += 1
    else:
        failed += 1
    
    # Check that local labels are unique across invocations
    expanded = [l.text for l in result.lines if l.location.macro_name]
    unique_labels = set()
    for line in expanded:
        if '@@' in line:
            for word in line.split():
                if '@@' in word:
                    unique_labels.add(word.rstrip(':'))
    
    if test("LOCAL labels made unique", len(unique_labels) >= 2):
        passed += 1
    else:
        failed += 1
        print(f"  Found labels: {unique_labels}")
    
    # ==== Conditional Assembly ====
    print("\n=== Conditional Assembly ===")
    
    cond_code = """
DEBUG EQU 1

IFDEF DEBUG
    MOV AX, 1  ; Debug mode
ELSE
    MOV AX, 0  ; Release mode
ENDIF
"""
    result = preprocess(cond_code)
    
    debug_line = [l for l in result.lines if 'Debug mode' in l.text]
    release_line = [l for l in result.lines if 'Release mode' in l.text]
    
    if test("IFDEF includes debug code", len(debug_line) == 1):
        passed += 1
    else:
        failed += 1
    
    if test("IFDEF excludes release code", len(release_line) == 0):
        passed += 1
    else:
        failed += 1
    
    # IFNDEF test
    ifndef_code = """
IFNDEF FEATURE_X
    MOV AX, 1  ; Feature X not defined
ELSE
    MOV AX, 2  ; Feature X defined
ENDIF
"""
    result = preprocess(ifndef_code)
    
    not_defined_line = [l for l in result.lines if 'not defined' in l.text]
    if test("IFNDEF when not defined", len(not_defined_line) == 1):
        passed += 1
    else:
        failed += 1
    
    # With pre-defined symbol
    result = preprocess(ifndef_code, defines={'FEATURE_X': '1'})
    defined_line = [l for l in result.lines if 'X defined' in l.text and 'not defined' not in l.text]
    if test("IFNDEF with defined symbol", len(defined_line) == 1):
        passed += 1
    else:
        failed += 1
    
    # ==== Source Map ====
    print("\n=== Source Map ===")
    
    code = """
LINE1
LINE2
LINE3
"""
    result = preprocess(code, "test.asm")
    
    if test("Source map populated", len(result.source_map) > 0):
        passed += 1
    else:
        failed += 1
    
    # Check line tracking
    lines_with_text = [(i, l) for i, l in enumerate(result.lines, 1) if 'LINE2' in l.text]
    if lines_with_text:
        idx, line = lines_with_text[0]
        if test("Source map tracks line numbers", line.location.line == 3):
            passed += 1
        else:
            failed += 1
            print(f"  Expected line 3, got {line.location.line}")
    else:
        failed += 1
        print("  LINE2 not found")
    
    # ==== Include Handling ====
    print("\n=== Include Handling ===")
    
    # Mock file reader
    include_files = {
        'macros.inc': 'MACRO1 MACRO\n    NOP\nENDM',
        'data.inc': 'VALUE1 EQU 100'
    }
    
    def mock_reader(path):
        basename = Path(path).name
        if basename in include_files:
            return include_files[basename]
        raise FileNotFoundError(f"Mock file not found: {path}")
    
    pp = Preprocessor(file_reader=mock_reader, dialect=Dialect.MASM)
    
    code_with_include = """
INCLUDE macros.inc
INCLUDE data.inc
START:
    MACRO1
"""
    result = pp.preprocess(code_with_include, "main.asm")
    
    if test("Include processes macros", 'MACRO1' in result.macros):
        passed += 1
    else:
        failed += 1
    
    if test("Include processes symbols", result.symbols.get('VALUE1') == 100):
        passed += 1
    else:
        failed += 1
    
    # Circular include detection
    circular_files = {
        'a.inc': 'INCLUDE b.inc',
        'b.inc': 'INCLUDE a.inc'
    }
    
    def circular_reader(path):
        basename = Path(path).name
        if basename in circular_files:
            return circular_files[basename]
        raise FileNotFoundError(path)
    
    pp2 = Preprocessor(file_reader=circular_reader, dialect=Dialect.MASM)
    result = pp2.preprocess('INCLUDE a.inc', 'main.asm')
    
    if test("Circular include detected", pp2.has_errors()):
        passed += 1
    else:
        failed += 1
    
    # ==== Error Handling ====
    print("\n=== Error Handling ===")
    
    # Unclosed macro
    unclosed = """
TEST MACRO
    NOP
"""
    result = preprocess(unclosed, dialect=Dialect.MASM)
    if test("Unclosed macro error", any('not terminated' in e['message'] for e in result.errors)):
        passed += 1
    else:
        failed += 1
    
    # Unclosed conditional
    unclosed_if = """
IFDEF TEST
    NOP
"""
    result = preprocess(unclosed_if)
    if test("Unclosed IF error", any('Unclosed conditional' in e['message'] for e in result.errors)):
        passed += 1
    else:
        failed += 1
    
    # ELSE without IF
    bad_else = """
ELSE
    NOP
ENDIF
"""
    result = preprocess(bad_else)
    if test("ELSE without IF error", any('ELSE without IF' in e['message'] for e in result.errors)):
        passed += 1
    else:
        failed += 1
    
    # ==== Multi-param Macro ====
    print("\n=== Multi-param Macro ===")
    
    multi_param = """
ADD_REGS MACRO dest, src1, src2
    MOV dest, src1
    ADD dest, src2
ENDM

    ADD_REGS AX, BX, CX
"""
    result = preprocess(multi_param, dialect=Dialect.MASM)
    
    expanded = [l.text.strip() for l in result.lines if l.location.macro_name]
    if test("Multi-param first line", any('MOV AX, BX' in l for l in expanded)):
        passed += 1
    else:
        failed += 1
        print(f"  Expanded: {expanded}")
    
    if test("Multi-param second line", any('ADD AX, CX' in l for l in expanded)):
        passed += 1
    else:
        failed += 1
    
    # ==== NASM %define ====
    print("\n=== NASM %define ===")
    
    define_code = """
%define MAX_VALUE 255
%define DOUBLE(x) (x * 2)

section .data
    val db MAX_VALUE
"""
    result = preprocess(define_code, dialect=Dialect.NASM)
    
    if test("%define creates symbol", 'MAX_VALUE' in result.symbols):
        passed += 1
    else:
        failed += 1
    
    if test("%define function-like creates macro", 'DOUBLE' in result.macros):
        passed += 1
    else:
        failed += 1
    
    # ==== Empty/Comment Lines ====
    print("\n=== Empty/Comment Handling ===")
    
    comment_code = """
; This is a comment
    ; Indented comment
// C-style comment

MOV AX, BX
"""
    result = preprocess(comment_code)
    
    empty_lines = [l for l in result.lines if l.is_empty]
    non_empty = [l for l in result.lines if not l.is_empty]
    
    if test("Empty lines flagged", len(empty_lines) >= 3):
        passed += 1
    else:
        failed += 1
    
    if test("Non-empty lines preserved", any('MOV AX, BX' in l.text for l in non_empty)):
        passed += 1
    else:
        failed += 1
    
    # ==== PreprocessedLine Structure ====
    print("\n=== PreprocessedLine Structure ===")
    
    code = "MOV AX, 1"
    result = preprocess(code, "test.asm")
    
    line = next((l for l in result.lines if 'MOV' in l.text), None)
    if test("Line has text", line and line.text.strip() == "MOV AX, 1"):
        passed += 1
    else:
        failed += 1
    
    if test("Line has location", line and line.location.file == "test.asm"):
        passed += 1
    else:
        failed += 1
    
    return passed, failed


# ============================================================================
# Pytest-Compatible Tests for Pseudo-Variables
# ============================================================================

import pytest

class TestPseudoVariables:
    """Test cases for MASM/TASM pseudo-variable resolution."""
    
    def test_at_data_small_model(self):
        """@data should resolve to '_DATA' in small model."""
        code = ".MODEL small\n.DATA\n.CODE\nmov ax, @data\nmov ds, ax\nEND"
        result = preprocess(code)
        # Find the line with @data and verify it was resolved
        mov_line = next((l for l in result.lines if 'mov ax' in l.text.lower()), None)
        assert mov_line is not None
        assert '_DATA' in mov_line.text.upper()
        assert len(result.errors) == 0
    
    def test_at_data_flat_model(self):
        """@data should resolve to 'FLAT' in flat model."""
        code = ".MODEL flat, STDCALL\nmov eax, @data\nEND"
        result = preprocess(code)
        mov_line = next((l for l in result.lines if 'mov eax' in l.text.lower()), None)
        assert mov_line is not None
        assert 'FLAT' in mov_line.text.upper()
        assert len(result.errors) == 0
    
    def test_at_code_resolved(self):
        """@code should resolve to '_TEXT' in small model."""
        code = ".MODEL small\n.CODE\nmov ax, @code\nEND"
        result = preprocess(code)
        mov_line = next((l for l in result.lines if 'mov ax' in l.text.lower()), None)
        assert mov_line is not None
        assert '_TEXT' in mov_line.text.upper()
        assert len(result.errors) == 0
    
    def test_at_stack_resolved(self):
        """@stack should resolve to '_STACK'."""
        code = ".MODEL small\n.STACK 100h\nmov ax, @stack\nEND"
        result = preprocess(code)
        mov_line = next((l for l in result.lines if 'mov ax' in l.text.lower()), None)
        assert mov_line is not None
        assert '_STACK' in mov_line.text.upper()
        assert len(result.errors) == 0
    
    def test_at_model_value(self):
        """@Model should resolve to integer 5 for large model."""
        code = ".MODEL large\n.CODE\nmov ax, @Model\nEND"
        result = preprocess(code)
        mov_line = next((l for l in result.lines if 'mov ax' in l.text.lower()), None)
        assert mov_line is not None
        assert '5' in mov_line.text
        assert len(result.errors) == 0
    
    def test_at_datasize_small(self):
        """@DataSize should resolve to 0 for small model."""
        code = ".MODEL small\n.CODE\nmov ax, @DataSize\nEND"
        result = preprocess(code)
        mov_line = next((l for l in result.lines if 'mov ax' in l.text.lower()), None)
        assert mov_line is not None
        assert ', 0' in mov_line.text or ',0' in mov_line.text
        assert len(result.errors) == 0
    
    def test_at_datasize_large(self):
        """@DataSize should resolve to 1 for large model."""
        code = ".MODEL large\n.CODE\nmov ax, @DataSize\nEND"
        result = preprocess(code)
        mov_line = next((l for l in result.lines if 'mov ax' in l.text.lower()), None)
        assert mov_line is not None
        assert ', 1' in mov_line.text or ',1' in mov_line.text
        assert len(result.errors) == 0
    
    def test_at_wordsize_16bit(self):
        """@WordSize should resolve to 2 for 16-bit model."""
        code = ".MODEL small\n.CODE\nmov ax, @WordSize\nEND"
        result = preprocess(code)
        mov_line = next((l for l in result.lines if 'mov ax' in l.text.lower()), None)
        assert mov_line is not None
        assert ', 2' in mov_line.text or ',2' in mov_line.text
        assert len(result.errors) == 0
    
    def test_at_wordsize_32bit(self):
        """@WordSize should resolve to 4 for 32-bit (flat) model."""
        code = ".MODEL flat\n.CODE\nmov eax, @WordSize\nEND"
        result = preprocess(code)
        mov_line = next((l for l in result.lines if 'mov eax' in l.text.lower()), None)
        assert mov_line is not None
        assert ', 4' in mov_line.text or ',4' in mov_line.text
        assert len(result.errors) == 0
    
    def test_full_dos_startup_sequence(self):
        """Full DOS startup sequence should assemble without errors."""
        code = """.MODEL small
.STACK 100h
.DATA
msg DB 'Hello', 0
.CODE
start:
    mov ax, @data
    mov ds, ax
    mov ax, @stack
    mov ss, ax
    mov ah, 4Ch
    int 21h
END start"""
        result = preprocess(code)
        # Verify @data and @stack are resolved
        data_line = next((l for l in result.lines if '@data' in l.text.lower()), None)
        stack_line = next((l for l in result.lines if '@stack' in l.text.lower()), None)
        # They should be resolved (no @data/@stack in output)
        assert data_line is None or '_DATA' in data_line.text.upper()
        assert stack_line is None or '_STACK' in stack_line.text.upper()
        assert len(result.errors) == 0
    
    def test_at_prefix_user_label_not_corrupted(self):
        """User-defined @-prefixed labels should not be substituted."""
        code = "@myLabel: NOP\njmp @myLabel"
        result = preprocess(code)
        # @myLabel should remain unchanged
        label_line = next((l for l in result.lines if '@myLabel' in l.text), None)
        assert label_line is not None
        assert '@myLabel' in label_line.text
        assert len(result.errors) == 0
    
    def test_at_version_constant(self):
        """@Version should resolve to 600 (MASM 6.00 compatible)."""
        code = "mov ax, @Version"
        result = preprocess(code)
        mov_line = next((l for l in result.lines if 'mov ax' in l.text.lower()), None)
        assert mov_line is not None
        assert '600' in mov_line.text
        assert len(result.errors) == 0
    
    def test_at_codesize_near(self):
        """@CodeSize should resolve to 0 for small model (near code)."""
        code = ".MODEL small\n.CODE\nmov ax, @CodeSize\nEND"
        result = preprocess(code)
        mov_line = next((l for l in result.lines if 'mov ax' in l.text.lower()), None)
        assert mov_line is not None
        assert ', 0' in mov_line.text or ',0' in mov_line.text
        assert len(result.errors) == 0
    
    def test_at_codesize_far(self):
        """@CodeSize should resolve to 1 for large model (far code)."""
        code = ".MODEL large\n.CODE\nmov ax, @CodeSize\nEND"
        result = preprocess(code)
        mov_line = next((l for l in result.lines if 'mov ax' in l.text.lower()), None)
        assert mov_line is not None
        assert ', 1' in mov_line.text or ',1' in mov_line.text
        assert len(result.errors) == 0


if __name__ == '__main__':
    passed, failed = run_tests()
    
    print(f"\n{'='*40}")
    print(f"Results: {passed}/{passed+failed} tests passed")
    
    if failed == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ {failed} test(s) failed")
        sys.exit(1)
