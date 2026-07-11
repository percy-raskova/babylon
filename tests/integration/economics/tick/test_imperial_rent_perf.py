"""Performance smoke test for the Spec 057 Leontief imperial-rent pipeline.

Per research.md §R3 + plan.md performance budget:
  - Warm cache (subsequent ticks within same year): mean ≤ 100ms,
    95th percentile ≤ 200ms over 100 consecutive ticks.
  - Cold cache (first tick of a new year): ≤ 250ms.

The synthetic-fixture coverage validates that the pipeline orchestration
overhead is bounded; real-data wall-clock will be dominated by SQLite
read latency, but those reads are cached after the first call within a
year per the CachedSource[T] contract.
"""

from __future__ import annotations

import time
from statistics import mean, quantiles
from typing import Any

import pytest

from babylon.domain.economics.tick.system.imperial_rent import compute
from tests.integration.economics.tick.test_imperial_rent_pipeline import (
    _county,
    _wired_services,
)


@pytest.fixture
def perf_county_states() -> dict[str, Any]:
    """Build a 50-county synthetic state — large enough to amortize fixed
    overhead, small enough that each tick is sub-100ms."""
    return {f"{i:05d}": _county(f"{i:05d}", phi_hour=0.0) for i in range(11111, 11161)}


@pytest.fixture
def perf_national_params() -> Any:
    from babylon.domain.economics.tick.types import NationalTickParameters

    return NationalTickParameters(
        year=2015,
        tau=62.0,
        gamma_basket=0.68,
        gamma_basket_raw=0.68,
        gamma_III=0.55,
        gamma_III_raw=0.55,
        tau_effective=42.16,
        v_reproduction=15.0,
        estimated=True,
    )


@pytest.mark.integration
def test_imperial_rent_perf_warm_cache(
    perf_county_states: dict[str, Any], perf_national_params: Any
) -> None:
    """100 consecutive ticks within the same year — should hit warm caches.

    Budget: mean ≤ 100ms, p95 ≤ 200ms.
    """
    services = _wired_services(
        allocation=dict.fromkeys(perf_county_states, 0.5),
    )

    # Warm-up tick (first call populates source caches)
    compute(perf_county_states, perf_national_params, services)

    durations: list[float] = []
    for _ in range(100):
        t0 = time.perf_counter()
        compute(perf_county_states, perf_national_params, services)
        durations.append((time.perf_counter() - t0) * 1000.0)  # ms

    mean_ms = mean(durations)
    p95_ms = quantiles(durations, n=20)[18]  # 95th percentile

    # Generous budgets — synthetic fixture overhead is much less than real DB
    assert mean_ms < 100.0, f"Warm-cache mean {mean_ms:.2f}ms exceeds 100ms budget"
    assert p95_ms < 200.0, f"Warm-cache p95 {p95_ms:.2f}ms exceeds 200ms budget"


@pytest.mark.integration
def test_imperial_rent_perf_cold_cache(
    perf_county_states: dict[str, Any], perf_national_params: Any
) -> None:
    """First tick (cold cache) — budget ≤ 250ms.

    With synthetic Mock fixtures the cold-cache overhead is essentially
    zero; this test is a smoke gate against future regressions when real
    DB-backed sources land.
    """
    services = _wired_services(
        allocation=dict.fromkeys(perf_county_states, 0.5),
    )
    t0 = time.perf_counter()
    compute(perf_county_states, perf_national_params, services)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 250.0, f"Cold-cache {elapsed_ms:.2f}ms exceeds 250ms budget"
