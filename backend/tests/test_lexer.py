#!/usr/bin/env python3
"""
Test suite for the Lexer module.

Tests all token types, edge cases, and error handling.
"""

import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lexer import Lexer, Token, TokenType, parse_immediate, tokenize


class TestTokenTypes:
    """Test recognition of all token types."""
    
    def test_mnemonic_recognition(self):
        """Test that mnemonics are correctly identified."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV ADD SUB JMP CALL RET")
        mnemonics = [t for t in tokens if t.type == TokenType.MNEMONIC]
        assert len(mnemonics) == 6
        assert mnemonics[0].value == "MOV"
        assert mnemonics[1].value == "ADD"
    
    def test_register_recognition_8086(self):
        """Test 8086 register recognition."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("AX BX CX DX SI DI SP BP")
        registers = [t for t in tokens if t.type == TokenType.REGISTER]
        assert len(registers) == 8
        assert all(t.norm in ["AX", "BX", "CX", "DX", "SI", "DI", "SP", "BP"] for t in registers)
    
    def test_register_recognition_8bit(self):
        """Test 8-bit register recognition."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("AL AH BL BH CL CH DL DH")
        registers = [t for t in tokens if t.type == TokenType.REGISTER]
        assert len(registers) == 8
    
    def test_segment_registers(self):
        """Test segment register recognition."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("CS DS ES SS")
        registers = [t for t in tokens if t.type == TokenType.REGISTER]
        assert len(registers) == 4
    
    def test_8085_registers(self):
        """Test 8085 register recognition."""
        lexer = Lexer("8085")
        tokens = lexer.tokenize("A B C D E H L M PSW")
        registers = [t for t in tokens if t.type == TokenType.REGISTER]
        assert len(registers) == 9
    
    def test_directive_with_dot(self):
        """Test directive recognition with leading dot."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize(".MODEL .DATA .CODE .STACK")
        directives = [t for t in tokens if t.type == TokenType.DIRECTIVE]
        assert len(directives) == 4
    
    def test_directive_without_dot(self):
        """Test directive recognition without leading dot."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("DB DW DD EQU ORG SEGMENT")
        directives = [t for t in tokens if t.type == TokenType.DIRECTIVE]
        assert len(directives) == 6
    
    def test_label_colon(self):
        """Test that colon is tokenized separately for labels."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("START:")
        # Should be IDENTIFIER + COLON (parser will combine them)
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "START"
        assert tokens[1].type == TokenType.COLON
    
    def test_comment_semicolon(self):
        """Test semicolon comment."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV AX, BX ; this is a comment")
        comments = [t for t in tokens if t.type == TokenType.COMMENT]
        assert len(comments) == 1
        assert "; this is a comment" in comments[0].value
    
    def test_comment_double_slash(self):
        """Test double-slash comment."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV AX, BX // this is a comment")
        comments = [t for t in tokens if t.type == TokenType.COMMENT]
        assert len(comments) == 1
    
    def test_string_double_quote(self):
        """Test double-quoted string."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize('DB "Hello, World!"')
        strings = [t for t in tokens if t.type == TokenType.STRING_LIT]
        assert len(strings) == 1
        assert strings[0].value == '"Hello, World!"'
    
    def test_string_single_quote(self):
        """Test single-quoted string."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("DB 'Hello'")
        strings = [t for t in tokens if t.type == TokenType.STRING_LIT]
        assert len(strings) == 1
        assert strings[0].value == "'Hello'"


class TestNumericFormats:
    """Test all numeric literal formats."""
    
    def test_decimal(self):
        """Test decimal numbers."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("42 100 0 255")
        immediates = [t for t in tokens if t.type == TokenType.IMMEDIATE]
        assert len(immediates) == 4
        assert immediates[0].value == "42"
    
    def test_negative_decimal(self):
        """Test negative decimal numbers."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("-10 -255")
        immediates = [t for t in tokens if t.type == TokenType.IMMEDIATE]
        assert len(immediates) == 2
        assert immediates[0].value == "-10"
    
    def test_hex_0x(self):
        """Test 0x prefix hex."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("0xFF 0x1A 0x0")
        immediates = [t for t in tokens if t.type == TokenType.IMMEDIATE]
        assert len(immediates) == 3
        assert immediates[0].value == "0xFF"
    
    def test_hex_h_suffix(self):
        """Test h suffix hex."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("0FFh 1Ah 00h 0FFFFh")
        immediates = [t for t in tokens if t.type == TokenType.IMMEDIATE]
        assert len(immediates) == 4
        assert immediates[0].value == "0FFh"
    
    def test_hex_dollar(self):
        """Test $ prefix hex (NASM style)."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("$FF $1A $0")
        # $ can be operator or part of hex
        immediates = [t for t in tokens if t.type == TokenType.IMMEDIATE]
        assert len(immediates) == 3
    
    def test_binary_b_suffix(self):
        """Test binary with b suffix."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("1010b 11111111b 0b")
        immediates = [t for t in tokens if t.type == TokenType.IMMEDIATE]
        assert len(immediates) >= 2
    
    def test_binary_0b_prefix(self):
        """Test binary with 0b prefix."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("0b1010 0b11111111")
        immediates = [t for t in tokens if t.type == TokenType.IMMEDIATE]
        assert len(immediates) == 2
    
    def test_octal(self):
        """Test octal numbers."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("77o 77q 10o")
        immediates = [t for t in tokens if t.type == TokenType.IMMEDIATE]
        assert len(immediates) == 3
    
    def test_char_literal(self):
        """Test character literals."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("'A' 'Z'")
        immediates = [t for t in tokens if t.type == TokenType.IMMEDIATE]
        assert len(immediates) == 2


