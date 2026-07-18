"""U1 (vol3-money-scissors): wire tensor_registry into the web bridge.

Before this fix, _bridge_economics_overrides built a TensorRegistry only
inside _build_capital_calculator, wrapped it in a CapitalStockCalculator, and
discarded the registry itself — services.tensor_registry stayed None for
every web session, so `_get_county_surplus`/`_get_county_profit_rate`
(domain/economics/tick/system/__init__.py:1547,1599) always returned None,
and surplus_distribution (s = p + i + r + t) never computed for the playable
game (design doc §1.1, "Vol III county layer: national only").

_build_tensor_registry is factored out of _build_capital_calculator so BOTH
capital_calculator and the standalone tensor_registry override share ONE
hydration pass over the reference DB, not two.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

WAYNE_FIPS = "26163"


@pytest.mark.requires_reference_db
class TestBridgeEconomicsOverridesWiresTensorRegistry:
    """``_bridge_economics_overrides`` must expose a real ``tensor_registry``."""

    def test_overrides_include_a_hydrated_tensor_registry(self) -> None:
        from game.engine_bridge import _bridge_economics_overrides

        overrides, leontief_session = _bridge_economics_overrides((WAYNE_FIPS,))
        try:
            assert "tensor_registry" in overrides
            assert WAYNE_FIPS in overrides["tensor_registry"].all_fips()
        finally:
            if leontief_session is not None:
                leontief_session.close()

    def test_tensor_registry_is_shared_with_the_capital_calculator(self) -> None:
        """DRY: one hydration pass backs both capital_calculator._registry
        and the standalone tensor_registry override — not two DB round-trips."""
        from game.engine_bridge import _bridge_economics_overrides

        overrides, leontief_session = _bridge_economics_overrides((WAYNE_FIPS,))
        try:
            assert overrides["tensor_registry"] is overrides["capital_calculator"]._registry
        finally:
            if leontief_session is not None:
                leontief_session.close()
