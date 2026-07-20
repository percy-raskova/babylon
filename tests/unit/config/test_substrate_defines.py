"""SubstrateDefines contract (#39 T6) — raw_material_stock coefficients."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.config.defines import SubstrateDefines

pytestmark = pytest.mark.unit


class TestSubstrateDefaults:
    def test_defaults(self) -> None:
        d = SubstrateDefines()
        assert d.depletion_scale == 1.0
        assert d.regeneration_rate == 0.0
        assert d.entropy_factor == 1.2

    def test_regeneration_defaults_to_zero_nonrenewable(self) -> None:
        """Minerals are non-renewable by default; not a fudge factor."""
        assert SubstrateDefines().regeneration_rate == 0.0


class TestSubstrateBounds:
    def test_depletion_scale_rejects_negative(self) -> None:
        with pytest.raises(ValidationError):
            SubstrateDefines(depletion_scale=-1.0)

    def test_depletion_scale_capped(self) -> None:
        with pytest.raises(ValidationError):
            SubstrateDefines(depletion_scale=10.1)

    def test_regeneration_rate_bounded_to_unit_interval(self) -> None:
        with pytest.raises(ValidationError):
            SubstrateDefines(regeneration_rate=1.1)

    def test_entropy_factor_must_exceed_one(self) -> None:
        """Extraction must cost more than it yields (thermodynamic floor)."""
        with pytest.raises(ValidationError):
            SubstrateDefines(entropy_factor=1.0)

    def test_entropy_factor_capped(self) -> None:
        with pytest.raises(ValidationError):
            SubstrateDefines(entropy_factor=3.1)
