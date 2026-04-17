#!/usr/bin/env python3
"""
Preprocessor module for 8085/8086 Assembler.

Handles:
- Dialect detection (NASM, TASM, MASM, GAS, Raw)
- Macro definition and expansion
- Include file processing
- Conditional assembly (%ifdef, IFDEF, etc.)
- Source mapping for error tracing
"""

from __future__ import annotations
import os
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Set, Callable


class Dialect(Enum):
    """Assembler dialect enumeration."""
    NASM = auto()    # Netwide Assembler
    TASM = auto()    # Turbo Assembler
    MASM = auto()    # Microsoft Macro Assembler
    GAS = auto()     # GNU Assembler (AT&T syntax)
    RAW = auto()     # Raw/minimal syntax


@dataclass
class SourceLocation:
    """
    Tracks the original source location of a line after preprocessing.
    
    Attributes:
        file: Original source file path
        line: Original line number (1-indexed)
        macro_name: Name of macro if expanded from a macro, None otherwise
        include_stack: Stack of include files if from an include
    """
    file: str
    line: int
    macro_name: Optional[str] = None
    include_stack: List[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        if self.macro_name:
            return f"{self.file}:{self.line} (macro {self.macro_name})"
        return f"{self.file}:{self.line}"


@dataclass
class PreprocessedLine:
    """
    A single line after preprocessing.
    
    Attributes:
        text: The preprocessed text
        location: Original source location
        is_empty: True if line is empty or comment-only
    """
    text: str
    location: SourceLocation
    is_empty: bool = False


@dataclass
class Macro:
    """
    Macro definition.
    
    Attributes:
        name: Macro name (uppercase)
        params: List of parameter names
        body: List of lines in macro body
        location: Where macro was defined
        local_labels: List of LOCAL label declarations
    """
    name: str
    params: List[str]
    body: List[str]
    location: SourceLocation
    local_labels: List[str] = field(default_factory=list)


@dataclass
class PreprocessorResult:
    """
    Result of preprocessing.
    
    Attributes:
        lines: List of preprocessed lines
        source_map: Mapping from output line number to source location
        macros: Dictionary of defined macros
        symbols: Dictionary of EQU/= defined symbols
        errors: List of preprocessing errors
        dialect: Detected or specified dialect
    """
    lines: List[PreprocessedLine]
    source_map: Dict[int, SourceLocation]
    macros: Dict[str, Macro]
    symbols: Dict[str, Any]
    errors: List[Dict[str, Any]]
    dialect: Dialect


class Preprocessor:
    """
    Assembly language preprocessor.
    
    Handles macro expansion, include processing, conditional assembly,
    and dialect detection.
    """
    
    # Dialect detection patterns
    DIALECT_PATTERNS = {
        Dialect.NASM: [
            re.compile(r'^\s*section\s+\.', re.IGNORECASE),  # section .text
            re.compile(r'^\s*%macro\b', re.IGNORECASE),      # %macro
            re.compile(r'^\s*%include\b', re.IGNORECASE),    # %include
            re.compile(r'^\s*%define\b', re.IGNORECASE),     # %define
            re.compile(r'^\s*global\s+', re.IGNORECASE),     # global _start
            re.compile(r'^\s*bits\s+\d+', re.IGNORECASE),    # bits 32
        ],
        Dialect.MASM: [
            re.compile(r'^\s*\.model\b', re.IGNORECASE),     # .model small
            re.compile(r'^\s*\.data\b', re.IGNORECASE),      # .data
            re.compile(r'^\s*\.code\b', re.IGNORECASE),      # .code
            re.compile(r'^\s*\.stack\b', re.IGNORECASE),     # .stack
            re.compile(r'^\s*\w+\s+proc\b', re.IGNORECASE),  # name PROC
            re.compile(r'^\s*assume\s+', re.IGNORECASE),     # ASSUME
            re.compile(r'^\s*end\s+\w+', re.IGNORECASE),     # END label
        ],
        Dialect.TASM: [
            re.compile(r'^\s*\.model\b', re.IGNORECASE),     # .model (shared with MASM)
            re.compile(r'^\s*ideal\b', re.IGNORECASE),       # IDEAL mode
            re.compile(r'^\s*segment\s+\w+', re.IGNORECASE), # SEGMENT name
            re.compile(r'^\s*model\s+', re.IGNORECASE),      # MODEL without dot
            re.compile(r'^\s*codeseg\b', re.IGNORECASE),     # CODESEG
            re.compile(r'^\s*dataseg\b', re.IGNORECASE),     # DATASEG
        ],
        Dialect.GAS: [
            re.compile(r'^\s*\.globl\b', re.IGNORECASE),     # .globl
            re.compile(r'^\s*\.text\b', re.IGNORECASE),      # .text
            re.compile(r'^\s*\.ascii\b', re.IGNORECASE),     # .ascii
            re.compile(r'\s+%[a-z]+', re.IGNORECASE),        # %register
            re.compile(r'^\s*\.section\b', re.IGNORECASE),   # .section
            re.compile(r'\$\d+', re.IGNORECASE),             # $immediate
        ],
    }
    
    # Macro patterns for each dialect
    MACRO_START_PATTERNS = {
        Dialect.NASM: re.compile(r'^\s*%macro\s+(\w+)\s*(\d+)?(?:\s*-\s*(\d+))?', re.IGNORECASE),
        Dialect.MASM: re.compile(r'^\s*(\w+)\s+macro\s*(.*)', re.IGNORECASE),
        Dialect.TASM: re.compile(r'^\s*(\w+)\s+macro\s*(.*)', re.IGNORECASE),
        Dialect.GAS: re.compile(r'^\s*\.macro\s+(\w+)\s*(.*)', re.IGNORECASE),
        Dialect.RAW: re.compile(r'^\s*(\w+)\s+macro\s*(.*)', re.IGNORECASE),
    }
    
    MACRO_END_PATTERNS = {
        Dialect.NASM: re.compile(r'^\s*%endmacro\b', re.IGNORECASE),
        Dialect.MASM: re.compile(r'^\s*endm\b', re.IGNORECASE),
        Dialect.TASM: re.compile(r'^\s*endm\b', re.IGNORECASE),
        Dialect.GAS: re.compile(r'^\s*\.endm\b', re.IGNORECASE),
        Dialect.RAW: re.compile(r'^\s*endm\b', re.IGNORECASE),
    }
    
    # Include patterns
    INCLUDE_PATTERNS = {
        Dialect.NASM: re.compile(r'^\s*%include\s+["\']?([^"\']+)["\']?', re.IGNORECASE),
        Dialect.MASM: re.compile(r'^\s*include\s+(\S+)', re.IGNORECASE),
        Dialect.TASM: re.compile(r'^\s*include\s+(\S+)', re.IGNORECASE),
        Dialect.GAS: re.compile(r'^\s*\.include\s+["\']?([^"\']+)["\']?', re.IGNORECASE),
        Dialect.RAW: re.compile(r'^\s*include\s+(\S+)', re.IGNORECASE),
    }
    
    # Conditional assembly patterns
    IFDEF_PATTERNS = {
        Dialect.NASM: re.compile(r'^\s*%ifdef\s+(\w+)', re.IGNORECASE),
        Dialect.MASM: re.compile(r'^\s*ifdef\s+(\w+)', re.IGNORECASE),
        Dialect.TASM: re.compile(r'^\s*ifdef\s+(\w+)', re.IGNORECASE),
        Dialect.GAS: re.compile(r'^\s*\.ifdef\s+(\w+)', re.IGNORECASE),
        Dialect.RAW: re.compile(r'^\s*ifdef\s+(\w+)', re.IGNORECASE),
    }
    
    IFNDEF_PATTERNS = {
        Dialect.NASM: re.compile(r'^\s*%ifndef\s+(\w+)', re.IGNORECASE),
        Dialect.MASM: re.compile(r'^\s*ifndef\s+(\w+)', re.IGNORECASE),
        Dialect.TASM: re.compile(r'^\s*ifndef\s+(\w+)', re.IGNORECASE),
        Dialect.GAS: re.compile(r'^\s*\.ifndef\s+(\w+)', re.IGNORECASE),
        Dialect.RAW: re.compile(r'^\s*ifndef\s+(\w+)', re.IGNORECASE),
    }
    
    ELSE_PATTERNS = {
        Dialect.NASM: re.compile(r'^\s*%else\b', re.IGNORECASE),
        Dialect.MASM: re.compile(r'^\s*else\b', re.IGNORECASE),
        Dialect.TASM: re.compile(r'^\s*else\b', re.IGNORECASE),
        Dialect.GAS: re.compile(r'^\s*\.else\b', re.IGNORECASE),
        Dialect.RAW: re.compile(r'^\s*else\b', re.IGNORECASE),
    }
    
    ENDIF_PATTERNS = {
        Dialect.NASM: re.compile(r'^\s*%endif\b', re.IGNORECASE),
        Dialect.MASM: re.compile(r'^\s*endif\b', re.IGNORECASE),
        Dialect.TASM: re.compile(r'^\s*endif\b', re.IGNORECASE),
        Dialect.GAS: re.compile(r'^\s*\.endif\b', re.IGNORECASE),
        Dialect.RAW: re.compile(r'^\s*endif\b', re.IGNORECASE),
    }
    
    # EQU/= patterns for symbol definition
    EQU_PATTERN = re.compile(r'^\s*(\w+)\s+equ\s+(.+)', re.IGNORECASE)
    ASSIGN_PATTERN = re.compile(r'^\s*(\w+)\s*=\s*(.+)', re.IGNORECASE)
    
    # NASM %define pattern
    DEFINE_PATTERN = re.compile(r'^\s*%define\s+(\w+)(?:\(([^)]*)\))?\s*(.*)', re.IGNORECASE)
    
    # LOCAL pattern for macro-local labels
    LOCAL_PATTERN = re.compile(r'^\s*local\s+([\w,\s]+)', re.IGNORECASE)
    
    # Model directive patterns (MASM/TASM)
    MODEL_PATTERN = re.compile(
        r'^\s*\.?model\s+(\w+)(?:\s*,\s*(\w+))?', 
        re.IGNORECASE
    )
    
    # Segment directive patterns
    SEGMENT_START_PATTERNS = {
        'DOT_DATA': re.compile(r'^\s*\.data\b', re.IGNORECASE),
        'DOT_CODE': re.compile(r'^\s*\.code\b(?:\s+(\w+))?', re.IGNORECASE),
        'DOT_STACK': re.compile(r'^\s*\.stack\b(?:\s+(\w+))?', re.IGNORECASE),
        'DATASEG': re.compile(r'^\s*dataseg\b', re.IGNORECASE),
        'CODESEG': re.compile(r'^\s*codeseg\b', re.IGNORECASE),
        'SEGMENT': re.compile(r'^\s*(\w+)\s+segment\b', re.IGNORECASE),
    }
    
    # ASSUME directive pattern
    ASSUME_PATTERN = re.compile(
        r'^\s*assume\s+(.+)', 
        re.IGNORECASE
    )
    
    # Pseudo-variable pattern (matches @identifier)
    PSEUDO_VAR_PATTERN = re.compile(r'@([A-Za-z][A-Za-z0-9]*)', re.IGNORECASE)
    
    # List of known pseudo-variables (case-insensitive keys)
    KNOWN_PSEUDO_VARS = {
        'DATA', 'CODE', 'STACK', 'CURSEG', 'CURS', 
        'DATASIZE', 'CODESIZE', 'WORDSIZE', 'MODEL',
        'INTERFACE', 'VERSION', 'FILENAME', 'LINE'
    }
    
    def __init__(
        self, 
        dialect: Optional[Dialect] = None,
        include_paths: Optional[List[str]] = None,
        defines: Optional[Dict[str, str]] = None,
        file_reader: Optional[Callable[[str], str]] = None
    ):
        """
        Initialize preprocessor.
        
        Args:
            dialect: Force specific dialect, or None for auto-detection
            include_paths: List of directories to search for include files
            defines: Pre-defined symbols (like -D in command line)
            file_reader: Custom function to read files (for testing/sandboxing)
        """
        self.forced_dialect = dialect
        self.include_paths = include_paths or ['.']
        self.defines = defines or {}
        self.file_reader = file_reader or self._default_file_reader
        
        # State
        self.macros: Dict[str, Macro] = {}
        self.symbols: Dict[str, Any] = dict(self.defines)
        self.errors: List[Dict[str, Any]] = []
        self.source_map: Dict[int, SourceLocation] = {}
        self._macro_counter = 0  # For generating unique local labels
        self._include_stack: List[str] = []
        self._filename: str = "<source>"  # Current source filename
        
        # Model and segment scope tracking for pseudo-variable resolution
        self._scope: Dict[str, Any] = {
            'model': None,           # tiny, small, compact, medium, large, huge, flat
            'bits': 16,              # 16, 32, or 64
            'calling_convention': None,  # C, STDCALL, PASCAL, etc.
            'current_segment': None,  # Name of currently open segment
            'segment_stack': [],      # Stack of open segments
            'assumes': {              # ASSUME directive values
                'CS': '_TEXT',
                'DS': '_DATA',
                'SS': '_STACK',
                'ES': None,
            },
            'segments': {},           # Defined segments: name -> {'class': ..., 'align': ...}
        }
        
        # MASM/TASM model definitions
        self._MODEL_MAP = {
            'TINY': 1, 'SMALL': 2, 'COMPACT': 3, 'MEDIUM': 4,
            'LARGE': 5, 'HUGE': 6, 'FLAT': 7
        }
        self._CALLING_CONVENTIONS = {
            'C': 1, 'SYSCALL': 2, 'STDCALL': 3, 'PASCAL': 4,
            'FORTRAN': 5, 'BASIC': 6
        }
        
    @staticmethod
    def _default_file_reader(path: str) -> str:
        """Default file reader using pathlib."""
        return Path(path).read_text()
    
    def detect_dialect(self, source: str) -> Dialect:
        """
        Detect assembler dialect from source code.
        
        Args:
            source: Source code to analyze
            
        Returns:
            Detected Dialect enum value
        """
        if self.forced_dialect:
            return self.forced_dialect
        
        # Score each dialect based on pattern matches
        scores: Dict[Dialect, int] = {d: 0 for d in Dialect}
        
        for line in source.split('\n')[:100]:  # Check first 100 lines
            for dialect, patterns in self.DIALECT_PATTERNS.items():
                for pattern in patterns:
                    if pattern.search(line):
                        scores[dialect] += 1
        
        # Find dialect with highest score
        max_score = max(scores.values())
        if max_score == 0:
            return Dialect.RAW
        
        # Prefer MASM over TASM if tied (more common)
        for dialect in [Dialect.MASM, Dialect.TASM, Dialect.NASM, Dialect.GAS]:
            if scores[dialect] == max_score:
                return dialect
        
        return Dialect.RAW
    
    def preprocess(
        self, 
        source: str, 
        filename: str = "<source>"
    ) -> PreprocessorResult:
        """
        Preprocess assembly source code.
        
        Args:
            source: Assembly source code
            filename: Source filename for error reporting
            
        Returns:
            PreprocessorResult with preprocessed lines and metadata
        """
        self.errors = []
        self.source_map = {}
        self._include_stack = []
        self._filename = filename  # Store for @FILENAME resolution
        
        # Detect dialect
        dialect = self.detect_dialect(source)
        
        # Split into lines
        lines = source.split('\n')
        
        # Process lines
        result_lines = self._process_lines(lines, filename, dialect)
        
        # Build source map
        for i, line in enumerate(result_lines, 1):
            self.source_map[i] = line.location
        
        return PreprocessorResult(
            lines=result_lines,
            source_map=self.source_map,
            macros=self.macros.copy(),
            symbols=self.symbols.copy(),
            errors=self.errors.copy(),
            dialect=dialect
        )
    
    def _process_lines(
        self, 
        lines: List[str], 
        filename: str,
        dialect: Dialect,
        macro_name: Optional[str] = None
    ) -> List[PreprocessedLine]:
        """
        Process a list of lines.
        
        Args:
            lines: List of source lines
            filename: Source filename
            dialect: Detected dialect
            macro_name: Name of macro if processing macro expansion
            
        Returns:
            List of preprocessed lines
        """
        result: List[PreprocessedLine] = []
        i = 0
        
        # Conditional assembly state
        cond_stack: List[bool] = []  # True = currently processing, False = skipping
        
        while i < len(lines):
            line = lines[i]
            line_num = i + 1
            location = SourceLocation(
                file=filename, 
                line=line_num, 
                macro_name=macro_name,
                include_stack=list(self._include_stack)
            )
            
            # Check for conditional assembly directives
            ifdef_match = self._match_pattern(self.IFDEF_PATTERNS, dialect, line)
            ifndef_match = self._match_pattern(self.IFNDEF_PATTERNS, dialect, line)
            else_match = self._match_pattern(self.ELSE_PATTERNS, dialect, line)
            endif_match = self._match_pattern(self.ENDIF_PATTERNS, dialect, line)
            
            if ifdef_match:
                symbol = ifdef_match.group(1).upper()
                cond_stack.append(symbol in self.symbols)
                i += 1
                continue
            
            if ifndef_match:
                symbol = ifndef_match.group(1).upper()
                cond_stack.append(symbol not in self.symbols)
                i += 1
                continue
            
            if else_match:
                if cond_stack:
                    cond_stack[-1] = not cond_stack[-1]
                else:
                    self._error(location, "ELSE without IF")
                i += 1
                continue
            
            if endif_match:
                if cond_stack:
                    cond_stack.pop()
                else:
                    self._error(location, "ENDIF without IF")
                i += 1
                continue
            
            # Skip if inside false conditional
            if cond_stack and not all(cond_stack):
                i += 1
                continue
            
            # Check for include directive FIRST (before macro detection)
            # This prevents "INCLUDE macros.inc" from being mistaken as a macro definition
            include_match = self._match_pattern(self.INCLUDE_PATTERNS, dialect, line)
            if include_match:
                include_file = include_match.group(1).strip()
                included_lines = self._process_include(include_file, filename, dialect)
                result.extend(included_lines)
                i += 1
                continue
            
            # Check for macro definition
            macro_start = self._match_pattern(self.MACRO_START_PATTERNS, dialect, line)
            if macro_start:
                i, macro = self._parse_macro(lines, i, filename, dialect)
                if macro:
                    self.macros[macro.name] = macro
                continue
            
            # Check for EQU/= definition
            equ_match = self.EQU_PATTERN.match(line)
            assign_match = self.ASSIGN_PATTERN.match(line)
            define_match = self.DEFINE_PATTERN.match(line) if dialect == Dialect.NASM else None
            
            if equ_match:
                symbol = equ_match.group(1).upper()
                value = equ_match.group(2).strip()
                self.symbols[symbol] = self._evaluate_constant(value)
                result.append(PreprocessedLine(line, location))
                i += 1
                continue
            
            if assign_match:
                symbol = assign_match.group(1).upper()
                value = assign_match.group(2).strip()
                self.symbols[symbol] = self._evaluate_constant(value)
                result.append(PreprocessedLine(line, location))
                i += 1
                continue
            
            if define_match:
                symbol = define_match.group(1).upper()
                params = define_match.group(2)
                value = define_match.group(3).strip()
                if params:
                    # Function-like macro
                    param_list = [p.strip().upper() for p in params.split(',')]
                    self.macros[symbol] = Macro(
                        name=symbol,
                        params=param_list,
                        body=[value] if value else [],
                        location=location
                    )
                else:
                    self.symbols[symbol] = value or '1'
                i += 1
                continue
            
            # Check for macro invocation
            expanded = self._try_expand_macro(line, location, dialect)
            if expanded is not None:
                result.extend(expanded)
                i += 1
                continue
            
            # Check for LOCAL directive (only relevant inside macro expansion)
            # This is handled during macro expansion, skip here
            if self.LOCAL_PATTERN.match(line):
                i += 1
                continue
            
            # Process model, segment, and assume directives to update scope
            self._process_model_directive(line)
            self._process_segment_directive(line)
            self._process_assume_directive(line)
            
            # Resolve pseudo-variables (@data, @code, etc.)
            resolved_line = self._resolve_pseudo_variables(line, line_num)
            
            # Regular line - check if empty or comment
            stripped = resolved_line.strip()
            is_empty = not stripped or stripped.startswith(';') or stripped.startswith('//')
            
            result.append(PreprocessedLine(resolved_line, location, is_empty))
            i += 1
        
        # Check for unclosed conditionals
        if cond_stack:
            self._error(
                SourceLocation(filename, len(lines)),
                f"Unclosed conditional assembly ({len(cond_stack)} IF(s) without ENDIF)"
            )
        
        return result
    
    def _match_pattern(
        self, 
        patterns: Dict[Dialect, re.Pattern], 
        dialect: Dialect, 
        line: str
    ) -> Optional[re.Match]:
        """Try to match a dialect-specific pattern."""
        pattern = patterns.get(dialect) or patterns.get(Dialect.RAW)
        if pattern:
            return pattern.match(line)
        return None
    
    def _parse_macro(
        self, 
        lines: List[str], 
        start_idx: int, 
        filename: str,
        dialect: Dialect
    ) -> Tuple[int, Optional[Macro]]:
        """
        Parse a macro definition.
        
        Args:
            lines: All source lines
            start_idx: Index of macro start line
            filename: Source filename
            dialect: Current dialect
            
        Returns:
            Tuple of (next line index, Macro object or None)
        """
        start_line = lines[start_idx]
        location = SourceLocation(filename, start_idx + 1)
        
        # Parse macro header
        match = self._match_pattern(self.MACRO_START_PATTERNS, dialect, start_line)
        if not match:
            self._error(location, "Invalid macro definition")
            return start_idx + 1, None
        
        # Extract macro name and parameters
        if dialect == Dialect.NASM:
            name = match.group(1).upper()
            # NASM uses positional parameters %1, %2, etc.
            min_params = int(match.group(2) or 0)
            max_params = int(match.group(3) or min_params)
            params = [f"%{i}" for i in range(1, max_params + 1)]
        else:
            name = match.group(1).upper()
            params_str = match.group(2) if match.lastindex >= 2 else ''
            params = [p.strip().upper() for p in params_str.split(',') if p.strip()]
        
        # Collect macro body
        body: List[str] = []
        local_labels: List[str] = []
        i = start_idx + 1
        end_pattern = self.MACRO_END_PATTERNS.get(dialect) or self.MACRO_END_PATTERNS[Dialect.RAW]
        
        while i < len(lines):
            line = lines[i]
            
            # Check for end of macro
            if end_pattern.match(line):
                return i + 1, Macro(
                    name=name,
                    params=params,
                    body=body,
                    location=location,
                    local_labels=local_labels
                )
            
            # Check for LOCAL declaration
            local_match = self.LOCAL_PATTERN.match(line)
            if local_match:
                labels = [l.strip().upper() for l in local_match.group(1).split(',')]
                local_labels.extend(labels)
            else:
                body.append(line)
            
            i += 1
        
        # Reached end of file without ENDM
        self._error(location, f"Macro '{name}' not terminated (missing ENDM)")
        return i, None
    
    def _try_expand_macro(
        self, 
        line: str, 
        location: SourceLocation,
        dialect: Dialect
    ) -> Optional[List[PreprocessedLine]]:
        """
        Try to expand a macro invocation.
        
        Args:
            line: Source line
            location: Source location
            dialect: Current dialect
            
        Returns:
            List of expanded lines, or None if not a macro invocation
        """
        # Extract first word (potential macro name)
        stripped = line.strip()
        if not stripped or stripped.startswith(';') or stripped.startswith('//'):
            return None
        
        # Handle label prefix
        label_prefix = ''
        if ':' in stripped:
            parts = stripped.split(':', 1)
            if parts[0].strip().isidentifier():
                label_prefix = parts[0] + ':'
                stripped = parts[1].strip()
        
        # Get macro name (first word)
        words = stripped.split(None, 1)
        if not words:
            return None
        
        macro_name = words[0].upper()
        args_str = words[1] if len(words) > 1 else ''
        
        # Check if it's a defined macro
        macro = self.macros.get(macro_name)
        if not macro:
            return None
        
        # Parse arguments
        args = self._parse_macro_args(args_str)
        
        # Generate unique counter for local labels
        self._macro_counter += 1
        counter = self._macro_counter
        
        # Expand macro body
        result: List[PreprocessedLine] = []
        
        # Add label prefix if present
        if label_prefix:
            result.append(PreprocessedLine(
                label_prefix,
                SourceLocation(
                    location.file,
                    location.line,
                    macro_name,
                    location.include_stack
                )
            ))
        
        for body_line in macro.body:
            expanded_line = body_line
            
            # Replace parameters
            for i, param in enumerate(macro.params):
                if i < len(args):
                    arg_value = args[i]
                else:
                    arg_value = ''  # Missing argument
                
                # Handle NASM-style positional params (%1, %2, etc.)
                if param.startswith('%'):
                    expanded_line = expanded_line.replace(param, arg_value)
                else:
                    # Case-insensitive replacement
                    pattern = re.compile(re.escape(param), re.IGNORECASE)
                    expanded_line = pattern.sub(arg_value, expanded_line)
            
            # Replace local labels with unique versions
            for local in macro.local_labels:
                unique_label = f"@@{local}_{counter}"
                pattern = re.compile(r'\b' + re.escape(local) + r'\b', re.IGNORECASE)
                expanded_line = pattern.sub(unique_label, expanded_line)
            
            result.append(PreprocessedLine(
                expanded_line,
                SourceLocation(
                    location.file,
                    location.line,
                    macro_name,
                    location.include_stack
                )
            ))
        
        return result
    
    def _parse_macro_args(self, args_str: str) -> List[str]:
        """
        Parse macro arguments, respecting string literals and nested parens.
        
        Args:
            args_str: Argument string
            
        Returns:
            List of argument values
        """
        if not args_str.strip():
            return []
        
        args: List[str] = []
        current = ''
        depth = 0
        in_string = False
        string_char = ''
        
        for char in args_str:
            if in_string:
                current += char
                if char == string_char:
                    in_string = False
            elif char in '"\'':
                in_string = True
                string_char = char
                current += char
            elif char == '(':
                depth += 1
                current += char
            elif char == ')':
                depth -= 1
                current += char
            elif char == ',' and depth == 0:
                args.append(current.strip())
                current = ''
            else:
                current += char
        
        if current.strip():
            args.append(current.strip())
        
        return args
    
    def _process_include(
        self, 
        include_file: str, 
        parent_file: str,
        dialect: Dialect
    ) -> List[PreprocessedLine]:
        """
        Process an include directive.
        
        Args:
            include_file: File to include
            parent_file: Parent file path
            dialect: Current dialect
            
        Returns:
            List of preprocessed lines from include file
        """
        # Check for circular includes
        if include_file in self._include_stack:
            self._error(
                SourceLocation(parent_file, 0),
                f"Circular include detected: {include_file}"
            )
            return []
        
        # Find the file
        resolved_path = self._resolve_include_path(include_file, parent_file)
        if not resolved_path:
            self._error(
                SourceLocation(parent_file, 0),
                f"Include file not found: {include_file}"
            )
            return []
        
        # Read and preprocess
        try:
            content = self.file_reader(resolved_path)
        except Exception as e:
            self._error(
                SourceLocation(parent_file, 0),
                f"Error reading include file {include_file}: {e}"
            )
            return []
        
        self._include_stack.append(include_file)
        lines = content.split('\n')
        result = self._process_lines(lines, resolved_path, dialect)
        self._include_stack.pop()
        
        return result
    
    def _resolve_include_path(
        self, 
        include_file: str, 
        parent_file: str
    ) -> Optional[str]:
        """
        Resolve include file path.
        
        Args:
            include_file: File to include
            parent_file: Parent file path
            
        Returns:
            Resolved path or None if not found
        """
        # Try relative to parent file first
        parent_dir = Path(parent_file).parent
        candidate = parent_dir / include_file
        if self._file_exists(str(candidate)):
            return str(candidate)
        
        # Try include paths
        for include_path in self.include_paths:
            candidate = Path(include_path) / include_file
            if self._file_exists(str(candidate)):
                return str(candidate)
        
        # If using a custom file reader, try the filename directly
        if self.file_reader != self._default_file_reader:
            if self._file_exists(include_file):
                return include_file
        
        return None
    
    def _file_exists(self, path: str) -> bool:
        """
        Check if a file exists (compatible with mock file readers).
        
        Args:
            path: Path to check
            
        Returns:
            True if file exists
        """
        # For default file reader, use Path.exists()
        if self.file_reader == self._default_file_reader:
            return Path(path).exists()
        
        # For custom file readers, try to read and catch FileNotFoundError
        try:
            self.file_reader(path)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            # Other errors mean the file might exist but has issues
            return True
    
    def _evaluate_constant(self, expr: str) -> Any:
        """
        Evaluate a constant expression.
        
        Args:
            expr: Expression string
            
        Returns:
            Evaluated value
        """
        expr = expr.strip()
        
        # Remove comments
        if ';' in expr:
            expr = expr.split(';')[0].strip()
        
        # Try numeric evaluation
        try:
            # Handle hex
            if expr.upper().startswith('0X'):
                return int(expr, 16)
            if expr.upper().endswith('H'):
                return int(expr[:-1], 16)
            # Handle binary
            if expr.upper().endswith('B'):
                return int(expr[:-1], 2)
            if expr.upper().startswith('0B'):
                return int(expr[2:], 2)
            # Handle octal
            if expr.upper().endswith('O') or expr.upper().endswith('Q'):
                return int(expr[:-1], 8)
            # Handle decimal
            return int(expr)
        except ValueError:
            pass
        
        # Return as string
        return expr
    
    def _process_model_directive(self, line: str) -> bool:
        """
        Process .MODEL directive and update scope.
        
        Args:
            line: Source line
            
        Returns:
            True if this was a MODEL directive
        """
        match = self.MODEL_PATTERN.match(line)
        if not match:
            return False
        
        model = match.group(1).upper()
        calling_conv = match.group(2).upper() if match.group(2) else None
        
        self._scope['model'] = model
        if calling_conv:
            self._scope['calling_convention'] = calling_conv
        
        # Set default segments based on model
        if model == 'FLAT':
            self._scope['bits'] = 32
            self._scope['assumes']['CS'] = 'FLAT'
            self._scope['assumes']['DS'] = 'FLAT'
            self._scope['assumes']['SS'] = 'FLAT'
        elif model in ('TINY', 'SMALL', 'COMPACT', 'MEDIUM', 'LARGE', 'HUGE'):
            self._scope['bits'] = 16
            self._scope['assumes']['CS'] = '_TEXT'
            self._scope['assumes']['DS'] = '_DATA' if model != 'TINY' else '_TEXT'
            self._scope['assumes']['SS'] = '_STACK'
        
        return True
    
    def _process_segment_directive(self, line: str) -> bool:
        """
        Process segment directives (.DATA, .CODE, .STACK, SEGMENT).
        
        Args:
            line: Source line
            
        Returns:
            True if this was a segment directive
        """
        for pattern_name, pattern in self.SEGMENT_START_PATTERNS.items():
            match = pattern.match(line)
            if match:
                if pattern_name == 'DOT_DATA':
                    self._scope['current_segment'] = '_DATA'
                    self._scope['assumes']['DS'] = '_DATA'
                elif pattern_name == 'DOT_CODE':
                    seg_name = match.group(1) if match.lastindex else '_TEXT'
                    self._scope['current_segment'] = seg_name or '_TEXT'
                    self._scope['assumes']['CS'] = seg_name or '_TEXT'
                elif pattern_name == 'DOT_STACK':
                    self._scope['current_segment'] = '_STACK'
                    self._scope['assumes']['SS'] = '_STACK'
                elif pattern_name == 'DATASEG':
                    self._scope['current_segment'] = '_DATA'
                    self._scope['assumes']['DS'] = '_DATA'
                elif pattern_name == 'CODESEG':
                    self._scope['current_segment'] = '_TEXT'
                    self._scope['assumes']['CS'] = '_TEXT'
                elif pattern_name == 'SEGMENT':
                    seg_name = match.group(1).upper()
                    self._scope['current_segment'] = seg_name
                    self._scope['segment_stack'].append(seg_name)
                    self._scope['segments'][seg_name] = {}
                return True
        return False
    
    def _process_assume_directive(self, line: str) -> bool:
        """
        Process ASSUME directive.
        
        Args:
            line: Source line
            
        Returns:
            True if this was an ASSUME directive
        """
        match = self.ASSUME_PATTERN.match(line)
        if not match:
            return False
        
        # Parse ASSUME CS:code, DS:data, etc.
        assumes_str = match.group(1)
        for part in assumes_str.split(','):
            part = part.strip()
            if ':' in part:
                reg, seg = part.split(':', 1)
                reg = reg.strip().upper()
                seg = seg.strip().upper()
                if reg in self._scope['assumes']:
                    self._scope['assumes'][reg] = seg if seg != 'NOTHING' else None
        
        return True
    
    def _resolve_pseudo_variables(self, line: str, line_num: int = 0) -> str:
        """
        Resolve MASM/TASM pseudo-variables (@data, @code, etc.) in a line.
        
        Args:
            line: Source line with potential pseudo-variables
            line_num: Current line number (for @LINE)
            
        Returns:
            Line with pseudo-variables substituted
        """
        def replace_pseudo_var(match: re.Match) -> str:
            var_name = match.group(1).upper()
            full_match = match.group(0)  # @varname
            
            # Only replace known pseudo-variables
            if var_name not in self.KNOWN_PSEUDO_VARS:
                # Unknown @-prefixed identifier - leave unchanged (user label)
                return full_match
            
            scope = self._scope
            model = scope.get('model', 'SMALL')
            if model is None:
                model = 'SMALL'
            model_upper = model.upper() if model else 'SMALL'
            
            # Resolve based on pseudo-variable name
            if var_name == 'DATA':
                # Return data segment name
                return scope['assumes'].get('DS') or '_DATA'
            
            elif var_name == 'CODE':
                # Return code segment name
                return scope['assumes'].get('CS') or '_TEXT'
            
            elif var_name == 'STACK':
                # Return stack segment name
                return scope['assumes'].get('SS') or '_STACK'
            
            elif var_name in ('CURSEG', 'CURS'):
                # Return current segment name
                if scope['segment_stack']:
                    return scope['segment_stack'][-1]
                return scope.get('current_segment') or '_TEXT'
            
            elif var_name == 'DATASIZE':
                # 0 for tiny/small/medium, 1 for compact/large/huge/flat
                if model_upper in ('COMPACT', 'LARGE', 'HUGE', 'FLAT'):
                    return '1'
                return '0'
            
            elif var_name == 'CODESIZE':
                # 0 for tiny/small/compact, 1 for medium/large/huge
                if model_upper in ('MEDIUM', 'LARGE', 'HUGE'):
                    return '1'
                return '0'
            
            elif var_name == 'WORDSIZE':
                # 2 for 16-bit, 4 for 32-bit, 8 for 64-bit
                bits = scope.get('bits', 16)
                if bits == 64:
                    return '8'
                elif bits == 32:
                    return '4'
                return '2'
            
            elif var_name == 'MODEL':
                # Model number: 1=tiny, 2=small, 3=compact, 4=medium, 5=large, 6=huge, 7=flat
                return str(self._MODEL_MAP.get(model_upper, 2))
            
            elif var_name == 'INTERFACE':
                # Calling convention code
                conv = scope.get('calling_convention')
                if conv:
                    return str(self._CALLING_CONVENTIONS.get(conv.upper(), 0))
                return '0'
            
            elif var_name == 'VERSION':
                # MASM version number (600 = 6.00 compatible)
                return '600'
            
            elif var_name == 'FILENAME':
                # Base filename without extension
                base = os.path.basename(self._filename)
                name = os.path.splitext(base)[0]
                return f"'{name}'"
            
            elif var_name == 'LINE':
                # Current line number
                return str(line_num)
            
            # Fallback: return original
            return full_match
        
        return self.PSEUDO_VAR_PATTERN.sub(replace_pseudo_var, line)
    
    def _error(self, location: SourceLocation, message: str) -> None:
        """Record a preprocessing error."""
        self.errors.append({
            'phase': 'PREPROCESSOR',
            'code': 'E0xx',
            'file': location.file,
            'line': location.line,
            'message': message,
            'include_stack': location.include_stack.copy()
        })
    
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Get list of errors."""
        return self.errors.copy()


def preprocess(
    source: str, 
    filename: str = "<source>",
    dialect: Optional[Dialect] = None,
    include_paths: Optional[List[str]] = None,
    defines: Optional[Dict[str, str]] = None
) -> PreprocessorResult:
    """
    Convenience function to preprocess assembly source.
    
    Args:
        source: Assembly source code
        filename: Source filename
        dialect: Force specific dialect
        include_paths: List of include directories
        defines: Pre-defined symbols
        
    Returns:
        PreprocessorResult
    """
    preprocessor = Preprocessor(
        dialect=dialect,
        include_paths=include_paths,
        defines=defines
    )
    return preprocessor.preprocess(source, filename)


if __name__ == '__main__':
    # Test the preprocessor
    test_code = '''
; Test MASM-style code
.MODEL SMALL
.STACK 100H

; Constants
BUFFER_SIZE EQU 256
MAX_COUNT = 100

; Macro definition
PRINT_MSG MACRO msg
    LEA DX, msg
    MOV AH, 09H
    INT 21H
ENDM

.DATA
    MSG1 DB 'Hello, World!$'
    MSG2 DB 'Goodbye!$'
    
.CODE
START:
    MOV AX, @DATA
    MOV DS, AX
    
    PRINT_MSG MSG1      ; Macro invocation
    PRINT_MSG MSG2
    
    MOV AX, 4C00H
    INT 21H
    
END START
'''
    
    result = preprocess(test_code, "test.asm")
    
    print(f"=== Dialect: {result.dialect.name} ===\n")
    
    print("=== Macros ===")
    for name, macro in result.macros.items():
        print(f"  {name}: params={macro.params}, body_lines={len(macro.body)}")
    
    print("\n=== Symbols ===")
    for name, value in result.symbols.items():
        print(f"  {name} = {value}")
    
    print("\n=== Preprocessed Lines (non-empty) ===")
    for i, line in enumerate(result.lines, 1):
        if not line.is_empty:
            loc = line.location
            prefix = f"[{loc.file}:{loc.line}]"
            if loc.macro_name:
                prefix += f" (macro {loc.macro_name})"
            print(f"  {i:3d}: {prefix}")
            print(f"       {line.text.rstrip()}")
    
    if result.errors:
        print("\n=== Errors ===")
        for err in result.errors:
            print(f"  {err['file']}:{err['line']}: {err['message']}")
    else:
        print("\n✅ No preprocessing errors")
