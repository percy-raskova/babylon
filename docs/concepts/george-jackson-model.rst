George Jackson Bifurcation Model
================================

The George Jackson model describes how economic crisis routes consciousness
toward either **class solidarity** or **national identity** (fascism),
depending on the presence of solidarity networks.

Named after the revolutionary theorist George Jackson, this model captures
a critical insight: material conditions alone do not determine revolutionary
outcomes—organizational infrastructure matters.

Theoretical Foundation
----------------------

When wages fall and material conditions deteriorate, agitation energy
increases. But where does this energy go?

**Without SOLIDARITY edges:**
   Energy routes toward national/racial identity → Fascism (+1 ideology)

**With SOLIDARITY edges:**
   Energy routes toward class consciousness → Revolution (-1 ideology)

This creates a **bifurcation** in ideological space:

.. mermaid::

   flowchart TB
       A[Agitation Energy] --> B{SOLIDARITY<br/>Edge Present?}
       B -->|No| C[FASCISM<br/>+ideology +1.0]
       B -->|Yes| D[REVOLUTION<br/>-ideology -1.0]
       C --> E[National/Racial<br/>Identity]
       D --> F[Class<br/>Consciousness]

The Ideology Axis
-----------------

Babylon models ideology on a continuous scale:

.. list-table:: Ideology Scale
   :header-rows: 1
   :widths: 20 80

   * - Value
     - Meaning
   * - -1.0
     - Revolutionary class consciousness
   * - 0.0
     - Apolitical / acquiescent
   * - +1.0
     - National/racial identity (fascism)

The scale represents not moral value but **organizational allegiance**:

- Negative values → International proletarian solidarity
- Positive values → National/imperial identification

ConsciousnessTendency and the Three Directions
-----------------------------------------------

Feature 029 formalizes Jackson's insight into a per-community
``ConsciousnessTendency`` enum with three values that correspond to the
directions consciousness can take under crisis and repression:

**LIBERAL** — The default. Seeks inclusion in existing institutions
without transforming them. In Jackson's analysis, this is the dominant
tendency in communities whose material conditions have not yet forced a
break with the system. Most communities default to LIBERAL in the
simulation's initial state.

**FASCIST** — Collaboration with the hegemonic order for individual
escape. Jackson identified this as the tendency that emerges when
crisis hits but solidarity networks are absent — the agent seeks to
climb out of the marginalized category rather than destroy the
category itself. This maps to the +1 ideology direction in the
bifurcation model above.

**REVOLUTIONARY** — Oppositional collective identity, independent
power. The contradiction is material, not a misunderstanding. This
maps to the -1 ideology direction. In the simulation's default
consciousness values, only FIRST_NATIONS and INCARCERATED communities
start with REVOLUTIONARY tendency — communities whose material
experience has foreclosed the liberal option.

The ``CommunityConsciousness`` model adds two further dimensions:
``collective_identity`` (how strongly the community identifies as a
collective subject) and ``ideological_contestation`` (how actively the
three tendencies compete within the community). High contestation
communities are sites of ideological struggle; low contestation
communities have a settled dominant tendency.

See :doc:`consciousness-taxonomy` for the full model specification
and default values for all 14 community types.

Consciousness Drift Formula
---------------------------

Consciousness drift is calculated each tick:

.. math::

   \Delta I = k \cdot A \cdot D

Where:

- :math:`\Delta I` = Change in ideology
- :math:`k` = Drift sensitivity coefficient (from GameDefines)
- :math:`A` = Agitation level (from material conditions)
- :math:`D` = Direction (+1 or -1, determined by SOLIDARITY presence)

**Agitation Level:**

Agitation increases when:

- Wages fall below subsistence
- Wealth declines over time
- Imperial rent extraction intensifies

**Direction Determination:**

.. code-block:: python

   def determine_direction(class_node, graph):
       """Determine ideological direction from solidarity network."""
       solidarity_edges = [
           e for e in graph.edges(class_node)
           if graph.edges[e]["edge_type"] == EdgeType.SOLIDARITY
       ]
       if solidarity_edges:
           return -1  # Class consciousness
       else:
           return +1  # National identity

Empirical Validation
--------------------

The George Jackson model has been validated through parameter sweep
analysis with the following findings:

**Key Parameter: solidarity_decay_base**

