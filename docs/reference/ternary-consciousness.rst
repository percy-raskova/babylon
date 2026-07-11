Ternary Consciousness Reference
================================

API reference for the ternary consciousness model (Feature 034). For
conceptual background, see :doc:`/concepts/ternary-consciousness`.

.. contents:: On this page
   :local:
   :depth: 2

TernaryConsciousness Model
--------------------------

.. py:class:: TernaryConsciousness

   A point in the 2-simplex representing community consciousness.
   Three components ``(r, l, f)`` sum to 1.0.

   Defined in :py:mod:`babylon.models.entities.consciousness`.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 15 45

      * - Field
        - Type
        - Default
        - Description
      * - ``r``
        - ``Probability``
        - 0.3
        - Revolutionary consciousness [0, 1]
      * - ``l``
        - ``Probability``
        - 0.6
        - Liberal consciousness [0, 1]
      * - ``f``
        - ``Probability``
        - 0.1
        - Fascist consciousness [0, 1]
      * - ``contestation_stored``
        - ``float | None``
        - ``None``
        - Legacy contestation value (None = use Shannon entropy)

   **Simplex constraint:** ``r + l + f = 1.0`` (tolerance: ``1e-4``).
   Violations raise ``ValueError``.

   **Computed properties:**

   .. list-table::
      :header-rows: 1
      :widths: 30 15 55

      * - Property
        - Type
        - Description
      * - ``collective_identity``
        - ``float``
        - Equals ``r``. Backward-compatible with old scalar field.
      * - ``dominant_tendency``
        - ``ConsciousnessTendency``
        - Argmax of ``(r, l, f)``. Ties broken: liberal > revolutionary > fascist.
      * - ``ideological_contestation``
        - ``float``
        - If ``contestation_stored`` is set, returns that value (legacy path).
          Otherwise, normalized Shannon entropy: ``H(r, l, f) / log(3)`` in [0, 1].
      * - ``assimilation_ratio``
        - ``float``
        - ``f / (l + f)``. Position along the liberal-fascist base.
          Returns 0.5 when ``l + f < 1e-6`` (fully revolutionary).

   **Construction paths:**

   1. **Native:** ``TernaryConsciousness(r=0.5, l=0.3, f=0.2)`` — direct
      simplex coordinates. Any leftover computed field names are stripped.
   2. **Legacy:** ``TernaryConsciousness(collective_identity=0.5,
      dominant_tendency=LIBERAL, ideological_contestation=0.4)`` — converts
      ``r = collective_identity``, splits remaining ``(1 - r)`` between ``l``
      and ``f`` based on ``dominant_tendency``, stores ``ideological_contestation``
      in ``contestation_stored``.
   3. **Default:** ``TernaryConsciousness()`` — sets ``contestation_stored=0.2``
      and uses field defaults ``(r=0.3, l=0.6, f=0.1)``.

CommunityConsciousness Alias
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``CommunityConsciousness`` in :py:mod:`babylon.models.entities.community` is
a type alias:

.. code-block:: python

   CommunityConsciousness = TernaryConsciousness

All code using ``CommunityConsciousness`` transparently uses the ternary model.

SubstrateFloor
--------------

.. py:class:: SubstrateFloor

   Per-community-type minimum revolutionary consciousness with provenance
   metadata.

   Defined in :py:mod:`babylon.models.entities.consciousness`.

   .. list-table::
      :header-rows: 1
      :widths: 25 20 55

      * - Field
        - Type
        - Description
      * - ``community_type``
        - ``CommunityType``
        - Which community this floor applies to
      * - ``floor_value``
        - ``Probability``
        - Minimum ``r`` regardless of org landscape [0, 1]. Default: 0.0.
      * - ``confidence``
        - ``ProvenanceLevel``
        - Data quality indicator. Default: ``SYNTHETIC``.
      * - ``data_sources``
        - ``list[str]``
        - Named data sources used for derivation
      * - ``computation_method``
        - ``str``
        - How the floor was derived from proxies

