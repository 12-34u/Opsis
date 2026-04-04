#!/usr/bin/env python3
"""
Emitter module for the Dynamic Two-Pass Assembler.
Handles byte-width-aware machine code emission with multiple output formats.
"""

from __future__ import annotations
import struct
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from assembler_engine import IRNode


class Emitter:
    """
    Machine code emitter with multiple output formats.
    
    Provides byte-width-aware emission and supports binary, hex,
    Intel HEX, and listing output formats.
    """
    
    def __init__(self, endianness: str = 'little', origin: int = 0):
        """
        Initialize emitter.
        
        Args:
            endianness: Byte order ('little' or 'big').
            origin: Base address for output.
        """
        self.endianness = endianness
        self.origin = origin
        self.output: bytearray = bytearray()
        self.current_address = origin
    
    def emit_byte(self, value: int) -> None:
        """
        Emit a single byte.
        
        Args:
            value: Byte value (0-255).
        """
        self.output.append(value & 0xFF)
        self.current_address += 1
    
    def emit_word(self, value: int) -> None:
        """
        Emit a 16-bit word.
        
        Args:
            value: Word value (0-65535).
        """
        if self.endianness == 'little':
            self.output.extend(struct.pack('<H', value & 0xFFFF))
        else:
            self.output.extend(struct.pack('>H', value & 0xFFFF))
        self.current_address += 2
    
    def emit_dword(self, value: int) -> None:
        """
        Emit a 32-bit double word.
        
        Args:
            value: Double word value.
        """
        if self.endianness == 'little':
            self.output.extend(struct.pack('<I', value & 0xFFFFFFFF))
        else:
            self.output.extend(struct.pack('>I', value & 0xFFFFFFFF))
        self.current_address += 4
    
    def emit_bytes(self, data: bytes) -> None:
        """
        Emit raw bytes.
        
        Args:
            data: Byte sequence to emit.
        """
        self.output.extend(data)
        self.current_address += len(data)
    
    def emit_signed_byte(self, value: int) -> None:
        """
        Emit a signed byte.
        
        Args:
            value: Signed byte value (-128 to 127).
        """
        if value < 0:
            value = (256 + value) & 0xFF
        self.emit_byte(value)
    
    def emit_signed_word(self, value: int) -> None:
        """
        Emit a signed word.
        
        Args:
            value: Signed word value.
        """
        if value < 0:
            value = (65536 + value) & 0xFFFF
        self.emit_word(value)
    
    def emit_modrm(self, mod: int, reg: int, rm: int) -> None:
        """
        Emit ModR/M byte.
        
        Args:
            mod: Addressing mode (0-3).
            reg: Register or opcode extension (0-7).
            rm: Register/memory operand (0-7).
        """
        modrm = ((mod & 0x3) << 6) | ((reg & 0x7) << 3) | (rm & 0x7)
        self.emit_byte(modrm)
    
    def get_position(self) -> int:
        """Get current output position."""
        return len(self.output)
    
    def patch_byte(self, offset: int, value: int) -> None:
        """
        Patch a byte at a specific offset.
        
        Args:
            offset: Offset in output buffer.
            value: New byte value.
        """
        self.output[offset] = value & 0xFF
    
    def patch_word(self, offset: int, value: int) -> None:
        """
        Patch a word at a specific offset.
        
        Args:
            offset: Offset in output buffer.
            value: New word value.
        """
        if self.endianness == 'little':
            packed = struct.pack('<H', value & 0xFFFF)
        else:
            packed = struct.pack('>H', value & 0xFFFF)
        self.output[offset:offset + 2] = packed
    
    def to_binary(self) -> bytes:
        """
        Get output as binary bytes.
        
        Returns:
            Binary output.
        """
        return bytes(self.output)
    
    def to_hex_string(self) -> str:
        """
        Get output as hex string.
        
        Returns:
            Hex string representation.
        """
        return self.output.hex().upper()
    
    def to_hex_dump(self, bytes_per_line: int = 16) -> str:
        """
        Get output as formatted hex dump.
        
        Args:
            bytes_per_line: Number of bytes per line.
            
        Returns:
            Formatted hex dump string.
        """
        lines = []
        for i in range(0, len(self.output), bytes_per_line):
            addr = self.origin + i
            chunk = self.output[i:i + bytes_per_line]
            hex_part = ' '.join(f'{b:02X}' for b in chunk)
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            lines.append(f"{addr:04X}: {hex_part:<{bytes_per_line * 3}} {ascii_part}")
        return '\n'.join(lines)
    
    def to_intel_hex(self) -> str:
        """
        Get output as Intel HEX format.
        
        Returns:
            Intel HEX string.
        """
        lines = []
        addr = self.origin
        
        for i in range(0, len(self.output), 16):
            chunk = self.output[i:i + 16]
            length = len(chunk)
            
            # Build record: :LLAAAA00DD...CC
            record = f':{length:02X}{addr:04X}00'
            for b in chunk:
                record += f'{b:02X}'
            
            # Calculate checksum
            checksum = length + (addr >> 8) + (addr & 0xFF) + sum(chunk)
            checksum = (~checksum + 1) & 0xFF
            record += f'{checksum:02X}'
            
            lines.append(record)
            addr += 16
        
        # End of file record
        lines.append(':00000001FF')
        return '\n'.join(lines)
    
    def to_listing(self, ir_nodes: List['IRNode']) -> str:
        """
        Generate assembly listing with addresses and machine code.
        
        Args:
            ir_nodes: List of IR nodes from assembly.
            
        Returns:
            Formatted listing string.
        """
        lines = [
            "Assembly Listing",
            "=" * 80,
            f"{'Addr':<8} {'Machine Code':<24} {'Source':<40}",
            "-" * 80
        ]
        
        for node in ir_nodes:
            addr_str = f"{node.address:04X}"
            # Get machine code bytes for this node
            start = node.address - self.origin
            end = start + node.byte_width if hasattr(node, 'byte_width') else start + 1
            if 0 <= start < len(self.output) and end <= len(self.output):
                code_bytes = self.output[start:end]
                code_str = ' '.join(f'{b:02X}' for b in code_bytes)
            else:
                code_str = ''
            
            source = node.source_line.strip() if node.source_line else ''
            lines.append(f"{addr_str:<8} {code_str:<24} {source:<40}")
        
        lines.append("=" * 80)
        return '\n'.join(lines)
    
    def reset(self, origin: int = 0) -> None:
        """
        Reset emitter state.
        
        Args:
            origin: New origin address.
        """
        self.origin = origin
        self.output = bytearray()
        self.current_address = origin