.. list-table:: Sweep Results
   :header-rows: 1
   :widths: 20 40 40

   * - Decay Rate
     - Outcome
     - Ideology Range
   * - 0.90
     - Revolution (tick ~30)
     - [-1.0, -0.8]
   * - 0.95
     - Stalemate
     - [-0.5, 0.5]
   * - 0.99
     - Fascism (tick ~50)
     - [0.8, 1.0]

The solidarity decay rate determines whether class networks persist
long enough to route agitation toward revolution.

Historical Parallel
-------------------

The model captures the historical pattern observed by George Jackson
and other revolutionary theorists:

1. **Weimar Germany (1929-1933)**
   - Economic crisis (wages fell)
   - Weak KPD solidarity networks
   - Agitation routed → National Socialism

2. **Russia (1905-1917)**
   - Economic crisis (wages fell)
   - Strong Bolshevik organizational networks
   - Agitation routed → October Revolution

3. **USA (2008-2016)**
   - Economic crisis (wages stagnated)
   - Weak labor/socialist networks
   - Agitation routed → Trump/MAGA nationalism

Implementation
--------------

The bifurcation logic is implemented in the ConsciousnessSystem:

.. code-block:: python

   # src/babylon/engine/systems/ideology.py

   class ConsciousnessSystem:
       def process(self, graph, services, context):
           for node_id, data in graph.nodes(data=True):
               if data.get("_node_type") != "social_class":
                   continue

               # Calculate agitation from material conditions
               agitation = self._calculate_agitation(node_id, data, graph)

               # Determine direction from solidarity network
               direction = self._determine_direction(node_id, graph)

               # Apply consciousness drift
               drift = self.drift_sensitivity * agitation * direction
               new_ideology = clamp(data["ideology"] + drift, -1.0, 1.0)

               graph.nodes[node_id]["ideology"] = new_ideology

Key Parameters
--------------

The following ``GameDefines`` parameters control bifurcation behavior:

.. list-table:: Configuration Parameters
   :header-rows: 1
   :widths: 30 20 50

   * - Parameter
     - Default
     - Effect
   * - ``consciousness.drift_sensitivity_k``
     - 0.1
     - How fast ideology changes
   * - ``consciousness.agitation_threshold``
     - 0.3
     - Minimum agitation to trigger drift
   * - ``solidarity.decay_base``
     - 0.95
     - How fast SOLIDARITY edges decay
   * - ``solidarity.transmission_rate``
     - 0.1
     - How fast consciousness spreads

Strategic Implications
----------------------

For revolutionary movements in the simulation:

1. **Build SOLIDARITY edges early**
   Without organizational infrastructure, crisis will route to fascism.

2. **Maintain solidarity networks**
   Higher decay rates favor fascism; strong networks favor revolution.

3. **Crisis is necessary but not sufficient**
   Material degradation creates agitation, but organization determines
   its direction.


Consciousness-Weighted Bifurcation Topology
============================================

The basic George Jackson model (above) asks a binary question: "are SOLIDARITY
edges present?" Feature 033 extends this to ask a much more demanding question:
"is the solidarity *real* — or is it the kind that collapses under crisis?"

The answer requires consciousness weighting. Not all SOLIDARITY edges carry
equal revolutionary potential. A solidarity edge between two communities with
low collective identity (CI < 0.4) is structurally fragile — it represents
the Democratic Party coalition pattern, where cross-line alliances exist in
name but dissolve when material conditions demand sacrifice.

The Assimilation Trap
---------------------

Consider two scenarios with identical graph topology — 20 SOLIDARITY edges
crossing the colonial contradiction axis:

**Scenario A**: CI = 0.2 for all communities (assimilated).
Each edge's consciousness weight is near-zero. The solidarity
looks real in the raw graph but evaporates under the sigmoid transform.
Classification: **fascist**.

**Scenario B**: CI = 0.8 for marginalized communities (oppositional).
Each edge's consciousness weight is near-one. The solidarity is backed
by collective political identity that survives crisis.
Classification: **revolutionary**.

This is the assimilation trap. A naive analysis that counts edges without
weighting them by the consciousness of the connected communities will
misclassify the Democratic Party coalition as a revolutionary formation.
The consciousness sigmoid reveals what raw edge density conceals.

