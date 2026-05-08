"""Shared scaffolding for the Protocol + ``Default*`` data-source pattern.

Spec 058 (Bundle 1, FR-004) — see ``contracts/protocol_kit.md`` and
``contracts/source_registry.md`` for the full semantic contracts.

Three primitives:

  - :class:`DataSource` — runtime-checkable Protocol marker; any source-style
    Protocol that wants to be discoverable via ``isinstance(impl, DataSource)``
    inherits from this marker.

  - :class:`CachedSource` — Generic ABC mixin providing LRU + ``NoDataSentinel``
    handling. Subclasses implement a ``_fetch`` method and call
    :meth:`CachedSource._resolve` from their public lookup methods.

  - :class:`SourceRegistry` — type-keyed registry replacing the four
    ``create_*_services()`` functions in ``economics/factory.py`` (commit 6).

Per the 2026-05-08 Q4 clarification: ``CachedSource[T]`` caches
``NoDataSentinel`` results by default; subclasses opt out by setting
``cache_negative_results = False`` at class level (correct for sources whose
missing-data signal is *transient* — DPD lifecycle, MELT recomputation, etc.).
"""

from __future__ import annotations

from collections.abc import Callable, Hashable
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    # Lazy import only at type-check time. The runtime import lives inside
    # CachedSource._resolve to break the import cycle that arises once the
    # 10 melt+gamma Default* classes inherit from CachedSource[T] (their
    # package __init__.py would otherwise re-enter protocol_kit before its
    # module body finishes loading).
    from babylon.economics.tensor import NoDataSentinel

__all__ = ["CachedSource", "DataSource", "SourceRegistry"]


@runtime_checkable
class DataSource(Protocol):
    """Marker protocol: every source has a ``name`` for registry diagnostics.

    All source Protocols in ``babylon.economics.*.data_sources`` and
    ``babylon.infrastructure.*.data_sources`` SHOULD inherit from this marker
    so that :class:`SourceRegistry` and downstream consumers can identify
    them via ``isinstance(impl, DataSource)``.

    The ``name`` attribute is for diagnostics (logging, registry error
    messages); it is NOT used as a registry key (the Protocol type itself
    is the key).
    """

    name: str


class CachedSource[T]:
    """LRU + ``NoDataSentinel``-aware base for ``Default*`` data sources.

    Subclasses implement a ``_fetch`` method (any signature) and call
    :meth:`_resolve` from their public lookup methods to get cached values.

    Per Spec 058 / Q4: ``NoDataSentinel`` results are cached by default.
    Subclasses whose missing-data semantics are *transient* (DPD lifecycle,
    MELT recomputation, sources whose ``_fetch`` consumes still-pending output
    from another derivation pass) opt out by setting::

        class DefaultFooSource(CachedSource[float]):
            cache_negative_results = False
            ...

    See ``specs/058-adr-bundle-1-pre-spec-057/contracts/protocol_kit.md`` for
    the full contract and 8 acceptance tests.
    """

    cache_negative_results: bool = True
    """When True (default): cache NoDataSentinel results. When False: re-fetch on every miss."""

    def __init__(self, *, max_entries: int = 1024) -> None:
        if max_entries < 1:
            raise ValueError(f"CachedSource max_entries must be >= 1, got {max_entries}")
        self._cache: dict[Hashable, T | NoDataSentinel] = {}
        self._max_entries = max_entries

    def _resolve(
        self,
        key: Hashable,
        fetch: Callable[[], T | NoDataSentinel | None],
    ) -> T | NoDataSentinel:
        """LRU-cached resolution with NoDataSentinel handling.

        Cache hit: returns the cached value (real or NoDataSentinel) without
        re-invoking ``fetch``.

        Cache miss: calls ``fetch()``. The returned value is one of:
          - ``T`` (real value) → cache and return
          - :class:`NoDataSentinel` (subclass-constructed) → cache per
            :attr:`cache_negative_results` and return as-is
          - ``None`` → wrap in a synthetic ``NoDataSentinel`` (with placeholder
            fips/year and ``reason = f"no data for {key}"``) and cache per
            :attr:`cache_negative_results`

        FIFO eviction at :attr:`_max_entries`.
        """
        # Lazy import — see TYPE_CHECKING comment at module top for circular-
        # import context. Python caches the import; runtime cost is negligible.
        from babylon.economics.tensor import NoDataSentinel

        if key in self._cache:
            return self._cache[key]

        value = fetch()
        result: T | NoDataSentinel
        if value is None:
            # Synthesize a NoDataSentinel with placeholder fips/year — subclasses
            # that need real fips/year should construct NoDataSentinel themselves
            # in _fetch and return it directly.
            result = NoDataSentinel(
                fips=str(key) if not isinstance(key, tuple) else "<unknown>",
                year=0,
                reason=f"no data for {key!r}",
            )
        elif isinstance(value, NoDataSentinel):
            result = value
        else:
            result = value

        # Negative-cache opt-out: don't cache NoDataSentinel if disabled
        if isinstance(result, NoDataSentinel) and not self.cache_negative_results:
            return result

        # FIFO eviction at capacity
        if len(self._cache) >= self._max_entries:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = result
        return result

    def invalidate(self, key: Hashable) -> None:
        """Drop one cache entry. No-op if key is not present."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Drop the entire cache."""
        self._cache.clear()


