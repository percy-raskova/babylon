"""Per-stage conservation property tests (T051 / FR-026 .. FR-035 / SC-011).

Hypothesis-driven verification of conservation invariants for each of the
load-bearing flow stages whose primitives are already implemented:

  - Distribution split (FR-032/FR-033): p + i + r + t == s exactly
  - Phi week distribution (FR-034/FR-035): annual sum == phi_year exactly
  - Equalization (Vol III Pt I): sum(c) preserved across hexes

Vol II circulation (LODES OD) is deferred to T055; the test docstring
notes the gap.
"""

from __future__ import annotations

import math
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from babylon.economics.boundary_flow_register import BoundaryFlowRegister
from babylon.engine.systems.distribution import split_surplus_to_pirt
from babylon.engine.systems.phi_distribution import distribute_phi_week_to_counties

pytestmark = [pytest.mark.cross_scale, pytest.mark.property]


@pytest.mark.parametrize("seed", [1, 2, 3])
@given(
    s=st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
    i_rate=st.floats(min_value=0.0, max_value=0.3, allow_nan=False),
    r_rate=st.floats(min_value=0.0, max_value=0.3, allow_nan=False),
    t_rate=st.floats(min_value=0.0, max_value=0.3, allow_nan=False),
)
@settings(max_examples=50, deadline=1000)
def test_distribution_conservation_property(
    seed: int, s: float, i_rate: float, r_rate: float, t_rate: float
):  # noqa: ARG001
    """FR-032/FR-033: any (s, i_rate, r_rate, t_rate) → p+i+r+t == s exactly."""
    out = split_surplus_to_pirt(s=s, interest_rate=i_rate, rent_rate=r_rate, tax_rate=t_rate)
    assert math.isclose(out.p + out.i + out.r + out.t, s, abs_tol=max(1e-9, abs(s) * 1e-12))


@given(
    phi_year=st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
    weights=st.lists(
        st.floats(min_value=0.01, max_value=1.0, allow_nan=False),
        min_size=1,
        max_size=5,
    ),
)
@settings(max_examples=30, deadline=2000, suppress_health_check=[HealthCheck.filter_too_much])
def test_phi_annual_conservation_property(phi_year: float, weights: list[float]):
    """FR-035: 52 weeks × (phi_year/52 × weight) == phi_year × weight (per county)."""
    # Normalize weights to sum to 1.0
    total = sum(weights)
    if total <= 0:
        return  # skip pathological case
    norm = [w / total for w in weights]
    counties = {f"261{i:02d}": w for i, w in enumerate(norm)}

    register = BoundaryFlowRegister()
    sid = uuid4()
    annual_per_county: dict[str, float] = dict.fromkeys(counties, 0.0)
    for week in range(52):
        transfers = distribute_phi_week_to_counties(
            session_id=sid,
            tick=week,
            external_node_id="canada",
            phi_year_inflow=phi_year,
            county_exposure=counties,
            register=register,
        )
        for c, amt in transfers.items():
            annual_per_county[c] += amt
        register.flush()  # discard buffer per week

    for c, expected_share in counties.items():
        expected = phi_year * expected_share
        assert math.isclose(
            annual_per_county[c], expected, abs_tol=max(1e-6, abs(expected) * 1e-9)
        ), f"County {c}: got {annual_per_county[c]}, expected {expected}"


@given(
    cs=st.lists(
        st.floats(min_value=1.0, max_value=1e6, allow_nan=False),
        min_size=2,
        max_size=8,
    ),
    vs=st.lists(
        st.floats(min_value=0.1, max_value=1e5, allow_nan=False),
        min_size=2,
        max_size=8,
    ),
)
@settings(max_examples=20, deadline=2000)
def test_equalization_conserves_total_capital(cs: list[float], vs: list[float]):
    """Vol III Pt I (FR-029/FR-030): sum(c) preserved across all hexes."""
    from babylon.economics.substrate.equalization import DefaultHexEqualizationComputer
    from babylon.economics.substrate.types import HexEconomicState, HexGrid

    n = min(len(cs), len(vs))
    if n < 2:
        return  # skip
    hexes = {}
    for i in range(n):
        h3 = f"872d34{i:04x}fffff"[:15]
        hexes[h3] = HexEconomicState(
            h3_index=h3,
            county_fips="26163",
            constant_capital=cs[i],
            variable_capital=vs[i],
            surplus_value=vs[i] * 0.3,  # arbitrary surplus
            employment=cs[i] / 10.0,
            dept_shares=(0.25, 0.25, 0.25, 0.25),
        )
    grid = HexGrid(
        hexes=hexes,
        county_hex_ids={"26163": frozenset(hexes.keys())},
        res6_parents={k: k for k in hexes},
        res5_parents={k: k for k in hexes},
        res5_children={k: frozenset({k}) for k in hexes},
        res6_children={k: frozenset({k}) for k in hexes},
    )
    pre_total = sum(h.constant_capital for h in hexes.values())

    computer = DefaultHexEqualizationComputer()
    grid_out = computer.equalize_capital(grid, alpha=0.01)
    post_total = sum(h.constant_capital for h in grid_out.hexes.values())

    assert math.isclose(post_total, pre_total, abs_tol=max(1e-6, pre_total * 1e-9)), (
        f"Equalization conservation broken: pre={pre_total}, post={post_total}"
    )
