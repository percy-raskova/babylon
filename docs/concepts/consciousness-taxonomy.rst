Community Consciousness and Structural Taxonomy
================================================

Feature 029 differentiates community hyperedges into three structurally
distinct categories with different material bases, relationships to
oppression, and modeling requirements. This document explains the
taxonomy and the consciousness model that operates on it.

.. contents:: On this page
   :local:
   :depth: 2

The Three-Category Taxonomy
---------------------------

Not all community memberships are alike. Feature 029 formalizes three
categories that emerged from theoretical analysis of how communities
relate to structures of oppression:

**Category 1 — Contradiction Pairs.** Both hegemonic and marginalized
sides exist as real hyperedges with extraction flows between them. The
settler nation extracts from colonized nations; patriarchy extracts
from women's reproductive labor. These are *axes* — the oppression has
a material direction, and both sides organize as communities.

**Category 2 — Institutional Exclusion.** Only the marginalized side
exists as a hyperedge. There is no "abled community" or "documented
community" that organizes as such. The oppression flows through
institutional defaults that assume able-bodiedness, heteronormativity,
legal residence, or freedom from incarceration. The excluded organize;
the included simply benefit from the default.

**Category 3 — Lifecycle Phases.** Universal positions in the D-P-D'
intergenerational circuit. Every agent passes through YOUTH (receives
socialization), ADULT (sells labor-power), and ELDER (post-productive
legitimation bargain). These are temporally permeable — agents move
between them — and defined by relationship to production, not identity.

.. list-table:: All 14 Community Types by Category
   :header-rows: 1
   :widths: 25 30 45

   * - Community Type
     - Category
     - Description
   * - ``SETTLER``
     - CONTRADICTION_PAIR
     - Settler nation (hegemonic). HOAs, police unions, border militias.
   * - ``PATRIARCHAL``
     - CONTRADICTION_PAIR
     - Patriarchal order (hegemonic). Gendered wage systems, family structure.
   * - ``NEW_AFRIKAN``
     - CONTRADICTION_PAIR
     - New Afrikan / Black internal nation (marginalized)
   * - ``FIRST_NATIONS``
     - CONTRADICTION_PAIR
     - Indigenous / First Nations peoples (marginalized)
   * - ``CHICANO``
     - CONTRADICTION_PAIR
     - Chicano / Mexican-American nation (marginalized)
   * - ``WOMEN``
     - CONTRADICTION_PAIR
     - Women — reproductive labor allocation (marginalized)
   * - ``TRANS``
     - CONTRADICTION_PAIR
     - Transgender / gender non-conforming (marginalized)
   * - ``DISABLED``
     - INSTITUTIONAL_EXCLUSION
     - Built environment assumes able-bodiedness
   * - ``QUEER``
     - INSTITUTIONAL_EXCLUSION
     - Institutional heteronormativity
   * - ``UNDOCUMENTED``
     - INSTITUTIONAL_EXCLUSION
     - Legal exclusion from protections
   * - ``INCARCERATED``
     - INSTITUTIONAL_EXCLUSION
     - Carceral system, civil death
   * - ``YOUTH``
     - LIFECYCLE_PHASE
     - D phase. Pre-productive, dependent, receives socialization.
   * - ``ADULT``
     - LIFECYCLE_PHASE
     - P phase. Sells labor-power. Where C-M-C and M-C-M' operate.
   * - ``ELDER``
     - LIFECYCLE_PHASE
     - D' phase. Post-productive. Legitimation bargain (pensions, Social Security).

The category assignment is fixed at import time via ``COMMUNITY_CATEGORY_MAP``
and validated exhaustively — every ``CommunityType`` must have exactly one
category. Adding a new community type without a category assignment raises
``RuntimeError`` at import.

Contradiction Axes
------------------

Contradiction pairs are organized into two named axes. Each axis has a
hegemonic side (one community type) and a marginalized side (one or
more community types), connected by a specific extraction mechanism.

**Colonial Axis**

