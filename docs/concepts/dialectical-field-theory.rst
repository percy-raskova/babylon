Dialectical Field Topology: Contradictions as Fields
=====================================================

The dialectical field topology system formalizes Mao Zedong's *On
Contradiction* (1937) as computable field operations on the simulation
graph. This document explains the theoretical foundation, why the
formalization works, and what it reveals about the dynamics of class
struggle.

.. contents:: On this page
   :local:
   :depth: 2

The Problem: Bridging Quantity and Quality
------------------------------------------

Classical dialectical materialism asserts that quantitative
accumulation gives rise to qualitative change — water heated
gradually boils suddenly; wages compressed gradually produce a
strike wave. But Babylon's simulation engine originally modeled
these as separate concerns: systems compute continuous quantities
(exploitation rate, wages, consciousness) while separate threshold
checks trigger discrete state changes (crisis, uprising, phase
transition).

This separation is theoretically impoverished. It cannot answer:

- *Where* do contradictions concentrate in the graph?
- *How fast* is a contradiction intensifying (character)?
- *Is it accelerating* (tendency toward antagonism)?
- *Why* does a qualitative transition happen at this node and not
  that one?
- *What topology* makes some contradictions persist while others
  dissipate?

The dialectical field framework answers all five by treating
contradictions as scalar fields on the graph and recovering
Mao's dialectical categories from the field's spatial and temporal
derivatives.

From Mao to Mathematics
------------------------

The key theoretical insight is that every concept in *On
Contradiction* has a direct mathematical analogue in field theory:

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Dialectical Category
     - Mathematical Analogue
     - Computed From
   * - Magnitude of contradiction
     - Field value f(i, t)
     - Economic calculators
   * - Character (intensifying / sublating)
     - Temporal first derivative df/dt
     - Finite differences
   * - Tendency toward antagonism
     - Temporal second derivative d²f/dt²
     - Finite differences
   * - Spatial concentration
     - Graph Laplacian Δf(i)
     - Neighbor differences
   * - Topological character
     - Ollivier-Ricci curvature κ(e)
     - Optimal transport
   * - Qualitative transition
     - Compound predicate firing
     - Threshold conditions

This is not a metaphor. These mathematical operations *are* the
dialectical categories, formalized on a graph rather than a
continuous manifold. The graph Laplacian of the exploitation field
at a node literally tells you whether that node is a pressure peak
(negative Laplacian — contradiction concentrated here more than
at neighbors) or a pressure trough (positive Laplacian —
contradiction flowing away).

The Four Contradiction Fields
-----------------------------

Exploitation
~~~~~~~~~~~~

Derived from the exploitation rate *e = s/v* (surplus value over
variable capital). Computed as the wealth deficit relative to
subsistence needs: ``(subsistence - wealth) / subsistence``.

High exploitation contradiction means the node is being
exploited beyond its subsistence threshold — the classical
condition for proletarian consciousness.

In the Detroit case study, Wayne County proletariat nodes
consistently show higher exploitation contradiction than Oakland
County nodes, reflecting the empirical wage and employment
differential. The Laplacian at Wayne is negative (pressure peak);
at Oakland it is positive or near-zero (contradiction flows
outward from the exploitation center).

Immiseration
~~~~~~~~~~~~

Derived from the *rate of change* of wealth — specifically, the
fraction of previous wealth that has been lost:
``(prev_wealth - wealth) / prev_wealth``.

Immiseration captures the *experience* of declining material
conditions, distinct from the absolute level of exploitation. A
worker with stable poverty has high exploitation but low
immiseration; a worker whose wages were just cut has both.

This distinction matters for consciousness dynamics: immiseration
produces more immediate political response than static
exploitation because it disrupts expectations. Marx calls this
the difference between "absolute" and "relative" impoverishment.

Imperial Rent
~~~~~~~~~~~~~

Derived directly from the ``unearned_increment`` node attribute —
the PPP bonus that marks a node as benefiting from imperial
rent extraction. Uses a saturating exponential normalization
(``10 × (1 - e^{-x/10})``) to handle the unbounded raw values.

Imperial rent contradiction captures the degree to which a node
*benefits* from the imperial system. High values indicate labor
aristocracy — nodes whose material interests are structurally
aligned with imperialism. These nodes resist revolutionary
consciousness not because of "false consciousness" but because
their material conditions genuinely benefit from the status quo.

When imperial rent declines (declining extraction from
periphery), the imperial rent contradiction field drops, which
can trigger transitions from CO-OPTIVE to ANTAGONISTIC as the
material basis for co-optation erodes.

Displacement
~~~~~~~~~~~~

Derived from population change rate:
``(prev_population - population) / prev_population``.

Displacement captures the spatial dynamics of capital — where
people are being pushed out. In the Detroit case study, Wayne
County shows high displacement (population loss from
foreclosure, eviction, gentrification), while Oakland County
shows lower or negative displacement (population gain from
in-migration of displaced Wayne residents and suburban growth).

