"""Internet access and consciousness field operations (Feature 036, US5).

Manages per-hex internet connectivity state, consciousness field diffusion
on the connected component of internet-enabled hexes, surveillance intelligence
generation, OPSEC tradeoff, and state response modes (PERMIT/THROTTLE/SEVER).

FCC broadband data is available in the 3NF SQLite database at
``data/sqlite/marxist-data-3NF.sqlite`` in ``fact_broadband_coverage``.

See Also:
    :mod:`babylon.domain.geography.protocols`: InternetAccessManager, InternetFieldOperator.
    ``specs/036-infrastructure-topology/spec.md``: FR-023 through FR-029.
"""

from __future__ import annotations

from babylon.config.defines import InfrastructureDefines, InfraTerrainDefines
from babylon.domain.geography.types import (
    InternetAccessState,
    InternetResponseResult,
    OpsecResult,
    SurveillanceResult,
)
from babylon.models.enums import InternetResponseMode


class DefaultInternetAccessManager:
    """Manages per-hex internet connectivity state.

    Stores mutable internet state internally, returning frozen DTOs
    via ``get_state()``. Supports initialization from FCC broadband
    data, OPSEC coupling reduction, and response mode transitions.

    Args:
        defines: InfraTerrainDefines for internet thresholds and defaults.
    """

    def __init__(self, defines: InfraTerrainDefines) -> None:
        self._defines = defines
        self._states: dict[str, InternetAccessState] = {}

    def get_state(self, h3_index: str) -> InternetAccessState | None:
        """Get internet state for a hex.

        Args:
            h3_index: H3 cell identifier.

        Returns:
            Internet access state, or None if not initialized.
        """
        return self._states.get(h3_index)

    def set_state(self, state: InternetAccessState) -> None:
        """Set internet state for a hex.

        Args:
            state: Internet access state to store.
        """
        self._states[state.h3_index] = state

    def get_all_states(self) -> dict[str, InternetAccessState]:
        """Get all internet states.

        Returns:
            Dict mapping h3_index to InternetAccessState.
        """
        return dict(self._states)

    def initialize_from_broadband(
        self,
        broadband: dict[str, float],
        hex_to_county: dict[str, str],
        quality_data: dict[str, float] | None = None,
        water_hexes: set[str] | None = None,
    ) -> None:
        """Initialize internet access from FCC broadband data.

        Maps county-level broadband penetration (pct_25_3 / 100) to
        per-hex internet_access. Quality derived from pct_100_20 / 100.

        Args:
            broadband: County FIPS → penetration fraction [0.0, 1.0].
            hex_to_county: H3 index → county FIPS mapping.
            quality_data: County FIPS → high-speed fraction (pct_100_20 / 100).
                Defaults to broadband penetration if not provided.
            water_hexes: Set of H3 indices classified as WATER (EC-009: no access).
        """
        threshold = self._defines.internet_access_threshold
        default_coupling = self._defines.default_surveillance_coupling
        water = water_hexes or set()

        for h3_index, county_fips in hex_to_county.items():
            penetration = broadband.get(county_fips, 0.0)
            quality = 0.0
            if quality_data is not None:
                quality = quality_data.get(county_fips, 0.0)
            else:
                quality = penetration

            # WATER hexes default to no access (EC-009)
            has_access = False if h3_index in water else penetration >= threshold

            self._states[h3_index] = InternetAccessState(
                h3_index=h3_index,
                internet_access=has_access,
                internet_quality=min(1.0, max(0.0, quality)) if has_access else 0.0,
                surveillance_coupling=default_coupling if has_access else 0.0,
                response_mode=InternetResponseMode.PERMIT,
            )

    def apply_opsec(
        self,
        h3_index: str,
        org_id: str,
        opsec_investment: float,
        infra_defines: InfrastructureDefines,
    ) -> OpsecResult:
        """Apply OPSEC to reduce surveillance coupling at a hex.

        Reduces coupling by ``opsec_investment * opsec_tradeoff_ratio``,
        but also reduces consciousness throughput proportionally.

        Args:
            h3_index: Target hex.
            org_id: Organization investing in OPSEC.
            opsec_investment: Investment magnitude [0.0, 1.0].
            infra_defines: For opsec_tradeoff_ratio.

        Returns:
            OpsecResult with before/after coupling and throughput reduction.

        Raises:
            KeyError: If hex not found.
        """
        state = self._states.get(h3_index)
        if state is None:
            msg = f"Hex not found: {h3_index!r}"
            raise KeyError(msg)

        coupling_before = state.surveillance_coupling
        reduction = opsec_investment * infra_defines.opsec_tradeoff_ratio
        coupling_after = max(0.0, coupling_before - reduction)

        # Throughput reduction proportional to coupling reduction
        throughput_reduction = (
            coupling_before - coupling_after
        ) * infra_defines.opsec_tradeoff_ratio

        # Update state
        self._states[h3_index] = state.model_copy(
            update={"surveillance_coupling": coupling_after},
        )

        return OpsecResult(
            h3_index=h3_index,
            org_id=org_id,
            coupling_before=coupling_before,
            coupling_after=coupling_after,
            throughput_reduction=throughput_reduction,
        )

    def set_response_mode(
        self,
        h3_index: str,
        mode: str,
        infra_defines: InfrastructureDefines,
    ) -> InternetResponseResult:
        """Set state apparatus internet response mode for a hex.

        PERMIT: full throughput (1.0), full surveillance (1.0), not visible.
        THROTTLE: reduced throughput, maintained surveillance, not visible.
        SEVER: zero throughput, zero surveillance, visible, backfire.

        Args:
            h3_index: Target hex.
            mode: InternetResponseMode value.
            infra_defines: For throttle_throughput_fraction.

        Returns:
            InternetResponseResult with effects.

        Raises:
            KeyError: If hex not found.
        """
        state = self._states.get(h3_index)
        if state is None:
            msg = f"Hex not found: {h3_index!r}"
            raise KeyError(msg)

        previous_mode = state.response_mode

        # Compute effects based on mode
        if mode == InternetResponseMode.SEVER:
            throughput_effect = 0.0
            surveillance_effect = 0.0
            visibility = True
            backfire = state.surveillance_coupling + 0.1  # Proportional to coupling
        elif mode == InternetResponseMode.THROTTLE:
            throughput_effect = infra_defines.throttle_throughput_fraction
            surveillance_effect = 1.0  # Maintained
            visibility = False
            backfire = 0.0
        else:  # PERMIT
            throughput_effect = 1.0
            surveillance_effect = 1.0
            visibility = False
            backfire = 0.0

        # Update state
        self._states[h3_index] = state.model_copy(
            update={"response_mode": mode},
        )

        return InternetResponseResult(
            h3_index=h3_index,
            previous_mode=previous_mode,
            new_mode=mode,
            throughput_effect=throughput_effect,
            surveillance_effect=surveillance_effect,
            visibility=visibility,
            backfire_magnitude=backfire,
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize manager state for tick-snapshot compatibility.

        Returns:
            Dict with states keyed by h3_index.
        """
        states: dict[str, dict[str, object]] = {}
        for h3_index, state in self._states.items():
            states[h3_index] = state.model_dump()
        return {"states": states}

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
        defines: InfraTerrainDefines,
    ) -> DefaultInternetAccessManager:
        """Deserialize manager state from tick-snapshot data.

        Args:
            data: Serialized state from ``to_dict()``.
            defines: InfraTerrainDefines for configuration.

        Returns:
            Reconstructed DefaultInternetAccessManager.
        """
        manager = cls(defines=defines)
        states_data = data.get("states", {})
        for _h3_index, state_dict in states_data.items():  # type: ignore[attr-defined]
            state = InternetAccessState.model_validate(state_dict)
            manager.set_state(state)
        return manager


class DefaultInternetFieldOperator:
    """Consciousness field diffusion and surveillance on internet-enabled hexes.

    Operates on the connected component of internet-enabled, non-SEVER
    hexes. Consciousness diffuses via mean-field approximation (FR-025):
    each hex moves toward the component mean at a rate modified by
    quality and response mode.

    Args:
        manager: InternetAccessManager for hex state lookup.
        infra_defines: InfrastructureDefines for throttle parameters.
    """

    def __init__(
        self,
        manager: DefaultInternetAccessManager,
        infra_defines: InfrastructureDefines | None = None,
    ) -> None:
        self._manager = manager
        self._infra_defines = infra_defines or InfrastructureDefines()

    def get_connected_component(self) -> set[str]:
        """Get the set of hexes in the internet-connected component.

        Includes hexes with internet_access=True and response_mode != SEVER.

        Returns:
            Set of h3_index strings.
        """
        component: set[str] = set()
        for h3_index, state in self._manager.get_all_states().items():
            if state.internet_access and state.response_mode != InternetResponseMode.SEVER:
                component.add(h3_index)
        return component

    def propagate_consciousness(
        self,
        field_values: dict[str, float],
        diffusion_rate: float,
    ) -> dict[str, float]:
        """Propagate consciousness via mean-field diffusion on connected component.

        Each enabled hex moves toward the component mean at a rate
        proportional to ``diffusion_rate * quality * throughput_factor``.
        THROTTLE hexes have reduced throughput factor.

        Args:
            field_values: H3 index → current consciousness field value.
            diffusion_rate: Base diffusion rate [0.0, 1.0].

        Returns:
            Updated field values for all hexes in field_values.
        """
        component = self.get_connected_component()
        result = dict(field_values)

        # Only diffuse among connected hexes that have field values
        active = [h for h in component if h in field_values]
        if len(active) < 2:
            return result

        # Compute mean of connected component
        total = sum(field_values.get(h, 0.0) for h in active)
        mean_val = total / len(active)

        # Diffuse each hex toward the mean
        throttle_fraction = self._infra_defines.throttle_throughput_fraction

        for h3_index in active:
            state = self._manager.get_state(h3_index)
            if state is None:
                continue

            # Throughput factor: 1.0 for PERMIT, throttle_fraction for THROTTLE
            if state.response_mode == InternetResponseMode.THROTTLE:
                throughput = throttle_fraction
            else:
                throughput = 1.0

            effective_rate = diffusion_rate * state.internet_quality * throughput
            current = field_values.get(h3_index, 0.0)
            result[h3_index] = current + effective_rate * (mean_val - current)

        return result

    def generate_surveillance(
        self,
        flow_magnitudes: dict[str, float],
        analytical_capacity: float,
    ) -> list[SurveillanceResult]:
        """Generate surveillance intelligence from consciousness flow.

        For each hex in the connected component:
        intelligence = flow_magnitude * surveillance_coupling * analytical_capacity

        Args:
            flow_magnitudes: H3 index → consciousness flow magnitude.
            analytical_capacity: State apparatus analytical capacity [0.0, 1.0].

        Returns:
            List of SurveillanceResult for each hex with surveillance.
        """
        component = self.get_connected_component()
        results: list[SurveillanceResult] = []

        for h3_index in component:
            state = self._manager.get_state(h3_index)
            if state is None:
                continue

            flow = flow_magnitudes.get(h3_index, 0.0)
            intelligence = flow * state.surveillance_coupling * analytical_capacity

            results.append(
                SurveillanceResult(
                    h3_index=h3_index,
                    flow_magnitude=flow,
                    surveillance_coupling=state.surveillance_coupling,
                    intelligence_generated=intelligence,
                ),
            )

        return results