class SourceRegistry:
    """Type-keyed registry for Protocol implementations.

    Replaces the four ``create_*_services()`` functions in
    ``babylon/economics/factory.py`` (Spec 058 / FR-006, commit 6).

    Lookup by Protocol type + (optional) variant name. Tests use
    ``variant="test"`` substitution to swap implementations cleanly.

    See ``specs/058-adr-bundle-1-pre-spec-057/contracts/source_registry.md``
    for the full contract and 13 acceptance tests.
    """

    DEFAULT_VARIANT = "default"
    TEST_VARIANT = "test"

    def __init__(self) -> None:
        self._impls: dict[tuple[type, str], Callable[[], object]] = {}

    def register(
        self,
        protocol: type,
        factory: Callable[[], object],
        *,
        variant: str = DEFAULT_VARIANT,
    ) -> None:
        """Register a factory for a Protocol type.

        Re-registration with the same ``(protocol, variant)`` silently replaces.
        Already-constructed instances from the prior factory are NOT invalidated.
        Tests that need a clean slate SHOULD construct a fresh ``SourceRegistry``.
        """
        self._impls[(protocol, variant)] = factory

    def get(self, protocol: type, *, variant: str = DEFAULT_VARIANT) -> object:
        """Look up and construct an implementation.

        Each call constructs a fresh instance via the registered factory.
        Callers that need a singleton MUST cache the instance themselves.

        Raises:
            LookupError: if no factory is registered for ``(protocol, variant)``.
        """
        try:
            factory = self._impls[(protocol, variant)]
        except KeyError as exc:
            raise LookupError(
                f"No {variant!r} implementation registered for {protocol.__name__}"
            ) from exc
        return factory()

    def has(self, protocol: type, *, variant: str = DEFAULT_VARIANT) -> bool:
        """Check whether a factory is registered without constructing it."""
        return (protocol, variant) in self._impls

    def builtin_economics(self) -> SourceRegistry:
        """Register the parameterless subset of migrated ``melt/`` + ``gamma/``
        ``Default*`` classes.

        Per Spec 058 / FR-006 / commit 6 (the SC-004-reformulation pass): only
        the 7 classes whose constructors take no required arguments (or
        all-default arguments) can be registered against the
        ``Callable[[], object]`` factory contract. The remaining 3 dep-laden
        classes (``DefaultMELTCalculator``, ``DefaultRentDifferentialCalculator``,
        ``DefaultGammaIIICalculator``) require explicit topological dependency
        resolution and stay constructed in :mod:`babylon.economics.factory`.

        See ``factory.py`` and the SC-004 not-met-by-design note in
        ``specs/058-adr-bundle-1-pre-spec-057/plan.md`` §R5 for the rationale.

        Returns ``self`` for fluent chaining: ``SourceRegistry().builtin_economics()``.
        """
        # Imports kept inside the method to keep `core/` package free of any
        # downstream-domain dependency at import time, and to avoid the
        # protocol_kit-circular-import we resolved in commit 5.
        from babylon.economics.gamma.gamma_basket import (
            DefaultGammaBasketCalculator,
            GammaBasketCalculator,
        )
        from babylon.economics.gamma.gamma_import import (
            DefaultGammaImportCalculator,
            GammaImportCalculator,
        )
        from babylon.economics.gamma.shadow_subsidy import (
            DefaultShadowSubsidyCalculator,
            ShadowSubsidyCalculator,
        )
        from babylon.economics.melt.basket_visibility import (
            BasketVisibilityCalculator,
            DefaultBasketVisibilityCalculator,
        )
        from babylon.economics.melt.class_position import (
            ClassPositionClassifier,
            DefaultClassPositionClassifier,
        )
        from babylon.economics.melt.unified_classifier import (
            DefaultUnifiedClassifier,
            UnifiedClassifier,
        )
        from babylon.economics.melt.wealth_proxy import (
            DefaultWealthProxyCalculator,
            WealthProxyCalculator,
        )

        # 7 registrations — parameterless / all-default-args Default* classes
        self.register(BasketVisibilityCalculator, DefaultBasketVisibilityCalculator)
        self.register(ClassPositionClassifier, DefaultClassPositionClassifier)
        self.register(UnifiedClassifier, DefaultUnifiedClassifier)
        self.register(WealthProxyCalculator, DefaultWealthProxyCalculator)
        self.register(GammaBasketCalculator, DefaultGammaBasketCalculator)
        self.register(GammaImportCalculator, DefaultGammaImportCalculator)
        self.register(ShadowSubsidyCalculator, DefaultShadowSubsidyCalculator)
        return self
