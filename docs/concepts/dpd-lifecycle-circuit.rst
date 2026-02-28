D-P-D' Lifecycle Circuit
========================

Why Babylon models intergenerational class reproduction as two
interlocking circuits, and what happens when material stress forces
them to desynchronize.

The Individual Lifecycle: D-P-D'
--------------------------------

Every person in the simulation traverses three phases exactly once:

**D (Dependent, pre-productive)** -- children and adolescents who
receive socialization but produce no value. They consume household
resources funded by P-phase labor.

**P (Productive)** -- working-age adults who sell labor-power. This
is where the daily :math:`C\text{-}M\text{-}C` circuit (labor for
wages for subsistence) operates. The P phase is the engine of value
production and the site of exploitation.

**D' (Dependent, post-productive)** -- elderly, disabled, retired
persons who no longer sell labor-power. Their material security depends
on the *legitimation bargain*: the promise that exploitation endured
during P will be compensated by security in D'.

The notation mirrors Marx's circuit algebra deliberately. Just as
:math:`C\text{-}M\text{-}C` describes the worker's daily exchange and
:math:`M\text{-}C\text{-}M'` describes capital's self-expansion, the
lifecycle phases map the temporal arc of labor-power from production
to exhaustion.

Each tick, population flows between phases:

.. math::

   \text{births} = \text{birth\_rate} \times \text{pop}_P

   D \xrightarrow{\text{rate}_{D \to P}} P
   \xrightarrow{\text{rate}_{P \to D'}} D'
   \xrightarrow{\text{rate}_{D' \to \text{death}}} \varnothing

Conservation holds: births enter D, deaths exit D', and all transitions
are rate-proportional. The system tracks aggregate cohort populations,
not individual agents -- a deliberate computational tractability choice
that preserves the class-level dynamics without agent-level overhead.

The Class Reproduction Circuit: P-D-P'
---------------------------------------

The individual circuit is finite. But the class is not. This
generation's productive workers (P) raise the next generation's
dependents (D of generation 2), who become the next generation's
workers (P of generation 2). The class perpetuates via the reproductive
circuit :math:`P_{g1} \to D_{g2} \to P_{g2}`.

The individual traverses D-P-D' once. The class traverses P-D-P'
indefinitely. This distinction is the deepest theoretical commitment
of the feature: the individual lifecycle is a line segment; class
reproduction is a spiral.

Capital benefits from both circuits without paying for either. The
**shadow subsidy** -- the difference between the value of P-generation-2
labor-power and the wages paid to P-generation-1 for raising
D-generation-2 -- measures the unpaid reproductive labor externalized
to households. This is the lifecycle analogue of the daily Department
III gamma visibility shadow subsidy (see :doc:`reproductive-labor`).

The Legitimation Bargain
------------------------

The D' phase depends on a social promise: endure exploitation in P and
you will be secure in D'. This promise is not psychological. It is
material, and the simulation measures it with a weighted legitimation
index computed from five observable conditions:

1. **Home ownership rate** (weight 0.35) -- the largest store of
   household wealth for most workers
2. **Healthcare security** (weight 0.30) -- whether D' medical costs
   are survivable
3. **Retirement confidence** (weight 0.20) -- subjective assessment
   of D' security
4. **Pension coverage** (weight 0.10) -- employer-provided retirement
   access
5. **Social Security replacement rate** (weight 0.05) -- federal
   floor under D' income

The weight ordering is a design invariant reflecting authorial political
judgment: home ownership matters more than pensions, which matter more
than Social Security. Individual values are tunable in
:py:class:`~babylon.config.defines.LifecycleDefines`; the ordinal
ranking is not.

The legitimation index classifies each county into one of three
regimes:

- **CRISIS** (index < 0.3): The D' promise is not credible. Agitation
  energy routes to the George Jackson bifurcation (see
  :doc:`george-jackson-model`).
- **UNSTABLE** (0.3 <= index < 0.5): The D' promise is weakening.
  Risk accumulates.
- **STABLE** (index >= 0.5): The D' promise is credible. Acquiescence
  is maintained.

When the legitimation index is blended with agitation-inverse and fed
into the bifurcation system, it creates a feedback loop: material
deterioration of D' conditions reduces legitimation, which increases
agitation, which feeds the George Jackson bifurcation, which determines
whether consciousness routes toward revolution or fascism.

Dual Circuit Interference
-------------------------

The two circuits -- D-P-D' (individual) and P-D-P' (class) -- run
simultaneously. Under normal conditions they are synchronized: P-phase
workers earn enough to fund both their own D' security and the next
generation's D socialization. Under material stress, they desynchronize.

Five interference phenomena emerge:

**Intergenerational austerity trap.** When wage extraction accelerates,
P-phase workers face a zero-sum choice: fund their own D' security
*or* invest in D-generation-2 child-rearing. They cannot do both.
The individual circuit and the class circuit compete for the same
finite resource pool.

**Shadow subsidy extraction.** Capital receives fully-formed P-generation-2
workers without paying the cost of D-generation-2 socialization. The
generational shadow subsidy measures this gap. When it widens, households
absorb more of the cost of producing labor-power while capital captures
more of its value -- the lifecycle dimension of increasing exploitation.

**Dispossession short-circuit.** Foreclosure or pension default extracts
wealth from P-generation-1 and routes it to capital rather than through
the P-D-P' inheritance pathway to D-generation-2. A single dispossession
event simultaneously degrades D' security (individual circuit) *and*
destroys the inheritance pathway (class circuit). This duality --
hitting both circuits at once -- is the core mechanism by which
financial crisis converts into intergenerational class degradation.

**Legitimation-fertility nexus.** When the D' promise collapses, workers
respond in both circuits: in D-P-D', agitation increases (George Jackson
bifurcation); in P-D-P', birth rates fall (it becomes irrational to
raise children for a system that will not care for you). This creates
a demographic feedback: legitimation crisis reduces reproduction,
which alters the dependency ratio, which further stresses the D'
promise.

**Sandwich squeeze.** When both D' (elderly parents) and D-generation-2
(children) simultaneously depend on P-phase workers, the *sandwich
generation* effect degrades both current D' security and
next-generation class mobility outcomes. The dependency ratio
:math:`(D + D') / P` measures this burden directly.

Inheritance and Class Mobility
------------------------------

At the D' terminus, dying cohort members transfer wealth to the next
generation. This transfer follows a Pareto distribution (shape
:math:`\alpha = 1.5`, from the Federal Survey of Consumer Finances)
where the top 1% owns approximately 33% of transferable wealth.

The resulting inheritance Gini is computed directly:

.. math::

   G_{\text{inherit}} = \frac{1}{2\alpha - 1}

At :math:`\alpha = 1.5`, this yields :math:`G = 0.5` -- inheritance is
always more unequal than income for the same county.

But inheritance does not flow freely. End-of-life care costs consume
a fraction (default 40%) of D' wealth before it can transfer. The
bottom 50% of families inherit net zero or negative -- this emerges
from the Pareto distribution, not from imposed per-class fractions.

Class mobility at the D-to-P transition is calibrated from Raj Chetty's
Opportunity Atlas. A child born in the bottom income quartile has a
44.5% probability of reaching the median (KFR pooled at P25). But this
rate is not uniform: Black children face a 13.4 percentage-point gap,
incarceration multiplies the premature exit rate by 2.8x, and early
mortality multiplies it by 1.24x. These are structural modifiers on
the D-to-P transition that reproduce inequality across generations
through the class circuit itself.

Ideology Transmission
---------------------

The D-to-P transition is not only economic. When children enter the
productive phase, they carry ideology formed during the D phase.
This ideology is a blend of two influences:

- **Caregiver influence** (weight 0.7): family and community consciousness
- **Institutional hegemony** (weight 0.3): schools, media, state apparatus

The transmitted ideology regresses toward the population mean (regression
coefficient 0.4), reflecting the empirical reality that children's
political consciousness partially converges toward the social center,
not fully reproducing parental extremism.

This mechanism is how revolutionary consciousness can -- or cannot --
transmit across generations. If P-generation-1 achieves revolutionary
consciousness, caregiver influence transmits 70% of it to D-generation-2.
But institutional hegemony pushes back, and regression toward the mean
further dampens the signal. The net effect: revolutionary consciousness
requires *sustained* intergenerational organizing, not a single generation
of awakening.

Integration With Existing Systems
---------------------------------

The lifecycle circuit does not operate in isolation. It feeds into and
draws from several existing systems:

The **SurvivalSystem** uses the dependency ratio to modify subsistence
burden. Counties with higher dependency ratios impose higher effective
subsistence thresholds on P-phase workers, reducing wealth accumulation
and P(S|A) -- the probability of survival through acquiescence.

The **ConsciousnessSystem** receives legitimation crisis events. When
legitimation drops below the crisis threshold, the resulting agitation
feeds the George Jackson bifurcation, routing consciousness toward
either revolution or fascism based on solidarity edge presence.

The **CommunitySystem** maintains the hypergraph layer where lifecycle
phase communities (YOUTH, ADULT, ELDER from Feature 029) provide the
qualitative membership structure. The lifecycle system provides the
quantitative population dynamics that sit alongside these hyperedges.

See Also
--------

- :doc:`/reference/lifecycle-system` -- Complete data model and formula reference
- :doc:`george-jackson-model` -- Bifurcation and consciousness routing
- :doc:`community-hypergraph` -- Hypergraph layer for lifecycle communities
- :doc:`survival-calculus` -- P(S|A) and P(S|R) survival probabilities
- :doc:`reproductive-labor` -- Department III gamma visibility and shadow subsidies
- :doc:`imperial-rent` -- Imperial rent extraction framework
