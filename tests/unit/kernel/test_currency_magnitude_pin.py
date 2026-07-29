"""Pins the Currency magnitude budget (Program 27 spec §6.1)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "tools"))
from currency_magnitude_census import census

# Pinned from the 2026-07-29 census (reports/currency-magnitude-census-2026-07-29.md),
# rounded UP to 2 sig figs: observed max was 2.30288e13
# (michigan-e2e.json.external_node_flows[1].total_phi_inflow, the 83-county
# Michigan e2e scenario). Re-derive via `python tools/currency_magnitude_census.py`
# against a fully LFS-hydrated checkout with the reference DB built if this fails.
MAX_OBSERVED_ABS_VALUE = 2.4e13
NATIONWIDE_SCALE_HEADROOM = 1_000  # tri-county/Michigan -> ~3,100 counties + growth
I64_MICROUNIT_CEILING = 2**63 / 1e6  # ≈ 9.2e12 units
I128_MICROUNIT_CEILING = 2**127 / 1e6


def test_observed_max_is_pinned() -> None:
    observed = census()[0][0]
    assert observed <= MAX_OBSERVED_ABS_VALUE, (
        f"data grew past the pinned budget ({observed:.3g}); re-derive §6.1"
    )


def test_i64_microunits_overflow_at_nationwide_scale() -> None:
    """The spec's B2 claim, kept true by construction."""
    assert MAX_OBSERVED_ABS_VALUE * NATIONWIDE_SCALE_HEADROOM > I64_MICROUNIT_CEILING


def test_i64_microunits_already_overflow_at_current_scale() -> None:
    """Stronger than the spec's B2 claim: the CURRENT (un-scaled) 83-county
    Michigan fixture's max |Currency| already exceeds the i64-microunit
    ceiling — nationwide scale-up isn't even needed to trigger overflow.
    See reports/currency-magnitude-census-2026-07-29.md for the finding."""
    assert MAX_OBSERVED_ABS_VALUE > I64_MICROUNIT_CEILING


def test_i128_microunits_have_headroom() -> None:
    assert MAX_OBSERVED_ABS_VALUE * NATIONWIDE_SCALE_HEADROOM * 1e6 < I128_MICROUNIT_CEILING
