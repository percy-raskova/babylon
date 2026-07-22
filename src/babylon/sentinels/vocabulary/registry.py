"""Declared invariants of the graph node-type vocabulary.

The vocabulary sentinel's registry: which trees are scanned, and the one
narrow, dated exemption to the production-closure rule. The *vocabulary
itself* is deliberately NOT duplicated here — it is read live from
:class:`~babylon.models.enums.topology.NodeType`, so the enum stays the single
source of truth and registry drift is structurally impossible.

Rule (c)'s SHAPE closure (task #45 audit, 2026-07-18) follows the identical
philosophy: :data:`MODEL_FIELDS_BY_NODE_TYPE` is read live from the real
Pydantic entity models (never a duplicated field list), and
:data:`EXTRA_STAMPABLE_ATTRIBUTES` / :data:`ATTRIBUTE_EXEMPTIONS` are the only
two places shape drift can be declared open.

:data:`LITERAL_EXEMPTIONS` and :data:`ATTRIBUTE_EXEMPTIONS` are recorded as
the family-wide :class:`~babylon.sentinels.exemptions.SentinelExemption`
(gate-governance ruling, 2026-07-18) — previously a bare
``frozenset[tuple[str, ...]]`` whose "reason" lived only in a source
*comment*. Matching stays exact-tuple (:func:`~babylon.sentinels.exemptions.
is_exempt`), keyed ``("node_type_literal", path, literal)`` /
``("node_attribute", path, node_type, attribute)`` — unchanged in spirit from
before, just now validated data instead of an implicit convention.

Layer 0.5: imports nothing above :mod:`babylon.models`.
"""

from __future__ import annotations

from typing import Final

from babylon.models.entities.balkanization_faction import BalkanizationFaction
from babylon.models.entities.industry import IndustryHyperedge
from babylon.models.entities.institution import Institution
from babylon.models.entities.organization import (
    Business,
    CivilSocietyOrg,
    Organization,
    PoliticalFaction,
    StateApparatus,
)
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.sovereign import Sovereign
from babylon.models.entities.territory import Territory
from babylon.models.enums.topology import NodeType
from babylon.sentinels.exemptions import SentinelExemption

__all__ = [
    "ATTRIBUTE_EXEMPTIONS",
    "EDGE_SOURCE_ALLOWLIST",
    "EXTRA_STAMPABLE_ATTRIBUTES",
    "LITERAL_EXEMPTIONS",
    "MODEL_FIELDS_BY_NODE_TYPE",
    "PHANTOM_ATTRIBUTE_EXEMPTIONS",
    "PHANTOM_ATTRIBUTE_READS",
    "PRODUCTION_ROOTS",
    "SCAN_ROOTS",
    "TERRITORY_KEYING_EXEMPTIONS",
    "TICK_PREFIXED_NODE_TYPES",
    "UNSTAMPED_QUERY_ALLOWLIST",
]

#: Every tree scanned by rule (a) — the "no invented strings" rule. ``tests``
#: is in scope *because* the bug this sentinel exists to prevent lived in a
#: fixture: a test that stamps a type production never emits is the whole
#: failure mode, so excluding tests would exclude the defect.
SCAN_ROOTS: Final[tuple[str, ...]] = ("src", "web", "tests")

#: The trees whose stamps and queries must CLOSE against each other — rule
#: (b). Test fixtures deliberately do not count as producers: a node type that
#: only a fixture ever stamps is exactly the "green test over a dead feature"
#: shape, so letting ``tests`` satisfy a production query would blind the
#: sentinel to its own founding bug.
PRODUCTION_ROOTS: Final[tuple[str, ...]] = ("src", "web")

