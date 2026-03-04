"""Output formatting utilities for CLI.

Supports multiple output formats:
- table: Human-readable tabular format (default)
- json: Machine-readable JSON format
- plain: Simple text format for scripting
"""

from __future__ import annotations

import json as json_module
import sys
from typing import Any


# =============================================================================
# OUTPUT CONTEXT
# =============================================================================

class OutputContext:
    """Holds output preferences for the current CLI invocation."""

    def __init__(self, json_mode: bool = False, quiet: bool = False):
        self.json_mode = json_mode
        self.quiet = quiet


# =============================================================================
# TABLE FORMATTING
# =============================================================================

def format_table(headers: list[str], rows: list[list[str]], min_width: int = 10) -> str:
    """Format data as an ASCII table.

    Args:
        headers: Column header names
        rows: List of row data (each row is a list of strings)
        min_width: Minimum column width

    Returns:
        Formatted table string
    """
    if not rows:
        return ""

    col_widths = [max(min_width, len(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    separator = "  ".join("-" * w for w in col_widths)

    lines = [header_line, separator]
    for row in rows:
        line = "  ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        lines.append(line)

    return "\n".join(lines)


# =============================================================================
# JSON OUTPUT
# =============================================================================

def output_json(data: Any) -> None:
    """Output data as JSON to stdout."""
    print(json_module.dumps(data, indent=2, ensure_ascii=False))


# =============================================================================
# UNIFIED OUTPUT
# =============================================================================

def output_result(
    ctx: OutputContext,
    data: Any,
    table_headers: list[str] | None = None,
    table_rows: list[list[str]] | None = None,
    plain_text: str | None = None,
) -> None:
    """Output result in the appropriate format based on context.

    Args:
        ctx: Output context with format preferences
        data: Raw data for JSON output
        table_headers: Headers for table format
        table_rows: Rows for table format
        plain_text: Text for plain format (fallback)
    """
    if ctx.json_mode:
        output_json(data)
    elif table_headers and table_rows:
        print(format_table(table_headers, table_rows))
    elif plain_text:
        print(plain_text)
    else:
        output_json(data)


def output_error(message: str, ctx: OutputContext | None = None) -> None:
    """Output error message."""
    if ctx and ctx.json_mode:
        output_json({"error": message})
    else:
        print(f"Error: {message}", file=sys.stderr)


def output_success(message: str, ctx: OutputContext | None = None) -> None:
    """Output success message."""
    if ctx and ctx.quiet:
        return
    if ctx and ctx.json_mode:
        output_json({"status": "success", "message": message})
    else:
        print(message)


def output_progress(message: str, ctx: OutputContext | None = None) -> None:
    """Output progress message to stderr (so it doesn't interfere with stdout data)."""
    if ctx and ctx.quiet:
        return
    if ctx and ctx.json_mode:
        return
    print(message, file=sys.stderr)
