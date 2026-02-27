"""QCEW-to-hex allocation via Census ACS tract weights.

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Allocates county-level QCEW data (constant capital, variable capital,
surplus value, employment) to H3 resolution 7 hexes using Census ACS
tract-level demographic weights.

Conservation: sum(hex_values) == county_total within 1e-10 by
construction (weights normalized to sum to 1.0 per county).

See Also:
    :mod:`babylon.economics.substrate.types`: HexGrid, HexEconomicState.
    :mod:`babylon.economics.substrate.protocols`: TractDemographicSource.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.economics.hydrator import MarxianHydrator
    from babylon.economics.substrate.protocols import TractDemographicSource
    from babylon.economics.substrate.types import HexGrid

logger = logging.getLogger(__name__)

# Default county-level economic data (approximate 2023 values in $M)
# Used when database QCEW data is not available
DEFAULT_COUNTY_ECONOMICS: dict[str, dict[str, float]] = {
    "26163": {  # Wayne County
        "constant_capital": 45000.0,
        "variable_capital": 35000.0,
        "surplus_value": 15000.0,
        "employment": 720000.0,
        "dept_I": 0.20,
        "dept_IIa": 0.35,
        "dept_IIb": 0.25,
        "dept_III": 0.20,
    },
    "26125": {  # Oakland County
        "constant_capital": 55000.0,
        "variable_capital": 40000.0,
        "surplus_value": 20000.0,
        "employment": 650000.0,
        "dept_I": 0.25,
        "dept_IIa": 0.30,
        "dept_IIb": 0.25,
        "dept_III": 0.20,
    },
    "26099": {  # Macomb County
        "constant_capital": 35000.0,
        "variable_capital": 25000.0,
        "surplus_value": 12000.0,
        "employment": 380000.0,
        "dept_I": 0.35,
        "dept_IIa": 0.25,
        "dept_IIb": 0.20,
        "dept_III": 0.20,
    },
}


def hydrate_hex_grid(
    grid: HexGrid,
    tract_source: TractDemographicSource | None = None,
    year: int = 2023,
    marxian_hydrator: MarxianHydrator | None = None,
) -> HexGrid:
    """Allocate county-level economic data to hexes via tract weights.

    For each county:
        1. Load county economic totals (c, v, s, employment, dept_shares).
           Uses ``marxian_hydrator`` for real QCEW data when available,
           falling back to ``DEFAULT_COUNTY_ECONOMICS``.
        2. Compute per-hex weight from tract demographics or uniform.
        3. Allocate: hex.c = county_c * weight, etc.

    Conservation: sum(hex.c) == county_c for each county.

    Args:
        grid: HexGrid with empty economic state.
        tract_source: Source for tract-level demographic weights.
        year: Data vintage year.
        marxian_hydrator: Optional MarxianHydrator for real QCEW-derived
            c/v/s values. When provided, produces more accurate profit rates
            (~10%) compared to hardcoded defaults (~20%).

    Returns:
        New HexGrid with populated economic values.
    """
    from babylon.economics.substrate.types import HexGrid as HexGridType

    updated_hexes = dict(grid.hexes)

    for county_fips, hex_ids in grid.county_hex_ids.items():
        if not hex_ids:
            continue

        # Get county-level totals: prefer MarxianHydrator, fall back to defaults
        county_econ = _get_county_economics(county_fips, year, marxian_hydrator)
        if county_econ is None:
            logger.warning("No economic data for county %s", county_fips)
            continue

        c_total, v_total, s_total, emp_total, dept_shares = county_econ

        # Compute weights per hex
        hex_list = sorted(hex_ids)
        n_hexes = len(hex_list)

        if tract_source is not None:
            weights = _compute_tract_weights(tract_source, county_fips, hex_list, year)
        else:
            # Uniform allocation
            weights = dict.fromkeys(hex_list, 1.0 / n_hexes)

        # Normalize weights to sum to 1.0
        weight_sum = sum(weights.values())
        if weight_sum > 0:
            weights = {h: w / weight_sum for h, w in weights.items()}

        # Allocate to hexes
        for h3_id in hex_list:
            w = weights.get(h3_id, 0.0)
            hex_c = c_total * w
            hex_v = v_total * w
            hex_s = s_total * w
            hex_emp = emp_total * w

            updated_hexes[h3_id] = grid.hexes[h3_id].model_copy(
                update={
                    "constant_capital": hex_c,
                    "variable_capital": hex_v,
                    "surplus_value": hex_s,
                    "employment": hex_emp,
                    "dept_shares": dept_shares,
                }
            )

        logger.info(
            "County %s: allocated c=%.1f, v=%.1f, s=%.1f to %d hexes",
            county_fips,
            c_total,
            v_total,
            s_total,
            n_hexes,
        )

    return HexGridType(
        hexes=updated_hexes,
        county_hex_ids=grid.county_hex_ids,
        res6_parents=grid.res6_parents,
        res5_parents=grid.res5_parents,
        res6_children=grid.res6_children,
        res5_children=grid.res5_children,
    )


def _get_county_economics(
    county_fips: str,
    year: int,
    marxian_hydrator: MarxianHydrator | None,
) -> tuple[float, float, float, float, tuple[float, float, float, float]] | None:
    """Get county-level c, v, s, employment, and dept_shares.

    Tries ``marxian_hydrator.hydrate()`` first for real QCEW-derived values.
    Falls back to ``DEFAULT_COUNTY_ECONOMICS`` when the hydrator is absent
    or returns zero total value (missing QCEW data for this county/year).

    Args:
        county_fips: 5-digit FIPS county code.
        year: Data vintage year.
        marxian_hydrator: Optional MarxianHydrator instance.

    Returns:
        Tuple of (c_total, v_total, s_total, emp_total, dept_shares),
        or None if no data is available from either source.
    """
    if marxian_hydrator is not None:
        tensor = marxian_hydrator.hydrate(county_fips, year)

        c_total = float(tensor.total_c)
        v_total = float(tensor.total_v)
        s_total = float(tensor.total_s)

        if c_total + v_total + s_total > 0:
            total_value = c_total + v_total + s_total
            dept_I_value = float(tensor.dept_I.total_value)
            dept_IIa_value = float(tensor.dept_IIa.total_value)
            dept_IIb_value = float(tensor.dept_IIb.total_value)
            dept_III_value = float(tensor.dept_III.total_value)
            dept_shares = (
                dept_I_value / total_value,
                dept_IIa_value / total_value,
                dept_IIb_value / total_value,
                dept_III_value / total_value,
            )

            # Employment comes from defaults if available; MarxianHydrator
            # does not track employment separately.
            fallback = DEFAULT_COUNTY_ECONOMICS.get(county_fips)
            emp_total = fallback["employment"] if fallback else 0.0

            logger.info(
                "County %s: using MarxianHydrator data (c=%.1f, v=%.1f, s=%.1f)",
                county_fips,
                c_total,
                v_total,
                s_total,
            )
            return c_total, v_total, s_total, emp_total, dept_shares

        logger.warning(
            "MarxianHydrator returned zero for county %s year %d, falling back to defaults",
            county_fips,
            year,
        )

    # Fall back to hardcoded defaults
    county_data = DEFAULT_COUNTY_ECONOMICS.get(county_fips)
    if county_data is None:
        return None

    return (
        county_data["constant_capital"],
        county_data["variable_capital"],
        county_data["surplus_value"],
        county_data["employment"],
        (
            county_data["dept_I"],
            county_data["dept_IIa"],
            county_data["dept_IIb"],
            county_data["dept_III"],
        ),
    )


def _compute_tract_weights(
    tract_source: TractDemographicSource,
    county_fips: str,
    hex_ids: list[str],
    year: int,
) -> dict[str, float]:
    """Compute per-hex weights from tract demographics.

    Args:
        tract_source: Source for tract-level data.
        county_fips: County FIPS code.
        hex_ids: List of H3 cell IDs in this county.
        year: Data vintage year.

    Returns:
        Mapping of h3_id to weight (unnormalized).
    """
    from babylon.economics.tensor import NoDataSentinel

    tract_weights = tract_source.get_tract_weights(county_fips, year)

    if isinstance(tract_weights, NoDataSentinel):
        # Fall back to uniform
        logger.warning(
            "No tract data for county %s year %d, using uniform weights",
            county_fips,
            year,
        )
        return dict.fromkeys(hex_ids, 1.0)

    # Get tract-to-hex mapping
    tract_hex_map = tract_source.get_tract_to_hex_mapping(county_fips)

    # Build hex weights from tract employment
    hex_weights: dict[str, float] = {}
    for tract_geoid, tract_weight in tract_weights.items():
        mapped_hexes = tract_hex_map.get(tract_geoid, [])
        if not mapped_hexes:
            continue

        per_hex_weight = tract_weight.weight / len(mapped_hexes)
        for h3_id in mapped_hexes:
            if h3_id in hex_ids:
                hex_weights[h3_id] = hex_weights.get(h3_id, 0.0) + per_hex_weight

    # Ensure all hex_ids have a weight (default to small value)
    for h3_id in hex_ids:
        if h3_id not in hex_weights:
            hex_weights[h3_id] = 1e-10

    return hex_weights


__all__ = [
    "DEFAULT_COUNTY_ECONOMICS",
    "hydrate_hex_grid",
]