Feature 034 makes the assimilation trap concretely detectable. Solidarity
edges where both endpoints have revolutionary consciousness ``r < 0.3``
are marked **crisis-fragile** — they represent assimilated solidarity that
would collapse when material conditions demand sacrifice. The
:class:`~babylon.domain.bifurcation.types.BifurcationResult` tracks
``mean_assimilation_ratio_marginalized`` (mean ``f / (l + f)`` across
marginalized communities) and ``crisis_fragile_edge_count`` (how many
solidarity edges carry this marker). A high ratio of crisis-fragile to
total solidarity edges signals the assimilation trap quantitatively.
See :doc:`/concepts/ternary-consciousness` for the full ternary model.

Why the Sigmoid of Collective Identity
---------------------------------------

The relationship between collective identity and solidarity reliability is
not linear. A community with CI = 0.39 is qualitatively different from one
with CI = 0.41 — the first has not crossed the threshold where collective
identity translates into durable cross-line action.

The logistic sigmoid captures this breakage cliff:

.. math::

   w(CI) = \frac{1}{1 + e^{-k \cdot (CI - m)}}

Where :math:`k = 10` (steepness) and :math:`m = 0.4` (midpoint). This
produces:

- CI = 0.1: :math:`w \approx 0.05` (assimilated — near-zero weight)
- CI = 0.4: :math:`w = 0.50` (inflection — equal odds)
- CI = 0.7: :math:`w \approx 0.95` (oppositional — near-full weight)

The midpoint at 0.4 (below center) is deliberate. It reflects the MLM-TW
observation that assimilation is the default condition in the imperial core,
and oppositional identity requires active construction against that default.

The steepness at 10.0 matches the existing sigmoid in
:func:`~babylon.formulas.survival_calculus.calculate_acquiescence_probability`,
maintaining consistency across the codebase.

Solidarity edges are then weighted:

.. math::

   S_{weighted} = S_{strength} \times w(\min(CI_{source}, CI_{target}))

The ``min`` operation implements a weakest-link principle at the edge level:
a SOLIDARITY edge is only as reliable as the less-conscious community
at either end.

Per-Axis Contradiction Analysis
-------------------------------

The simple binary model asks "are solidarity edges present?" The
consciousness-weighted model asks a more specific question for *each
structural contradiction axis*:

   "Along this axis of oppression, does consciousness-weighted cross-line
   solidarity outweigh lateral antagonism?"

The system analyzes each ``ContradictionAxis`` (colonial, patriarchal, etc.)
independently. For each axis:

1. **Cross-line solidarity**: SOLIDARITY edges where one endpoint is in
   the hegemonic community and the other is in a marginalized community.
   Each edge is weighted by the consciousness sigmoid.

2. **Lateral antagonism**: EXPLOITATION, REPRESSION, and COMPETITION edges
   within the same side of the axis. These represent intra-group conflict
   that fragments solidarity potential.

3. **Tendency ratio**: The axis tendency is the ratio of consciousness-weighted
   cross-line solidarity to lateral antagonism (with an epsilon guard against
   division by zero):

.. math::

   R_{axis} = \frac{\sum S_{weighted}}{\sum A_{lateral} + \epsilon}

- :math:`R > 1.2`: solidarity-dominant on this axis
- :math:`0.8 < R < 1.2`: indeterminate (within dead zone)
- :math:`R < 0.8`: antagonism-dominant on this axis

The Weakest-Link Model
----------------------

After computing per-axis tendencies, the overall classification uses a
weakest-link model: if *any single* active axis is deeply antagonism-dominant,
the overall tendency is "fascist" — regardless of how strong solidarity is on
other axes.

This reflects the historical pattern that a single unresolved contradiction
(typically the national/colonial question) can derail an otherwise strong
revolutionary formation. The German KPD's failure to resolve the national
question enabled the Nazis to route working-class agitation toward
nationalism, even though the KPD had strong labor solidarity.

The classification logic has three tiers:

1. **No relevant edges at all** → "indeterminate" (nothing to analyze).
2. **Assimilation trap** → "fascist" (cross-line edges exist but their
   mean consciousness-weighted value falls below the filter threshold).
3. **Weakest-link on active axes** → if any axis below lower threshold,
   "fascist"; if all above upper threshold, "revolutionary"; otherwise
   "indeterminate".

Only axes that have edges are considered "active." An axis with zero
relevant edges (no solidarity and no lateral antagonism) is excluded
from classification to prevent false signals from structural absences.

Community Bridges and Orthogonal Solidarity
-------------------------------------------

Some communities exist orthogonal to the primary contradiction axes. The
DISABLED community, for instance, includes both settlers and New Afrikans.
The INCARCERATED community similarly spans the colonial axis. These communities
are potential bridges — their membership naturally crosses contradiction
boundaries.