#: Node types production QUERIES but never STAMPS. Every entry is a live
#: defect held open by an owner decision, not an approved pattern — a query
#: here iterates the empty set on every tick.
#:
#: Added 2026-07-18 (Task 1b). TODO(owner): scope the repair or delete the
#: dead queries; this list must only ever shrink.
#:
#: - ``hex``: production carries hex substrate state on TERRITORY nodes via
#:   ``domain/economics/substrate/hex_graph_bridge.py``; no code path stamps a
#:   ``hex`` node onto the engine graph. ``territory_diagnostics`` and the
#:   ``simulation_engine`` determinism-hash row collector iterate an empty set
#:   at runtime. (#39 T6, 2026-07-20: ``SubstrateSystem`` (MATERIAL_BASE @2.5)
#:   was rewritten to query ``NodeType.TERRITORY`` instead -- it no longer
#:   belongs to this list. Vol II U4, 2026-07-21 (ADR120/ADR123):
#:   ``Vol2CirculationStep`` was reconciled the same way -- its read/write
#:   endpoints moved off ``NodeType.HEX`` onto county-keyed
#:   ``NodeType.TERRITORY`` nodes via a constructor-injected
#:   ``ScaleAdjunction`` (hex-grain <-> county-grain allocate/aggregate), so it
#:   no longer belongs to this list either -- leaving ``territory_diagnostics``
#:   and the ``simulation_engine`` collector as the two still-live citations.
#:   The entry itself stays open on those two; the #40 lesson is to keep this
#:   citation matching reality, not to remove the entry the moment a consumer
#:   is fixed.)
#: - ``community``: community membership lives in the XGI *hypergraph*
#:   (``engine/systems/community.py``), not the main graph, so no production
#:   code ever stamps a ``community`` node onto the engine graph either. Task
#:   #40 deleted the previously-cited "last surviving query"
#:   (``domain/institution/queries.py::community_embeddedness``, zero
#:   production callers). Removing this allowlist entry entirely was
#:   attempted and empirically fails: ``engine/invariants.py::
#:   _is_community_node_attr`` (``node_attrs.get("_node_type") ==
#:   "community"``, backing ``NoCommunityFanOut``, INV-010's defensive
#:   negative-check invariant) is a second scanner-visible "query" for this
#:   type. It is intentional -- the invariant asserts community is NEVER
#:   stamped as a MEMBERSHIP-edge source -- but it too has no production
#:   *caller* (``NoCommunityFanOut`` is only ever instantiated by
#:   ``tests/property/invariants/test_community_membership_lint.py``), so the
#:   same "test-only caller in a production-tree file" shape the deleted
#:   queries.py function had. Left open rather than remediated: out of task
#:   #40's scoped checklist (which named only queries.py), a new finding for
#:   an owner to scope (wire ``NoCommunityFanOut`` into a real invariant
#:   runner, or delete it the same way).
UNSTAMPED_QUERY_ALLOWLIST: Final[frozenset[str]] = frozenset({"community", "hex"})