ProvenanceLevel
~~~~~~~~~~~~~~~~

.. py:class:: ProvenanceLevel

   Data quality indicator for substrate floor computation. ``StrEnum`` values:

   .. list-table::
      :header-rows: 1
      :widths: 20 80

      * - Value
        - Meaning
      * - ``HIGH``
        - Derived from 2+ independent proxy data sources
      * - ``MEDIUM``
        - Derived from 1 proxy data source
      * - ``LOW``
        - Estimated from related data, not direct proxy
      * - ``SYNTHETIC``
        - Stipulated placeholder with no data path

SUBSTRATE_FLOOR_DEFAULTS
-------------------------

Default substrate floors for all 14 community types. Defined in
:py:mod:`babylon.models.entities.consciousness`.

.. list-table::
   :header-rows: 1
   :widths: 20 10 12 58

   * - Community
     - Floor
     - Confidence
     - Data Sources
   * - ``NEW_AFRIKAN``
     - 0.12
     - MEDIUM
     - Vera incarceration rates, Chetty mobility atlas
   * - ``FIRST_NATIONS``
     - 0.12
     - MEDIUM
     - Vera incarceration rates, Chetty mobility atlas
   * - ``INCARCERATED``
     - 0.18
     - MEDIUM
     - Vera incarceration rates
   * - ``CHICANO``
     - 0.08
     - LOW
     - Chetty mobility atlas
   * - ``WOMEN``
     - 0.04
     - LOW
     - Estimated
   * - ``TRANS``
     - 0.06
     - LOW
     - Estimated
   * - ``DISABLED``
     - 0.03
     - LOW
     - Estimated
   * - ``QUEER``
     - 0.04
     - LOW
     - Estimated
   * - ``UNDOCUMENTED``
     - 0.10
     - LOW
     - Estimated
   * - ``SETTLER``
     - 0.0
     - HIGH
     - Structural (hegemonic default)
   * - ``PATRIARCHAL``
     - 0.0
     - HIGH
     - Structural (hegemonic default)
   * - ``YOUTH``
     - 0.0
     - HIGH
     - Structural (lifecycle phase)
   * - ``ADULT``
     - 0.0
     - HIGH
     - Structural (lifecycle phase)
   * - ``ELDER``
     - 0.02
     - LOW
     - Estimated (generational memory)

OrgContribution
----------------

.. py:class:: OrgContribution

   An organization's weighted contribution to community consciousness.
   Input to :func:`~babylon.formulas.consciousness.compute_ternary_consciousness`.

   Defined in :py:mod:`babylon.models.entities.consciousness`.

   .. list-table::
      :header-rows: 1
      :widths: 25 20 55

      * - Field
        - Type
        - Description
      * - ``tendency``
        - ``ConsciousnessTendency``
        - Which simplex vertex this org pulls toward
      * - ``membership_density``
        - ``Probability``
        - Members in community / community population [0, 1]
      * - ``cadre_level``
        - ``Probability``
        - Organizational development level [0, 1]
      * - ``cohesion``
        - ``Probability``
        - Internal organizational cohesion [0, 1]

compute_ternary_consciousness
------------------------------