- **Hegemonic:** SETTLER
- **Marginalized:** NEW_AFRIKAN, FIRST_NATIONS, CHICANO
- **Extraction:** Land, imperial rent, carceral labor, property value regimes
- **Exclusive:** Yes — agents belong to one side
- **Permeable:** No — colonial position is not individually crossable

**Patriarchal Axis**

- **Hegemonic:** PATRIARCHAL
- **Marginalized:** WOMEN, TRANS
- **Extraction:** Unwaged reproductive labor, wage gap, care externalization
- **Exclusive:** Yes
- **Permeable:** No

The ``ContradictionAxis`` model formalizes these relationships. Helper
functions operate on them:

- ``get_contradiction_axis(community)`` — returns the axis a community
  belongs to, or ``None``
- ``is_hegemonic(community)`` — True if on the hegemonic side
- ``is_marginalized(community)`` — True if on the marginalized side
  (includes institutional exclusion)
- ``get_opposing_communities(community)`` — returns the other side of
  the axis (empty list if not a contradiction pair)

Community Consciousness
-----------------------

Each community carries a ``CommunityConsciousness`` model representing
its ideological dimension — the distinction between *class-in-itself*
(objective structural position) and *class-for-itself* (subjective
collective awareness of that position).

Three fields capture this:

**collective_identity** — Oppositional consciousness [0, 1]. How
strongly the community identifies *as* a collective with shared
interests distinct from the dominant order. Low values: atomized
individuals who happen to share a trait. High values: coherent
political subject.

**dominant_tendency** — The prevailing direction of collective
consciousness. One of three ``ConsciousnessTendency`` values:

.. list-table:: Consciousness Tendencies
   :header-rows: 1
   :widths: 20 80

   * - Tendency
     - Description
   * - ``LIBERAL``
     - Seeks inclusion in existing institutions without transforming them.
       Organizational vehicle: liberal CSOs, Democratic Party.
   * - ``FASCIST``
     - Collaboration with hegemonic order for individual escape. Strategy:
       shrink the marginalized definition, exclude the most marginal.
   * - ``REVOLUTIONARY``
     - Oppositional collective identity, independent power. The contradiction
       is material, not a misunderstanding.

These map to George Jackson's analysis of the three directions
consciousness can take under repression. See
:doc:`george-jackson-model` for the theoretical foundation.

**ideological_contestation** — Active debate between tendencies [0, 1].
High contestation means the community is a site of struggle between
competing directions. Low contestation means the dominant tendency is
unchallenged (whether through genuine consensus or suppression of
dissent).

Default Consciousness Values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``CONSCIOUSNESS_DEFAULTS`` provides starting values for all 14 community
types. These are SYNTHETIC values for a Detroit 2010 test case — placeholders
for future calibration against historical data.

.. list-table:: CONSCIOUSNESS_DEFAULTS (Detroit 2010, Synthetic)
   :header-rows: 1
   :widths: 20 20 20 20

   * - Community
     - Collective Identity
     - Dominant Tendency
     - Contestation
   * - SETTLER
     - 0.4
     - LIBERAL
     - 0.3
   * - PATRIARCHAL
     - 0.3
     - LIBERAL
     - 0.2
   * - NEW_AFRIKAN
     - 0.5
     - LIBERAL
     - 0.4
   * - FIRST_NATIONS
     - 0.6
     - REVOLUTIONARY
     - 0.3
   * - CHICANO
     - 0.4
     - LIBERAL
     - 0.3
   * - WOMEN
     - 0.3
     - LIBERAL
     - 0.3
   * - TRANS
     - 0.5
     - LIBERAL
     - 0.4
   * - DISABLED
     - 0.3
     - LIBERAL
     - 0.2
   * - QUEER
     - 0.4
     - LIBERAL
     - 0.4
   * - UNDOCUMENTED
     - 0.5
     - LIBERAL
     - 0.3
   * - INCARCERATED
     - 0.6
     - REVOLUTIONARY
     - 0.3
   * - YOUTH
     - 0.2
     - LIBERAL
     - 0.5
   * - ADULT
     - 0.1
     - LIBERAL
     - 0.1
   * - ELDER
     - 0.3
     - LIBERAL
     - 0.2

