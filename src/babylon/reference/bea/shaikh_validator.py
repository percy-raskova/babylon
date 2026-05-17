"""Shaikh-band validator for spec-068 US4 (SC-006).

Takes a per-(bea_industry, year) c/v dict + the Shaikh empirical bands
and returns the list of industries whose measured c/v falls outside
its band (with the SC-006 ±50 % tolerance widening).
"""

from __future__ import annotations

from babylon.reference.bea.shaikh_bands import (
    ShaikhBand,
    ShaikhBandViolation,
    lookup_shaikh_band,
)

_SC_006_DEFAULT_TOLERANCE_FRACTION: float = 0.5


def _widen_band(band: ShaikhBand, tolerance_fraction: float) -> tuple[float, float]:
    """Widen ``[lower, upper]`` by ``tolerance_fraction`` symmetrically."""
    if tolerance_fraction <= 0:
        return (band.lower, band.upper)
    return (
        band.lower * (1.0 - tolerance_fraction),
        band.upper * (1.0 + tolerance_fraction),
    )


def validate_per_industry_c_v(
    c_v_by_industry: dict[int, float],
    bea_code_by_industry_id: dict[int, str],
    tolerance_fraction: float = _SC_006_DEFAULT_TOLERANCE_FRACTION,
) -> list[ShaikhBandViolation]:
    """Validate measured c/v values against the Shaikh empirical bands.

    Args:
        c_v_by_industry: Mapping ``bea_industry_id -> measured c/v``
            (typically the population-weighted mean across counties).
        bea_code_by_industry_id: Mapping ``bea_industry_id -> bea_code``
            (XLSX-style code like ``"111CA"``).
        tolerance_fraction: How much to widen each band (default 0.5
            per SC-006 ±50 % allowance for between-county heterogeneity).

    Returns:
        List of :class:`ShaikhBandViolation` for industries whose
        measured c/v falls outside the widened band. Empty list means
        SC-006 passes.
    """
    violations: list[ShaikhBandViolation] = []
    for industry_id, measured_c_v in c_v_by_industry.items():
        bea_code = bea_code_by_industry_id.get(industry_id)
        if bea_code is None:
            continue
        band = lookup_shaikh_band(bea_code)
        lower, upper = _widen_band(band, tolerance_fraction)
        if not (lower <= measured_c_v <= upper):
            violations.append(
                ShaikhBandViolation(
                    bea_code=bea_code,
                    bea_industry_id=industry_id,
                    measured_c_v=measured_c_v,
                    band_lower=lower,
                    band_upper=upper,
                )
            )
    return violations
