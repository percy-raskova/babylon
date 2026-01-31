"""Validation utilities for God Mode Dashboard.

This module provides validation functions for H3 indices and FIPS codes
used in the dashboard's spatial and territory data.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

import re

# H3 index pattern: 15-character hexadecimal string (resolution 5)
# Example: "852a1072fffffff"
H3_INDEX_PATTERN = re.compile(r"^[0-9a-f]{15}$")

# FIPS code pattern: 5-digit string for US counties
# Example: "26163" (Wayne County, Michigan)
FIPS_PATTERN = re.compile(r"^[0-9]{5}$")


def is_valid_h3_index(h3_index: str) -> bool:
    """Check if a string is a valid H3 index.

    Valid H3 indices are 15-character lowercase hexadecimal strings.
    This function accepts both upper and lowercase input but normalizes
    to lowercase for comparison.

    Args:
        h3_index: String to validate.

    Returns:
        True if the string is a valid H3 index, False otherwise.

    Example:
        >>> is_valid_h3_index("852a1072fffffff")
        True
        >>> is_valid_h3_index("852A1072FFFFFFF")  # uppercase accepted
        True
        >>> is_valid_h3_index("invalid")
        False
        >>> is_valid_h3_index("852a107")  # too short
        False
    """
    if not isinstance(h3_index, str):
        return False
    return bool(H3_INDEX_PATTERN.match(h3_index.lower()))


def validate_h3_index(h3_index: str) -> str:
    """Validate and normalize an H3 index.

    Args:
        h3_index: H3 index string to validate.

    Returns:
        Normalized (lowercase) H3 index.

    Raises:
        ValueError: If h3_index is not a valid H3 index.

    Example:
        >>> validate_h3_index("852A1072FFFFFFF")
        '852a1072fffffff'
        >>> validate_h3_index("invalid")
        Traceback (most recent call last):
        ...
        ValueError: Invalid H3 index: 'invalid'. Expected 15-char hex string.
    """
    if not is_valid_h3_index(h3_index):
        msg = f"Invalid H3 index: '{h3_index}'. Expected 15-char hex string."
        raise ValueError(msg)
    return h3_index.lower()


def is_valid_fips_code(fips_code: str) -> bool:
    """Check if a string is a valid 5-digit FIPS code.

    FIPS codes identify US counties. They are 5-digit strings where:
    - First 2 digits: State code (e.g., 26 = Michigan)
    - Last 3 digits: County code (e.g., 163 = Wayne County)

    Args:
        fips_code: String to validate.

    Returns:
        True if the string is a valid FIPS code, False otherwise.

    Example:
        >>> is_valid_fips_code("26163")  # Wayne County, MI
        True
        >>> is_valid_fips_code("26")  # too short
        False
        >>> is_valid_fips_code("123456")  # too long
        False
        >>> is_valid_fips_code("abcde")  # non-numeric
        False
    """
    if not isinstance(fips_code, str):
        return False
    return bool(FIPS_PATTERN.match(fips_code))


def validate_fips_code(fips_code: str) -> str:
    """Validate a FIPS code.

    Args:
        fips_code: FIPS code string to validate.

    Returns:
        Validated FIPS code (unchanged).

    Raises:
        ValueError: If fips_code is not a valid 5-digit FIPS code.

    Example:
        >>> validate_fips_code("26163")
        '26163'
        >>> validate_fips_code("123")
        Traceback (most recent call last):
        ...
        ValueError: Invalid FIPS code: '123'. Expected 5-digit string.
    """
    if not is_valid_fips_code(fips_code):
        msg = f"Invalid FIPS code: '{fips_code}'. Expected 5-digit string."
        raise ValueError(msg)
    return fips_code


__all__ = [
    "H3_INDEX_PATTERN",
    "FIPS_PATTERN",
    "is_valid_h3_index",
    "validate_h3_index",
    "is_valid_fips_code",
    "validate_fips_code",
]
