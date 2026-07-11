"""Year-scoped reference-series lookup (Spec 062, US2).

Implements :class:`ImmutableReferenceLookup` per
``contracts/reference_series.yaml``. Each immutable_reference_* series is
queried for the current simulated year and interpolated (or step-evaluated)
per the policy registered in
:attr:`babylon.config.defines.EconomyDefines.coefficient_lookup_policies`.

FR-012: ``SLOWLY_VARYING`` series linearly interpolate across the 52 weeks
of the simulated year.

FR-013: ``EVENT_DISCRETE`` series step-evaluate: tick ``t`` reads the value
for ``start_year + (t // 52)``.

FR-016: out-of-range lookups (year > end_year) clamp to the last available
year and emit a one-time warning per ``(session_id, series_id)`` pair.

FR-041 (T038b): below-range lookups (year < start_year) clamp to the
earliest available year, set ``lookup_method='clamped_to_earliest'``, and
emit a ``severity='warn'`` audit row via the per-tick audit pipeline.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from babylon.persistence import PostgresRuntime


class LookupMethod(StrEnum):
    """How a reference value was obtained for the requested tick."""

    EXACT_YEAR = "exact_year"
    LINEAR_INTERPOLATED = "linear_interpolated"
    CLAMPED_TO_LAST = "clamped_to_last"
    CLAMPED_TO_EARLIEST = "clamped_to_earliest"


@dataclass
class ReferenceLookupResult:
    """Result of one :meth:`ImmutableReferenceLookup.get` call.

    Attributes:
        value: Numeric (or matrix-shaped) coefficient value.
        simulated_year: The year computed from ``start_year + (tick // 52)``.
        lookup_method: How the value was obtained (see :class:`LookupMethod`).
        bracketing_years: Years bracketing the interpolation. Length 1 for
            exact_year / clamped_to_last / clamped_to_earliest, length 2 for
            linear_interpolated.
        warning_emitted: True if a one-shot warning was emitted for this series.
    """

    value: float
    simulated_year: int
    lookup_method: LookupMethod
    bracketing_years: tuple[int, ...]
    warning_emitted: bool = False


class ImmutableReferenceLookup:
    """Read-only typed-protocol facade for immutable_reference_* tables.

    Spec 062 — FR-011..FR-013 + FR-016 + FR-041. One instance per session;
    caches the per-session out-of-range warning so the user sees each
    warning at most once even across many ticks.

    Parameters:
        runtime: Underlying PostgresRuntime.
        session_id: Session UUID.
        start_year: Earliest year the session has reference data for.
        end_year: Latest year the session has reference data for (inclusive).
    """

    def __init__(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        start_year: int,
        end_year: int,
    ) -> None:
        self._runtime = runtime
        self._session_id = session_id
        self._start_year = start_year
        self._end_year = end_year
        self._warned: set[tuple[UUID, str]] = set()

    # ─────────────────────── public API ────────────────────────────

    def get(
        self,
        series_id: str,
        tick: int,
        *,
        policy: str | None = None,
        value_provider: Any | None = None,
    ) -> ReferenceLookupResult:
        """Return the policy-correct value for ``series_id`` at ``tick``.

        Args:
            series_id: Stable series identifier.
            tick: Simulation tick (>= 0).
            policy: Override the registered policy. Either
                ``"slowly_varying"`` or ``"event_discrete"``. When None,
                falls back to the GameDefines registry (set on the runtime).
            value_provider: Optional callable ``(series_id, year) -> float``
                that returns the raw annual value. When None the lookup is
                expected to read from Postgres; for the MVP the caller
                supplies a provider so the policy dispatch can be exercised
                without a live database.
        """
        from babylon.domain.economics.coefficient_lookup import LookupPolicy

        simulated_year, week_index = self._tick_to_year_and_week(tick)
        resolved_policy = self._resolve_policy(series_id, policy)

        # Clamp to series coverage range first.
        if simulated_year < self._start_year:
            return self._clamped_to_earliest(series_id, simulated_year, value_provider)
        if simulated_year > self._end_year:
            return self._clamped_to_last(series_id, simulated_year, value_provider)

        if resolved_policy is LookupPolicy.SLOWLY_VARYING and week_index != 0:
            return self._linear_interp(series_id, simulated_year, week_index, value_provider)

        return self._exact_year(series_id, simulated_year, value_provider)

    def list_copied_years(self, series_id: str) -> tuple[int, int]:  # noqa: ARG002
        """Return ``(start_year, end_year)`` for this session's copy of the series."""
        return (self._start_year, self._end_year)

    # ─────────────────────── helpers ────────────────────────────────

    def _tick_to_year_and_week(self, tick: int) -> tuple[int, int]:
        if tick < 0:
            raise ValueError(f"tick must be >= 0, got {tick}")
        return self._start_year + (tick // 52), tick % 52

    def _resolve_policy(self, series_id: str, override: str | None) -> Any:
        from babylon.domain.economics.coefficient_lookup import LookupPolicy

        if override is not None:
            return LookupPolicy(override)
        # Fallback: read from runtime's defines registry if available.
        registry: dict[str, Any] = getattr(self._runtime, "_lookup_policy_registry", {})
        descriptor = registry.get(series_id)
        if descriptor is None:
            # Sensible default: economic aggregates are slowly varying.
            return LookupPolicy.SLOWLY_VARYING
        return descriptor.policy

    def _exact_year(
        self, series_id: str, year: int, value_provider: Any | None
    ) -> ReferenceLookupResult:
        value = self._fetch_value(series_id, year, value_provider)
        return ReferenceLookupResult(
            value=value,
            simulated_year=year,
            lookup_method=LookupMethod.EXACT_YEAR,
            bracketing_years=(year,),
        )

    def _linear_interp(
        self,
        series_id: str,
        year: int,
        week_index: int,
        value_provider: Any | None,
    ) -> ReferenceLookupResult:
        v_lo = self._fetch_value(series_id, year, value_provider)
        # Year + 1 may exceed end_year; in that case the slowly-varying
        # interpolation freezes at the last value (consistent with FR-016
        # but no warning emitted because we are still inside the year range).
        next_year = min(year + 1, self._end_year)
        v_hi = self._fetch_value(series_id, next_year, value_provider)
        frac = week_index / 52.0
        interp = v_lo + (v_hi - v_lo) * frac
        return ReferenceLookupResult(
            value=interp,
            simulated_year=year,
            lookup_method=LookupMethod.LINEAR_INTERPOLATED,
            bracketing_years=(year, next_year),
        )

    def _clamped_to_last(
        self, series_id: str, simulated_year: int, value_provider: Any | None
    ) -> ReferenceLookupResult:
        key = (self._session_id, series_id)
        emit = key not in self._warned
        if emit:
            self._warned.add(key)
            warnings.warn(
                f"FR-016: requested year {simulated_year} > end_year "
                f"{self._end_year} for series '{series_id}'; "
                f"clamping to {self._end_year}.",
                RuntimeWarning,
                stacklevel=3,
            )
        value = self._fetch_value(series_id, self._end_year, value_provider)
        return ReferenceLookupResult(
            value=value,
            simulated_year=simulated_year,
            lookup_method=LookupMethod.CLAMPED_TO_LAST,
            bracketing_years=(self._end_year,),
            warning_emitted=emit,
        )

    def _clamped_to_earliest(
        self, series_id: str, simulated_year: int, value_provider: Any | None
    ) -> ReferenceLookupResult:
        """FR-041: below-range fallback clamps to the earliest available year.

        Implementation note: callers running inside a tick should also write
        a ``severity='warn'`` audit row via the conservation audit pipeline.
        That is handled at the engine level — this method only returns the
        substituted value and metadata.
        """
        key = (self._session_id, series_id)
        emit = key not in self._warned
        if emit:
            self._warned.add(key)
            warnings.warn(
                f"FR-041: requested year {simulated_year} < start_year "
                f"{self._start_year} for series '{series_id}'; "
                f"clamping to {self._start_year}.",
                RuntimeWarning,
                stacklevel=3,
            )
        value = self._fetch_value(series_id, self._start_year, value_provider)
        return ReferenceLookupResult(
            value=value,
            simulated_year=simulated_year,
            lookup_method=LookupMethod.CLAMPED_TO_EARLIEST,
            bracketing_years=(self._start_year,),
            warning_emitted=emit,
        )

    def _fetch_value(self, series_id: str, year: int, value_provider: Any | None) -> float:
        """Fetch the raw annual value.

        If ``value_provider`` is supplied, it overrides any Postgres read.
        Otherwise the Postgres-backed implementation will be added in a
        downstream commit when the immutable_reference_* hydration
        becomes real.
        """
        if value_provider is not None:
            return float(value_provider(series_id, year))
        # MVP: signal absence of real data so callers handle it explicitly.
        raise NotImplementedError(
            f"Postgres-backed lookup not yet wired for series '{series_id}' "
            f"year {year}; supply value_provider= for testing."
        )


__all__ = [
    "ImmutableReferenceLookup",
    "ReferenceLookupResult",
    "LookupMethod",
]
