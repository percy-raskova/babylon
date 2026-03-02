Unified Class System
====================

Feature 038 integrates community-hyperedge-aware classification,
dual-criteria validation, and class-differentiated lifecycle mechanics
into a single coherent class system. This document explains the
theoretical reasoning behind each component.

.. contents:: On this page
   :local:
   :depth: 2

The Two-Criteria Problem
------------------------

The existing class position classifier (Feature 013) assigns households
to one of five ``ClassPosition`` values based on wealth percentile
thresholds. This is a necessary simplification: wealth stock is the
primary determinant of a household's relationship to the means of
production.

But a single criterion is insufficient for calibration. Two households
at the 65th wealth percentile may have very different relationships to
value production. One may produce far more value than they consume
(surplus-extracting, bourgeois-relation); the other may consume more
than they produce (dependent, lumpen-relation). The wealth criterion
alone cannot distinguish them.

The **accounting criterion** resolves this by comparing value produced
(:math:`V_{\text{produced}}`) to value required for household
reproduction (:math:`V_{\text{reproduction}}`):

.. math::

   R = \frac{V_{\text{produced}}}{V_{\text{reproduction}}}

The ratio maps to class positions:

- :math:`R \geq 1.5` --- bourgeois-relation (surplus extraction)
- :math:`1.2 \leq R < 1.5` --- petit-bourgeois (simple reproduction
  with buffer)
- :math:`0.8 \leq R < 1.2` --- proletarian (simple reproduction)
- :math:`0.5 \leq R < 0.8` --- proletarian (below reproduction)
- :math:`R < 0.5` --- lumpen-relation (dependent)

When both criteria agree, the classification is high-confidence. When
they disagree, the disagreement magnitude signals calibration drift ---
either the wealth thresholds need adjustment or the accounting data is
stale. This is a *diagnostic tool*, not a tiebreaker: the wealth
criterion remains authoritative for gameplay.

Community Filtration as Structural Modification
-----------------------------------------------

Four community types trigger filtration predicates that modify
classification inputs *before* the base classifier runs. These are not
post-hoc "corrections" applied to a universal classification. They
recognize that certain community memberships place households in
structurally different relationships to property, labor markets, and
the state.

**FIRST_NATIONS** applies a trust land discount to effective wealth.
Reservation property operates under federal trust, not fee simple.
It cannot be sold on the open market, used as collateral, or
accumulated through appreciation in the same way as settler property.
A household at the 70th wealth percentile on trust land does not have
the same effective wealth as a settler household at the 70th percentile.
The discount (default 0.5) reduces the effective wealth percentile
before classification.

**INCARCERATED** overrides precarity to ``EXCLUDED``. Incarceration
severs labor market participation completely. Regardless of prior wealth
or employment history, an incarcerated household member cannot sell
labor-power. This is not precarity (unstable attachment to the labor
market) but exclusion (no attachment at all).

**UNDOCUMENTED** applies both a wealth discount and a precarity floor.
Legal exclusion from formal banking, property ownership protections,
and labor market regulations means that documented wealth overstates
effective economic power. The documentation exclusion factor (default
0.6) reduces effective wealth. The precarity floor (``PRECARIOUS``
minimum) recognizes that undocumented workers are structurally
precarious regardless of current employment stability --- any
interaction with the state can terminate employment.

**DISABLED** inflates reproduction costs. When a ``CommunityState``
has ``reproduction_cost_modifier > 1.0``, it indicates that the
community's members face higher costs for the same standard of
reproduction (accessibility requirements, medical costs, assistive
technology). The effective wealth is divided by this modifier, reducing
the household's position relative to their reproduction threshold.

**Composition**: when multiple predicates apply (e.g., FIRST_NATIONS
and DISABLED), each evaluates independently against the *original*
inputs, and the most restrictive composite result applies. "Most
restrictive" means lowest effective wealth and highest precarity
severity. This prevents ordering effects: the result is the same
regardless of which predicate is evaluated first.

Class-Pair Solidarity Matrix
----------------------------

The solidarity potential formula (Feature 022) computes how much
solidarity *could* form between two agents based on shared community
membership and imperial rent differential. The formula takes a
``base_solidarity`` parameter:

.. math::

   SP = S_{\text{base}} + \beta \cdot N_{\text{shared}}
        - \gamma \cdot |\Phi_a - \Phi_b|

where :math:`S_{\text{base}}` is base class solidarity,
:math:`N_{\text{shared}}` is shared community count, and
:math:`|\Phi_a - \Phi_b|` is the rent differential.

Before Feature 038, ``base_solidarity`` was a flat constant. But
solidarity potential varies by class pairing. Two proletarian
households have a higher baseline for solidarity formation than a
bourgeois household and a proletarian household, because their material
interests align more closely.

The **class-pair solidarity matrix** is a symmetric 5x5 matrix stored
in ``ClassSystemDefines.base_class_solidarity``. The upper triangle
(15 unique values including diagonal):

