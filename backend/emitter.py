#!/usr/bin/env python3
"""
Emitter module for 8086 Assembler.
Generates machine code bytes with multiple output formats.
"""

import struct
from typing import List, Optional


class Emitter:
    """
    Machine code emitter.
    Emits bytes with proper byte ordering and provides multiple output formats.
    """
    
    def __init__(self, endianness: str = 'little', origin: int = 0):
        """
        Initialize emitter.
        
        Args:
            endianness: 'little' or 'big'.
            origin: Base address for output.
        """
        self.endianness = endianness
        self.origin = origin
        self.buffer: bytearray = bytearray()
        self.address = origin
    
    def emit_byte(self, value: int) -> None:
        """Emit a single byte (8-bit)."""
        self.buffer.append(value & 0xFF)
        self.address += 1
    
    def emit_word(self, value: int) -> None:
        """Emit a word (16-bit)."""
        if self.endianness == 'little':
            self.buffer.append(value & 0xFF)
            self.buffer.append((value >> 8) & 0xFF)
        else:
            self.buffer.append((value >> 8) & 0xFF)
            self.buffer.append(value & 0xFF)
        self.address += 2
    
    def emit_dword(self, value: int) -> None:
        """Emit a double word (32-bit)."""
        if self.endianness == 'little':
            self.buffer.extend(struct.pack('<I', value & 0xFFFFFFFF))
        else:
            self.buffer.extend(struct.pack('>I', value & 0xFFFFFFFF))
        self.address += 4
    
    def emit_bytes(self, data: bytes) -> None:
        """Emit raw bytes."""
        self.buffer.extend(data)
        self.address += len(data)
    
    def emit_string(self, s: str, null_terminate: bool = False) -> None:
        """Emit ASCII string."""
        self.buffer.extend(s.encode('ascii', errors='replace'))
        if null_terminate:
            self.buffer.append(0)
        self.address += len(s) + (1 if null_terminate else 0)
    
    def emit_signed_byte(self, value: int) -> None:
        """Emit signed byte."""
        if value < 0:
            value = (256 + value) & 0xFF
        self.emit_byte(value)
    
    def emit_signed_word(self, value: int) -> None:
        """Emit signed word."""
        if value < 0:
            value = (65536 + value) & 0xFFFF
        self.emit_word(value)
    
    def get_position(self) -> int:
        """Get current position in buffer."""
        return len(self.buffer)
    
    def patch_byte(self, offset: int, value: int) -> None:
        """Patch a byte at specific offset."""
        if 0 <= offset < len(self.buffer):
            self.buffer[offset] = value & 0xFF
    
    def patch_word(self, offset: int, value: int) -> None:
        """Patch a word at specific offset."""
        if 0 <= offset < len(self.buffer) - 1:
            if self.endianness == 'little':
                self.buffer[offset] = value & 0xFF
                self.buffer[offset + 1] = (value >> 8) & 0xFF
            else:
                self.buffer[offset] = (value >> 8) & 0xFF
                self.buffer[offset + 1] = value & 0xFF
    
    def reset(self, origin: int = 0) -> None:
        """Reset emitter state."""
        self.origin = origin
        self.address = origin
        self.buffer = bytearray()
    
    def to_binary(self) -> bytes:
        """Get binary output."""
        return bytes(self.buffer)
    
    def to_hex_string(self) -> str:
        """Get output as hex string."""
        return self.buffer.hex().upper()
    
    def to_hex_dump(self, bytes_per_line: int = 16) -> str:
        """Get formatted hex dump."""
        lines = []
        for i in range(0, len(self.buffer), bytes_per_line):
            addr = self.origin + i
            chunk = self.buffer[i:i + bytes_per_line]
            hex_part = ' '.join(f'{b:02X}' for b in chunk)
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            lines.append(f"{addr:04X}: {hex_part:<{bytes_per_line * 3}} {ascii_part}")
        return '\n'.join(lines)
    
    def to_intel_hex(self) -> str:
        """Get Intel HEX format output."""
        lines = []
        addr = self.origin
        
        for i in range(0, len(self.buffer), 16):
            chunk = self.buffer[i:i + 16]
            length = len(chunk)
            
            # :LLAAAA00DD...CC
            record = f':{length:02X}{addr:04X}00'
            for b in chunk:
                record += f'{b:02X}'
            
            checksum = length + (addr >> 8) + (addr & 0xFF) + sum(chunk)
            checksum = (~checksum + 1) & 0xFF
            record += f'{checksum:02X}'
            
            lines.append(record)
            addr += 16
        
        lines.append(':00000001FF')  # EOF record
        return '\n'.join(lines)
