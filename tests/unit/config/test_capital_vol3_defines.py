"""GameDefines.capital_vol3 contract — Volume III financial-claims coefficients.

Honesty sweep (spec 2026-07-18 vol3-money-scissors-design, U2): pins the
defaults migrated off module-level Final constants in distribution/types.py,
counter_tendencies/types.py and credit/types.py — all five now defines-backed
accessor functions (moddability, Constitution III.1).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.config.defines import CapitalVolumeIIIDefines, GameDefines

pytestmark = pytest.mark.unit


class TestCapitalVolumeIIIDefaults:
    def test_defaults_match_migrated_constants(self) -> None:
        d = CapitalVolumeIIIDefines()
        assert d.debt_spiral_threshold == pytest.approx(0.5)
        assert d.distribution_epsilon == pytest.approx(1e-9)
        assert d.counter_tendency_weights == [0.20, 0.15, 0.15, 0.15, 0.20, 0.15]
        assert d.imperial_rent_reference_scale == pytest.approx(500_000_000_000.0)
        assert d.profit_rate_fallback == pytest.approx(0.05)
        assert d.national_county_count == 3300
        assert d.default_rate_estimate == pytest.approx(0.02)
        assert d.housing_capitalization_rate_default == pytest.approx(0.05)

    def test_reachable_from_game_defines(self) -> None:
        defines = GameDefines.load_default()
        assert defines.capital_vol3.debt_spiral_threshold == pytest.approx(0.5)


class TestDebtSpiralThresholdRejectsZero:
    """Review finding (U5.10): ``debt_spiral_threshold`` became a live divisor
    in ``ContradictionSystem._county_money_ratios``
    (``(total_debt / total_surplus) / debt_spiral_threshold``) with no
    in-function guard, mirroring ``credit_fragility_scale``'s own
    ``gt=0.0`` — which exists for exactly this reason (it too is a live
    divisor in the same module). Before U5.10 the field was inert prose and
    ``ge=0.0`` was harmless; a schema-legal 0.0 is now a ``ZeroDivisionError``
    reachable from a single modded ``defines.yaml`` edit on any tick where a
    county carries both a distribution and nonzero accumulated debt. Pinned
    at the schema boundary rather than left to the division site, matching
    ``credit_fragility_scale``'s own precedent in this file.
    """

    def test_zero_is_rejected_at_construction(self) -> None:
        with pytest.raises(ValidationError, match="debt_spiral_threshold"):
            CapitalVolumeIIIDefines(debt_spiral_threshold=0.0)

    def test_shipped_default_survives_the_tightened_constraint(self) -> None:
        assert CapitalVolumeIIIDefines().debt_spiral_threshold == pytest.approx(0.5)


class TestStagnationCreditGrowthIsAnAccessor:
    def test_no_import_time_snapshot_remains(self) -> None:
        """credit/types.py must expose an accessor, not a module-level Final
        snapshot — an import-time snapshot reads defines.yaml on every process
        start and freezes the value before any runtime override can reach it.

        Pinned at source level rather than by importlib.reload: reloading a
        module other already-imported modules hold references to leaves them
        bound to stale class objects, which corrupts sibling tests under the
        xdist workers test:unit runs on.
        """
        from pathlib import Path

        import babylon.domain.economics.credit.types as credit_types

        source = Path(str(credit_types.__file__)).read_text(encoding="utf-8")
        assert "def stagnation_credit_growth(" in source
        assert "STAGNATION_CREDIT_GROWTH" not in source
        assert "GameDefines().crisis.stagnation_credit_growth" not in source

    def test_value_matches_the_canonical_yaml(self) -> None:
        from babylon.domain.economics.credit.types import stagnation_credit_growth

        assert stagnation_credit_growth() == pytest.approx(
            GameDefines.load_default().crisis.stagnation_credit_growth
        )

    def test_explicit_defines_override_is_honoured(self) -> None:
        """The whole point of the accessor: a caller-supplied GameDefines wins."""
        from babylon.domain.economics.credit.types import stagnation_credit_growth

        base = GameDefines.load_default()
        overridden = base.model_copy(
            update={"crisis": base.crisis.model_copy(update={"stagnation_credit_growth": 0.123})}
        )
        assert stagnation_credit_growth(overridden) == pytest.approx(0.123)


class TestCounterTendencyWeightsAreConstrainedAtTheSchemaBoundary:
    """Migrating the weights off a module-level ``Final`` made them
    player-editable — and therefore able to be *wrong*.

    The sole consumer zips them against a fixed six-element indicator list with
    ``strict=True`` inside a ``@computed_field``, so a wrong-length list from
    ``defines.yaml`` used to surface as an opaque ``ValueError: zip() argument
    2 is shorter than argument 1`` on every attribute access and every
    ``model_dump()`` mid-tick, and a list summing to anything other than 1.0
    silently rescaled the whole TRPF counter-tendency signal with no diagnostic
    at all. Both now fail loudly at config-load time (Constitution III.11).
    """

    def test_short_weight_list_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="counter_tendency_weights"):
            CapitalVolumeIIIDefines(counter_tendency_weights=[0.2, 0.2, 0.2, 0.2, 0.2])

    def test_long_weight_list_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="counter_tendency_weights"):
            CapitalVolumeIIIDefines(
                counter_tendency_weights=[0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.10]
            )

    def test_weights_not_summing_to_one_are_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must sum to 1.0"):
            CapitalVolumeIIIDefines(counter_tendency_weights=[0.9, 0.9, 0.9, 0.9, 0.9, 0.9])

    def test_error_names_the_yaml_key_and_the_observed_sum(self) -> None:
        """A modder needs to know WHICH key and WHAT it summed to."""
        with pytest.raises(ValidationError) as excinfo:
            CapitalVolumeIIIDefines(counter_tendency_weights=[0.25, 0.25, 0.25, 0.25, 0.25, 0.25])
        message = str(excinfo.value)
        assert "capital_vol3.counter_tendency_weights" in message
        assert "1.5" in message

    def test_shipped_default_survives_the_constraint(self) -> None:
        """The migrated default must not be rejected by its own validator."""
        assert CapitalVolumeIIIDefines().counter_tendency_weights == [
            0.20,
            0.15,
            0.15,
            0.15,
            0.20,
            0.15,
        ]


class TestAccessorsReadTheYamlNotTheDataclassDefaults:
    """``defines.yaml`` is GENERATED from the schema, so every shipped value
    equals its field default by construction — and ``test_constants_sync.py``
    enforces ``GameDefines.load_default() == GameDefines()`` on every run.

    Every other assertion in this estate compares an accessor to
    ``GameDefines.load_default().<field>``, which is therefore blind to the
    difference between reading the YAML and reading the dataclass defaults:
    respelling ``load_default()`` as a bare ``GameDefines()`` — the exact
    import-time-defaults defect U2.3 removed from
    ``credit/types.py`` — leaves the whole suite green. These tests make the
    YAML and the defaults DISAGREE, so only the loader path passes.
    """

    def test_credit_accessor_reads_the_yaml(
        self, divergent_defines_yaml: Callable[..., Path]
    ) -> None:
        from babylon.domain.economics.credit import types as credit_types

        divergent_defines_yaml(
            {"crisis": {"stagnation_credit_growth": 0.077}},
            credit_types._default_defines,
        )
        assert credit_types.stagnation_credit_growth() == pytest.approx(0.077)
        assert GameDefines().crisis.stagnation_credit_growth == pytest.approx(0.01)

    def test_distribution_accessors_read_the_yaml(
        self, divergent_defines_yaml: Callable[..., Path]
    ) -> None:
        from babylon.domain.economics.distribution import types as distribution_types

        divergent_defines_yaml(
            {"capital_vol3": {"debt_spiral_threshold": 0.77, "distribution_epsilon": 1e-6}},
            distribution_types._default_defines,
        )
        assert distribution_types.debt_spiral_threshold() == pytest.approx(0.77)
        assert distribution_types.distribution_epsilon() == pytest.approx(1e-6)

    def test_counter_tendency_accessors_read_the_yaml(
        self, divergent_defines_yaml: Callable[..., Path]
    ) -> None:
        from babylon.domain.economics.counter_tendencies import types as ct_types

        divergent_defines_yaml(
            {
                "capital_vol3": {
                    "counter_tendency_weights": [0.5, 0.1, 0.1, 0.1, 0.1, 0.1],
                    "imperial_rent_reference_scale": 1_000.0,
                }
            },
            ct_types._default_defines,
        )
        assert ct_types.counter_tendency_weights() == [0.5, 0.1, 0.1, 0.1, 0.1, 0.1]
        assert ct_types.imperial_rent_reference_scale() == pytest.approx(1_000.0)


class TestCoefficientDescriptionsDoNotNameAbsentMechanisms:
    """Finding U2.3-2: never document a feature that does not exist in code.

    U5.10 wired ``debt_spiral_threshold`` into
    ``ContradictionSystem._county_money_ratios`` as a live divisor, so the
    description must now describe that live behaviour rather than continue
    to claim the field is unread (Constitution III.11 in the other
    direction: a stale "not yet read" claim is exactly as dishonest as a
    fabricated feature once the consumer lands).

    Pinned as a contract rather than left to review: the description is the
    only thing a modder reads before spending an evening on a knob.
    """

    def test_debt_spiral_threshold_description_declares_it_live(self) -> None:
        field = CapitalVolumeIIIDefines.model_fields["debt_spiral_threshold"]
        description = field.description or ""
        assert "NOT YET READ" not in description, (
            "debt_spiral_threshold has been live since U5.10 "
            "(ContradictionSystem._county_money_ratios divides by it); the "
            "description must not still claim it changes nothing in the "
            "shipped game"
        )
        assert "contradiction.py" in description or "debt_spiral" in description

    def test_credit_fragility_threshold_is_calibrated_for_decimal_inputs(self) -> None:
        """The predicate must be reachable on real FRED data.

        ``credit_fragility = default_rate * credit_spread > threshold``.
        ``credit_spread`` carries FRED BAA10Y as a DECIMAL (factory.py
        divides the percent series by 100), peaking at 0.0556 in Dec 2008.
        With the documented 0.02 default-rate estimate the peak product is
        1.11e-3, so any threshold at or above that is unreachable in every
        modeled year.
        """
        d = CapitalVolumeIIIDefines()
        peak_product = d.default_rate_estimate * 0.0556
        assert d.credit_fragility_threshold < peak_product, (
            f"credit_fragility_threshold {d.credit_fragility_threshold} is not "
            f"crossable by the 2008-peak product {peak_product} — the signal "
            "is hardwired False for every county in every year"
        )
        calm_product = d.default_rate_estimate * 0.018
        assert d.credit_fragility_threshold > calm_product, (
            f"credit_fragility_threshold {d.credit_fragility_threshold} fires "
            f"even on a calm-year product {calm_product} — a signal that is "
            "always True is as uninformative as one that is never True"
        )
