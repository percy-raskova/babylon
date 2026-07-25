"""GameDefines.capital_vol2 contract — Volume II circulation coefficients.

Honesty sweep (U7, 2026-07-21 vol2-circulation-engine program): pins the
defaults for the reproduction-schema thresholds (U3) plus the seven
crisis/inventory/replacement/scaling coefficients migrated off module-level
hardcoded literals during the U7 defines sweep — two became keyword
parameters on ``assess_circulation_crisis`` (``crisis.py``), five became
GameDefines-backed accessor functions in ``circulation/types/_legacy.py``
(mirroring ``capital_vol3``'s ``distribution_epsilon()`` convention), and
three (``national_employment``, ``fallback_days_inventory``,
``min_annual_depreciation_floor``) replaced hardcoded literals directly at
the Volume II tick call site (``_compute_county_circulation_state``).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.config.defines import CapitalVolumeIIDefines, GameDefines

pytestmark = pytest.mark.unit


class TestCapitalVolumeIIDefaults:
    def test_defaults_match_migrated_constants(self) -> None:
        d = CapitalVolumeIIDefines()
        assert d.reproduction_tolerance == pytest.approx(0.01)
        assert d.dept_i_share_required == pytest.approx(0.6667)
        assert d.commodity_overhang_threshold == pytest.approx(0.3)
        assert d.liquidity_crisis_ratio == pytest.approx(0.1)
        assert d.supply_crisis_days_threshold == pytest.approx(7.0)
        assert d.overproduction_days_threshold == pytest.approx(60.0)
        assert d.replacement_boom_ratio == pytest.approx(1.5)
        assert d.replacement_expansion_ratio == pytest.approx(1.0)
        assert d.replacement_maintenance_ratio == pytest.approx(0.7)
        assert d.national_employment == pytest.approx(155_000_000.0)
        assert d.fallback_days_inventory == pytest.approx(30.0)
        assert d.min_annual_depreciation_floor == pytest.approx(1.0)

    def test_reachable_from_game_defines(self) -> None:
        defines = GameDefines.load_default()
        assert defines.capital_vol2.commodity_overhang_threshold == pytest.approx(0.3)


class TestReplacementRatiosAreConstrainedAtTheSchemaBoundary:
    """Migrating the three replacement-cycle ratios off module-level ``Final``
    constants made them player-editable — and therefore able to invert the
    cascade ``DepreciationFundState.replacement_cycle_position`` relies on
    (boom > expansion > maintenance). An inverted ordering silently makes
    one or more ``ReplacementCyclePosition`` values unreachable with no
    diagnostic; this is now pinned at config-load time (Constitution III.11,
    mirroring capital_vol3's ``verify_interest_share_ordering``).
    """

    def test_shipped_default_survives_the_constraint(self) -> None:
        d = CapitalVolumeIIDefines()
        assert d.replacement_maintenance_ratio < d.replacement_expansion_ratio
        assert d.replacement_expansion_ratio < d.replacement_boom_ratio

    def test_boom_at_or_below_expansion_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="replacement_expansion_ratio"):
            CapitalVolumeIIDefines(replacement_boom_ratio=1.0, replacement_expansion_ratio=1.0)

    def test_expansion_at_or_below_maintenance_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="replacement_maintenance_ratio"):
            CapitalVolumeIIDefines(
                replacement_expansion_ratio=0.7, replacement_maintenance_ratio=0.7
            )

    def test_fully_inverted_ordering_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CapitalVolumeIIDefines(
                replacement_boom_ratio=0.5,
                replacement_expansion_ratio=1.0,
                replacement_maintenance_ratio=1.5,
            )


class TestLiveDivisorsRejectZero:
    """``supply_crisis_days_threshold``, ``overproduction_days_threshold``,
    ``national_employment``, ``fallback_days_inventory``, and
    ``min_annual_depreciation_floor`` all feed a comparison or a division
    reachable from a single modded ``defines.yaml`` edit — pinned ``gt=0.0``
    at the schema boundary rather than left to the call site.
    """

    @pytest.mark.parametrize(
        "field",
        [
            "supply_crisis_days_threshold",
            "overproduction_days_threshold",
            "replacement_boom_ratio",
            "replacement_expansion_ratio",
            "replacement_maintenance_ratio",
            "national_employment",
            "fallback_days_inventory",
            "min_annual_depreciation_floor",
        ],
    )
    def test_zero_is_rejected_at_construction(self, field: str) -> None:
        with pytest.raises(ValidationError, match=field):
            CapitalVolumeIIDefines(**{field: 0.0})

    @pytest.mark.parametrize("field", ["commodity_overhang_threshold", "liquidity_crisis_ratio"])
    def test_zero_and_one_are_rejected_for_share_fields(self, field: str) -> None:
        with pytest.raises(ValidationError, match=field):
            CapitalVolumeIIDefines(**{field: 0.0})
        with pytest.raises(ValidationError, match=field):
            CapitalVolumeIIDefines(**{field: 1.0})


class TestThresholdAccessorsAreAccessorsNotImportTimeSnapshots:
    """``circulation/types/_legacy.py`` must expose accessor functions, not
    module-level ``Final`` snapshots, for the five thresholds consumed
    inside frozen-model ``computed_field`` properties — an import-time
    snapshot reads defines.yaml on every process start and freezes the
    value before any runtime override can reach it.
    """

    def test_no_final_constants_remain_for_the_migrated_five(self) -> None:
        import babylon.domain.economics.circulation.types._legacy as legacy_types

        source = Path(str(legacy_types.__file__)).read_text(encoding="utf-8")
        for name in (
            "def supply_crisis_days_threshold(",
            "def overproduction_days_threshold(",
            "def replacement_boom_ratio(",
            "def replacement_expansion_ratio(",
            "def replacement_maintenance_ratio(",
            "def fallback_days_inventory(",
        ):
            assert name in source, f"{name} accessor missing from _legacy.py"
        for stale_final in (
            "SUPPLY_CRISIS_DAYS_THRESHOLD: Final",
            "OVERPRODUCTION_DAYS_THRESHOLD: Final",
            "REPLACEMENT_BOOM_RATIO: Final",
            "REPLACEMENT_EXPANSION_RATIO: Final",
            "REPLACEMENT_MAINTENANCE_RATIO: Final",
            "COMMODITY_OVERHANG_CRISIS: Final",
            "LIQUIDITY_CRISIS_RATIO: Final",
        ):
            assert stale_final not in source, f"{stale_final} should have been removed"

    def test_accessors_match_the_canonical_yaml(self) -> None:
        from babylon.domain.economics.circulation.types import (
            fallback_days_inventory,
            overproduction_days_threshold,
            replacement_boom_ratio,
            replacement_expansion_ratio,
            replacement_maintenance_ratio,
            supply_crisis_days_threshold,
        )

        defaults = GameDefines.load_default().capital_vol2
        assert supply_crisis_days_threshold() == pytest.approx(
            defaults.supply_crisis_days_threshold
        )
        assert overproduction_days_threshold() == pytest.approx(
            defaults.overproduction_days_threshold
        )
        assert replacement_boom_ratio() == pytest.approx(defaults.replacement_boom_ratio)
        assert replacement_expansion_ratio() == pytest.approx(defaults.replacement_expansion_ratio)
        assert replacement_maintenance_ratio() == pytest.approx(
            defaults.replacement_maintenance_ratio
        )
        assert fallback_days_inventory() == pytest.approx(defaults.fallback_days_inventory)

    def test_explicit_defines_override_is_honoured(self) -> None:
        """The whole point of the accessor: a caller-supplied GameDefines wins."""
        from babylon.domain.economics.circulation.types import supply_crisis_days_threshold

        base = GameDefines.load_default()
        overridden = base.model_copy(
            update={
                "capital_vol2": base.capital_vol2.model_copy(
                    update={"supply_crisis_days_threshold": 3.5}
                )
            }
        )
        assert supply_crisis_days_threshold(overridden) == pytest.approx(3.5)


class TestAccessorsReadTheYamlNotTheDataclassDefaults:
    """``defines.yaml`` is GENERATED from the schema, so every shipped value
    equals its field default by construction — an assertion of the form
    ``accessor() == GameDefines.load_default().x`` is blind to the
    difference between reading the YAML and reading the dataclass defaults.
    This test makes the YAML and the defaults DISAGREE, so only the loader
    path passes (mirrors the capital_vol3 honesty-sweep test estate).
    """

    def test_replacement_boom_ratio_accessor_reads_the_yaml(
        self, divergent_defines_yaml: Callable[..., Path]
    ) -> None:
        from babylon.domain.economics.circulation.types import _legacy as legacy_types

        divergent_defines_yaml(
            {"capital_vol2": {"replacement_boom_ratio": 2.5}},
            legacy_types._default_defines,
        )
        assert legacy_types.replacement_boom_ratio() == pytest.approx(2.5)
        assert GameDefines().capital_vol2.replacement_boom_ratio == pytest.approx(1.5)


class TestCirculationCrisisStateInitialUsesTheAccessor:
    """``CirculationCrisisState.initial()``/``.default()`` (the
    ``default_factory`` for ``CountyEconomicState.circulation_state``) seeds
    a fresh county's inventory days with the same
    ``fallback_days_inventory`` value used for a missing national reading —
    not an independent hardcoded literal that could drift out of sync.
    """

    def test_default_state_inventory_days_match_the_define(self) -> None:
        from babylon.domain.economics.circulation.types import CirculationCrisisState

        state = CirculationCrisisState.default()
        defaults = GameDefines.load_default().capital_vol2
        assert state.inventory_state.days_inventory_raw == pytest.approx(
            defaults.fallback_days_inventory
        )
        assert state.inventory_state.days_inventory_finished == pytest.approx(
            defaults.fallback_days_inventory
        )
        # And it must actually be NORMAL, not an accidental crisis diagnosis.
        from babylon.domain.economics.circulation.types import InventoryDiagnosis

        assert state.inventory_state.inventory_problem == InventoryDiagnosis.NORMAL


class TestAssessCirculationCrisisThresholdParameters:
    """``assess_circulation_crisis``'s two new keyword parameters must
    default to the original hardcoded values (so the pre-existing
    direct-invocation test suite is unaffected) and must actually change
    the outcome when overridden (so they are not orphaned parameters)."""

    def test_defaults_match_the_original_hardcoded_thresholds(self) -> None:
        from babylon.domain.economics.circulation.crisis import assess_circulation_crisis
        from babylon.domain.economics.circulation.types import (
            CircuitState,
            InventoryState,
            TurnoverProfile,
        )
        from babylon.models.types import Currency

        circuit = CircuitState(
            fips_code="26163",
            year=2022,
            money_capital=Currency(400.0),
            productive_capital=Currency(400.0),
            commodity_capital=Currency(200.0),
            fixed_capital=Currency(300.0),
            circulating_capital=Currency(100.0),
        )
        turnover = TurnoverProfile(
            naics_code="31",
            working_period_days=20,
            non_working_production_days=5,
            purchase_time_days=3,
            sale_time_days=7,
            fixed_capital_ratio=0.6,
        )
        inventory = InventoryState(
            fips_code="26163",
            year=2022,
            raw_materials=Currency(50_000.0),
            work_in_progress=Currency(30_000.0),
            finished_goods=Currency(80_000.0),
            days_inventory_raw=15.0,
            days_inventory_finished=30.0,
        )
        result = assess_circulation_crisis(
            circuit_state=circuit,
            turnover=turnover,
            inventory=inventory,
            reproduction_balance=None,
            reproduction_analysis=None,
        )
        assert result.realization_crisis is False  # 0.2 <= default 0.3
        assert result.turnover_crisis is False  # liquidity 0.4 >= default 0.1

        # A tighter threshold flips the realization flag with the SAME inputs.
        tightened = assess_circulation_crisis(
            circuit_state=circuit,
            turnover=turnover,
            inventory=inventory,
            reproduction_balance=None,
            reproduction_analysis=None,
            commodity_overhang_threshold=0.1,
        )
        assert tightened.realization_crisis is True
