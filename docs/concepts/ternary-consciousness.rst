Ternary Consciousness Model
===========================

Why does Babylon model consciousness as a ternary simplex, and what does
this enable?

Feature 034 replaces the stipulated scalar ``CommunityConsciousness``
(three independent fields) with a **2-simplex model** where
``r + l + f = 1.0``. This document explains the theoretical motivation,
the geometric structure, and the design trade-offs.

.. contents:: On this page
   :local:
   :depth: 2

The Problem with Stipulated Consciousness
------------------------------------------

The original consciousness model (Features 022 and 029) stored three
independent fields per community:

- ``collective_identity`` — oppositional consciousness [0, 1]
- ``dominant_tendency`` — LIBERAL, FASCIST, or REVOLUTIONARY
- ``ideological_contestation`` — debate intensity [0, 1]

These fields had no material referent. A community's ``collective_identity``
was set by a designer and modified by formulas, but nothing in the
simulation *derived* consciousness from observable material conditions.
The dominant tendency was an enum that could only change through direct
assignment, not through the aggregation of organizational activity.

This creates a modeling problem: stipulated consciousness cannot respond
organically to the organizational landscape. If a community's organizations
are all liberal CSOs, but the designer set ``dominant_tendency = REVOLUTIONARY``,
the model silently carries that contradiction.

The 2-Simplex Model
---------------------

Feature 034 models consciousness as a point in the 2-simplex — a triangle
whose three vertices represent the three directions consciousness can take
under crisis:

- **r** (revolutionary) — Oppositional collective identity, independent power.
  Distance from the liberal-fascist base of the triangle.
- **l** (liberal) — Seeks inclusion in existing institutions without
  transforming them. The default when no organizations are active.
- **f** (fascist) — Collaboration with hegemonic order for individual escape.

The simplex constraint ``r + l + f = 1.0`` means these are not three
independent quantities. They are shares of a single whole: the community's
total consciousness. Increasing one component necessarily decreases the
others. This geometric constraint eliminates the possibility of a community
being simultaneously 90% revolutionary and 90% fascist — a state the old
model could represent but that has no political meaning.

The old fields become computed properties of the simplex position:

- ``collective_identity`` equals ``r`` — oppositional consciousness *is*
  the revolutionary component.
- ``dominant_tendency`` is the argmax of ``(r, l, f)``, with ties broken
  in favor of liberal (the structural advantage of the status quo).
- ``ideological_contestation`` is the normalized Shannon entropy of
  ``(r, l, f)``: ``H(r, l, f) / log(3)``. A pure position
  (one component = 1.0) has zero entropy; a uniform distribution
  (r = l = f = 1/3) has maximum entropy.

Organizational Landscape Derivation
------------------------------------

The central design choice: consciousness is not stipulated but **derived
from the organizational landscape** operating within the community.
Organizations are the agents of consciousness formation.

The function :func:`~babylon.formulas.consciousness.compute_ternary_consciousness`
implements this derivation:

1. **Sum weighted contributions.** Each organization contributes to its
   tendency vertex with weight ``membership_density * cadre_level * cohesion``.
   A large, disciplined, cohesive organization pulls harder than a small,
   fragmented one.

2. **Unorganized fraction defaults to liberal.** The population not claimed
   by any organization is assigned to the liberal vertex. This follows
   George Jackson's insight: passive acceptance of the existing order
   *is* liberal hegemony. You have to actively organize to leave liberalism.

3. **Normalize to simplex.** The raw contributions are scaled so that
   ``r + l + f = 1.0``.

4. **Apply substrate floor.** If the normalized ``r`` falls below the
   community's substrate floor, ``r`` is raised to the floor and ``l``
   and ``f`` are proportionally redistributed in the remaining space.

This means consciousness responds dynamically to organizational changes:
if revolutionary organizations are destroyed by state repression, the
community's ``r`` drops. If liberal CSOs expand their membership, ``l``
increases. The model tracks real organizational activity, not designer
stipulations.

Substrate Floor
----------------

Some communities carry a minimum level of revolutionary consciousness
that persists even when all organizations are destroyed. This is the
**substrate floor** — the grandmother who teaches her grandchild not to
talk to cops, the survival knowledge transmitted through socialization
rather than formal organization.

Each of the 14 community types has a ``SubstrateFloor`` entry with:

- **floor_value** — the minimum ``r`` regardless of org landscape.
- **confidence** — a ``ProvenanceLevel`` (HIGH, MEDIUM, LOW, SYNTHETIC)
  indicating data quality.
- **data_sources** — named proxy datasets used to estimate the floor.
- **computation_method** — how the floor was derived from those proxies.

Communities with the highest substrate floors are those whose material
experience of oppression is most intense:

- **INCARCERATED** (0.18, MEDIUM) — Stripped of all pretense of inclusion.
  Proxy: Vera Institute incarceration rates.
