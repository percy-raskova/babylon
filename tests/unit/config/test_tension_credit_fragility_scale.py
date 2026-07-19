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
        # FRED BAA-AAA spread * Moody's default rate: the product exceeded
        # 0.02 during the 2008 crisis (CREDIT_FRAGILITY_THRESHOLD's own
        # derivation, domain/economics/credit/types.py).
        assert GameDefines().capital_vol3.credit_fragility_scale == pytest.approx(0.02)

    def test_must_be_positive(self) -> None:
        from pydantic import ValidationError

        from babylon.config.defines import CapitalVolumeIIIDefines

        with pytest.raises(ValidationError):
            CapitalVolumeIIIDefines(credit_fragility_scale=0.0)

    def test_the_shipped_yaml_carries_it(self) -> None:
        loaded = GameDefines.load_default()
        assert loaded.capital_vol3.credit_fragility_scale > 0.0

    def test_a_yaml_edit_reaches_the_engine(self) -> None:
        modded = GameDefines(
            capital_vol3=GameDefines().capital_vol3.model_copy(
                update={"credit_fragility_scale": 0.04}
            )
        )
        assert modded.capital_vol3.credit_fragility_scale == pytest.approx(0.04)
