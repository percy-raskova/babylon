"""Internet connectivity and consciousness field operation contracts.

Defines the Protocol interfaces for internet access management,
consciousness field diffusion on the internet-connected component,
surveillance coupling, and state response modes.

See Also:
    ``specs/036-infrastructure-topology/spec.md``: FR-023 through FR-029
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enumerations (as string literals for contract-level specification)
# ---------------------------------------------------------------------------

INTERNET_RESPONSE_MODES = (
    "PERMIT",
    "THROTTLE",
    "SEVER",
)


# ---------------------------------------------------------------------------
# Data Transfer Objects
# ---------------------------------------------------------------------------


class InternetAccessState(BaseModel):
    """Per-hex internet connectivity state.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-023, FR-024
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(description="H3 cell identifier")
    internet_access: bool = Field(
        default=False,
        description="Whether broadband is available at this hex",
    )
    internet_quality: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Coverage quality scalar derived from FCC data",
    )
    surveillance_coupling: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of consciousness flow visible to the state",
    )
    response_mode: str = Field(
        default="PERMIT",
        description="State apparatus control mode: PERMIT, THROTTLE, or SEVER",
    )


class SurveillanceResult(BaseModel):
    """Result of surveillance intelligence generation for a tick.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-027
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(description="H3 cell where surveillance occurred")
    flow_magnitude: float = Field(
        ge=0.0,
        description="Consciousness flow magnitude through this hex",
    )
    surveillance_coupling: float = Field(
        ge=0.0,
        le=1.0,
        description="Current coupling value at this hex",
    )
    intelligence_generated: float = Field(
        ge=0.0,
        description="Intelligence added to state observation graph",
    )
    org_ids_observed: list[str] = Field(
        default_factory=list,
        description="Organization node IDs observed at this hex",
    )


class OpsecResult(BaseModel):
    """Result of COUNTER_INTEL action on internet surveillance coupling.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-028
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(description="H3 cell where OPSEC was applied")
    org_id: str = Field(description="Organization that invested in OPSEC")
    coupling_before: float = Field(
        ge=0.0,
        le=1.0,
        description="Surveillance coupling before OPSEC",
    )
    coupling_after: float = Field(
        ge=0.0,
        le=1.0,
        description="Surveillance coupling after OPSEC",
    )
    throughput_reduction: float = Field(
        ge=0.0,
        le=1.0,
        description="Fraction of consciousness throughput lost",
    )


class InternetResponseResult(BaseModel):
    """Result of state apparatus internet response mode change.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-029
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(description="H3 cell targeted")
    previous_mode: str = Field(description="Previous response mode")
    new_mode: str = Field(description="New response mode")
    throughput_effect: float = Field(
        ge=0.0,
        le=1.0,
        description="Remaining throughput fraction (1.0=full, 0.0=severed)",
    )
    surveillance_effect: float = Field(
        ge=0.0,
        le=1.0,
        description="Remaining surveillance fraction",
    )
    visibility: bool = Field(
        description="Whether the mode change is visible to target community",
    )
    backfire_magnitude: float = Field(
        ge=0.0,
        description="Consciousness backfire effect (signals state fear)",
    )


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class InternetFieldOperator(Protocol):
    """Manages internet consciousness field diffusion operations.

    Internet consciousness propagation is a field diffusion operation on the
    connected component of internet-enabled hexes, NOT pairwise edge flows.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-025, FR-027
    """

    def get_connected_component(self) -> set[str]:
        """Get the set of internet-enabled hex indices forming the component.

        Only hexes with ``internet_access=True`` and ``response_mode != SEVER``
        participate in the internet consciousness field.

        Returns:
            Set of H3 indices in the internet-connected component.
        """
        ...

    def propagate_consciousness(
        self,
        field_values: dict[str, float],
        diffusion_rate: float,
    ) -> dict[str, float]:
        """Run consciousness field diffusion on the internet-connected component.

        A single computation pass that propagates consciousness values among
        all enabled hexes simultaneously (FR-025). Not pairwise edge flows.

        Hexes with ``response_mode=THROTTLE`` have reduced effective
        diffusion rate. Hexes with ``response_mode=SEVER`` are excluded
        from the component entirely.

        Args:
            field_values: Current consciousness field values per h3_index.
            diffusion_rate: Base diffusion rate from GameDefines.

        Returns:
            Updated consciousness field values after propagation.
        """
        ...

    def generate_surveillance(
        self,
        field_values: dict[str, float],
        state_analytical_capacity: float,
    ) -> list[SurveillanceResult]:
        """Generate state intelligence from internet consciousness flows.

        Per FR-027: intelligence = flow_magnitude * surveillance_coupling
        * state_analytical_capacity.

        Args:
            field_values: Current consciousness field values per h3_index.
            state_analytical_capacity: State apparatus analytical capacity.

        Returns:
            List of surveillance results for hexes with nonzero intelligence.
        """
        ...


@runtime_checkable
class InternetAccessManager(Protocol):
    """Manages per-hex internet access state and mutations.

    See Also:
        ``specs/036-infrastructure-topology/spec.md``: FR-023 through FR-029
    """

    def initialize_from_broadband(
        self,
        broadband_data: dict[str, float],
        hex_to_county: dict[str, str],
        access_threshold: float,
    ) -> dict[str, InternetAccessState]:
        """Initialize internet access from FCC broadband data.

        Args:
            broadband_data: County FIPS to broadband penetration percentage.
            hex_to_county: Mapping of h3_index to county FIPS.
            access_threshold: Minimum penetration for internet_access=True.

        Returns:
            Dict mapping h3_index to InternetAccessState.
        """
        ...

    def get_access(self, h3_index: str) -> InternetAccessState | None:
        """Get internet access state for a hex.

        Args:
            h3_index: H3 cell identifier.

        Returns:
            Internet access state, or None if hex not tracked.
        """
        ...

    def apply_opsec(
        self,
        h3_index: str,
        org_id: str,
        opsec_investment: float,
        tradeoff_ratio: float,
    ) -> OpsecResult:
        """Apply COUNTER_INTEL action to reduce surveillance coupling.

        Per FR-028: reduces surveillance_coupling at cost of reduced
        consciousness throughput. The tradeoff_ratio is from GameDefines.

        Args:
            h3_index: H3 cell where OPSEC is applied.
            org_id: Organization investing in OPSEC.
            opsec_investment: Amount of OPSEC investment (AP spent).
            tradeoff_ratio: Coupling-reduction-to-throughput-loss ratio.

        Returns:
            OpsecResult documenting the coupling and throughput changes.
        """
        ...

    def set_response_mode(
        self,
        h3_index: str,
        new_mode: str,
    ) -> InternetResponseResult:
        """Set state apparatus response mode for a hex's internet access.

        Per FR-029: PERMIT (full throughput, full surveillance),
        THROTTLE (reduced throughput, maintained surveillance, hidden),
        SEVER (zero throughput, zero surveillance, visible, backfire).

        Args:
            h3_index: H3 cell to modify.
            new_mode: New response mode (PERMIT, THROTTLE, or SEVER).

        Returns:
            InternetResponseResult with effects of the mode change.
        """
        ...