The gradient of the displacement field along the Wayne-to-Oakland
edge captures the direction and intensity of population flow
driven by capital accumulation.

Spatial Derivatives: Where Contradictions Concentrate
-----------------------------------------------------

The Gradient
~~~~~~~~~~~~

The gradient along an edge tells you whether contradiction is
*increasing* or *decreasing* as you move along that relationship.
A negative exploitation gradient from Wayne to Oakland means
exploitation decreases as you move from the periphery to the
core of the Detroit metro area — the fundamental spatial structure
of unequal exchange operating within a single metropolitan area.

Gradients are directional and signed. The simulation computes
them for every edge and every field each tick, creating a
complete picture of how contradictions are distributed across
the social graph.

The Graph Laplacian
~~~~~~~~~~~~~~~~~~~

The Laplacian tells you whether a node is a pressure peak or
trough relative to its neighbors. It is the discrete analogue
of the continuous Laplacian operator in physics — the divergence
of the gradient.

**Negative Laplacian** means the node has higher contradiction
than its neighbors. This is a *pressure peak* — contradictions
are concentrated here. In physical terms, this node is under
more stress than its surroundings. Wayne County proletariat
consistently shows negative exploitation Laplacian.

**Positive Laplacian** means the node has lower contradiction
than its neighbors. This is a *pressure trough* — the node is
relatively sheltered. Oakland County petit bourgeoisie typically
shows positive or near-zero exploitation Laplacian.

The Laplacian is critical for compound predicates: a transition
from EXTRACTIVE to ANTAGONISTIC requires not just high
exploitation (magnitude) and rising exploitation (positive
df/dt) but also concentration (negative Laplacian). All three
conditions must converge at the same node for the qualitative
transition to fire.

Ollivier-Ricci Curvature
~~~~~~~~~~~~~~~~~~~~~~~~

Curvature measures the *topological character* of each edge:
whether it connects two well-clustered neighborhoods (positive
curvature — redundant paths, resilient to disruption) or serves
as a bridge between sparse regions (negative curvature —
bottleneck, fragile).

Curvature matters for contradiction dynamics because:

- **Bottleneck edges** (κ < 0) sustain steeper gradients. A
  contradiction differential across a bottleneck persists because
  there are no alternative paths for equalization. The single
  bridge between two communities concentrates all the tension.

- **Redundant edges** (κ > 0) allow gradients to dissipate. When
  multiple paths connect two neighborhoods, contradiction flows
  through all of them, preventing sharp concentration at any
  single point.

This connects to organizing strategy: revolutionary movements
must build solidarity bridges (increasing κ) across divisions
that capital exploits as bottlenecks (low κ). The topological
structure of the solidarity graph determines whether
contradictions concentrate into explosive rupture or dissipate
into manageable tensions.

Temporal Derivatives: How Fast and in What Direction
----------------------------------------------------

The first derivative df/dt captures the *character* of the
contradiction — whether it is intensifying (positive df/dt) or
being sublated (negative df/dt). This is the most important
quantity in the entire system because it determines the
**principal contradiction**: the field with the largest maximum
\|df/dt\| across all nodes at a given tick.

The second derivative d²f/dt² captures the *tendency* — whether
intensification is accelerating (positive d²f/dt²) or
decelerating (negative d²f/dt²). Accelerating intensification
is the signature of approaching crisis: not just getting worse,
but getting worse *faster*.

The interaction between first and second derivatives maps onto
Mao's analysis of contradiction development:

- **df/dt > 0, d²f/dt² > 0**: Contradiction intensifying and
  accelerating — crisis approaching
- **df/dt > 0, d²f/dt² < 0**: Contradiction still intensifying
  but decelerating — reform may be working
- **df/dt < 0, d²f/dt² > 0**: Contradiction being resolved but
  deceleration is slowing — partial resolution, may reverse
- **df/dt < 0, d²f/dt² < 0**: Contradiction being rapidly
  resolved — qualitative change or successful intervention

The Principal Contradiction
---------------------------

Mao's concept of the *principal contradiction* — the contradiction
that determines the character of the entire period — is formalized
as the field with the largest maximum \|df/dt\| across all nodes.
This is not the *biggest* contradiction but the *fastest-changing*
one, because a large static contradiction is less politically
significant than a smaller one that is rapidly intensifying.

When the principal contradiction shifts (e.g., from exploitation
to displacement during a gentrification wave), this represents a
qualitative change in the political terrain. The simulation records
these shifts as ``PRINCIPAL_CONTRADICTION_SHIFT`` events.

Tie-breaking uses total magnitude (Σ\|df/dt\|), then structural
primacy (exploitation preferred) — reflecting Marx's claim that the
exploitation relation is the foundational contradiction of
capitalist society even when other contradictions temporarily
dominate the political landscape.

CO-OPTIVE Edges: The Theory of Co-optation
------------------------------------------

