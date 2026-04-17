#!/usr/bin/env python3
"""
Output Writer module for the Dynamic Two-Pass Assembler.
Handles writing output in various formats.
"""

from pathlib import Path
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from emitter import Emitter
    from assembler_engine import IRNode


class OutputWriter:
    """
    Writes assembled output in various formats.
    
    Supports binary (.bin), hex dump (.hex), listing (.lst),
    and Intel HEX (.ihex) formats.
    """
    
    def __init__(self, output_stem: str = "output"):
        """
        Initialize output writer.
        
        Args:
            output_stem: Base filename for output files.
        """
        self.output_stem = output_stem
    
    def write_binary(self, data: bytes, path: Optional[Path] = None) -> Path:
        """
        Write binary output.
        
        Args:
            data: Binary data to write.
            path: Output path (optional).
            
        Returns:
            Path to written file.
        """
        output_path = path or Path(f"{self.output_stem}.bin")
        output_path.write_bytes(data)
        return output_path
    
    def write_hex(self, hex_string: str, path: Optional[Path] = None) -> Path:
        """
        Write hex string output.
        
        Args:
            hex_string: Hex string to write.
            path: Output path (optional).
            
        Returns:
            Path to written file.
        """
        output_path = path or Path(f"{self.output_stem}.hex")
        output_path.write_text(hex_string)
        return output_path
    
    def write_listing(self, listing: str, path: Optional[Path] = None) -> Path:
        """
        Write listing output.
        
        Args:
            listing: Listing text to write.
            path: Output path (optional).
            
        Returns:
            Path to written file.
        """
        output_path = path or Path(f"{self.output_stem}.lst")
        output_path.write_text(listing)
        return output_path
    
    def write_intel_hex(self, ihex: str, path: Optional[Path] = None) -> Path:
        """
        Write Intel HEX output.
        
        Args:
            ihex: Intel HEX string to write.
            path: Output path (optional).
            
        Returns:
            Path to written file.
        """
        output_path = path or Path(f"{self.output_stem}.ihex")
        output_path.write_text(ihex)
        return output_path
    
    def write_all(
        self, 
        binary: bytes, 
        hex_dump: str, 
        listing: str, 
        intel_hex: str
    ) -> dict:
        """
        Write all output formats.
        
        Args:
            binary: Binary data.
            hex_dump: Hex dump string.
            listing: Assembly listing.
            intel_hex: Intel HEX format.
            
        Returns:
            Dictionary mapping format to output path.
        """
        return {
            'bin': self.write_binary(binary),
            'hex': self.write_hex(hex_dump),
            'lst': self.write_listing(listing),
            'ihex': self.write_intel_hex(intel_hex)
        }
