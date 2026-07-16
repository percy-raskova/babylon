"""Empirical wealth-distribution invariants — the Pareto structure of capitalism.

Owner-directed (2026-07-16): US wealth ownership follows a stable quantile law
under the capitalist mode of production — the top 1% of the population, the
next 9% (p90–99), and the next 40% (p50–90) each hold roughly a third of net
personal wealth, while the bottom 50% of the population holds approximately
nothing. These tests pin ``GameDefines.class_dynamics.equilibrium_w1..w4``
(the calibration target the class-wealth-flow ODEs relax toward) inside bands
corroborated by two methodologically independent sources:

* **WID/Piketty** (``/media/user/data/babylon-data/piketty/WID_data_US.csv``,
  variable ``shwealj992`` = net personal wealth share, equal-split adults;
  tax-data-based). 2010–2024 observed: top1 [0.346, 0.363],
  p90–99 [0.346, 0.384] (derived p90p100 − p99p100), p50–90 [0.274, 0.295],
  bottom50 [−0.018, 0.010]. Full 1913–2024 record: bottom50 NEVER left
  [−0.0183 (2009), +0.0385 (1947)]; top decile ≥ 0.6271 every year since 1820.
  Reproduce::

      rg "^US;shwealj992;(p99p100|p90p100|p50p90|p0p50);" WID_data_US.csv \
        | awk -F';' '{print $4, $3, $5}'

* **Federal Reserve DFA** (SCF-benchmarked, independent of tax data; shipped
  in the reference DB as ``fact_fred_wealth_shares``, FRED series
  WFRBST01134/WFRBSN09161/WFRBSN40188/WFRBSB50215). 2010Q1–2024Q4 observed
  (percent): top1 [28.1, 31.0], p90–99 [36.4, 40.1], p50–90 [28.1, 31.6],
  bottom50 [0.4, 2.7] — strictly positive. See
  ``tests/unit/reference/test_fred_wealth_shares.py`` for the redundant-source
  leg against the DB itself.

Test bands below are the UNION of the two sources' observed 2010+ extremes
with ±1pp headroom for future data revisions.

**Conditionality (owner ruling, 2026-07-16):** these are laws of the
*capitalist mode of production*, not universal laws. They gate the CALIBRATION
defines (what the shipped equilibrium targets, i.e. the world the game starts
in) — they must NEVER be asserted against a live simulation trajectory, where
a communist revolution breaking the distribution is the mechanic working as
designed. Runtime checks take the contrapositive form (distribution leaves the
capitalist band ⟹ a rupture event exists in history) and await the
wealth-share axis landing in the tick engine.

CI-safe: no babylon-data drive access — all empirical numbers are pinned
constants with reproduction commands above.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines

#: Cross-source bands (union of WID 2010–2024 and Fed DFA 2010Q1–2024Q4
#: observed extremes, ±0.01 headroom), as wealth-share fractions.
TOP1_BAND = (0.27, 0.37)
P90_99_BAND = (0.33, 0.41)
P50_90_BAND = (0.26, 0.33)
BOTTOM50_BAND = (-0.02, 0.04)

#: Full-record (1913–2024 WID) ceiling on the bottom-50% wealth share: 0.0385
#: (1947) is the historical maximum through the New Deal and the Great
#: Compression. Reformism does not redistribute wealth.
BOTTOM50_HISTORICAL_CEILING = 0.04

#: Top-decile (w1 + w2) wealth share has been an outright supermajority every
#: year on record (1820–2024 WID minimum: 0.6271 in 1985).
TOP_DECILE_FLOOR = 0.60


@pytest.mark.unit
class TestEquilibriumWealthSharesMatchEmpiricalBands:
    """The shipped 4-class equilibrium targets sit inside the WID⋃DFA bands.

    ``equilibrium_w1..w4`` map onto the WID/DFA population quantile brackets:
    w1 ↔ top 1% (core bourgeoisie), w2 ↔ p90–99 (petty bourgeoisie),
    w3 ↔ p50–90 (labor aristocracy bracket; named "proletariat"/class 3 in
    the Feature-016 fit), w4 ↔ bottom 50%.
    """

    def test_w1_top1_band(self) -> None:
        """Bourgeoisie (top 1%) equilibrium wealth share ≈ one third."""
        w1 = GameDefines().class_dynamics.equilibrium_w1
        assert TOP1_BAND[0] <= w1 <= TOP1_BAND[1], (
            f"equilibrium_w1={w1} outside the WID⋃DFA top-1% band {TOP1_BAND}"
        )

    def test_w2_p90_99_band(self) -> None:
        """Petty bourgeoisie (p90–99) equilibrium wealth share ≈ one third."""
        w2 = GameDefines().class_dynamics.equilibrium_w2
        assert P90_99_BAND[0] <= w2 <= P90_99_BAND[1], (
            f"equilibrium_w2={w2} outside the WID⋃DFA p90–99 band {P90_99_BAND}"
        )

    def test_w3_p50_90_band(self) -> None:
        """The p50–90 bracket's equilibrium wealth share ≈ one (slim) third."""
        w3 = GameDefines().class_dynamics.equilibrium_w3
        assert P50_90_BAND[0] <= w3 <= P50_90_BAND[1], (
            f"equilibrium_w3={w3} outside the WID⋃DFA p50–90 band {P50_90_BAND}"
        )

    def test_w4_bottom50_band(self) -> None:
        """Bottom 50% of the population owns approximately nothing."""
        w4 = GameDefines().class_dynamics.equilibrium_w4
        assert BOTTOM50_BAND[0] <= w4 <= BOTTOM50_BAND[1], (
            f"equilibrium_w4={w4} outside the WID⋃DFA bottom-50% band {BOTTOM50_BAND}"
        )


@pytest.mark.unit
class TestStructuralWealthLaws:
    """Laws that held for the FULL historical record, not just the modern era."""

    def test_shares_sum_to_one(self) -> None:
        """The four quantile brackets partition total net personal wealth."""
        cd = GameDefines().class_dynamics
        total = cd.equilibrium_w1 + cd.equilibrium_w2 + cd.equilibrium_w3 + cd.equilibrium_w4
        assert abs(total - 1.0) <= 0.01, f"equilibrium shares sum to {total}, expected ~1.0"

    def test_bottom50_never_exceeds_historical_ceiling(self) -> None:
        """1913–2024: the bottom-50% share never exceeded 3.85% (1947 peak).

        The Fundamental Theorem in empirical form — within capitalism, no
        reform era (New Deal included) ever pushed the bottom half of the
        population above ~4% of net personal wealth. A calibration that does
        would model a world that has never existed without a rupture.
        """
        w4 = GameDefines().class_dynamics.equilibrium_w4
        assert w4 <= BOTTOM50_HISTORICAL_CEILING, (
            f"equilibrium_w4={w4} exceeds the 111-year historical ceiling "
            f"{BOTTOM50_HISTORICAL_CEILING} — no capitalist era on record did this"
        )

    def test_top_decile_holds_supermajority(self) -> None:
        """1820–2024: the top 10% held >60% of wealth every year on record."""
        cd = GameDefines().class_dynamics
        top_decile = cd.equilibrium_w1 + cd.equilibrium_w2
        assert top_decile >= TOP_DECILE_FLOOR, (
            f"top-decile equilibrium share {top_decile} below the 205-year "
            f"historical floor {TOP_DECILE_FLOOR} (observed minimum 0.6271, 1985)"
        )
