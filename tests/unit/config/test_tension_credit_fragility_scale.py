"""The credit-fragility reference scale is a player-editable define.

``GraphInputs.credit_fragility`` reaches the defines-free catalog already
divided by this reference, so the shared ratio map's balance crosses zero
exactly AT the crisis threshold. Hardcoding the divisor in the engine would
be a Constitution III.1 violation and would make the credit opposition
unmoddable.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines

pytestmark = pytest.mark.unit


class TestCreditFragilityScale:
    def test_default_matches_the_material_crisis_threshold(self) -> None:
        # The engine computes credit_fragility = raw / credit_fragility_scale
        # and the shared ratio map crosses zero at x=1, so 1.0 must mean
        # "exactly at the crisis threshold". That only holds if this scale
        # equals credit_fragility_threshold — the same raw
        # (default_rate * spread) product IS the threshold
        # (capital_vol3.credit_fragility_threshold's own derivation). Assert
        # the cross-field invariant, not a duplicated literal, so a future
        # edit that breaks the identity fails loudly.
        vol3 = GameDefines().capital_vol3
        assert vol3.credit_fragility_scale == pytest.approx(vol3.credit_fragility_threshold)

    def test_must_be_positive(self) -> None:
        from pydantic import ValidationError

        from babylon.config.defines import CapitalVolumeIIIDefines

        with pytest.raises(ValidationError):
            CapitalVolumeIIIDefines(credit_fragility_scale=0.0)

    def test_the_shipped_yaml_carries_it(self) -> None:
        loaded = GameDefines.load_default()
        assert loaded.capital_vol3.credit_fragility_scale > 0.0

    def test_a_yaml_edit_reaches_the_engine(self) -> None:
        # Route the mod through real validation (model_validate on a full
        # field dump), not model_copy(update=...) — under this model's
        # frozen config, model_copy(update=...) writes straight into
        # __dict__ without validating that the key names a declared field,
        # so it would pass even if credit_fragility_scale were renamed or
        # deleted. model_validate on a dict runs full field validation, so a
        # missing/renamed field surfaces as a real error instead.
        from babylon.config.defines import CapitalVolumeIIIDefines

        base = GameDefines()
        modded_vol3 = CapitalVolumeIIIDefines.model_validate(
            {**base.capital_vol3.model_dump(), "credit_fragility_scale": 0.04}
        )
        modded = GameDefines(capital_vol3=modded_vol3)
        assert modded.capital_vol3.credit_fragility_scale == pytest.approx(0.04)
