"""Centralized field parsing for all data loaders.

This module provides standardized parsing functions for converting raw data
(strings from CSV/API responses) into typed Python values. All loaders should
use these functions instead of implementing their own parsing logic.

Usage:
    from babylon.data.utils.field_parsers import parse_int, parse_str, parse_float

    value = parse_int(row.get("count"))  # Returns int | None
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def parse_int(value: object) -> int | None:
    """Parse integer, returning None for empty/invalid.

    Handles:
    - None values
    - Empty strings
    - Strings with commas (e.g., "1,234")
    - Float strings (e.g., "123.0" -> 123)

    Args:
        value: Raw value to parse.

    Returns:
        Parsed integer or None if invalid/empty.
    """
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return int(float(text))  # Handle "123.0" strings
    except (ValueError, TypeError):
        return None


def parse_str(value: object) -> str | None:
    """Parse string, returning None for empty.

    Args:
        value: Raw value to parse.

    Returns:
        Stripped string or None if empty.
    """
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def parse_decimal(value: object) -> Decimal | None:
    """Parse Decimal for currency/precise values.

    Use this for monetary amounts that require exact decimal representation.
    For ratios and percentages that can be very large, use parse_float instead.

    Args:
        value: Raw value to parse.

    Returns:
        Decimal or None if invalid/empty.
    """
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def parse_float(value: object) -> float | None:
    """Parse float for ratios/percentages (large range).

    Use this for location quotients, percentage changes, and other statistical
    ratios that can have very large values (e.g., 1,000,000% change).

    Args:
        value: Raw value to parse.

    Returns:
        Float or None if invalid/empty.
    """
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


__all__ = ["parse_int", "parse_str", "parse_decimal", "parse_float"]