.. py:function:: compute_ternary_consciousness(community_type, org_landscape, substrate_floor=0.0)

   Compute ternary consciousness from organizational landscape.

   Defined in :py:mod:`babylon.formulas.consciousness`.

   :param community_type: Which community this is for (used for logging)
   :type community_type: CommunityType
   :param org_landscape: Organizations operating in the community
   :type org_landscape: list[OrgContribution]
   :param substrate_floor: Minimum ``r`` regardless of org landscape [0, 1]
   :type substrate_floor: float
   :returns: TernaryConsciousness with ``contestation_stored = None``
             (uses Shannon entropy for ideological_contestation)
   :rtype: TernaryConsciousness

   **Algorithm:**

   1. Sum weighted contributions per tendency.
      Weight ``w_i = membership_density * cadre_level * cohesion``.
   2. Unorganized fraction ``= max(0, 1 - sum(membership_densities))``.
      Defaults to liberal (Jackson: passive acceptance is liberal hegemony).
   3. Normalize to simplex (``r + l + f = 1.0``).
   4. Apply substrate floor post-normalization: if ``r < floor``,
      set ``r = floor`` and redistribute ``(1 - floor)`` to ``l`` and ``f``
      proportionally.

   **Example:**

   .. code-block:: python

      from babylon.formulas.consciousness import compute_ternary_consciousness
      from babylon.models.entities.consciousness import OrgContribution
      from babylon.models.enums import CommunityType, ConsciousnessTendency

      result = compute_ternary_consciousness(
          community_type=CommunityType.NEW_AFRIKAN,
          org_landscape=[
              OrgContribution(
                  tendency=ConsciousnessTendency.REVOLUTIONARY,
                  membership_density=0.3,
                  cadre_level=0.8,
                  cohesion=0.9,
              ),
          ],
          substrate_floor=0.12,
      )
      print(f"r={result.r}, l={result.l}, f={result.f}")

anisotropic_observation_error
------------------------------

.. py:function:: anisotropic_observation_error(true_consciousness, *, rng_seed=None, r_noise_stddev=0.06, lf_noise_stddev=0.02)

   Apply anisotropic noise modeling state surveillance asymmetry.

   Defined in :py:mod:`babylon.domain.bifurcation.consciousness`.

   :param true_consciousness: Actual community consciousness position
   :type true_consciousness: TernaryConsciousness
   :param rng_seed: Seed for reproducible noise (None = system entropy)
   :type rng_seed: int | None
   :param r_noise_stddev: Gaussian noise std for ``r`` component (default: 0.06)
   :type r_noise_stddev: float
   :param lf_noise_stddev: Gaussian noise std for ``l/f`` ratio (default: 0.02)
   :type lf_noise_stddev: float
   :returns: Observed TernaryConsciousness with anisotropic noise applied,
             clamped to valid simplex point
   :rtype: TernaryConsciousness

   **Noise model:**

   1. Perturb ``r`` with Gaussian noise (stddev 0.06). Clamp to [0, 1].
   2. Compute observed ``l/f`` ratio from perturbed ``f / (l + f)`` with
      Gaussian noise (stddev 0.02). Clamp to [0, 1].
   3. Reconstruct ``l`` and ``f`` from remaining budget ``(1 - observed_r)``
      and perturbed ratio.

   The ``r`` component has ~3x higher observation error than the ``l/f``
   split, reflecting that revolutionary consciousness is hidden from
   state surveillance while liberal/fascist expression is legible.

WeightedSolidarityResult
-------------------------

.. py:class:: WeightedSolidarityResult

   Result of consciousness-weighted solidarity computation.

   Defined in :py:mod:`babylon.domain.bifurcation.types`.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``weight``
        - ``float``
        - Consciousness-weighted solidarity value (>= 0)
      * - ``crisis_fragile``
        - ``bool``
        - ``True`` if effective CI < crisis-fragile threshold (0.3).
          Default: ``False``.

consciousness_weighted_solidarity
----------------------------------

.. py:function:: consciousness_weighted_solidarity(source_id, target_id, graph, H, community_states, defines)

   Weight a solidarity edge by consciousness of connected communities.

   Defined in :py:mod:`babylon.domain.bifurcation.consciousness`.

   :param source_id: Source agent node ID
   :type source_id: str
   :param target_id: Target agent node ID
   :type target_id: str
   :param graph: The simulation DiGraph (for edge attribute access)
   :type graph: nx.DiGraph
   :param H: XGI hypergraph (for community membership lookup)
   :type H: xgi.Hypergraph
   :param community_states: Current community consciousness data
   :type community_states: dict[CommunityType, CommunityState]
   :param defines: Configurable parameters (sigmoid midpoint/steepness)
   :type defines: BifurcationDefines
   :returns: Weighted solidarity with crisis-fragile flag
   :rtype: WeightedSolidarityResult

   Edges where the effective CI (min of both endpoints) falls below the
   crisis-fragile threshold (0.3) are marked ``crisis_fragile = True``.

