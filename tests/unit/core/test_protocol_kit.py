"""Spec 058 / FR-004 — protocol_kit contract tests.

Covers:
  - 8 ``CachedSource[T]`` semantic guarantees from
    ``specs/058-adr-bundle-1-pre-spec-057/contracts/protocol_kit.md``
  - 10 ``SourceRegistry`` semantic guarantees (items 1–10) from
    ``specs/058-adr-bundle-1-pre-spec-057/contracts/source_registry.md``

Items 11–13 of the source_registry.md test contract live in
``tests/unit/economics/test_factory_shims.py`` per the analyze
remediation pass; they verify the ``factory.py`` shim's compatibility
with the SourceRegistry and land GREEN at commit 6.
"""

from __future__ import annotations

import pytest

from babylon.core.protocol_kit import CachedSource, DataSource, SourceRegistry
from babylon.economics.tensor import NoDataSentinel

# ---------------------------------------------------------------------------
# CachedSource[T] — 8 contract tests
# ---------------------------------------------------------------------------


class _CountingFloatSource(CachedSource[float]):
    """Subclass for unit tests; tracks how often `_fetch` is invoked."""

    def __init__(
        self, *, return_value: float | None | NoDataSentinel = 1.0, **kwargs: object
    ) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.return_value = return_value
        self.fetch_count = 0

    def _fetch(self) -> float | None | NoDataSentinel:
        self.fetch_count += 1
        return self.return_value

    def get(self, key: tuple[object, ...]) -> float | NoDataSentinel:
        return self._resolve(key, self._fetch)


class _NegOptOutSource(_CountingFloatSource):
    """Subclass that opts out of negative caching."""

    cache_negative_results: bool = False


@pytest.mark.unit
class TestCachedSource:
    """8 contract tests from contracts/protocol_kit.md."""

    def test_cache_hit_returns_same_instance(self) -> None:
        """Repeat call with same key returns cached value; `_fetch` runs once."""
        src = _CountingFloatSource(return_value=42.0)
        r1 = src.get(("k",))
        r2 = src.get(("k",))
        assert r1 == 42.0
        assert r1 == r2  # values equal
        assert src.fetch_count == 1

    def test_none_from_fetch_becomes_no_data_sentinel(self) -> None:
        """If `_fetch` returns None, `_resolve` wraps it in NoDataSentinel."""
        src = _CountingFloatSource(return_value=None)
        result = src.get(("missing",))
        assert isinstance(result, NoDataSentinel)
        assert bool(result) is False

    def test_negative_cached_by_default(self) -> None:
        """`cache_negative_results=True` (default): NoDataSentinel is cached."""
        src = _CountingFloatSource(return_value=None)
        src.get(("k",))
        src.get(("k",))
        assert src.fetch_count == 1, "negative result MUST be cached by default"

    def test_negative_re_fetched_when_opted_out(self) -> None:
        """`cache_negative_results=False`: NoDataSentinel triggers re-fetch."""
        src = _NegOptOutSource(return_value=None)
        src.get(("k",))
        src.get(("k",))
        assert src.fetch_count == 2, "with cache_negative_results=False, every miss MUST re-fetch"

    def test_invalidate_removes_one_entry(self) -> None:
        """`invalidate(key)` removes the entry; next call re-fetches."""
        src = _CountingFloatSource(return_value=99.0)
        src.get(("k",))
        src.invalidate(("k",))
        src.get(("k",))
        assert src.fetch_count == 2

    def test_clear_removes_all_entries(self) -> None:
        """`clear()` removes every cached entry."""
        src = _CountingFloatSource(return_value=99.0)
        src.get(("a",))
        src.get(("b",))
        src.clear()
        src.get(("a",))
        src.get(("b",))
        assert src.fetch_count == 4

    def test_fifo_eviction_at_max_entries(self) -> None:
        """At `max_entries`, the oldest insert is evicted on next insert."""
        src = _CountingFloatSource(return_value=1.0, max_entries=2)
        src.get(("a",))  # cache: [a]
        src.get(("b",))  # cache: [a, b]
        src.get(("c",))  # cache: [b, c] — a evicted
        # Re-fetching `a` should be a cache miss (evicted)
        before = src.fetch_count
        src.get(("a",))
        assert src.fetch_count == before + 1, "evicted entry MUST re-fetch"

    def test_resolve_never_returns_none(self) -> None:
        """`_resolve` always returns `T | NoDataSentinel`, never None."""
        src = _CountingFloatSource(return_value=None)
        result = src.get(("k",))
        assert result is not None
        assert isinstance(result, NoDataSentinel)


