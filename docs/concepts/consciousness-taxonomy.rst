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

Each community carries a ``CommunityConsciousness`` model (type alias for
:class:`~babylon.models.entities.consciousness.TernaryConsciousness`)
representing its ideological dimension — the distinction between
*class-in-itself* (objective structural position) and *class-for-itself*
(subjective collective awareness of that position).

Feature 034 replaces the original three independent scalar fields with
a **2-simplex model** where ``r + l + f = 1.0``. Three components
capture the share of consciousness devoted to each direction:

- **r** (revolutionary) — Oppositional consciousness. How strongly the
  community identifies *as* a collective with shared interests distinct
  from the dominant order. Equivalent to the old ``collective_identity``.
- **l** (liberal) — Seeks inclusion in existing institutions without
  transforming them. The default when no organizations are active.
- **f** (fascist) — Collaboration with hegemonic order for individual
  escape. Shrinks the marginalized definition, excludes the most marginal.

The simplex constraint means these are shares of a single whole: increasing
one component necessarily decreases the others. The old scalar fields
become computed properties:

- ``collective_identity`` = ``r``
- ``dominant_tendency`` = argmax of ``(r, l, f)`` (ties favor liberal)
- ``ideological_contestation`` = normalized Shannon entropy ``H(r, l, f) / log(3)``
- ``assimilation_ratio`` = ``f / (l + f)`` (position along liberal-fascist base)

These three tendencies map to George Jackson's analysis of the directions
consciousness can take under repression. See
:doc:`george-jackson-model` for the theoretical foundation, and
:doc:`ternary-consciousness` for the full explanation of the simplex model
and organizational landscape derivation.

Default Consciousness Values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``CONSCIOUSNESS_DEFAULTS`` provides starting values for all 14 community
types as native ternary ``(r, l, f)`` coordinates. These are SYNTHETIC
values for a Detroit 2010 test case — placeholders for future calibration
against historical data. The ``ideological_contestation`` is now computed
as Shannon entropy of the distribution rather than stored independently.

.. list-table:: CONSCIOUSNESS_DEFAULTS (Detroit 2010, Synthetic)
   :header-rows: 1
   :widths: 20 12 12 12 22

   * - Community
     - r
     - l
     - f
     - Dominant Tendency
   * - SETTLER
     - 0.40
     - 0.45
     - 0.15
     - LIBERAL
   * - PATRIARCHAL
     - 0.30
     - 0.525
     - 0.175
     - LIBERAL
   * - NEW_AFRIKAN
     - 0.50
     - 0.50
     - 0.0
     - LIBERAL
   * - FIRST_NATIONS
     - 0.60
     - 0.24
     - 0.16
     - REVOLUTIONARY
   * - CHICANO
     - 0.40
     - 0.45
     - 0.15
     - LIBERAL
   * - WOMEN
     - 0.30
     - 0.525
     - 0.175
     - LIBERAL
   * - TRANS
     - 0.50
     - 0.50
     - 0.0
     - LIBERAL
   * - DISABLED
     - 0.30
     - 0.525
     - 0.175
     - LIBERAL
   * - QUEER
     - 0.40
     - 0.45
     - 0.15
     - LIBERAL
   * - UNDOCUMENTED
     - 0.50
     - 0.50
     - 0.0
     - LIBERAL
   * - INCARCERATED
     - 0.60
     - 0.24
     - 0.16
     - REVOLUTIONARY
   * - YOUTH
     - 0.20
     - 0.60
     - 0.20
     - LIBERAL
   * - ADULT
     - 0.10
     - 0.675
     - 0.225
     - LIBERAL
   * - ELDER
     - 0.30
     - 0.525
     - 0.175
     - LIBERAL

Notable patterns:

- **FIRST_NATIONS and INCARCERATED** have the highest ``r`` (0.6) and are
  the only communities with REVOLUTIONARY dominant tendency.
  First Nations communities have maintained oppositional identity through
  centuries of settler colonialism. The incarcerated population, stripped
  of all pretense of inclusion, develops revolutionary consciousness
  through material experience of the carceral state (Jackson's insight).
- **NEW_AFRIKAN, TRANS, and UNDOCUMENTED** have ``f = 0.0`` — no fascist
  component, split evenly between revolutionary and liberal.
- **ADULT** has the lowest ``r`` (0.1) — fully integrated into the labor
  market, atomized by liberal hegemony.

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

- :doc:`ternary-consciousness` — Why consciousness is modeled as a ternary simplex
- :doc:`community-hypergraph` — Why hyperedges, not pairwise edges
- :doc:`george-jackson-model` — Bifurcation and consciousness tendencies
- :doc:`/reference/ternary-consciousness` — API reference for ternary consciousness types
- :doc:`/reference/community-system` — Complete API reference
- :py:mod:`babylon.models.entities.consciousness` — TernaryConsciousness source module
- :py:mod:`babylon.models.entities.community` — Source models and constants
- :py:mod:`babylon.models.enums` — CommunityType, HyperedgeCategory, ConsciousnessTendency