.. _consciousness-defaults-table:

CONSCIOUSNESS_DEFAULTS
-----------------------

Starting values for all 14 community types. Synthetic data for a Detroit
2010 test case. Defined in :py:mod:`babylon.models.entities.community`.

All values are native ternary ``(r, l, f)`` coordinates. The
``ideological_contestation`` is computed as Shannon entropy of the
distribution.

.. list-table::
   :header-rows: 1
   :widths: 20 12 12 12 22

   * - Community
     - r
     - l
     - f
     - Dominant Tendency
   * - ``SETTLER``
     - 0.40
     - 0.45
     - 0.15
     - LIBERAL
   * - ``PATRIARCHAL``
     - 0.30
     - 0.525
     - 0.175
     - LIBERAL
   * - ``NEW_AFRIKAN``
     - 0.50
     - 0.50
     - 0.0
     - LIBERAL
   * - ``FIRST_NATIONS``
     - 0.60
     - 0.24
     - 0.16
     - REVOLUTIONARY
   * - ``CHICANO``
     - 0.40
     - 0.45
     - 0.15
     - LIBERAL
   * - ``WOMEN``
     - 0.30
     - 0.525
     - 0.175
     - LIBERAL
   * - ``TRANS``
     - 0.50
     - 0.50
     - 0.0
     - LIBERAL
   * - ``DISABLED``
     - 0.30
     - 0.525
     - 0.175
     - LIBERAL
   * - ``QUEER``
     - 0.40
     - 0.45
     - 0.15
     - LIBERAL
   * - ``UNDOCUMENTED``
     - 0.50
     - 0.50
     - 0.0
     - LIBERAL
   * - ``INCARCERATED``
     - 0.60
     - 0.24
     - 0.16
     - REVOLUTIONARY
   * - ``YOUTH``
     - 0.20
     - 0.60
     - 0.20
     - LIBERAL
   * - ``ADULT``
     - 0.10
     - 0.675
     - 0.225
     - LIBERAL
   * - ``ELDER``
     - 0.30
     - 0.525
     - 0.175
     - LIBERAL

Notable patterns:

- **FIRST_NATIONS and INCARCERATED** have the highest ``r`` (0.6) and are
  the only communities with REVOLUTIONARY dominant tendency.
- **NEW_AFRIKAN, TRANS, and UNDOCUMENTED** have ``f = 0.0`` — no fascist
  component, split evenly between revolutionary and liberal.
- **ADULT** has the lowest ``r`` (0.1) — fully integrated into the labor
  market, atomized by liberal hegemony.

Module Cross-References
------------------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Module
     - Contains
   * - :py:mod:`babylon.models.entities.consciousness`
     - ``TernaryConsciousness``, ``SubstrateFloor``, ``OrgContribution``,
       ``ProvenanceLevel``, ``SUBSTRATE_FLOOR_DEFAULTS``
   * - :py:mod:`babylon.models.entities.community`
     - ``CommunityConsciousness`` (alias), ``CONSCIOUSNESS_DEFAULTS``
   * - :py:mod:`babylon.formulas.consciousness`
     - ``compute_ternary_consciousness()``
   * - :py:mod:`babylon.domain.bifurcation.consciousness`
     - ``anisotropic_observation_error()``,
       ``consciousness_weighted_solidarity()``
   * - :py:mod:`babylon.domain.bifurcation.types`
     - ``WeightedSolidarityResult``, ``BifurcationResult``
       (updated with assimilation fields)

See Also
--------

- :doc:`/concepts/ternary-consciousness` — Theoretical explanation
- :doc:`/reference/community-system` — Community layer API reference
- :doc:`/reference/topology` — Bifurcation analysis API reference