- **NEW_AFRIKAN** and **FIRST_NATIONS** (0.12, MEDIUM) — Centuries of
  settler-colonial oppression. Proxies: Vera incarceration + Chetty
  mobility atlas.
- **UNDOCUMENTED** (0.10, LOW) — Legal exclusion from protections.

Hegemonic and lifecycle communities (SETTLER, PATRIARCHAL, YOUTH, ADULT)
have floor 0.0 — no accumulated substrate revolutionary consciousness.
ELDER has 0.02, reflecting generational memory transmission.

See :class:`~babylon.models.entities.consciousness.SubstrateFloor` and
``SUBSTRATE_FLOOR_DEFAULTS`` for the complete table.

The Assimilation Trap
---------------------

The ternary model exposes a pattern invisible to the old scalar model:
the **assimilation trap**. This is the condition where a community has
nominal solidarity edges but low revolutionary consciousness — the
Democratic Party coalition pattern.

The ``assimilation_ratio`` property (``f / (l + f)``) measures how much
of the non-revolutionary consciousness is fascist. But the deeper metric
is the simplex position itself: a community with ``r < 0.3`` is in the
danger zone where solidarity edges appear on the graph but would collapse
under crisis.

Feature 034 marks solidarity edges where the effective collective identity
(min of both endpoints) falls below 0.3 as **crisis-fragile**. The
:class:`~babylon.domain.bifurcation.types.BifurcationResult` tracks two new
fields:

- ``mean_assimilation_ratio_marginalized`` — the mean ``f / (l + f)``
  across marginalized communities.
- ``crisis_fragile_edge_count`` — how many solidarity edges are marked
  crisis-fragile.

These metrics quantify the gap between nominal and effective solidarity.
A high ``crisis_fragile_edge_count`` relative to total solidarity edges
signals an assimilation trap: the movement looks connected but would
fragment under crisis.

See :doc:`george-jackson-model` for the broader theory of the assimilation
trap and how it connects to the bifurcation topology analysis.

Anisotropic Observation Error
------------------------------

The state does not observe all components of consciousness equally. Liberal
and fascist consciousness are expressed through legible channels — voting,
public discourse, media consumption, organizational membership in legal
entities. Revolutionary consciousness is hidden: it operates through
informal networks, oral tradition, and practices designed to evade
surveillance.

The function :func:`~babylon.domain.bifurcation.consciousness.anisotropic_observation_error`
models this asymmetry. It applies Gaussian noise to a consciousness position
with different standard deviations per component:

- **r** (revolutionary): ``stddev = 0.06`` — high observation error.
- **l/f ratio**: ``stddev = 0.02`` — the state observes the liberal-fascist
  split relatively well, but struggles to measure ``r``.

The noise is applied in two steps: first perturbing ``r`` directly, then
perturbing the ``l/f`` ratio within the remaining space (``1 - r``). The
result is re-normalized to a valid simplex point.

This means the state systematically underestimates or overestimates
revolutionary potential. A community with true ``r = 0.5`` might appear
to the state as ``r = 0.38`` or ``r = 0.62`` — a significant range that
affects repression targeting decisions. Meanwhile, the state's estimate of
whether the non-revolutionary population is liberal or fascist is relatively
accurate.

Backward Compatibility
-----------------------

``CommunityConsciousness`` in
:mod:`~babylon.models.entities.community` is now a type alias for
:class:`~babylon.models.entities.consciousness.TernaryConsciousness`.
All existing code that constructs ``CommunityConsciousness`` with the
old keyword arguments (``collective_identity``, ``dominant_tendency``,
``ideological_contestation``) continues to work via the legacy
construction path in the model validator.

Three construction paths are supported:

1. **Native**: ``TernaryConsciousness(r=0.5, l=0.3, f=0.2)``
2. **Legacy**: ``TernaryConsciousness(collective_identity=0.5,
   dominant_tendency=LIBERAL, ideological_contestation=0.4)``
3. **Default**: ``TernaryConsciousness()`` — uses default ``(r=0.3, l=0.6, f=0.1)``

The legacy path converts old arguments to ternary coordinates: ``r = collective_identity``,
remaining ``(1 - r)`` split between ``l`` and ``f`` based on ``dominant_tendency``,
and ``ideological_contestation`` stored for backward-compatible property access.

See Also
--------

- :doc:`/reference/ternary-consciousness` — API reference for all Feature 034 types and functions
- :doc:`consciousness-taxonomy` — Three-category community taxonomy and consciousness model
- :doc:`george-jackson-model` — Bifurcation theory and the assimilation trap
- :py:mod:`babylon.models.entities.consciousness` — Source module
- :py:mod:`babylon.formulas.consciousness` — Computation function
- :py:mod:`babylon.domain.bifurcation.consciousness` — Observation error and weighted solidarity
