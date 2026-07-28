"""P26 U5d — σ-gradient Φ attribution (Option C, ADR165 Q1) pure math.

Written RED first. Pins the ruled three-tier treatment rule
(``specs/101-trade-activation/u5a-core-bloc-theory.md``): CORE-tier blocs
source zero Φ (Amin/Wallerstein/MIM convergence + the Ricci empirical
partition — zero CORE OUTFLOW rows in all 51), SEMI_PERIPHERY blocs are
damped by ``w_semi`` (derived from Ricci's own OUTFLOW magnitudes, the
delegated-decision analog of ADR165 D1), PERIPHERY blocs carry the ruled
undamped Option C form ``max(0, σ_US − σ_i)^p × trade_i``. Shares
renormalize to Σ = 1.0 (conservation, spec-101 D3).
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.sigma.attribution import (
    AttributionInputError,
    compute_bloc_shares,
    derive_w_semi,
    nearest_vintage,
)

_TIERS = {
    "eu": "CORE",
    "canada": "CORE",
    "china": "SEMI_PERIPHERY",
    "russia_csi": "SEMI_PERIPHERY",
    "india": "PERIPHERY",
    "southeast_asia": "PERIPHERY",
    "sub_saharan_africa": "PERIPHERY",
    "latin_america": "PERIPHERY",
}
_GAP = {
    "eu": 0.0,  # at/above the US position — clamped upstream
    "canada": 0.0,
    "china": 0.8,
    "russia_csi": 0.9,
    "india": 1.6,
    "southeast_asia": 1.4,
    "sub_saharan_africa": 2.0,
    "latin_america": 1.2,
}
_TRADE = {
    "eu": 700_000.0,
    "canada": 600_000.0,
    "china": 550_000.0,
    "russia_csi": 40_000.0,
    "india": 90_000.0,
    "southeast_asia": 300_000.0,
    "sub_saharan_africa": 40_000.0,
    "latin_america": 400_000.0,
}


class TestComputeBlocShares:
    def test_shares_sum_to_one_and_core_is_zero(self) -> None:
        shares = compute_bloc_shares(tiers=_TIERS, sigma_gap=_GAP, trade=_TRADE, w_semi=0.5)
        assert sum(shares.values()) == pytest.approx(1.0)
        assert shares["eu"] == 0.0
        assert shares["canada"] == 0.0

    def test_periphery_outranks_equal_trade_semi_periphery(self) -> None:
        """With equal gap and trade, a periphery bloc takes 1/w_semi times
        the semi-periphery share (the damping is the ONLY difference)."""
        tiers = {"p": "PERIPHERY", "s": "SEMI_PERIPHERY"}
        gap = {"p": 1.0, "s": 1.0}
        trade = {"p": 100.0, "s": 100.0}
        shares = compute_bloc_shares(tiers=tiers, sigma_gap=gap, trade=trade, w_semi=0.25)
        assert shares["p"] == pytest.approx(0.8)
        assert shares["s"] == pytest.approx(0.2)

    def test_gap_exponent_sharpens_the_gradient(self) -> None:
        tiers = {"a": "PERIPHERY", "b": "PERIPHERY"}
        gap = {"a": 2.0, "b": 1.0}
        trade = {"a": 100.0, "b": 100.0}
        linear = compute_bloc_shares(tiers=tiers, sigma_gap=gap, trade=trade, w_semi=0.5)
        squared = compute_bloc_shares(
            tiers=tiers, sigma_gap=gap, trade=trade, w_semi=0.5, gap_exponent=2.0
        )
        assert linear["a"] == pytest.approx(2.0 / 3.0)
        assert squared["a"] == pytest.approx(4.0 / 5.0)

    def test_all_zero_raw_mass_fails_loud(self) -> None:
        """A world where every bloc is CORE (or gapless) has no attribution
        target — that is a modelling contradiction, never a silent 0-map
        (Constitution III.11)."""
        tiers = {"x": "CORE", "y": "CORE"}
        with pytest.raises(AttributionInputError):
            compute_bloc_shares(
                tiers=tiers,
                sigma_gap={"x": 0.0, "y": 0.0},
                trade={"x": 1.0, "y": 1.0},
                w_semi=0.5,
            )

    def test_key_mismatch_fails_loud(self) -> None:
        with pytest.raises(AttributionInputError):
            compute_bloc_shares(
                tiers={"a": "PERIPHERY"},
                sigma_gap={"a": 1.0, "b": 1.0},
                trade={"a": 1.0},
                w_semi=0.5,
            )

    def test_unknown_tier_fails_loud(self) -> None:
        with pytest.raises(AttributionInputError):
            compute_bloc_shares(
                tiers={"a": "METROPOLE"},
                sigma_gap={"a": 1.0},
                trade={"a": 1.0},
                w_semi=0.5,
            )

    def test_deterministic_ordering_of_result(self) -> None:
        """Result keys iterate in sorted order (determinism discipline)."""
        shares = compute_bloc_shares(tiers=_TIERS, sigma_gap=_GAP, trade=_TRADE, w_semi=0.5)
        assert list(shares) == sorted(shares)


class TestDeriveWSemi:
    def test_ratio_of_mean_outflow_intensities(self) -> None:
        """w_semi = mean(semi OUTFLOW %GDP) / mean(periphery OUTFLOW %GDP),
        data-derived from the Ricci sample, never an invented constant."""
        w = derive_w_semi(
            semi_outflow_pct_gdp=[2.0, 4.0],  # mean 3.0
            periphery_outflow_pct_gdp=[5.0, 7.0],  # mean 6.0
        )
        assert w == pytest.approx(0.5)

    def test_clamped_to_unit_interval(self) -> None:
        w = derive_w_semi(
            semi_outflow_pct_gdp=[9.0],
            periphery_outflow_pct_gdp=[3.0],
        )
        assert w == 1.0

    def test_empty_samples_fail_loud(self) -> None:
        with pytest.raises(AttributionInputError):
            derive_w_semi(semi_outflow_pct_gdp=[], periphery_outflow_pct_gdp=[1.0])
        with pytest.raises(AttributionInputError):
            derive_w_semi(semi_outflow_pct_gdp=[1.0], periphery_outflow_pct_gdp=[])


class TestNearestVintage:
    def test_prefers_latest_vintage_at_or_before(self) -> None:
        assert nearest_vintage(2010, (1995, 2000, 2007, 2009)) == 2009
        assert nearest_vintage(2007, (1995, 2000, 2007, 2009)) == 2007

    def test_pre_first_vintage_takes_earliest(self) -> None:
        assert nearest_vintage(1990, (1995, 2000, 2007, 2009)) == 1995

    def test_empty_vintages_fail_loud(self) -> None:
        with pytest.raises(AttributionInputError):
            nearest_vintage(2010, ())