class TestMemoryReferences:
    """Test memory reference tokenization."""
    
    def test_simple_register_indirect(self):
        """Test [BX] style memory reference."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV AX, [BX]")
        mem_refs = [t for t in tokens if t.type == TokenType.MEMORY_REF]
        assert len(mem_refs) == 1
        assert mem_refs[0].value == "[BX]"
    
    def test_base_plus_index(self):
        """Test [BX+SI] style memory reference."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV AX, [BX+SI]")
        mem_refs = [t for t in tokens if t.type == TokenType.MEMORY_REF]
        assert len(mem_refs) == 1
        assert "BX" in mem_refs[0].value and "SI" in mem_refs[0].value
    
    def test_base_plus_displacement(self):
        """Test [BX+4] style memory reference."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV AX, [BX+4]")
        mem_refs = [t for t in tokens if t.type == TokenType.MEMORY_REF]
        assert len(mem_refs) == 1
    
    def test_complex_addressing(self):
        """Test [BX+SI+8] style memory reference."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV AX, [BX+SI+8]")
        mem_refs = [t for t in tokens if t.type == TokenType.MEMORY_REF]
        assert len(mem_refs) == 1
    
    def test_direct_address(self):
        """Test [1000h] style direct address."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV AX, [1000h]")
        mem_refs = [t for t in tokens if t.type == TokenType.MEMORY_REF]
        assert len(mem_refs) == 1
    
    def test_segment_override(self):
        """Test ES:[BX] style segment override."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV AX, ES:[BX]")
        # ES is a register, : is colon, [BX] is mem ref
        registers = [t for t in tokens if t.type == TokenType.REGISTER]
        mem_refs = [t for t in tokens if t.type == TokenType.MEMORY_REF]
        assert any(r.norm == "ES" for r in registers)
        assert len(mem_refs) == 1


