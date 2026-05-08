"""Community type and hyperedge category enums.

Spec 058: extracted from the historical ``babylon.models.enums`` monolith.
Re-exported via :mod:`babylon.models.enums.__init__`.
"""

from __future__ import annotations

from enum import StrEnum


class CommunityType(StrEnum):
    """Community types for hypergraph membership (Constitution II.7).

    Three structurally distinct categories — NOT a spectrum.

    Category 1 — Contradiction Pairs (both sides real hyperedges):
        SETTLER: Settler nation (hegemonic). Institutions: HOAs, police unions, border militias.
        NEW_AFRIKAN: New Afrikan / Black internal nation (marginalized)
        FIRST_NATIONS: Indigenous / First Nations peoples (marginalized)
        CHICANO: Chicano / Mexican-American nation (marginalized)
        PATRIARCHAL: Patriarchal order (hegemonic). Institutions: gendered wage systems, family structure.
        WOMEN: Women — reproductive labor allocation (marginalized)
        TRANS: Transgender / gender non-conforming (marginalized)

    Category 2 — Institutional Exclusion (only marginalized side):
        DISABLED: Disabled community. Built environment assumes able-bodiedness.
        QUEER: Queer / LGBQ. Institutional heteronormativity.
        UNDOCUMENTED: Undocumented. Legal exclusion from protections.
        INCARCERATED: Incarcerated. Carceral system, civil death.

    Category 3 — Lifecycle Phases (D-P-D' Circuit):
        YOUTH: D phase. Pre-productive, dependent, receives socialization.
        ADULT: P phase. Sells labor-power. Where C-M-C and M-C-M' operate.
        ELDER: D' phase. Post-productive. Legitimation bargain (pensions, Social Security).
    """

    # Category 1: Contradiction Pairs — hegemonic
    SETTLER = "settler"
    PATRIARCHAL = "patriarchal"
    # Category 1: Contradiction Pairs — marginalized
    NEW_AFRIKAN = "new_afrikan"
    FIRST_NATIONS = "first_nations"
    CHICANO = "chicano"
    WOMEN = "women"
    TRANS = "trans"
    # Category 2: Institutional Exclusion — marginalized only
    DISABLED = "disabled"
    QUEER = "queer"
    UNDOCUMENTED = "undocumented"
    INCARCERATED = "incarcerated"
    # Category 3: Lifecycle Phases — D-P-D' Circuit
    YOUTH = "youth"
    ADULT = "adult"
    ELDER = "elder"


class HyperedgeCategory(StrEnum):
    """Structural category for community hyperedges (Feature 029, Constitution II.7).

    Three qualitatively distinct categories with different material bases,
    relationships to oppression, and modeling requirements.

    Values:
        CONTRADICTION_PAIR: Both hegemonic and marginalized sides exist as real
            hyperedges with extraction flows between them.
        INSTITUTIONAL_EXCLUSION: Only marginalized side exists. Oppression flows
            through institutional defaults, not a paired oppressor community.
        LIFECYCLE_PHASE: Temporal positions in D-P-D' intergenerational lifecycle.
            Universal, temporally permeable, defined by relationship to production.
        ECONOMIC_SECTOR: Industry sectors represented by 2-digit NAICS codes. Used
            for tracking economic metabolism, business coordination, and profit equalization.
    """

    CONTRADICTION_PAIR = "contradiction_pair"
    INSTITUTIONAL_EXCLUSION = "institutional_exclusion"
    LIFECYCLE_PHASE = "lifecycle_phase"
    ECONOMIC_SECTOR = "economic_sector"


__all__ = [
    "CommunityType",
    "HyperedgeCategory",
]