- **PROLETARIAT--PROLETARIAT**: 0.80 (highest --- shared exploitation)
- **BOURGEOISIE--BOURGEOISIE**: 0.70 (class cohesion via shared interests)
- **LUMPENPROLETARIAT--LUMPENPROLETARIAT**: 0.60 (mutual aid under exclusion)
- **LABOR_ARISTOCRACY--LABOR_ARISTOCRACY**: 0.60 (shared position)
- **PETIT_BOURGEOISIE--PETIT_BOURGEOISIE**: 0.50 (individualist competition)
- **LUMPENPROLETARIAT--PROLETARIAT**: 0.50 (proximity, shared precarity)
- **LABOR_ARISTOCRACY--PETIT_BOURGEOISIE**: 0.40 (aspirational alignment)
- **LABOR_ARISTOCRACY--PROLETARIAT**: 0.30 (same class, different rent access)
- **PETIT_BOURGEOISIE--BOURGEOISIE**: 0.30 (aspirational identification)
- **PETIT_BOURGEOISIE--PROLETARIAT**: 0.15 (limited shared interests)
- **LABOR_ARISTOCRACY--BOURGEOISIE**: 0.10 (rent-mediated alignment)
- **LABOR_ARISTOCRACY--LUMPENPROLETARIAT**: 0.10 (distance)
- **PETIT_BOURGEOISIE--LUMPENPROLETARIAT**: 0.05 (class contempt)
- **BOURGEOISIE--PROLETARIAT**: 0.00 (antagonism)
- **BOURGEOISIE--LUMPENPROLETARIAT**: 0.00 (antagonism)

The matrix feeds into bifurcation dynamics: low base solidarity between
class pairs means that community overlap and rent convergence must do
more work to create conditions for cross-class solidarity. When they
fail, the bifurcation routes toward fascism rather than revolution.

National Rent Differential
--------------------------

Imperial rent theory (Feature 013, the economics pipeline) models
extraction at the national level: core workers receive more value than
they produce, with the difference extracted from the periphery. But
within the core, rent is not distributed equally. **Internally
colonized populations** --- New Afrikan, First Nations, Chicano ---
receive less rent than settler workers in the same occupation at the
same location.

The **rent differential calculator** operationalizes this by measuring
wage gaps from ACS (American Community Survey) earnings data. For a
given county, NAICS sector, and nation:

.. math::

   \Phi_{\text{diff}} = W_{\text{settler}} - W_{\text{nation}}

Positive values indicate settler advantage (the standard case).
County-level aggregation weights NAICS-specific differentials by
employment composition from QCEW data, producing a single
employment-weighted average differential per county-nation pair.

The SETTLER nation's self-differential is always zero (no gap with
itself). Suppressed ACS data (small sample sizes below the Census
disclosure threshold) propagates ``NoDataSentinel`` rather than
imputing values --- the absence of data is itself informative and
must not be masked by synthetic values.

The **Detroit validation case** confirms the internal colony thesis:
Wayne County (Detroit proper) shows larger rent differentials than
Oakland County (suburbs), because the extractive relationship
between settler capital and the New Afrikan population is more
direct in the urban core where that population is concentrated.

Class Reproduction via Inheritance and Dispossession
----------------------------------------------------

Class position reproduces across generations through two mechanisms:
inheritance (wealth transfer) and dispossession (wealth destruction).
Both are class-differentiated.

**Inheritance** scales by class position because different classes hold
wealth in different forms. Bourgeois households transfer full estates
(scale 1.0). Petit-bourgeois households transfer business capital
(scale 0.7). Labor aristocracy households transfer home equity --- the
primary vehicle of intergenerational wealth for this class (scale 0.5).
Proletarian households transfer near-zero (scale 0.05): their wealth
is consumed by reproduction. Lumpenproletarian households transfer
nothing (scale 0.0).

**Foreclosure** severs the inheritance mechanism entirely. When a
household is foreclosed, the home equity that would have been the
inheritance vehicle is destroyed. The inheritance flow returns zero
net inheritance regardless of class position. This models the 2008
crisis dynamic where Black and Latino homeowners (disproportionately
labor aristocracy) lost the primary mechanism of intergenerational
class reproduction.

**Crisis dispossession** models wealth destruction events (foreclosure,
eviction) with a community-modifiable targeting multiplier. The base
foreclosure rate is a crisis parameter; the ``community_targeting_multiplier``
captures racialized targeting (e.g., subprime lending concentrated in
Black neighborhoods). When remaining wealth drops below 50% of original,
a class position change is indicated --- the LA-to-proletariat transition
that destroys the household's claim to imperial rent.

Wealth conservation is enforced: ``wealth_destroyed + remaining_wealth``
must equal the original ``household_wealth``. Dispossession redistributes
wealth upward (to creditors, banks); it does not destroy it at the
system level.

Fractal Consistency
-------------------

The Unified Class System must produce coherent classifications at
every geographic resolution. The same ``ClassPosition`` enum, the same
thresholds, and the same filtration predicates apply whether
classifying a single household, a county, or a metro area. This
is the **fractal consistency** requirement.

Concretely, fractal consistency validation checks that:

1. Each county in a metro area has all five class positions represented
   (no county is so homogeneous that entire positions vanish).
2. County-level distributions sum to approximately 1.0.
3. The metro-level aggregate (population-weighted average across
   counties) is itself a valid distribution.

This ensures that the internal colony thesis holds at every zoom level:
Wayne County and Oakland County each have their own class structure,
and the metro-level aggregate reflects the combined structure rather
than erasing county-level variation.

See Also
--------

- :doc:`/reference/unified-class-system` --- Complete API reference,
  data models, and configuration parameters
- :doc:`economics-pipeline-theory` --- Economics pipeline and class
  position thresholds
- :doc:`dpd-lifecycle-circuit` --- D-P-D' lifecycle and inheritance
  mechanics
- :doc:`community-hypergraph` --- Hypergraph layer and solidarity
  potential
- :doc:`imperial-rent` --- Imperial rent theory
- :doc:`/reference/community-system` --- Community system API
  (solidarity potential formula)