The CO-OPTIVE edge mode is the most theoretically significant
addition. It models relationships where the more powerful party
offers material concessions to prevent resistance — imperial rent
to labor aristocracy, welfare state to working class, reform as a
mechanism of fascist stabilization.

The New Deal Analogy
~~~~~~~~~~~~~~~~~~~~

Consider the historical example: the post-war American settlement
(1945–1973) was a CO-OPTIVE arrangement. Capital offered high
wages, benefits, and suburban homeownership to the white working
class in exchange for anti-communism, racial solidarity with
capital against Black and Third World liberation movements, and
political quiescence regarding the fundamental exploitation
relation.

In the simulation, this is modeled as a CO-OPTIVE edge that
*suppresses* the exploitation contradiction's temporal derivative.
The exploitation exists — surplus value is still being extracted —
but its *rate of change* is masked by rising living standards.
The principal contradiction during stable co-optation appears to
be something other than exploitation (perhaps displacement, as
suburbanization displaces the contradiction from workplaces to
spatial segregation).

The Breakdown
~~~~~~~~~~~~~

When the material basis for co-optation erodes — declining imperial
rent from periphery, rising costs, austerity — the CO-OPTIVE edge
can no longer be maintained. The transition from CO-OPTIVE to
ANTAGONISTIC releases the **latent contradiction**: all the
suppressed df/dt accumulated during the co-optation period is
released as a spike, multiplied by 1.5 (configurable) to model
the political whiplash of "suddenly" discovering exploitation that
was there all along.

This is the "return of the repressed" — exploitation reasserts
itself as the principal contradiction, producing the
characteristic political disorientation of a population that
thought it had transcended class struggle.

The George Jackson Bifurcation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The direction of the resulting antagonism is determined by the
solidarity topology at the moment of breakdown:

**Revolutionary outcome**: If the co-opted node has more
solidarity connections *across the colonial divide* (with
oppressed nations, international proletariat) than *within its
group* (racial/national solidarity with capital), the antagonism
is directed upward — against the system that extracted surplus
while offering concessions.

**Fascist outcome**: If the co-opted node has more *within-group*
solidarity (racial solidarity, national chauvinism) than
*cross-divide* solidarity, the antagonism is directed laterally —
against other workers, immigrants, oppressed nations — while
leaving the fundamental exploitation relation intact.

This is the George Jackson bifurcation formalized on the graph:
the same material conditions (collapse of co-optation, rising
exploitation) produce opposite political outcomes depending
entirely on the topology of solidarity at the moment of crisis.

Compound Predicates: Declarative Transition Logic
-------------------------------------------------

Edge mode transitions are governed by compound predicates —
conjunctions of threshold conditions over field values and
derivatives. This replaces ad hoc threshold checks in the tick
loop with a unified, extensible framework.

A transition fires only when **all** conditions are met
simultaneously. This captures the dialectical insight that
qualitative change requires the convergence of multiple factors:
high exploitation (magnitude) + rising exploitation (positive
derivative) + concentration (negative Laplacian) + bottleneck
topology (negative curvature).

Any single condition unmet prevents the transition — high
exploitation alone doesn't produce rupture if it's stable, and
rising exploitation doesn't produce rupture if it's spatially
diffuse rather than concentrated.

Detroit as Empirical Validation
-------------------------------

The field framework makes specific, falsifiable predictions about
the Detroit metropolitan area:

**Exploitation gradient**: The exploitation field gradient along
the Wayne-to-Oakland edge should be negative (exploitation
decreasing from periphery to core), consistent with the empirical
wage and employment differential.

**Laplacian structure**: Wayne County proletariat should show
consistently negative Laplacian (pressure peak), Oakland County
petit bourgeoisie positive or near-zero.

**Principal contradiction shift**: The dominant field should shift
from exploitation (2010–2014, post-crisis austerity) to
displacement (2015–2020, gentrification wave), identifiable by
crossover in max \|df/dt\|.

**CO-OPTIVE breakdown correlation**: The erosion of New Deal-era
co-optation (public sector austerity, foreclosure crisis, welfare
state retrenchment) should correlate with the spike in exploitation
df/dt that reasserts exploitation as the principal contradiction
in the Wayne County subgraph.

**Curvature and gradient persistence**: Edges with negative
Ollivier-Ricci curvature (bottleneck topology between Wayne and
Oakland) should sustain steeper contradiction gradients than edges
with positive curvature (within Oakland's redundant suburban
topology).

See Also
--------

- :doc:`/reference/dialectical-field-topology` — Data types,
  formulas, parameters, state machine
- :doc:`/concepts/george-jackson-model` — Consciousness
  bifurcation dynamics
- :doc:`/concepts/imperial-rent` — Imperial rent extraction
- :doc:`/concepts/percolation-theory` — Topology and phase
  transitions
- :doc:`/concepts/topology` — Graph topology concepts
