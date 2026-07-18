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
    KeyFigure,
    Organization,
    PoliticalFaction,
    StateApparatus,
)
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.sovereign import Sovereign
from babylon.models.entities.territory import Territory
from babylon.models.enums.topology import NodeType

__all__ = [
    "ATTRIBUTE_EXEMPTIONS",
    "EXTRA_STAMPABLE_ATTRIBUTES",
    "LITERAL_EXEMPTIONS",
    "MODEL_FIELDS_BY_NODE_TYPE",
    "PRODUCTION_ROOTS",
    "SCAN_ROOTS",
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
#:   ``hex`` node onto the engine graph. ``SubstrateSystem`` (MATERIAL_BASE
#:   @2.5), ``Vol2CirculationStep``, ``territory_diagnostics`` and the
#:   ``simulation_engine`` determinism-hash row collector therefore all iterate
#:   an empty set at runtime.
#: - ``community``: community membership lives in the XGI *hypergraph*
#:   (``engine/systems/community.py``), not the main graph. The last surviving
#:   query is ``domain/institution/queries.py::community_embeddedness``, which
#:   has no production caller. The same defect was already found and fixed once
#:   in the web bridge (see ``tests/unit/web/test_engine_bridge.py``,
#:   ``test_educate_targets_uses_social_class_not_community``).
UNSTAMPED_QUERY_ALLOWLIST: Final[frozenset[str]] = frozenset({"hex", "community"})

#: Exact ``(path, literal)`` pairs exempt from rule (a). Deliberately keyed on
#: BOTH file and string so an exemption cannot leak to another call site: the
#: point of the rule is that an invented type is invisible, and a broad
#: exemption would re-hide it.
#:
#: Added 2026-07-18 (Task 1b). This list must only ever shrink.
LITERAL_EXEMPTIONS: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        # The 3b60dcfe regression test asserts the WRONG string matches
        # NOTHING. Naming the bogus type is the whole point of the test, so
        # this exemption is permanent rather than debt.
        (
            "tests/unit/balkanization/test_faction_node_type_query.py",
            "balkanization_faction",
        ),
        # Legacy CamelCase persistence format. ``postgres_runtime/_legacy.py``
        # deliberately tolerates BOTH casings (see ``_extract_promoted_columns``,
        # which branches on ``node_type in ("SocialClass", "social_class")``),
        # and these tests cover the legacy branch by hydrating legacy rows.
        # NOT a live bug — but note a graph hydrated from CamelCase rows will
        # NOT answer ``query_nodes(NodeType.SOCIAL_CLASS)``.
        # TODO(owner): decide whether the legacy casing should be normalised on
        # hydration; until then the tolerance stays covered and visible here.
        ("tests/unit/persistence/test_postgres_runtime.py", "SocialClass"),
    }
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
    NodeType.KEY_FIGURE.value: frozenset(KeyFigure.model_fields),
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

