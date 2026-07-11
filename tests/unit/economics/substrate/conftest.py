"""Fixtures for substrate module unit tests.

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.substrate.types import (
    TRI_COUNTY_FIPS,
    BoundaryFlowRegister,
    HexEconomicState,
    HexGrid,
    SubstrateConfig,
    TractWeight,
)
from babylon.domain.economics.tensor import DepartmentRow, ValueTensor4x3

# =============================================================================
# Default Test Constants
# =============================================================================

# Wayne County hex IDs (mock - 3 hexes)
WAYNE_HEX_IDS: list[str] = [
    "872830828ffffff",
    "872830829ffffff",
    "87283082affffff",
]

# Oakland County hex IDs (mock - 3 hexes)
OAKLAND_HEX_IDS: list[str] = [
    "872830880ffffff",
    "872830881ffffff",
    "872830882ffffff",
]

# Macomb County hex IDs (mock - 3 hexes)
MACOMB_HEX_IDS: list[str] = [
    "872830890ffffff",
    "872830891ffffff",
    "872830892ffffff",
]

ALL_HEX_IDS: list[str] = WAYNE_HEX_IDS + OAKLAND_HEX_IDS + MACOMB_HEX_IDS

DEFAULT_POPULATION: int = 10000
DEFAULT_EMPLOYMENT: int = 5000
DEFAULT_DEPT_SHARES: tuple[float, float, float, float] = (0.30, 0.30, 0.20, 0.20)


# =============================================================================
# Mock Data Sources
# =============================================================================


class MockSpatialSubstrateSource:
    """Mock spatial source returning 9 hexes (3 per county).

    Returns deterministic hex IDs for Wayne, Oakland, Macomb counties.
    """

    def __init__(
        self,
        hex_ids_by_county: dict[str, list[str]] | None = None,
    ) -> None:
        """Initialize mock spatial source.

        Args:
            hex_ids_by_county: Optional county_fips -> hex IDs mapping.
        """
        if hex_ids_by_county is not None:
            self._hex_ids_by_county = hex_ids_by_county
        else:
            self._hex_ids_by_county = {
                "26163": WAYNE_HEX_IDS,
                "26125": OAKLAND_HEX_IDS,
                "26099": MACOMB_HEX_IDS,
            }

    def generate_hex_mesh(
        self,
        county_fips_list: list[str] | tuple[str, ...],
        resolution: int = 7,
    ) -> HexGrid:
        """Generate mock hex mesh with 9 hexes."""
        hexes: dict[str, HexEconomicState] = {}
        county_hex_ids: dict[str, frozenset[str]] = {}

        for fips in county_fips_list:
            ids = self._hex_ids_by_county.get(fips, [])
            county_hex_ids[fips] = frozenset(ids)
            for h3_id in ids:
                hexes[h3_id] = HexEconomicState(
                    h3_index=h3_id,
                    county_fips=fips,
                    constant_capital=0.0,
                    variable_capital=0.0,
                    surplus_value=0.0,
                    employment=0.0,
                    dept_shares=(0.25, 0.25, 0.25, 0.25),
                )

        # Build mock resolution hierarchy
        res6_parents: dict[str, str] = {}
        res5_parents: dict[str, str] = {}
        res6_children: dict[str, frozenset[str]] = {}
        res5_children: dict[str, frozenset[str]] = {}

        # Each county's hexes share one r6 and one r5 parent
        for fips, ids in self._hex_ids_by_county.items():
            if not ids:
                continue
            r6_parent = f"86{fips}ffffff"
            r5_parent = f"85{fips}fffffff"
            r6_set: set[str] = set()
            r5_set: set[str] = set()
            for h3_id in ids:
                if h3_id in hexes:
                    res6_parents[h3_id] = r6_parent
                    res5_parents[h3_id] = r5_parent
                    r6_set.add(h3_id)
                    r5_set.add(h3_id)
            res6_children[r6_parent] = frozenset(r6_set)
            res5_children[r5_parent] = frozenset(r5_set)

        return HexGrid(
            hexes=hexes,
            county_hex_ids=county_hex_ids,
            res6_parents=res6_parents,
            res5_parents=res5_parents,
            res6_children=res6_children,
            res5_children=res5_children,
        )

    def get_county_boundary(self, county_fips: str) -> None:
        """Mock: returns None (no real geometry)."""
        return None


class MockTractDemographicSource:
    """Mock tract demographic source for testing.

    Returns configurable tract weights per county.
    """

    def __init__(
        self,
        weights_by_county: dict[str, dict[str, TractWeight]] | None = None,
    ) -> None:
        """Initialize mock tract source.

        Args:
            weights_by_county: Optional county_fips -> tract weights mapping.
        """
        if weights_by_county is not None:
            self._weights_by_county = weights_by_county
        else:
            # Default: 2 tracts per county with equal weights
            self._weights_by_county = {}
            for fips in TRI_COUNTY_FIPS:
                state_county = fips  # e.g. "26163"
                self._weights_by_county[fips] = {
                    f"{state_county}010100": TractWeight(
                        tract_geoid=f"{state_county}010100",
                        population=DEFAULT_POPULATION,
                        employed=DEFAULT_EMPLOYMENT,
                        weight=0.5,
                    ),
                    f"{state_county}010200": TractWeight(
                        tract_geoid=f"{state_county}010200",
                        population=DEFAULT_POPULATION,
                        employed=DEFAULT_EMPLOYMENT,
                        weight=0.5,
                    ),
                }

    def get_tract_weights(self, county_fips: str, year: int) -> dict[str, TractWeight]:
        """Return mock tract weights for a county."""
        return self._weights_by_county.get(county_fips, {})

    def get_tract_to_hex_mapping(
        self, county_fips: str, resolution: int = 7
    ) -> dict[str, list[str]]:
        """Return mock tract-to-hex mapping."""
        # Map each tract to some hex IDs in the county
        hex_ids = {
            "26163": WAYNE_HEX_IDS,
            "26125": OAKLAND_HEX_IDS,
            "26099": MACOMB_HEX_IDS,
        }
        county_hexes = hex_ids.get(county_fips, [])
        tracts = list(self._weights_by_county.get(county_fips, {}).keys())

        result: dict[str, list[str]] = {}
        if len(tracts) >= 2 and len(county_hexes) >= 2:
            # Split hexes between tracts
            mid = len(county_hexes) // 2
            result[tracts[0]] = county_hexes[:mid]
            result[tracts[1]] = county_hexes[mid:]
        elif tracts and county_hexes:
            result[tracts[0]] = county_hexes

        return result


class MockCommuterFlowSource:
    """Mock commuter flow source for testing.

    Returns configurable county-to-county OD flows.
    """

    # Default OD flows: 7 pairs covering intra-county + cross-county
    DEFAULT_OD_FLOWS: dict[tuple[str, str], int] = {
        ("26163", "26163"): 300000,  # Wayne internal
        ("26125", "26125"): 250000,  # Oakland internal
        ("26099", "26099"): 150000,  # Macomb internal
        ("26163", "26125"): 50000,  # Wayne -> Oakland
        ("26125", "26163"): 40000,  # Oakland -> Wayne
        ("26099", "26163"): 30000,  # Macomb -> Wayne
        ("26163", "26099"): 20000,  # Wayne -> Macomb
    }

    def __init__(
        self,
        od_flows: dict[tuple[str, str], int] | None = None,
        external_flows: BoundaryFlowRegister | None = None,
    ) -> None:
        """Initialize mock commuter flow source.

        Args:
            od_flows: Optional (home_county, work_county) -> worker count.
            external_flows: Optional boundary flow register.
        """
        self._od_flows = od_flows if od_flows is not None else self.DEFAULT_OD_FLOWS
        self._external_flows = external_flows or BoundaryFlowRegister(
            external_outflow_v=5000.0,
            external_inflow_v=4000.0,
            net_flow=-1000.0,
        )

    def get_county_od_flows(
        self,
        county_fips_list: list[str] | tuple[str, ...],
        year: int,
    ) -> dict[tuple[str, str], int]:
        """Return mock county-to-county OD flows."""
        fips_set = set(county_fips_list)
        return {k: v for k, v in self._od_flows.items() if k[0] in fips_set or k[1] in fips_set}

    def get_external_flows(
        self,
        county_fips_list: list[str] | tuple[str, ...],
        year: int,
    ) -> BoundaryFlowRegister:
        """Return mock boundary flow register."""
        return self._external_flows


class MockMarxianHydrator:
    """Mock MarxianHydrator returning configurable ValueTensor4x3 per county.

    Provides realistic c/v/s values with lower profit rates (~10%) compared
    to DEFAULT_COUNTY_ECONOMICS defaults (~20%), simulating real QCEW data.
    """

    # Realistic BEA-calibrated values: profit rate ~ 10%
    # c/v ratio ~2.5, s/v ratio ~0.5 -> r = s/(c+v) = 0.5v/(2.5v+v) ≈ 14%
    DEFAULT_TENSORS: dict[str, dict[str, DepartmentRow]] = {
        "26163": {  # Wayne County
            "dept_I": DepartmentRow(c=5000.0, v=2000.0, s=1000.0),
            "dept_IIa": DepartmentRow(c=8000.0, v=3500.0, s=1500.0),
            "dept_IIb": DepartmentRow(c=6000.0, v=2500.0, s=1200.0),
            "dept_III": DepartmentRow(c=4000.0, v=2000.0, s=800.0),
        },
        "26125": {  # Oakland County
            "dept_I": DepartmentRow(c=7000.0, v=2500.0, s=1200.0),
            "dept_IIa": DepartmentRow(c=9000.0, v=3000.0, s=1400.0),
            "dept_IIb": DepartmentRow(c=7000.0, v=2500.0, s=1300.0),
            "dept_III": DepartmentRow(c=5000.0, v=2000.0, s=900.0),
        },
        "26099": {  # Macomb County
            "dept_I": DepartmentRow(c=5000.0, v=1500.0, s=700.0),
            "dept_IIa": DepartmentRow(c=4000.0, v=1500.0, s=600.0),
            "dept_IIb": DepartmentRow(c=3000.0, v=1200.0, s=500.0),
            "dept_III": DepartmentRow(c=2000.0, v=1000.0, s=400.0),
        },
    }

    def __init__(
        self,
        tensors: dict[str, dict[str, DepartmentRow]] | None = None,
    ) -> None:
        """Initialize mock hydrator.

        Args:
            tensors: Optional county_fips -> department rows mapping.
        """
        self._tensors = tensors if tensors is not None else self.DEFAULT_TENSORS

    def hydrate(self, fips_code: str, year: int) -> ValueTensor4x3:
        """Return mock ValueTensor4x3 for the given county."""
        county = self._tensors.get(fips_code)
        if county is None:
            # Return zero tensor for unknown counties
            zero_row = DepartmentRow(c=0.0, v=0.0, s=0.0)
            return ValueTensor4x3(
                fips_code=fips_code,
                year=year,
                dept_I=zero_row,
                dept_IIa=zero_row,
                dept_IIb=zero_row,
                dept_III=zero_row,
                naics_granularity=0.0,
                excluded_wages=0.0,
            )

        return ValueTensor4x3(
            fips_code=fips_code,
            year=year,
            dept_I=county["dept_I"],
            dept_IIa=county["dept_IIa"],
            dept_IIb=county["dept_IIb"],
            dept_III=county["dept_III"],
            naics_granularity=0.85,
            excluded_wages=0.0,
        )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def substrate_config() -> SubstrateConfig:
    """Provide default substrate configuration."""
    return SubstrateConfig()


@pytest.fixture
def mock_spatial_source() -> MockSpatialSubstrateSource:
    """Provide mock spatial substrate source with 9 hexes."""
    return MockSpatialSubstrateSource()


@pytest.fixture
def mock_tract_source() -> MockTractDemographicSource:
    """Provide mock tract demographic source."""
    return MockTractDemographicSource()


@pytest.fixture
def mock_commuter_source() -> MockCommuterFlowSource:
    """Provide mock commuter flow source."""
    return MockCommuterFlowSource()


@pytest.fixture
def mock_marxian_hydrator() -> MockMarxianHydrator:
    """Provide mock MarxianHydrator with realistic BEA-calibrated values."""
    return MockMarxianHydrator()


@pytest.fixture
def sample_hex_grid(
    mock_spatial_source: MockSpatialSubstrateSource,
) -> HexGrid:
    """Provide a sample hex grid with 9 empty hexes."""
    return mock_spatial_source.generate_hex_mesh(
        county_fips_list=["26163", "26125", "26099"],
    )


@pytest.fixture
def hydrated_hex_grid() -> HexGrid:
    """Provide a hex grid with economic data populated.

    Wayne hexes: higher employment, lower c/v (service economy).
    Oakland hexes: moderate employment, higher c/v (suburban).
    Macomb hexes: lower employment, highest c/v (manufacturing).
    """
    hexes: dict[str, HexEconomicState] = {}

    # Wayne County - urban, service-heavy
    for i, h3_id in enumerate(WAYNE_HEX_IDS):
        hexes[h3_id] = HexEconomicState(
            h3_index=h3_id,
            county_fips="26163",
            constant_capital=100.0 + i * 10,
            variable_capital=80.0 + i * 5,
            surplus_value=40.0 + i * 3,
            employment=1000.0 + i * 100,
            dept_shares=(0.20, 0.35, 0.25, 0.20),
        )

    # Oakland County - suburban, balanced
    for i, h3_id in enumerate(OAKLAND_HEX_IDS):
        hexes[h3_id] = HexEconomicState(
            h3_index=h3_id,
            county_fips="26125",
            constant_capital=150.0 + i * 10,
            variable_capital=60.0 + i * 5,
            surplus_value=50.0 + i * 3,
            employment=800.0 + i * 100,
            dept_shares=(0.25, 0.30, 0.25, 0.20),
        )

    # Macomb County - manufacturing-heavy
    for i, h3_id in enumerate(MACOMB_HEX_IDS):
        hexes[h3_id] = HexEconomicState(
            h3_index=h3_id,
            county_fips="26099",
            constant_capital=200.0 + i * 10,
            variable_capital=50.0 + i * 5,
            surplus_value=60.0 + i * 3,
            employment=600.0 + i * 100,
            dept_shares=(0.35, 0.25, 0.20, 0.20),
        )

    # Build mock resolution hierarchy (same as MockSpatialSubstrateSource)
    res6_parents: dict[str, str] = {}
    res5_parents: dict[str, str] = {}
    res6_children: dict[str, frozenset[str]] = {}
    res5_children: dict[str, frozenset[str]] = {}

    county_hex_map = {
        "26163": WAYNE_HEX_IDS,
        "26125": OAKLAND_HEX_IDS,
        "26099": MACOMB_HEX_IDS,
    }

    for fips, ids in county_hex_map.items():
        r6_parent = f"86{fips}ffffff"
        r5_parent = f"85{fips}fffffff"
        r6_set: set[str] = set()
        r5_set: set[str] = set()
        for h3_id in ids:
            res6_parents[h3_id] = r6_parent
            res5_parents[h3_id] = r5_parent
            r6_set.add(h3_id)
            r5_set.add(h3_id)
        res6_children[r6_parent] = frozenset(r6_set)
        res5_children[r5_parent] = frozenset(r5_set)

    return HexGrid(
        hexes=hexes,
        county_hex_ids={
            "26163": frozenset(WAYNE_HEX_IDS),
            "26125": frozenset(OAKLAND_HEX_IDS),
            "26099": frozenset(MACOMB_HEX_IDS),
        },
        res6_parents=res6_parents,
        res5_parents=res5_parents,
        res6_children=res6_children,
        res5_children=res5_children,
    )
