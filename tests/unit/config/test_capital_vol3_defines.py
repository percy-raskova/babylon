"""GameDefines.capital_vol3 contract — Volume III financial-claims coefficients.

Honesty sweep (spec 2026-07-18 vol3-money-scissors-design, U2): pins the
defaults migrated off module-level Final constants in distribution/types.py,
counter_tendencies/types.py and credit/types.py — all five now defines-backed
accessor functions (moddability, Constitution III.1).
"""

from __future__ import annotations

import pytest

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
