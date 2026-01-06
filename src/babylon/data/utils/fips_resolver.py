"""FIPS code resolution and extraction utilities.

Provides consistent FIPS code extraction from various data sources,
used by multiple data loaders for geographic aggregation.

Common patterns:
- ArcGIS/GeoJSON feature attributes (HIFLD, MIRTA)
- Census area codes (QCEW, Census)
- Direct county identifiers (FCC, CFS)
"""

from __future__ import annotations

from typing import Any

# Standard FIPS field names in ArcGIS/GeoJSON data
FIPS_FIELD_NAMES = (
    "COUNTYFIPS",
    "CNTY_FIPS",
    "FIPS",
    "COUNTY_FIPS",
    "COUNTY_FIP",
)

# State FIPS field names
STATE_FIPS_FIELD_NAMES = (
    "STATE_FIPS",
    "STATEFP",
    "STATE_FIP",
)

# County-only (3-digit) FIPS field names
COUNTY_ONLY_FIELD_NAMES = (
    "CNTY_FIPS_3",
    "COUNTYFP",
    "CNTY_FIP",
)


def normalize_fips(
    fips_value: str | int | None,
    expected_length: int = 5,
    min_length: int | None = None,
) -> str | None:
    """Normalize a FIPS code to expected length with zero-padding.

    Args:
        fips_value: Raw FIPS value (string or integer).
        expected_length: Expected length (5 for county, 2 for state, 3 for county-only).
        min_length: Minimum length for valid input. If provided, shorter values return None.
                    Useful for rejecting clearly invalid codes (e.g., 2-digit when 5 expected).

    Returns:
        Zero-padded FIPS string or None if input is invalid.

    Example:
        >>> normalize_fips("6001", 5)
        '06001'
        >>> normalize_fips(6, 2)
        '06'
        >>> normalize_fips("", 5)
        None
        >>> normalize_fips("06", 5, min_length=4)
        None
    """
    if fips_value is None:
        return None

    fips_str = str(fips_value).strip()
    if not fips_str or fips_str.lower() in ("nan", "none", "null"):
        return None

    # Reject values below minimum length if specified
    if min_length is not None and len(fips_str) < min_length:
        return None

    # Handle numeric-looking strings that might have been truncated
    if len(fips_str) < expected_length:
        return fips_str.zfill(expected_length)

    # Truncate to expected length (e.g., "060010" -> "06001")
    return fips_str[:expected_length].zfill(expected_length)


def extract_state_fips(area_fips: str) -> str | None:
    """Extract 2-digit state FIPS from a 5-digit county FIPS code.

    Args:
        area_fips: 5-digit county FIPS code (e.g., "06001" for Alameda, CA).

    Returns:
        2-digit state FIPS or None if input is invalid.

    Example:
        >>> extract_state_fips("06001")
        '06'
        >>> extract_state_fips("6001")
        '06'
    """
    if not area_fips:
        return None

    fips_str = str(area_fips).strip()

    # Handle short FIPS (missing leading zero)
    if len(fips_str) == 4:
        return "0" + fips_str[0]
    elif len(fips_str) >= 5:
        return fips_str[:2]

    return None


def extract_county_fips_from_attrs(
    attrs: dict[str, Any],
    field_names: tuple[str, ...] | None = None,
    try_construct: bool = True,
) -> str | None:
    """Extract 5-digit county FIPS from feature attributes.

    Tries common field names and optionally constructs from state + county.
    Used by HIFLD, MIRTA, and other ArcGIS-sourced loaders.

    Args:
        attrs: Feature attribute dictionary from ArcGIS/GeoJSON.
        field_names: Custom field names to try (defaults to FIPS_FIELD_NAMES).
        try_construct: If True, try to construct from state + county fields.

    Returns:
        5-digit FIPS code or None if not extractable.

    Example:
        >>> extract_county_fips_from_attrs({"COUNTYFIPS": "06001"})
        '06001'
        >>> extract_county_fips_from_attrs({"STATE_FIPS": "06", "COUNTYFP": "001"})
        '06001'
    """
    names = field_names or FIPS_FIELD_NAMES

    # Try direct FIPS fields
    # County FIPS must be at least 4 digits (e.g., "6001" -> "06001")
    # Reject very short values like "06" which are state codes
    for field_name in names:
        value = attrs.get(field_name)
        if value:
            normalized = normalize_fips(value, 5, min_length=4)
            if normalized:
                return normalized

    # Try constructing from state + county
    if try_construct:
        state_fips = None
        for state_field in STATE_FIPS_FIELD_NAMES:
            state_val = attrs.get(state_field)
            if state_val:
                state_fips = normalize_fips(state_val, 2)
                break

        county_only = None
        for county_field in COUNTY_ONLY_FIELD_NAMES:
            county_val = attrs.get(county_field)
            if county_val:
                county_only = normalize_fips(county_val, 3)
                break

        if state_fips and county_only:
            return f"{state_fips}{county_only}"

    return None


__all__ = [
    "COUNTY_ONLY_FIELD_NAMES",
    "FIPS_FIELD_NAMES",
    "STATE_FIPS_FIELD_NAMES",
    "extract_county_fips_from_attrs",
    "extract_state_fips",
    "normalize_fips",
]