Notable patterns:

- **FIRST_NATIONS and INCARCERATED** default to REVOLUTIONARY tendency.
  First Nations communities have maintained oppositional identity through
  centuries of settler colonialism. The incarcerated population, stripped
  of all pretense of inclusion, develops revolutionary consciousness
  through material experience of the carceral state (Jackson's insight).
- **YOUTH** has the highest contestation (0.5) — the site of ideological
  struggle over the next generation's direction.
- **ADULT** has the lowest collective identity (0.1) and contestation (0.1)
  — fully integrated into the labor market, atomized.

Infiltration Resistance
-----------------------

Community resistance to state infiltration is a computed property of
``CommunityState``, derived from collective identity and internal
cohesion:

.. math::

   IR = CI \times 0.6 + \text{cohesion} \times 0.3 + CI \times \text{cohesion} \times 0.1

Where:

- :math:`CI` = ``consciousness.collective_identity`` [0, 1]
- :math:`\text{cohesion}` = ``CommunityState.cohesion`` [0, 1]
- Weights: ``INFILTRATION_CI_WEIGHT = 0.6``,
  ``INFILTRATION_COHESION_WEIGHT = 0.3``,
  ``INFILTRATION_INTERACTION_WEIGHT = 0.1``

The interaction term (:math:`CI \times \text{cohesion} \times 0.1`)
means that collective identity and cohesion reinforce each other —
a community that both *knows what it is* and *trusts its members*
is harder to infiltrate than either factor alone would predict.

The maximum possible infiltration resistance is 1.0 (when both CI
and cohesion are 1.0: ``0.6 + 0.3 + 0.1 = 1.0``).

Effective Infiltration Ceiling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``effective_infiltration_ceiling`` function reduces the state's
infiltration effectiveness based on the target agent's community
memberships:

.. math::

   \text{ceiling}_{\text{eff}} = \text{ceiling}_{\text{base}} \times (1 - IR_{\max} \times 0.7)

Where :math:`IR_{\max}` is the highest infiltration resistance across
all communities the target agent belongs to, and
``INFILTRATION_CEILING_FACTOR = 0.7``.

At maximum resistance (:math:`IR = 1.0`), the effective ceiling drops
to 30% of base — infiltration becomes very difficult but not impossible.

Cross-Class Bridges
-------------------

Only ``INSTITUTIONAL_EXCLUSION`` communities can serve as cross-class
bridges — structures that span contradiction axes by including members
from both the hegemonic and marginalized sides.

This is because institutional exclusion operates orthogonally to
contradiction axes. A disabled person can be settler *or* colonized.
A queer person can be on either side of the patriarchal axis. The
DISABLED community hyperedge therefore potentially contains members
from both sides of the colonial axis, creating a structural bridge.

Contradiction pair communities cannot bridge because they *are*
the axis. SETTLER and NEW_AFRIKAN are opposite sides of the same
contradiction — they cannot bridge across it.

Lifecycle phases are universal (everyone passes through them) so
they provide no bridging information — everyone is in them.

The ``communities_spanning_axis`` function in
:mod:`babylon.engine.systems.community` detects which institutional
exclusion communities actually bridge a given axis in the current
simulation state, based on the community memberships of agents.

The ``is_cross_class_bridge`` computed property on ``CommunityState``
returns ``True`` for all ``INSTITUTIONAL_EXCLUSION`` communities,
indicating their structural *potential* for bridging. Whether they
actually bridge depends on the membership composition at runtime.

See Also
--------

- :doc:`community-hypergraph` — Why hyperedges, not pairwise edges
- :doc:`george-jackson-model` — Bifurcation and consciousness tendencies
- :doc:`/reference/community-system` — Complete API reference
- :py:mod:`babylon.models.entities.community` — Source models and constants
- :py:mod:`babylon.models.enums` — CommunityType, HyperedgeCategory, ConsciousnessTendency