#: Exact ``("node_type_literal", path, literal)`` keys exempt from rule (a).
#: Deliberately keyed on BOTH file and string so an exemption cannot leak to
#: another call site: the point of the rule is that an invented type is
#: invisible, and a broad exemption would re-hide it.
#:
#: Added 2026-07-18 (Task 1b). This list must only ever shrink.
LITERAL_EXEMPTIONS: Final[tuple[SentinelExemption, ...]] = (
    SentinelExemption(
        key=(
            "node_type_literal",
            "tests/unit/balkanization/test_faction_node_type_query.py",
            "balkanization_faction",
        ),
        reason=(
            "The 3b60dcfe regression test asserts the WRONG string matches NOTHING. "
            "Naming the bogus type is the whole point of the test, so this exemption "
            "is permanent rather than debt."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="N/A (permanent by design -- regression test for the founding bug)",
    ),
    SentinelExemption(
        key=(
            "node_type_literal",
            "tests/unit/persistence/test_postgres_runtime.py",
            "SocialClass",
        ),
        reason=(
            "Legacy CamelCase persistence format. postgres_runtime/_legacy.py "
            "deliberately tolerates BOTH casings (_extract_promoted_columns branches "
            "on node_type in ('SocialClass', 'social_class')), and this test covers "
            "the legacy branch by hydrating legacy rows. NOT a live bug -- but a "
            "graph hydrated from CamelCase rows will NOT answer "
            "query_nodes(NodeType.SOCIAL_CLASS)."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task=(
            "N/A (owner design question open -- whether to normalise legacy casing "
            "on hydration -- no ticket filed; the tolerance itself is intentional)"
        ),
    ),
)

#: Rule (c) — shape closure. Every REAL production-stamped node type's
#: declared field set, read live from the Pydantic entity models (never
#: duplicated). ``organization`` unions the base :class:`Organization` with
#: every subtype the scenario seeders actually instantiate
#: (:class:`StateApparatus`, :class:`Business`, :class:`PoliticalFaction`,
#: :class:`CivilSocietyOrg`) — a subtype-only field (``is_player``,
#: ``jurisdiction``, ``surveillance_capacity``, ``violence_capacity``,
#: ``service_type``) is real production shape, not a fabrication, the
#: instant ANY seeded org is that subtype. Only the 8 types
#: :class:`~babylon.models.enums.topology.NodeType`'s docstring calls
#: "Production-stamped" get an entry — ``hex``/``community``/``person``/
#: ``entity``/``external``/``county`` are declared fixture-only vocabulary
#: with no corresponding model, so shape-closure does not apply to them
#: (task #45 audit).
MODEL_FIELDS_BY_NODE_TYPE: Final[dict[str, frozenset[str]]] = {
    NodeType.TERRITORY.value: frozenset(Territory.model_fields),
    NodeType.SOCIAL_CLASS.value: frozenset(SocialClass.model_fields),
    NodeType.ORGANIZATION.value: frozenset(
        Organization.model_fields
        | StateApparatus.model_fields
        | Business.model_fields
        | PoliticalFaction.model_fields
        | CivilSocietyOrg.model_fields
    ),
    NodeType.INSTITUTION.value: frozenset(Institution.model_fields),
    NodeType.INDUSTRY.value: frozenset(IndustryHyperedge.model_fields),
    NodeType.SOVEREIGN.value: frozenset(Sovereign.model_fields),
    NodeType.FACTION.value: frozenset(BalkanizationFaction.model_fields),
}

#: Attribute keys stamped or read outside a node's own Pydantic model that
#: production genuinely writes onto that node type via
#: ``BabylonGraph.update_node``/a generic setter (``SystemBase._write_clamped``)
#: — real graph-only shape, confirmed live by a production writer, not a
#: fabrication. Each entry names its writer. ``tick_*``-prefixed keys are
#: handled separately (see :data:`TICK_PREFIXED_NODE_TYPES`), not enumerated
#: here one-by-one.
EXTRA_STAMPABLE_ATTRIBUTES: Final[dict[str, frozenset[str]]] = {
    NodeType.SOCIAL_CLASS.value: frozenset(
        {
            "contradiction_fields",  # engine/systems/contradiction_field.py
            "field_derivatives",  # engine/systems/field_derivative.py
            "hope",  # engine/systems/allegiance.py (P25 U8 — H(c), per-tick)
            "threat_score",  # engine/systems/community.py
            "v_produced",  # engine/systems/economic.py (market pricing)
            "w_paid",  # engine/systems/economic.py (market pricing)
        }
    ),
    NodeType.TERRITORY.value: frozenset(
        {
            "legitimation_index",  # engine/systems/lifecycle.py
            "legitimation_crisis",  # engine/systems/lifecycle.py
            "dependency_ratio",  # engine/systems/lifecycle.py
            "dpd_state",  # engine/systems/lifecycle.py
            "vision_state",  # engine/systems/epistemic_horizon.py (Phase 1 shadow)
            "mass_receptivity",  # engine/systems/epistemic_horizon.py
            "intel_confidence",  # engine/systems/epistemic_horizon.py
            "price_divergence",  # engine/systems/market_scissors.py + web bridge
            "habitability",  # engine/systems/metabolism.py (via _write_clamped)
            "v",  # engine/systems/vol2_circulation.py (Vol2CirculationStep.step,
            # update_node(fips_to_node[fips], v=v_post_val) -- the county-grain
            # variable-capital vector written back after the hex-grain LODES OD
            # pass; #39/Amendment U's ScaleAdjunction binding reads/writes this
            # via county Territory nodes, never a hex node. Real production
            # shape invisible to rule (c) because update_node is out of its
            # static scope (same reason the rule's own docstring already
            # scopes out update_node/`_write_clamped` calls generally).
            # NOT declared Territory fields, and no production writer stamps
            # them onto a territory node either -- but every reader is a
            # `.get(attr, default)` guard applied UNIFORMLY across every node
            # type (never territory-specific), so a territory fixture
            # carrying one is decorative, not a masked bug: unlike
            # agitation/class_consciousness, nothing claims to derive a real
            # per-territory value from a model field that doesn't exist.
            # Found alongside the real suspects in the task #45 audit.
            "active",
            "s_bio",
            "s_class",
        }
    ),
}

#: Node types whose ``tick_``-prefixed attributes are real, engine-written
#: shape (``domain/economics/tick/graph_bridge.py`` and its web-bridge carry
#: counterpart) — mirrors :func:`babylon.sentinels._ast.tick_write_set`'s own
#: domain knowledge that ``tick_*`` is a load-bearing naming convention, not
#: an accident. A prefix rule rather than an enumeration because the tick
#: dynamics surface grows independently of this sentinel.
TICK_PREFIXED_NODE_TYPES: Final[frozenset[str]] = frozenset(
    {NodeType.SOCIAL_CLASS.value, NodeType.TERRITORY.value}
)

#: Exact ``("node_attribute", path, node_type, attribute)`` keys exempt from
#: Rule (c). Keyed on all four so an exemption cannot leak to another call
#: site or node type — same discipline as :data:`LITERAL_EXEMPTIONS`. Two
#: different reasons populate this list; each row's ``reason``/
#: ``tracking_task`` says which:
#:
#: 1. **Generic/duck-typed utility tests, and orphaned-but-not-broken domain
#:    functions** (``tracking_task`` is ``"N/A"`` — nothing to remediate).
#:    The function under test takes the attribute NAME as a runtime
#:    parameter (attribute-agnostic aggregation, a generic clamped-write
#:    helper, a property-based iteration-order oracle) — the fixture is not
#:    claiming the attribute is real ``SocialClass`` shape, any string would
#:    do; OR the reader is a real, currently-uncalled domain function (task
#:    #45 audit's "orphaned computation" finding — not a masked live bug).
#: 2. **KNOWN LIVE BUGS held open by an owner decision** (mirrors
#:    :data:`UNSTAMPED_QUERY_ALLOWLIST`'s governance, ``tracking_task="#45"``
#:    — the audit that found them): the production reader lives in
#:    ``src/babylon/engine/``, one of the two scenario seeders
#:    (``src/babylon/engine/scenarios/_legacy.py`` / ``_legacy_wayne.py``),
#:    or an engine-adjacent economics module a live System calls every tick
#:    (``src/babylon/domain/economics/crisis/bifurcation.py``, wired into
#:    ``TickDynamicsSystem`` — fixing it would move ``qa:regression``
#:    baselines) — all out of scope for the task that discovered them (#45).
#:    Fix the read side (or the seeder) and delete the row — this half of
#:    the list must only ever shrink.
ATTRIBUTE_EXEMPTIONS: Final[tuple[SentinelExemption, ...]] = (
    # -- Reason 1: generic/duck-typed attribute-name tests -----------------
    SentinelExemption(
        key=(
            "node_attribute",
            "tests/unit/engine/adapters/test_aggregation_mixin.py",
            "social_class",
            "consciousness",
        ),
        reason=(
            "Generic/duck-typed attribute-name test: the attribute-agnostic "
            "aggregation mixin takes the attribute NAME as a runtime parameter -- "
            "not a claim that 'consciousness' is real SocialClass shape here, any "
            "string would do."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="N/A (permanent by design)",
    ),
    SentinelExemption(
        key=(
            "node_attribute",
            "tests/unit/engine/adapters/test_query_mixin.py",
            "social_class",
            "consciousness",
        ),
        reason=(
            "Generic/duck-typed attribute-name test: the attribute-agnostic query "
            "mixin takes the attribute NAME as a runtime parameter -- not a claim "
            "that 'consciousness' is real SocialClass shape here."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="N/A (permanent by design)",
    ),
    SentinelExemption(
        key=(
            "node_attribute",
            "tests/unit/engine/systems/test_system_base.py",
            "social_class",
            "wage",
        ),
        reason=(
            "Generic/duck-typed attribute-name test: SystemBase's clamped-write "
            "helper takes the attribute NAME as a runtime parameter -- not a claim "
            "that 'wage' is real SocialClass shape here."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="N/A (permanent by design)",
    ),
    SentinelExemption(
        key=(
            "node_attribute",
            "tests/unit/engine/test_graph_iteration_order.py",
            "social_class",
            "w",
        ),
        reason=(
            "Generic/duck-typed attribute-name test: a property-based "
            "iteration-order oracle takes the attribute NAME as a runtime "
            "parameter -- not a claim that 'w' is real SocialClass shape here."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="N/A (permanent by design)",
    ),
    SentinelExemption(
        key=(
            "node_attribute",
            "tests/unit/engine/test_graph_conformance.py",
            "social_class",
            "consciousness",
        ),
        reason=(
            "GraphProtocol conformance suite: a pure store/retrieve round-trip "
            "check (add_node -> node.attributes[...] -> update_node -> "
            "node.attributes[...] again) over the generic protocol surface, not a "
            "claim that 'consciousness' is real SocialClass shape."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="N/A (permanent by design)",
    ),
    SentinelExemption(
        key=(
            "node_attribute",
            "tests/unit/engine/systems/test_metabolism.py",
            "faction",
            "s_bio",
        ),
        reason=(
            "Deliberate negative control (mirrors LITERAL_EXEMPTIONS' "
            "balkanization_faction row): proves MetabolismSystem filters by "
            "_node_type and ignores a wrong-typed node's s_bio."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="N/A (permanent by design -- negative-control test)",
    ),
    SentinelExemption(
        key=(
            "node_attribute",
            "tests/unit/engine/systems/test_metabolism.py",
            "faction",
            "s_class",
        ),
        reason=(
            "Deliberate negative control (mirrors LITERAL_EXEMPTIONS' "
            "balkanization_faction row): proves MetabolismSystem filters by "
            "_node_type and ignores a wrong-typed node's s_class."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="N/A (permanent by design -- negative-control test)",
    ),
    SentinelExemption(
        key=(
            "node_attribute",
            "tests/unit/organizations/test_composition.py",
            "social_class",
            "lifecycle_phase",
        ),
        reason=(
            "domain/organizations/composition.py's lifecycle_composition() "
            "genuinely reads 'lifecycle_phase' off social_class nodes via "
            "MEMBERSHIP edges -- no System currently calls it, so this is an "
            "orphaned-computation finding (task #45 audit), not a masked live bug."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="N/A (task #45 audit; orphaned computation, not an owner-gated bug)",
    ),
    SentinelExemption(
        key=(
            "node_attribute",
            "tests/integration/test_organization_detroit.py",
            "social_class",
            "lifecycle_phase",
        ),
        reason=(
            "Same orphaned-computation finding as test_composition.py's "
            "lifecycle_phase row (task #45 audit) -- lifecycle_composition() has "
            "no System caller."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="N/A (task #45 audit; orphaned computation, not an owner-gated bug)",
    ),
    # -- Reason 2: known live bugs, owner-gated, src/babylon/engine/ -------
    SentinelExemption(
        key=(
            "node_attribute",
            "tests/unit/engine/test_wealth_distribution_system.py",
            "social_class",
            "class_consciousness",
        ),
        reason=(
            "wealth_distribution.py::_bracket_resistances reads a flat "
            "'class_consciousness' key that NO production graph carries (the real "
            "field is nested ideology.class_consciousness) -- the ODE's resistance "
            "term is silently always 0.0 in every real game."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="#45",
    ),
    # NOTE (merge resolution, 2026-07-18): the two ``social_class``/``territory``
    # rows that used to sit here -- for ``test_bifurcation_risk.py`` and
    # ``test_crisis_lifecycle.py`` -- were DELETED under Blocker I-2, which fixed
    # the underlying read (``territory`` -> ``county_fips``) in
    # ``domain/economics/crisis/bifurcation.py``. This half of the list must only
    # ever SHRINK, and this is what shrinking looks like: fix the read side, then
    # delete the row.
    #
    # CORRECTION worth keeping: this file previously cited that row as THE example
    # of an engine-adjacent fix that "would move qa:regression baselines." It did
    # not. The 2-line rename moved ZERO baselines, because none of the 5 canonical
    # regression scenarios wire a ``melt_calculator`` -- the per-county pipeline
    # short-circuits before ``_compute_bifurcation_risk`` is reached. The
    # prediction was inference, not measurement. VERIFY BASELINE IMPACT
    # EMPIRICALLY before trusting that inference for the next instance; and note
    # the corollary, which is the more uncomfortable half: a fix the regression
    # suite cannot feel is a fix the regression suite was never guarding.
    SentinelExemption(
        key=(
            "node_attribute",
            "tests/integration/test_ooda_detroit.py",
            "organization",
            "ooda_profile",
        ),
        reason=(
            "ooda.py / ooda/initiative.py read 'ooda_profile' off organization "
            "nodes; neither scenarios/_legacy.py nor _legacy_wayne.py (the only "
            "two production seeders) ever stamps it, so it is always the safe "
            "default (OODAProfile()) in every real game."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="#45",
    ),
    SentinelExemption(
        key=(
            "node_attribute",
            "tests/integration/test_ooda_detroit.py",
            "organization",
            "counter_intel_score",
        ),
        reason=(
            "Same seeder gap as the ooda_profile row (task #45 audit): neither "
            "production seeder ever stamps 'counter_intel_score', so it is always "
            "the safe default (0.0) in every real game."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="#45",
    ),
    SentinelExemption(
        key=(
            "node_attribute",
            "tests/property/invariants/test_consequence_after_actions.py",
            "organization",
            "ooda_profile",
        ),
        reason=(
            "Same ooda_profile seeder gap (task #45 audit), covered from the "
            "property-invariant angle."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="#45",
    ),
    SentinelExemption(
        key=(
            "node_attribute",
            "tests/unit/ooda/test_ooda_system.py",
            "organization",
            "ooda_profile",
        ),
        reason=(
            "Same ooda_profile seeder gap (task #45 audit), covered from the "
            "OODA-system unit angle."
        ),
        owner="Persephone Raskova",
        date="2026-07-18",
        tracking_task="#45",
    ),
)

#: Rule (d) (ADR087, 2026-07-19) — edge-shape closure: every
#: ``(edge_type, SOURCE node type)`` combination stamped anywhere in
#: :data:`SCAN_ROOTS` via a literal ``add_edge(...)``/``Relationship(...)``
#: call (source resolved against a SAME-FILE ``add_node``/entity-constructor
#: binding — see :func:`babylon.sentinels._ast.edge_source_type_uses`) must
#: match a combination :data:`PRODUCTION_ROOTS` produces the SAME literal way.
#: This is a NARROWER static lens than rule (b)'s node-type closure: most
#: edges in this codebase are NOT created via a literal, statically-resolvable
#: call at all —
#:
#: 1. **Verb resolvers write with a runtime ``org_id``/``target_id``**
#:    (``engine/actions/negotiate.py``'s real TRANSACTIONAL producer,
#:    ``engine/actions/_mass_work.py``'s new SOLIDARITY producer, ADR087) —
#:    the source is a function PARAMETER, never a literal or same-file bound
#:    Name, so these real producers are invisible to this rule by
#:    construction (mirrors rule (c)'s own explicit ``update_node``
#:    scope-out: "inferring one would require dataflow analysis this static
#:    scanner does not do").
#: 2. **Bulk/dynamic hydration** (``persistence/postgres_runtime/_legacy.py``'s
#:    ``graph.add_edge(row["source_id"], row["target_id"], **attrs)``,
#:    TIGER-derived territory ADJACENCY, LODES-derived MEMBERSHIP/EMPLOYMENT) —
#:    the source id is a runtime value from a data row, never a literal.
#: 3. **Engine-computed edges** (``FactionInfluenceSystem``'s INFLUENCES,
#:    written from territory computation at runtime).
#:
#: This rule therefore catches EXACTLY the class of bug ADR085 diagnosed — a
#: fixture that ALSO hand-stamps the source node's type in the SAME file,
#: closing a loop with no external referent — not "every edge in the game has
#: a literal Python producer" (false; see above). Every entry below is a
#: PRE-EXISTING (edge_type, source_type) combination this rule's static lens
#: cannot confirm a producer for, verified NOT to be a masked instance of the
#: ADR085 bug (each cited). TODO(owner): entries under category 1/2/3 could
#: be closed by teaching the scanner real dataflow, but that is a
#: disproportionate undertaking for what each individually is — a documented,
#: honest gap, not a live defect. This list must only ever shrink.
#:
#: - ``("ADJACENCY"/"adjacency", "territory")``: category 2 — TIGER-derived
#:   spatial adjacency; heavily consumed (``engine/systems/territory.py``,
#:   ``domain/bifurcation/ceiling.py``) but never literally produced.
#: - ``("EXPLOITATION", "social_class")`` / ``("SOLIDARITY", "social_class")``
#:   / ``("TENANCY", "social_class")`` / ``("WAGES", "social_class")``
#:   (UPPERCASE): ``tests/unit/engine/test_graph_conformance.py`` +
#:   ``test_graph_iteration_order.py`` — generic graph-PROTOCOL conformance
#:   tests using the bare enum NAME as an arbitrary string, not
#:   ``EdgeType.X.value`` — the exact "generic/duck-typed, not a real shape
#:   claim" reasoning already covering these two files' node-attribute rows
#:   (Reason 1, above). The real lowercase combination
#:   (``"solidarity"``/``"exploitation"``/etc., ``"social_class"``) IS
#:   produced (``scenarios/_legacy.py`` + ``_legacy_wayne.py``) and needs no
#:   allowlisting.
#: - ``("command", "key_figure")`` / ``("membership", "key_figure")``:
#:   ``key_figure`` is DECLARED but NOT production-stamped (``NodeType``'s own
#:   docstring: "the node type remains only to type ``classify_topology``'s
#:   COMMAND-edge test fixtures" — the backing ``KeyFigure`` model was retired,
#:   ADR084/III.10). Mirrors :data:`UNSTAMPED_QUERY_ALLOWLIST`'s ``hex``/
#:   ``community`` precedent exactly.
#: - ``("exploitation", "organization")``: ``tests/unit/web/test_engine_bridge.py``
#:   — a plausible real economic shape (a Business/StateApparatus extracting
#:   from a class) the two legacy scenario factories simply never wire;
#:   category 1/3 (an org-sourced extraction edge would come from a runtime
#:   economic computation, not a literal).
#: - ``("friendship", "social_class")``: ``tests/unit/models/test_relationship.py::
#:   test_rejects_invalid_edge_type_string`` — a DELIBERATE negative control:
#:   asserts ``Relationship(edge_type="friendship")`` is REJECTED
#:   (``pytest.raises(ValidationError)``). Mirrors :data:`LITERAL_EXEMPTIONS`'
#:   ``balkanization_faction`` precedent — naming the bogus type is the point.
#: - ``("influences", "faction")``: ``FactionInfluenceSystem`` reads INFLUENCES
#:   (category 3 — engine-computed from territory state at runtime, never a
#:   literal ``add_edge``).
#: - ``("membership", "organization")`` / ``("membership", "social_class")``:
#:   category 1/2 — MEMBERSHIP is consumed extensively (``ooda/_helpers.py``,
#:   ``domain/organizations/composition.py``, ``engine/systems/reactionary.py``,
#:   ``engine/systems/community.py``) but every real writer found uses a
#:   runtime/dynamic source; ``test_community_membership_lint.py``'s row is
#:   additionally a deliberate negative control ("Deliberately seed the
#:   violation") for ``NoCommunityFanOut``.
#: - ``("repression", "social_class")``: ``tests/unit/models/test_relationship.py::
#:   test_repression_edge`` — a ``Relationship`` MODEL unit test (can the
#:   model represent a comprador->periphery REPRESSION edge), independent of
#:   whether the two CURRENT scenario factories choose to wire one.
#: - ``("solidarity", "organization")``: category 1 — the real producer is
#:   ``engine/actions/_mass_work.py``'s ``apply_mass_work_solidarity``,
#:   ``graph.add_edge(org_id, target_id, edge_type=EdgeType.SOLIDARITY.value,
#:   ...)`` (org -> social_class mass-work SOLIDARITY, ADR087), invisible to
#:   this rule for the SAME reason as ``("transactional", "organization")``
#:   below: ``org_id``/``target_id`` are function parameters, never literals.
#:   Adversary-train W5 (2026-07-22) added the first test fixtures exercising
#:   this real shape from the READ side (``action_effects.
#:   _propagate_repression_to_class_base`` walks the SAME org -> social_class
#:   SOLIDARITY edge to propagate a state REPRESS/SURVEIL onto an org's class
#:   base) — ``tests/unit/ooda/test_action_effects.py::
#:   TestRepressiveOrgTargetPropagatesToClassBase`` and
#:   ``tests/unit/game/test_session.py::
#:   TestStateRepressOnOrgPropagatesToClassBase``.
#: - ``("tenancy", "organization")``: ``tests/unit/web/test_map_dominant_class_solidarity.py::
#:   test_non_social_class_tenants_are_excluded`` — the test's own comment:
#:   "malformed data, still real-world-possible" — a deliberate negative case
#:   proving the web bridge's tenancy reader excludes non-social_class tenants.
#: - ``("transactional", "organization")``: category 1 — the real producer
#:   is ``engine/actions/negotiate.py``'s
#:   ``graph.add_edge(org_id, target_id, edge_type=EdgeType.TRANSACTIONAL.value)``,
#:   invisible to this rule because ``org_id``/``target_id`` are function
#:   parameters, never literals.
EDGE_SOURCE_ALLOWLIST: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("ADJACENCY", "territory"),
        ("adjacency", "territory"),
        ("EXPLOITATION", "social_class"),
        ("SOLIDARITY", "social_class"),
        ("TENANCY", "social_class"),
        ("WAGES", "social_class"),
        ("command", "key_figure"),
        ("membership", "key_figure"),
        ("exploitation", "organization"),
        ("friendship", "social_class"),
        ("influences", "faction"),
        ("membership", "organization"),
        ("membership", "social_class"),
        ("repression", "social_class"),
        ("solidarity", "organization"),
        ("tenancy", "organization"),
        ("transactional", "organization"),
    }
)

# ─────────────────────────────────────────────────────────────────────────────
# Rule (e) (task #40) — phantom-attribute closure: a graph-node attribute no
# producer ever writes must not be READ (production or test) or STAMPED
# (test), because a reader keyed on it matches ZERO real nodes forever. The
# founding instance: ``ooda/initiative.py::compute_community_embeddedness``
# read ``node_data.get("community_type")`` -- an attribute NO production
# code ever writes (community is never a main-graph node, INV-010) -- and
# was therefore structurally always 0.0. Task #40 rewrote that function to
# read the real TENANCY/``community_memberships`` substrate instead; this
# rule gates the class so the phantom-read shape cannot recur.
# ─────────────────────────────────────────────────────────────────────────────

#: Graph-node attribute names BANNED as a ``.get()``/``.pop()``/``[...]``
#: READ off a raw node-payload dict, or a keyword/dict-literal STAMP on a
#: real ``add_node(...)`` call -- in production (``src``/``web``) AND in
#: tests (a fixture stamping the phantom attribute is the fabrication half
#: of the exact same bug; the sentinel's OWN tests are the sole exemption,
#: since they must construct the violating shape to prove the gate rejects
#: it). This list must only ever GROW as new phantom-attribute classes are
#: discovered and shrink only when an attribute gains a real producer (at
#: which point it is simply removed, not "fixed" here).
#:
#: - ``community_type``: community is NEVER a main-graph node (INV-010); no
#:   production code stamps this onto a graph node, ever. The attribute DOES
#:   legitimately exist on the XGI hypergraph's own ``CommunityMembership``/
#:   ``CommunityState``/``SubstrateFloor`` Pydantic models (``mem.
#:   community_type``, ``CommunityState(community_type=...)``) and as a
#:   column in the REAL, Postgres-persisted community-state tables
#:   (``persistence/postgres_runtime/_legacy.py``) -- plain attribute
#:   access, constructor keywords, and DB-row dict reads, never a graph-node
#:   ``.get()``/``[...]``/``add_node(...)`` shape, so
#:   :func:`~babylon.sentinels._ast.graph_node_attribute_reads`'s
#:   receiver-scoping (only a raw ``<x>.nodes.get(...)``/``<x>.nodes[...]``
#:   payload counts) already excludes that entirely legitimate, unrelated
#:   namespace by construction -- no exemption row needed or present for it.
PHANTOM_ATTRIBUTE_READS: Final[frozenset[str]] = frozenset({"community_type"})

#: Exact ``("phantom_attribute_read"|"phantom_attribute_stamp", path,
#: attribute)`` keys exempt from rule (e) — KNOWN LIVE BUGS, owner-gated,
#: discovered incidentally while building this gate, out of task #40's
#: scoped checklist (mirrors :data:`ATTRIBUTE_EXEMPTIONS`'s "Reason 2"
#: governance; ``tracking_task`` documents each as unscoped rather than
#: "#40" itself).
PHANTOM_ATTRIBUTE_EXEMPTIONS: Final[tuple[SentinelExemption, ...]] = (
    SentinelExemption(
        key=("phantom_attribute_read", "src/babylon/ooda/action_costs.py", "community_type"),
        reason=(
            "Task #40 discovery (NOT part of the assigned checklist): "
            "_get_org_community_types/_get_target_community_type read "
            "'community_type' off real graph.nodes.get(...) payloads -- the "
            "identical phantom-attribute-read bug Fix B retired in "
            "ooda/initiative.py. _is_contradiction_pair is therefore always "
            "False and compute_action_cost's 'Across contradiction axis' branch "
            "is dead in every real game. compute_action_cost (the only entry "
            "point) additionally has ZERO production callers of its own "
            "(mirrors Fix A's community_embeddedness shape exactly) -- an "
            "earlier-order defect than the phantom read. Flagging for a future "
            "task to either delete (Fix-A-style) or wire+repair (Fix-B-style)."
        ),
        owner="Persephone Raskova",
        date="2026-07-19",
        tracking_task="#58 (task #40 discovery; wire-or-delete owner-gated)",
    ),
    SentinelExemption(
        key=(
            "phantom_attribute_stamp",
            "tests/unit/ooda/test_action_costs.py",
            "community_type",
        ),
        reason=(
            "Fixture feeding action_costs.py's own phantom-attribute-read bug "
            "(see the sibling production-read exemption above) -- same tracking, "
            "same future task."
        ),
        owner="Persephone Raskova",
        date="2026-07-19",
        tracking_task="#58 (task #40 discovery; wire-or-delete owner-gated)",
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# Rule (f) (#39 T8) — Territory wrong-rung keying: the res-3 inversion class,
# both directions. USScenario's historical bug minted a bare FIPS string as
# Territory(id=...) (identity must live ONLY in county_fips); the mirror-image
# mistake would stamp an H3-cell value onto county_fips (Wayne's hex path and
# the county path must never cross). See
# :func:`~babylon.sentinels._ast.territory_keying_uses` for the two recognised
# forms and their documented static-heuristic narrowing.
# ─────────────────────────────────────────────────────────────────────────────

#: Exact ``("territory_keying", path, kind, detail)`` keys exempt from rule
#: (f). Empty today -- no production or test call site currently constructs a
#: wrong-rung Territory (T4 landed the county-keyed fix cleanly; Wayne's hex
#: path never sets county_fips at all). Expected future occupants: a test
#: that DELIBERATELY constructs a malformed Territory to prove a validator
#: rejects it (mirrors :data:`LITERAL_EXEMPTIONS`' ``balkanization_faction``
#: precedent) -- each such row must cite the covering test by name.
TERRITORY_KEYING_EXEMPTIONS: Final[tuple[SentinelExemption, ...]] = ()