#: Exact ``(path, node_type, attribute)`` triples exempt from Rule (c).
#: Keyed on all three so an exemption cannot leak to another call site or
#: node type — same discipline as :data:`LITERAL_EXEMPTIONS`. Two different
#: reasons populate this list; each row says which:
#:
#: 1. **Generic/duck-typed utility tests.** The function under test takes
#:    the attribute NAME as a runtime parameter (attribute-agnostic
#:    aggregation, a generic clamped-write helper, a property-based
#:    iteration-order oracle) — the fixture is not claiming the attribute is
#:    real ``SocialClass`` shape, any string would do.
#: 2. **KNOWN LIVE BUGS held open by an owner decision** (mirrors
#:    :data:`UNSTAMPED_QUERY_ALLOWLIST`'s governance): the production reader
#:    lives in ``src/babylon/engine/``, one of the two scenario seeders
#:    (``src/babylon/engine/scenarios/_legacy.py`` / ``_legacy_wayne.py``),
#:    or an engine-adjacent economics module a live System calls every tick
#:    (``src/babylon/domain/economics/crisis/bifurcation.py``, wired into
#:    ``TickDynamicsSystem`` — fixing it would move ``qa:regression``
#:    baselines) — all out of scope for the task that discovered them (#45).
#:    TODO(owner): fix the read side (or the seeder) and delete the row —
#:    this half of the list must only ever shrink. Full detail in the task
#:    #45 audit report.
ATTRIBUTE_EXEMPTIONS: Final[frozenset[tuple[str, str, str]]] = frozenset(
    {
        # -- Reason 1: generic/duck-typed attribute-name tests -------------
        (
            "tests/unit/engine/adapters/test_aggregation_mixin.py",
            "social_class",
            "consciousness",
        ),
        (
            "tests/unit/engine/adapters/test_query_mixin.py",
            "social_class",
            "consciousness",
        ),
        ("tests/unit/engine/systems/test_system_base.py", "social_class", "wage"),
        ("tests/unit/engine/test_graph_iteration_order.py", "social_class", "w"),
        # GraphProtocol conformance suite: a pure store/retrieve round-trip
        # check (add_node -> node.attributes[...] -> update_node ->
        # node.attributes[...] again) over the generic protocol surface, not
        # a claim that "consciousness" is real SocialClass shape.
        ("tests/unit/engine/test_graph_conformance.py", "social_class", "consciousness"),
        # Deliberate negative control (mirrors LITERAL_EXEMPTIONS'
        # balkanization_faction row): proves MetabolismSystem filters by
        # _node_type and ignores a wrong-typed node's s_bio/s_class.
        ("tests/unit/engine/systems/test_metabolism.py", "faction", "s_bio"),
        ("tests/unit/engine/systems/test_metabolism.py", "faction", "s_class"),
        # Real (if currently unwired) domain functions:
        # domain/organizations/composition.py's community_composition() /
        # lifecycle_composition() genuinely read "community"/
        # "lifecycle_phase" off social_class nodes via MEMBERSHIP edges — no
        # System currently calls either composition function, so this is an
        # orphaned-computation finding (task #45 audit), not a masked live
        # bug the way agitation/class_consciousness were.
        ("tests/unit/organizations/test_composition.py", "social_class", "community"),
        (
            "tests/unit/organizations/test_composition.py",
            "social_class",
            "lifecycle_phase",
        ),
        (
            "tests/integration/test_organization_detroit.py",
            "social_class",
            "lifecycle_phase",
        ),
        # -- Reason 2: known live bugs, owner-gated, src/babylon/engine/ ---
        # wealth_distribution.py::_bracket_resistances reads a flat
        # "class_consciousness" key that NO production graph carries (the
        # real field is nested ideology.class_consciousness) -- the ODE's
        # resistance term is silently always 0.0 in every real game.
        (
            "tests/unit/engine/test_wealth_distribution_system.py",
            "social_class",
            "class_consciousness",
        ),
        # domain/economics/crisis/bifurcation.py's
        # _compute_solidarity_density/_compute_legitimation read a flat
        # "territory" key off social_class nodes to filter by county FIPS;
        # SocialClass carries no such field (the real one is "county_fips").
        # Wired into TickDynamicsSystem (a live System), so solidarity
        # density and the agitation-fallback legitimation path are silently
        # 0.0-input/empty-set in every real game.
        ("tests/unit/economics/crisis/test_bifurcation_risk.py", "social_class", "territory"),
        (
            "tests/unit/economics/crisis/test_crisis_lifecycle.py",
            "social_class",
            "territory",
        ),
        # ooda.py / ooda/initiative.py read "ooda_profile"/
        # "counter_intel_score" off organization nodes; neither
        # scenarios/_legacy.py nor _legacy_wayne.py (the only two production
        # seeders) ever stamps either, so both are always the safe default
        # (OODAProfile()/0.0) in every real game.
        ("tests/integration/test_ooda_detroit.py", "organization", "ooda_profile"),
        ("tests/integration/test_ooda_detroit.py", "organization", "counter_intel_score"),
        (
            "tests/property/invariants/test_consequence_after_actions.py",
            "organization",
            "ooda_profile",
        ),
        ("tests/unit/ooda/test_ooda_system.py", "organization", "ooda_profile"),
    }
)
