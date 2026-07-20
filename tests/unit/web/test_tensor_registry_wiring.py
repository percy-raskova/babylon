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

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

pytestmark = pytest.mark.unit

WAYNE_FIPS = "26163"


class TestEconomicsCacheHygiene:
    """PR #209 Copilot review, both findings on the module caches.

    (a) ``_build_tensor_registry`` caches by ``frozenset(fips_codes)`` but
        hydrated ``sorted(fips_codes)`` — duplicate FIPS in the tuple made
        the hydration work diverge from the cache key.
    (b) ``_TENSOR_REGISTRY_CACHE``/``_CAPITAL_CALCULATOR_CACHE`` grew without
        bound: one hydrated registry retained per distinct FIPS-set for the
        life of the process.

    No reference DB here: hydration is stubbed and the stub records the
    county list each call receives, which is the very thing under test.
    """

    @pytest.fixture(autouse=True)
    def _isolated_caches(self) -> Iterator[None]:
        from game import engine_bridge

        saved_registries = dict(engine_bridge._TENSOR_REGISTRY_CACHE)
        saved_calculators = dict(engine_bridge._CAPITAL_CALCULATOR_CACHE)
        engine_bridge._TENSOR_REGISTRY_CACHE.clear()
        engine_bridge._CAPITAL_CALCULATOR_CACHE.clear()
        yield
        engine_bridge._TENSOR_REGISTRY_CACHE.clear()
        engine_bridge._TENSOR_REGISTRY_CACHE.update(saved_registries)
        engine_bridge._CAPITAL_CALCULATOR_CACHE.clear()
        engine_bridge._CAPITAL_CALCULATOR_CACHE.update(saved_calculators)

    @pytest.fixture()
    def hydrated_county_lists(self, monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
        """Stub the DB seam; return the counties list each hydration received."""
        import babylon.reference.database as reference_database
        from babylon.domain.economics.tensor_registry import TensorRegistry

        calls: list[list[str]] = []

        def record_hydration(
            self: TensorRegistry, hydrator: Any, counties: list[str], years: list[int]
        ) -> None:
            del hydrator, years
            calls.append(list(counties))

        @contextmanager
        def no_session() -> Iterator[None]:
            yield None

        monkeypatch.setattr(TensorRegistry, "hydrate_counties", record_hydration)
        monkeypatch.setattr(reference_database, "get_reference_session", no_session)
        return calls

    def test_duplicate_fips_hydrate_the_deduped_key(
        self, hydrated_county_lists: list[list[str]]
    ) -> None:
        from game.engine_bridge import _build_tensor_registry

        _build_tensor_registry(("26163", "26099", "26163"))

        # Hydration must cover exactly the deduped, sorted cache key —
        # a duplicate county in the tuple is one hydration, not two.
        assert hydrated_county_lists == [["26099", "26163"]]

    def test_registry_cache_is_bounded_fifo(self, hydrated_county_lists: list[list[str]]) -> None:
        from game import engine_bridge

        cap = engine_bridge._ECONOMICS_CACHE_MAX
        keys = [(f"{10000 + i:05d}",) for i in range(cap + 3)]
        for key in keys:
            engine_bridge._build_tensor_registry(key)

        assert len(engine_bridge._TENSOR_REGISTRY_CACHE) == cap
        assert frozenset(keys[0]) not in engine_bridge._TENSOR_REGISTRY_CACHE  # oldest evicted
        assert frozenset(keys[-1]) in engine_bridge._TENSOR_REGISTRY_CACHE

    def test_calculator_cache_is_bounded_fifo(self, hydrated_county_lists: list[list[str]]) -> None:
        from game import engine_bridge

        cap = engine_bridge._ECONOMICS_CACHE_MAX
        keys = [(f"{20000 + i:05d}",) for i in range(cap + 3)]
        for key in keys:
            engine_bridge._build_capital_calculator(key)

        assert len(engine_bridge._CAPITAL_CALCULATOR_CACHE) == cap
        assert frozenset(keys[0]) not in engine_bridge._CAPITAL_CALCULATOR_CACHE
        assert frozenset(keys[-1]) in engine_bridge._CAPITAL_CALCULATOR_CACHE


@pytest.mark.requires_reference_db
class TestBridgeEconomicsOverridesWiresTensorRegistry:
    """``_bridge_economics_overrides`` must expose a real ``tensor_registry``."""

    def test_overrides_include_a_hydrated_tensor_registry(self) -> None:
        from babylon.domain.economics.tensor import NoDataSentinel
        from game.engine_bridge import _bridge_economics_overrides

        overrides, leontief_session = _bridge_economics_overrides((WAYNE_FIPS,))
        try:
            assert "tensor_registry" in overrides
            registry = overrides["tensor_registry"]
            assert WAYNE_FIPS in registry.all_fips()

            # Pin real content, not just a key in the cache: all_fips() is
            # derived from _county_cache, which hydrate_counties() populates
            # on BOTH success (put) and failure (put_sentinel in the bare
            # except). A silently-degraded hydration (reference-DB path
            # change, table/column rename, NAICS YAML drift) would still
            # pass the all_fips() check above with every county-year a
            # NoDataSentinel — this assertion is the one that would catch it.
            tensor = registry.get(WAYNE_FIPS, 2022)
            assert not isinstance(tensor, NoDataSentinel), getattr(tensor, "reason", "")
            assert tensor.total_s > 0.0  # the field _get_county_surplus actually reads
            assert len(registry.available_years(WAYNE_FIPS)) == 15
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