# ---------------------------------------------------------------------------
# SourceRegistry — 10 contract tests (items 1-10 from source_registry.md)
# ---------------------------------------------------------------------------


class _ProtoA:
    """Stand-in protocol class for registry tests (need a hashable type key)."""


class _ImplA:
    pass


class _ImplA2:
    pass


@pytest.mark.unit
class TestSourceRegistry:
    """10 contract tests from contracts/source_registry.md items 1-10."""

    def test_register_and_get(self) -> None:
        """register(P, factory) → get(P) constructs an instance."""
        reg = SourceRegistry()
        reg.register(_ProtoA, _ImplA)
        assert isinstance(reg.get(_ProtoA), _ImplA)

    def test_get_unknown_raises_lookup_error(self) -> None:
        """Unknown (P, variant) → LookupError, not KeyError."""
        reg = SourceRegistry()

        class _NeverRegistered:
            pass

        with pytest.raises(LookupError, match="No 'default' implementation registered"):
            reg.get(_NeverRegistered)

    def test_has_returns_true_for_registered_false_for_unknown(self) -> None:
        reg = SourceRegistry()
        reg.register(_ProtoA, _ImplA)
        assert reg.has(_ProtoA) is True

        class _Unregistered:
            pass

        assert reg.has(_Unregistered) is False

    def test_variant_discrimination(self) -> None:
        """Default and test variants register independently."""
        reg = SourceRegistry()
        reg.register(_ProtoA, _ImplA, variant="default")
        reg.register(_ProtoA, _ImplA2, variant="test")
        assert isinstance(reg.get(_ProtoA), _ImplA)
        assert isinstance(reg.get(_ProtoA, variant="test"), _ImplA2)

    def test_re_registration_replaces_silently(self) -> None:
        """Re-register with same (P, variant) replaces; no warning, no error."""
        reg = SourceRegistry()
        reg.register(_ProtoA, _ImplA)
        reg.register(_ProtoA, _ImplA2)
        assert isinstance(reg.get(_ProtoA), _ImplA2)

    def test_replaced_factory_previous_instances_unaffected(self) -> None:
        """Instances already constructed before re-registration keep working."""
        reg = SourceRegistry()
        reg.register(_ProtoA, _ImplA)
        first_instance = reg.get(_ProtoA)
        reg.register(_ProtoA, _ImplA2)
        # The old instance must still be usable as its original type
        assert isinstance(first_instance, _ImplA)
        assert not isinstance(first_instance, _ImplA2)

    def test_per_call_construction(self) -> None:
        """Two `get(P)` calls return distinct instances (no singleton caching)."""
        reg = SourceRegistry()
        reg.register(_ProtoA, _ImplA)
        a = reg.get(_ProtoA)
        b = reg.get(_ProtoA)
        assert a is not b

    def test_factory_exceptions_propagate(self) -> None:
        """Factory ValueError → re-raised by get; no wrapping."""

        def _explosive_factory() -> object:
            raise ValueError("boom")

        reg = SourceRegistry()
        reg.register(_ProtoA, _explosive_factory)
        with pytest.raises(ValueError, match="boom"):
            reg.get(_ProtoA)

    def test_builtin_economics_returns_self_for_chaining(self) -> None:
        """builtin_economics() MUST return self for fluent chaining."""
        reg = SourceRegistry()
        result = reg.builtin_economics()
        assert result is reg

    def test_builtin_economics_idempotent(self) -> None:
        """Calling builtin_economics() twice does not raise."""
        reg = SourceRegistry()
        reg.builtin_economics().builtin_economics()


# ---------------------------------------------------------------------------
# DataSource — Protocol marker smoke check
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDataSourceProtocol:
    """DataSource is runtime-checkable — sanity check (covers contracts/protocol_kit.md §1)."""

    def test_runtime_checkable_against_object_with_name(self) -> None:
        class _HasName:
            name = "DefaultFooSource"

        assert isinstance(_HasName(), DataSource)

    def test_runtime_checkable_rejects_object_without_name(self) -> None:
        class _NoName:
            pass

        assert not isinstance(_NoName(), DataSource)