The bridge potential is weighted by consciousness and infrastructure:

.. math::

   B_{potential} = infrastructure \times w(CI)

A bridge community with high CI and strong infrastructure (organizations,
communication networks, mutual aid) has high potential to transmit
solidarity across the axes it spans. A bridge community with low CI —
one whose members identify primarily with their position on the main axis
rather than with the shared condition — has near-zero bridge potential
regardless of infrastructure.

Only ``INSTITUTIONAL_EXCLUSION`` communities (DISABLED, INCARCERATED,
UNDOCUMENTED, UNHOUSED) qualify as bridge candidates, because their
membership is defined by a condition orthogonal to the hegemonic/marginalized
axis structure.

The Material Solidarity Ceiling
-------------------------------

Solidarity between agents with qualitatively different material conditions
faces a structural upper bound. Two agents whose wages differ by 10x live
in different worlds — their solidarity is limited by the material gap
regardless of subjective intent.

The solidarity ceiling is computed from:

- **Wage gap ratio**: Linear interpolation from ``wage_ceiling_max`` (0.9,
  at ratios < 2x) down to ``wage_ceiling_min`` (0.3, at ratios > 10x).
- **Shared exploitation bonus** (+0.2): If both agents are exploited by the
  same capitalist, shared oppression raises the ceiling.
- **Community bonus** (+0.05 per shared community): Shared marginalized
  community membership provides material basis for solidarity.

This captures the MLM-TW critique of "solidarity" between core and
periphery workers: when imperial rent creates a 10x wage gap, the
material basis for sustained solidarity is structurally limited.

Two-Pass Betti Numbers
----------------------

The topology of the solidarity network reveals structural properties that
edge counts alone cannot capture. Betti numbers provide two key metrics:

- :math:`\beta_0` = number of connected components (organizational cells)
- :math:`\beta_1` = cycle rank = :math:`|E| - |V| + \beta_0` (redundant paths)

The bifurcation analysis computes Betti numbers twice:

**Raw pass**: All SOLIDARITY edges included. This measures the naive
topology — what the network looks like if you take every solidarity
claim at face value.

**Filtered pass**: Only SOLIDARITY edges whose consciousness-weighted
value exceeds the filter threshold (0.2). This measures the *effective*
topology — what survives when you strip away assimilated solidarity.

The gap between raw and filtered Betti numbers reveals the assimilation
trap quantitatively. If :math:`\beta_0^{raw} = 1` (one connected component)
but :math:`\beta_0^{filtered} = 5` (five disconnected cells), the network
appears unified but is actually fragmented once you account for
consciousness. The "unity" is an artifact of assimilated edges that would
not survive crisis.

Legitimation Crisis Amplifier
-----------------------------

The territorial legitimation system (managed by the LifecycleSystem)
tracks how much state legitimacy each territory retains. When legitimation
falls, crises become more severe — Gramsci's interregnum where the old
cannot sustain itself and the new cannot yet be born.

The amplifier scales inversely with mean territorial legitimation:

.. math::

   A = 1 + (1 - \bar{L}) \times (s - 1)

Where :math:`\bar{L}` is population-weighted mean legitimation and
:math:`s = 2.0` is the amplifier scale. At full legitimation (:math:`\bar{L} = 1`),
the amplifier is 1.0 (no effect). At zero legitimation, the amplifier
reaches 2.0 — crisis intensity doubles.

This connects the bifurcation topology to the broader simulation state:
even if solidarity networks are strong, a legitimation crisis amplifies
the stakes, making the difference between fascism and revolution sharper
and the outcome more decisive.


See Also
--------

- :doc:`consciousness-taxonomy` -- Three-category taxonomy and consciousness model
- :doc:`/concepts/survival-calculus` -- How agents choose acquiescence vs revolution
- :doc:`/concepts/topology` -- SOLIDARITY edge dynamics
- :doc:`/concepts/percolation-theory` -- Network condensation and resilience
- :doc:`/reference/formulas` -- Complete formula reference
- :doc:`/reference/topology` -- Bifurcation analysis API reference
- :doc:`/reference/configuration` -- GameDefines parameters
- :py:mod:`babylon.engine.systems.ideology` -- Consciousness drift implementation
- :py:mod:`babylon.domain.bifurcation` -- Bifurcation topology analysis package