class TestCompleteStatements:
    """Test tokenization of complete assembly statements."""
    
    def test_simple_mov(self):
        """Test simple MOV instruction."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV AX, BX")
        types = [t.type for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
        assert types == [TokenType.MNEMONIC, TokenType.REGISTER, TokenType.COMMA, TokenType.REGISTER]
    
    def test_mov_immediate(self):
        """Test MOV with immediate."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV AX, 100h")
        types = [t.type for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
        assert types == [TokenType.MNEMONIC, TokenType.REGISTER, TokenType.COMMA, TokenType.IMMEDIATE]
    
    def test_mov_memory(self):
        """Test MOV with memory operand."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV AX, [BX+SI]")
        types = [t.type for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
        assert types == [TokenType.MNEMONIC, TokenType.REGISTER, TokenType.COMMA, TokenType.MEMORY_REF]
    
    def test_label_definition(self):
        """Test label definition."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("LOOP_START: MOV AX, 1")
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "LOOP_START"
        assert tokens[1].type == TokenType.COLON
        assert tokens[2].type == TokenType.MNEMONIC
    
    def test_data_definition(self):
        """Test data definition."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize('MSG DB "Hello", 0')
        assert tokens[0].type == TokenType.IDENTIFIER  # MSG
        assert tokens[1].type == TokenType.DIRECTIVE   # DB
        assert tokens[2].type == TokenType.STRING_LIT  # "Hello"
        assert tokens[3].type == TokenType.COMMA
        assert tokens[4].type == TokenType.IMMEDIATE   # 0
    
    def test_equ_definition(self):
        """Test EQU constant definition."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("COUNT EQU 100")
        assert tokens[0].type == TokenType.IDENTIFIER  # COUNT
        assert tokens[1].type == TokenType.DIRECTIVE   # EQU
        assert tokens[2].type == TokenType.IMMEDIATE   # 100
    
    def test_8085_instruction(self):
        """Test 8085 instruction."""
        lexer = Lexer("8085")
        tokens = lexer.tokenize("MVI A, 55H")
        assert tokens[0].type == TokenType.MNEMONIC
        assert tokens[0].value == "MVI"
        assert tokens[1].type == TokenType.REGISTER
        assert tokens[1].value == "A"


class TestParseImmediate:
    """Test the parse_immediate helper function."""
    
    def test_decimal(self):
        """Test decimal parsing."""
        assert parse_immediate("42") == 42
        assert parse_immediate("0") == 0
        assert parse_immediate("255") == 255
    
    def test_negative(self):
        """Test negative number parsing."""
        assert parse_immediate("-10") == -10
        assert parse_immediate("-1") == -1
    
    def test_hex_0x(self):
        """Test 0x hex parsing."""
        assert parse_immediate("0xFF") == 255
        assert parse_immediate("0x10") == 16
        assert parse_immediate("0x0") == 0
    
    def test_hex_h(self):
        """Test h suffix hex parsing."""
        assert parse_immediate("0FFh") == 255
        assert parse_immediate("10h") == 16
        assert parse_immediate("0FFFFh") == 65535
    
    def test_hex_dollar(self):
        """Test $ prefix hex parsing."""
        assert parse_immediate("$FF") == 255
        assert parse_immediate("$10") == 16
    
    def test_binary_b(self):
        """Test b suffix binary parsing."""
        assert parse_immediate("1010b") == 10
        assert parse_immediate("11111111b") == 255
    
    def test_binary_0b(self):
        """Test 0b prefix binary parsing."""
        assert parse_immediate("0b1010") == 10
        assert parse_immediate("0b11111111") == 255
    
    def test_octal(self):
        """Test octal parsing."""
        assert parse_immediate("77o") == 63
        assert parse_immediate("10o") == 8
        assert parse_immediate("77q") == 63
    
    def test_char_literal(self):
        """Test character literal parsing."""
        assert parse_immediate("'A'") == 65
        assert parse_immediate("'Z'") == 90
        assert parse_immediate("'0'") == 48


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_input(self):
        """Test empty input."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF
    
    def test_whitespace_only(self):
        """Test whitespace-only input."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("   \t\t   ")
        # Should only have newlines/EOF
        non_ws = [t for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
        assert len(non_ws) == 0
    
    def test_multiple_lines(self):
        """Test multi-line input."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV AX, 1\nMOV BX, 2\nMOV CX, 3")
        mnemonics = [t for t in tokens if t.type == TokenType.MNEMONIC]
        assert len(mnemonics) == 3
    
    def test_unknown_character(self):
        """Test unknown character handling."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV AX, ~BX")
        unknown = [t for t in tokens if t.type == TokenType.UNKNOWN]
        assert len(unknown) == 1
        assert lexer.has_errors()
    
    def test_case_insensitivity(self):
        """Test case insensitivity."""
        lexer = Lexer("8086")
        tokens1 = lexer.tokenize("MOV AX, BX")
        tokens2 = lexer.tokenize("mov ax, bx")
        tokens3 = lexer.tokenize("Mov Ax, Bx")
        
        # All should produce same token types
        types1 = [t.type for t in tokens1 if t.type != TokenType.EOF]
        types2 = [t.type for t in tokens2 if t.type != TokenType.EOF]
        types3 = [t.type for t in tokens3 if t.type != TokenType.EOF]
        
        assert types1 == types2 == types3
    
    def test_line_column_tracking(self):
        """Test line and column number tracking."""
        lexer = Lexer("8086")
        code = "MOV AX, 1\nADD BX, 2"
        tokens = lexer.tokenize(code)
        
        # MOV should be line 1, col 1
        mov = tokens[0]
        assert mov.line == 1
        assert mov.col == 1
        
        # ADD should be line 2
        add = [t for t in tokens if t.value == "ADD"][0]
        assert add.line == 2
    
    def test_raw_line_preservation(self):
        """Test that raw_line is correctly preserved."""
        lexer = Lexer("8086")
        code = "MOV AX, BX ; comment"
        tokens = lexer.tokenize(code)
        
        # All tokens on this line should have the full line
        for token in tokens:
            if token.type not in (TokenType.NEWLINE, TokenType.EOF):
                assert "MOV AX, BX ; comment" in token.raw_line or token.raw_line == code


class TestDialectSupport:
    """Test dialect-specific features."""
    
    def test_nasm_percent_directives(self):
        """Test NASM %define style directives."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("%define MAX 100")
        directives = [t for t in tokens if t.type == TokenType.DIRECTIVE]
        assert len(directives) >= 1
    
    def test_masm_at_symbol(self):
        """Test MASM @data style symbols."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV AX, @DATA")
        # @DATA should be recognized as identifier
        identifiers = [t for t in tokens if t.type == TokenType.IDENTIFIER]
        assert any("DATA" in t.norm for t in identifiers)
    
    def test_ptr_operator(self):
        """Test PTR operator recognition."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV BYTE PTR [BX], 0")
        operators = [t for t in tokens if t.type == TokenType.OPERATOR]
        assert any(t.norm == "PTR" for t in operators)
    
    def test_offset_operator(self):
        """Test OFFSET operator recognition."""
        lexer = Lexer("8086")
        tokens = lexer.tokenize("MOV DX, OFFSET MSG")
        operators = [t for t in tokens if t.type == TokenType.OPERATOR]
        assert any(t.norm == "OFFSET" for t in operators)


class TestModuleLevelFunction:
    """Test the module-level tokenize function."""
    
    def test_tokenize_function(self):
        """Test the convenience tokenize function."""
        tokens = tokenize("MOV AX, BX")
        assert len(tokens) > 0
        assert tokens[0].type == TokenType.MNEMONIC
    
    def test_tokenize_with_architecture(self):
        """Test tokenize with architecture parameter."""
        tokens = tokenize("MVI A, 55H", architecture="8085")
        assert tokens[0].type == TokenType.MNEMONIC
        assert tokens[0].value == "MVI"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
