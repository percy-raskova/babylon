"""Lifecycle-modified action capacity (Feature 032).

Computes lifecycle-weighted effectiveness modifier and elder legitimacy
bonus for consciousness effects, reusing Feature 031 composition
calculators.

See Also:
    ``babylon.organizations.composition``: Underlying lifecycle analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.config.defines import OODADefines, OrganizationDefines
from babylon.organizations.composition import effective_capacity, lifecycle_composition

if TYPE_CHECKING:
    import networkx as nx


def compute_lifecycle_modifier(
    org_id: str,
    graph: nx.DiGraph[str],
    org_defines: OrganizationDefines,
) -> float:
    """Compute lifecycle-weighted capacity modifier for an organization.

    Youth contribute zero capacity, adults full (1.0), elders a fraction
    (elder_capacity_factor). The result scales action effectiveness.

    Args:
        org_id: Organization node ID.
        graph: World graph with MEMBERSHIP edges.
        org_defines: OrganizationDefines with elder_capacity_factor.

    Returns:
        Capacity modifier in [0, 1].
    """
    lifecycle = lifecycle_composition(org_id, graph)
    return effective_capacity(lifecycle, org_defines.elder_capacity_factor)


def elder_legitimacy_bonus(
    org_id: str,
    graph: nx.DiGraph[str],
    org_defines: OrganizationDefines,  # noqa: ARG001 — reserved for future elder capacity weighting
    ooda_defines: OODADefines,
) -> float:
    """Compute elder legitimacy multiplier for consciousness delta.

    When an organization has elder members (D'-phase proportion > 0),
    the consciousness delta is multiplied by elder_legitimacy_multiplier.

    Args:
        org_id: Organization node ID.
        graph: World graph with MEMBERSHIP edges.
        org_defines: OrganizationDefines with elder_capacity_factor.
        ooda_defines: OODADefines with elder_legitimacy_multiplier.

    Returns:
        Multiplier (1.0 = no bonus, > 1.0 = elder bonus).
    """
    lifecycle = lifecycle_composition(org_id, graph)

    elder_proportion = lifecycle.distribution.get("elder", 0.0)
    if elder_proportion > 0.0:
        return ooda_defines.elder_legitimacy_multiplier

    return 1.0


__all__ = [
    "compute_lifecycle_modifier",
    "elder_legitimacy_bonus",
]
