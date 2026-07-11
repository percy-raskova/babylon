"""Dispossession intensity calculator (Feature 021, FR-005).

Computes weighted aggregate dispossession intensity from individual
type rates and territory state.
"""

from __future__ import annotations

from babylon.config.defines import DispossessionDefines
from babylon.domain.economics.dispossession.types import TerritoryDispossessionState


class DispossessionIntensityCalculator:
    """Computes aggregate dispossession intensity from weighted components.

    Each dispossession type contributes to the composite intensity
    proportional to its configured weight.

    Args:
        defines: Configuration with per-type intensity weights.
    """

    def __init__(self, defines: DispossessionDefines | None = None) -> None:
        self._defines = defines if defines is not None else DispossessionDefines()

    def compute_intensity(self, state: TerritoryDispossessionState) -> float:
        """Compute composite dispossession intensity for a territory.

        Uses the territory's rate fields weighted by the configured
        per-type weights. Only foreclosure_rate, eviction_rate, and
        displacement_rate are territory-level rates; concentrated_ownership
        and absentee_landlord_share contribute as structural factors.

        Args:
            state: Territory dispossession state with per-type rates.

        Returns:
            Composite dispossession intensity in [0, 1].
        """
        d = self._defines
        intensity = (
            d.weight_foreclosure * state.foreclosure_rate
            + d.weight_eviction * state.eviction_rate
            + d.weight_displacement * state.displacement_rate
            + d.weight_tax_sale * state.concentrated_ownership
            + d.weight_eminent_domain * state.absentee_landlord_share
        )
        return min(max(intensity, 0.0), 1.0)

    def compute_value_transfer(
        self,
        total_value: float,
        deadweight_fraction: float | None = None,
    ) -> tuple[float, float]:
        """Compute net value transfer and deadweight loss.

        Args:
            total_value: Total value being transferred.
            deadweight_fraction: Override for deadweight loss fraction.
                If None, uses the configured default.

        Returns:
            Tuple of (net_received, deadweight_loss) where
            net_received + deadweight_loss == total_value.
        """
        if total_value <= 0.0:
            return (0.0, 0.0)

        fraction = (
            deadweight_fraction
            if deadweight_fraction is not None
            else self._defines.deadweight_loss_fraction
        )
        fraction = min(max(fraction, 0.0), 1.0)

        deadweight = total_value * fraction
        received = total_value - deadweight
        return (received, deadweight)
