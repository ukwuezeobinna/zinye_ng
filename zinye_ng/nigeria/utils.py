"""
Nigeria-specific Jinja helpers for print formats.

Registered in hooks.py → jinja.methods so they are available in
Letter Head, Print Format, Email Template, etc.

Usage in a Jinja template:
  {{ format_tin("1234567890123") }}   → 1234-56789-01234 (12-digit FIRS TIN)
  {{ format_naira(250000) }}          → ₦250,000.00
"""
from __future__ import annotations


def format_tin(tin: str | None) -> str:
    """
    Format a FIRS TIN for display.

    FIRS TIN format is 13 digits: XXXX-XXXXX-XXXXX
    12-digit legacy TINs are zero-padded to 13 digits.
    Returns the raw value if it doesn't match expected lengths.
    """
    if not tin:
        return ""
    digits = "".join(filter(str.isdigit, str(tin)))
    if len(digits) == 13:
        return f"{digits[:4]}-{digits[4:9]}-{digits[9:]}"
    if len(digits) == 12:
        digits = "0" + digits
        return f"{digits[:4]}-{digits[4:9]}-{digits[9:]}"
    return str(tin)


def format_naira(amount: float | int | str | None, show_symbol: bool = True) -> str:
    """
    Format a numeric value as Nigerian Naira.

    format_naira(250000)        → ₦250,000.00
    format_naira(250000, False) → 250,000.00
    """
    if amount is None:
        return ""
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return str(amount)

    formatted = f"{value:,.2f}"
    return f"₦{formatted}" if show_symbol else formatted
