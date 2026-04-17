#!/usr/bin/env python3
"""
CLI for the Dynamic Two-Pass Assembler.
"""

import argparse
import json
import sys
from pathlib import Path
from assembler_standalone import ISADefinition, AssemblerEngine, create_full_isa


def main():
    parser = argparse.ArgumentParser(description='Dynamic Two-Pass Assembler')
    parser.add_argument('input', help='Input assembly file')
    parser.add_argument('--format', choices=['bin', 'hex', 'lst', 'all'], default='all',
                        help='Output format')
    parser.add_argument('--isa', default='isa.json', help='Path to ISA JSON')
    parser.add_argument('--origin', type=lambda x: int(x, 0), default=0,
                        help='Base address (e.g., 0x0100)')
    parser.add_argument('--output', '-o', help='Output file stem')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Read input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        return 1
    
    source = input_path.read_text()
    output_stem = args.output or input_path.stem
    
    # Load ISA
    isa_path = Path(args.isa)
    if not isa_path.exists():
        print(f"Warning: ISA file not found, using embedded defaults", file=sys.stderr)
        isa_data = {}
    else:
        isa_data = json.loads(isa_path.read_text())
    
    # Assemble
    try:
        isa = ISADefinition(create_full_isa())
        engine = AssemblerEngine(isa)
        result = engine.assemble(source)
        
        if result is None:
            print("Assembly failed:", file=sys.stderr)
            for err in engine.errors.errors:
                print(f"  Line {err.line}: {err.message}", file=sys.stderr)
            return 1
        
        if args.verbose:
            print(engine.symbol_table.dump())
            print()
        
        # Output
        if args.format in ('bin', 'all'):
            Path(f"{output_stem}.bin").write_bytes(result)
            print(f"Wrote {output_stem}.bin ({len(result)} bytes)")
        
        if args.format in ('hex', 'all'):
            hex_dump = engine.emitter.get_formatted_hex()
            Path(f"{output_stem}.hex").write_text(hex_dump)
            print(f"Wrote {output_stem}.hex")
        
        if args.format in ('lst', 'all'):
            listing = engine.get_listing()
            Path(f"{output_stem}.lst").write_text(listing)
            print(f"Wrote {output_stem}.lst")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
