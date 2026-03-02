"""Ternary consciousness computation (Feature 034, US1).

Computes community consciousness as a derived quantity from the
organizational landscape operating within the community. Organizations
are the agents: consciousness is read off the pattern of which
organizations are active, their tendencies, and their capacity.

Key design choices:
- Unorganized population defaults to liberal (Jackson's insight).
- Substrate floor sets a minimum r regardless of org landscape.
- Capacity factor = membership_density * cadre_level * cohesion.

See Also:
    :mod:`babylon.models.entities.consciousness`: Data models.
    :mod:`babylon.engine.systems.community`: System that calls this.
    ``specs/034-ternary-consciousness/spec.md``: Feature specification.
"""

from __future__ import annotations

import logging

from babylon.models.entities.consciousness import OrgContribution, TernaryConsciousness
from babylon.models.enums import CommunityType, ConsciousnessTendency

logger = logging.getLogger(__name__)


def compute_ternary_consciousness(
    community_type: CommunityType,
    org_landscape: list[OrgContribution],
    substrate_floor: float = 0.0,
) -> TernaryConsciousness:
    """Compute ternary consciousness from organizational landscape.

    Algorithm:
    1. Sum weighted contributions per tendency.
       Weight w_i = membership_density * cadre_level * cohesion.
    2. Unorganized fraction = max(0, 1 - sum(membership_densities)).
       Defaults to liberal (Jackson: passive acceptance is liberal hegemony).
    3. Normalize to simplex (r + l + f = 1.0).
    4. Apply substrate floor post-normalization: if r < floor,
       set r = floor and redistribute remaining (1-floor)
       to l and f proportionally.

    Args:
        community_type: Which community this is for (used for logging).
        org_landscape: Organizations operating in the community.
        substrate_floor: Minimum r regardless of org landscape [0, 1].

    Returns:
        TernaryConsciousness with r, l, f derived from org landscape.
        contestation_stored is None (uses Shannon entropy).
    """
    # Step 1: Sum weighted contributions per tendency
    r_raw = 0.0
    l_raw = 0.0
    f_raw = 0.0
    total_density = 0.0

    max_orgs = 500
    for idx, org in enumerate(org_landscape):
        weight = float(org.membership_density) * float(org.cadre_level) * float(org.cohesion)
        density = float(org.membership_density)
        total_density += density

        if org.tendency == ConsciousnessTendency.REVOLUTIONARY:
            r_raw += weight
        elif org.tendency == ConsciousnessTendency.LIBERAL:
            l_raw += weight
        elif org.tendency == ConsciousnessTendency.FASCIST:
            f_raw += weight

        if idx >= max_orgs:
            break

    # Step 2: Unorganized fraction defaults to liberal
    unorganized = max(0.0, 1.0 - total_density)
    l_raw += unorganized

    # Step 3: Normalize to simplex
    total = r_raw + l_raw + f_raw
    if total < 1e-10:
        # Degenerate case: no data at all
        logger.warning(
            "Zero total consciousness for %s, defaulting to pure liberal",
            community_type.value,
        )
        r_norm = substrate_floor
        l_norm = 1.0 - substrate_floor
        f_norm = 0.0
    else:
        r_norm = r_raw / total
        l_norm = l_raw / total
        f_norm = f_raw / total

    # Step 4: Apply substrate floor post-normalization
    if r_norm < substrate_floor:
        remaining = 1.0 - substrate_floor
        lf_sum = l_norm + f_norm
        if lf_sum > 1e-10:
            l_norm = l_norm * remaining / lf_sum
            f_norm = f_norm * remaining / lf_sum
        else:
            l_norm = remaining
            f_norm = 0.0
        r_norm = substrate_floor

    return TernaryConsciousness(r=r_norm, l=l_norm, f=f_norm)


__all__ = ["compute_ternary_consciousness"]
