"""FR-029a startup invariant test (T052).

Initialization MUST raise InitializationError when alpha_weekly >= 1/52.
The invariant is checked by
:func:`babylon.persistence.postgres_initialization._validate_alpha_invariant`
against ``GameDefines.economy.alpha_weekly``.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from babylon.config.defines import GameDefines
from babylon.persistence.postgres_initialization import (
    InitializationError,
    _validate_alpha_invariant,
)


@pytest.mark.cross_scale
class TestAlphaWeeklyInvariant:
    def test_default_alpha_passes_invariant(self) -> None:
        # Default alpha_annual=0.01 -> alpha_weekly ≈ 1.93e-4 < 1/52 ≈ 1.92e-2.
        defines = GameDefines()
        assert defines.economy.alpha_weekly < 1.0 / 52.0
        _validate_alpha_invariant(defines)  # no raise

    def test_oversized_alpha_raises(self) -> None:
        # alpha_annual large enough to push alpha_weekly above 1/52.
        bad = GameDefines.model_validate(
            {
                **GameDefines().model_dump(),
                "economy": {
                    **GameDefines().economy.model_dump(),
                    "alpha_annual": 0.7,
                },
            }
        )
        assert bad.economy.alpha_weekly >= 1.0 / 52.0
        with pytest.raises(InitializationError, match="FR-029a"):
            _validate_alpha_invariant(bad)

    def test_session_id_not_required_for_invariant_check(self) -> None:
        """The check is on defines alone, not session state."""
        _ = uuid4()  # session_id not referenced
        defines = GameDefines()
        _validate_alpha_invariant(defines)
