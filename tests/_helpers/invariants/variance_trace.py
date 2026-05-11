"""Profit-rate variance trace — spec 060 US7(c) / FR-019.

Collects per-tick inter-sectoral profit-rate variance over a multi-tick
run. The trace is the input to the Volume III equalization-tendency
assertion: ``variance_late() < variance_early()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import variance as _variance


@dataclass(frozen=True)
class VarianceObservation:
    """One tick of inter-sectoral profit-rate data."""

    tick: int
    sector_rates: dict[str, float]
    variance: float


@dataclass(frozen=True)
class ProfitRateVarianceTrace:
    """Ordered series of per-tick variance observations."""

    observations: list[VarianceObservation] = field(default_factory=list)

    @classmethod
    def from_sector_rate_series(
        cls, series: list[tuple[int, dict[str, float]]]
    ) -> ProfitRateVarianceTrace:
        """Build a trace from ``[(tick, {sector: rate})]`` pairs."""
        obs: list[VarianceObservation] = []
        for tick, rates in series:
            rate_list = list(rates.values())
            v = _variance(rate_list) if len(rate_list) >= 2 else 0.0
            obs.append(VarianceObservation(tick=tick, sector_rates=dict(rates), variance=v))
        return cls(observations=obs)

    def variance_window(self, start: int, end: int) -> float:
        """Mean variance over ``observations[start:end]``."""
        window = self.observations[start:end]
        if not window:
            return 0.0
        return sum(o.variance for o in window) / len(window)

    def variance_early(self, window: int = 10) -> float:
        return self.variance_window(0, window)

    def variance_late(self, window: int = 10) -> float:
        n = len(self.observations)
        return self.variance_window(max(0, n - window), n)

    def has_equalized(self, window: int = 10) -> bool:
        return self.variance_late(window) < self.variance_early(window)

    def __len__(self) -> int:
        return len(self.observations)


__all__ = ["VarianceObservation", "ProfitRateVarianceTrace"]
