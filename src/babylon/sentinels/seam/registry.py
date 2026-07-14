"""The single declared source of truth for player-observable seam quantities.

Every quantity that crosses the engine → web-bridge → frontend seam is declared
here as one :class:`~babylon.sentinels.seam.types.SeamEntry`. The sensors in
``babylon.sentinels.seam.checks`` (run via ``tools/sentinel_check.py seam``) diff
reality against this tuple and fail loudly when
something is computed-but-unserialized, serialized-but-unregistered,
serialized-but-unrendered, or classified dishonestly.

The registry grows with the codebase: Sensor 1, wired into the always-on dev
fast-gate, fails any newly-serialized wire key until a row is added here with a
deliberate liveness ruling. That forcing function is the "mutant" growth
mechanism — the registry cannot silently rot because adding an observable
without declaring it breaks the build.

Rows are added phase by phase (see the build plan). This literal is intentionally
hand-written, not generated: it is a dev-time contract, not player-moddable
runtime config, so it carries no round-trip/regeneration machinery.
"""

from __future__ import annotations

from babylon.sentinels.seam.types import LivenessClass, SeamEntry, SeamScope

# ---------------------------------------------------------------------------
# MAP scope — the ``/map/`` lens metrics (spec-109 A3 ``MAP_METRIC_PROPERTIES``).
#
# These ten wire keys are the single-source-of-truth map contract in
# ``web/game/map_contract.py``, emitted on every hex- and county-zoom ``/map/``
# feature by ``EngineBridge._aggregate_hex_features`` (county, engine_bridge.py
# :1653) and ``_hex_feature_properties`` (hex, engine_bridge.py:5271), advertised
# via ``metadata.available_metrics`` and gated by the API's ``lens`` filter
# (``VALID_MAP_LAYERS``, api.py:286). Every one is a numeric ramp EXCEPT
# ``dominant_class`` (a categorical ``SocialRole`` string).
#
# Sensor 1's ``check_map_metrics`` asserts this MAP-scope wire-key set equals
# ``MAP_METRIC_PROPERTIES`` byte-for-byte; ``map_contract.py`` stays the SoT and
# the registry mirrors it, so a drift on either side reds the dev fast-gate.
#
# Provenance depth grows with the build: ``owner_layer`` / ``read_paths`` here
# are as-verified (bridge-derived + MetabolismSystem attributions come from
# ``map_contract.py``'s own docstring; derived-rate attributions from the
# Program-17 item-25 work); line-precise write-sites are pinned by the Phase-3
# bridge-serialization sweep.
# ---------------------------------------------------------------------------

_MAP_EMITTERS: tuple[str, ...] = (
    "web/game/engine_bridge.py::EngineBridge._aggregate_hex_features (county zoom, :1653)",
    "web/game/engine_bridge.py::_hex_feature_properties (hex zoom, :5271)",
)

#: Derived rates + Φ stamp only at year boundaries; null between them (Program-17
#: item-25). Per owner Decision 3 these are NOT ``known_conditional`` — their
#: IMPORT_USE+QCEW reference data is published to CI (Phase 4a).
_YEAR_BOUNDARY = (
    "stamps only at year-boundary ticks (tick % ticks_per_year == 0); null between boundaries"
)

_MAP_METRICS: tuple[SeamEntry, ...] = (
    SeamEntry(
        payload="tick_profit_rate",
        wire_keys=("profit_rate",),
        scope=SeamScope.MAP,
        owner_layer="domain.economics.tick (DerivedRateCalculator)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="float",
        read_paths=_MAP_EMITTERS,
        spec_ref="spec-109 A3 · Program-17 item-25",
        notes="TRPF numerator/denominator: s/(K+v). Distinct from exploitation_rate once K>0.",
    ),
    SeamEntry(
        payload="tick_exploitation_rate",
        wire_keys=("exploitation_rate",),
        scope=SeamScope.MAP,
        owner_layer="domain.economics.tick (DerivedRateCalculator)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="float",
        read_paths=_MAP_EMITTERS,
        spec_ref="spec-109 A3 · Program-17 item-25",
        notes="Rate of surplus value e = s/v; employment-invariant.",
    ),
    SeamEntry(
        payload="tick_occ",
        wire_keys=("occ",),
        scope=SeamScope.MAP,
        owner_layer="domain.economics.tick (DerivedRateCalculator)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="float",
        read_paths=_MAP_EMITTERS,
        spec_ref="spec-109 A3 · Program-17 item-25",
        notes="Organic composition of capital K/v; zero until a real capital_calculator is wired.",
    ),
    SeamEntry(
        payload="tick_phi_hour",
        wire_keys=("imperial_rent",),
        scope=SeamScope.MAP,
        owner_layer="domain.economics (Leontief/MELT via TickDynamics)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            f"{_YEAR_BOUNDARY}; also requires per-county IMPORT_USE+QCEW coverage "
            "(published to CI, Phase 4a)"
        ),
        dtype="float",
        read_paths=_MAP_EMITTERS,
        spec_ref="spec-109 A3 · Program-17 1a",
        notes=(
            "Leontief imperial-rent FLOW rate. COLLIDES on wire key with the ECONOMY-scope "
            "'imperial_rent' STOCK (imperial_rent_pool) — scope keeps them distinct."
        ),
    ),
    SeamEntry(
        payload="heat",
        wire_keys=("heat",),
        scope=SeamScope.MAP,
        owner_layer="engine",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
        read_paths=_MAP_EMITTERS,
        spec_ref="spec-109 A3",
        notes="Repression/tension heat on the territory node; structural, emitted every tick.",
    ),
    SeamEntry(
        payload="org_presence",
        wire_keys=("org_presence",),
        scope=SeamScope.MAP,
        owner_layer="bridge-derived",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
        read_paths=_MAP_EMITTERS,
        spec_ref="spec-109 A3",
        notes="Organization incidence on the territory, derived at serialization time.",
    ),
    SeamEntry(
        payload="population",
        wire_keys=("population",),
        scope=SeamScope.MAP,
        owner_layer="engine",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
        read_paths=_MAP_EMITTERS,
        spec_ref="spec-109 A3",
        notes="Territory population; structural, emitted every tick.",
    ),
    SeamEntry(
        payload="habitability",
        wire_keys=("habitability",),
        scope=SeamScope.MAP,
        owner_layer="domain (MetabolismSystem, Sovereign-driven)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
        read_paths=_MAP_EMITTERS,
        spec_ref="spec-109 A2",
        notes=(
            "Read live off the graph node (Territory model excludes it — TERRITORY_EXCLUDED_FIELDS) "
            "and projected into hex_latest's JSONB attributes column."
        ),
    ),
    SeamEntry(
        payload="dominant_class",
        wire_keys=("dominant_class",),
        scope=SeamScope.MAP,
        owner_layer="bridge-derived (_dominant_class_by_territory)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="str",
        read_paths=_MAP_EMITTERS,
        spec_ref="spec-113 Lane D",
        notes=(
            "The one NON-numeric map metric: population-weighted-majority SocialRole among the "
            "territory's TENANCY-linked social_class members. HexState.dominant_class column."
        ),
    ),
    SeamEntry(
        payload="solidarity_index",
        wire_keys=("solidarity_index",),
        scope=SeamScope.MAP,
        owner_layer="bridge-derived (_solidarity_index_by_territory)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
        read_paths=_MAP_EMITTERS,
        spec_ref="spec-113 Lane D",
        notes=(
            "Mean live-SOLIDARITY-edge incidence over the territory's TENANCY-linked members; "
            "rides hex_latest's JSONB attributes column like habitability."
        ),
    ),
)

# ---------------------------------------------------------------------------
# INSPECTOR scope — the ``get_inspector_node`` social_class drill-down
# (Program 17 Wave 1 W1.4/W1.6, ``web/game/engine_bridge.py``
# ``_social_class_inspector_fields``/``_build_circuit_flows``). Registered
# here rather than left as an undeclared drift because this pass is what
# brings the ``/node/`` inspector endpoint's new observables under the Seam
# Observatory for the first time — scoped to exactly the three NEW
# observables this pass introduces (ternary consciousness, agitation,
# circuit_flows), not a retroactive audit of the endpoint's older fields.
# ---------------------------------------------------------------------------

_INSPECTOR_EMITTERS: tuple[str, ...] = (
    "web/game/engine_bridge.py::_social_class_inspector_fields (:1476)",
    "web/game/engine_bridge.py::EngineBridge.get_inspector_node",
)

_INSPECTOR_METRICS: tuple[SeamEntry, ...] = (
    SeamEntry(
        payload="ideology_ternary_consciousness",
        wire_keys=("consciousness",),
        scope=SeamScope.INSPECTOR,
        owner_layer=(
            "bridge-derived (_ternary_consciousness_or_none, engine_bridge.py :1449), "
            "reusing babylon.persistence.county_aggregation._ideology_to_ternary"
        ),
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "requires the node's ideology dict to carry both class_consciousness and "
            "national_identity; null when either axis is absent, never a ternary computed "
            "from a defaulted-to-0.0 axis"
        ),
        dtype="json",
        read_paths=_INSPECTOR_EMITTERS,
        derivation_site="web/game/engine_bridge.py::_ternary_consciousness_or_none (:1449)",
        spec_ref="Program 17 Wave 1 · W1.4",
        notes=(
            "{revolutionary, liberal, fascist} simplex point on the class InspectionCard — "
            "shares the exact bridge mapping babylon.persistence.county_aggregation uses for "
            "per-county consciousness aggregation, not a duplicated formula."
        ),
    ),
    SeamEntry(
        payload="ideology_agitation",
        wire_keys=("agitation",),
        scope=SeamScope.INSPECTOR,
        owner_layer="engine (IdeologicalProfile.agitation, babylon.models.entities.social_class)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "requires the node's ideology dict to carry an 'agitation' key; null for a "
            "social_class-shaped fixture with no ideology dict at all"
        ),
        dtype="float",
        read_paths=_INSPECTOR_EMITTERS,
        spec_ref="Program 17 Wave 1 · W1.4",
        notes=(
            "Raw political energy from crisis, [0.0, inf). Pre-existing field on this "
            "endpoint's payload; registered now as part of bringing get_inspector_node under "
            "the Seam Observatory."
        ),
    ),
    SeamEntry(
        payload="class_inequality",
        wire_keys=("inequality",),
        scope=SeamScope.INSPECTOR,
        owner_layer="engine (SocialClass.inequality Gini, read by VitalitySystem for attrition)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "requires the node to carry an 'inequality' graph attribute; null for a "
            "social_class-shaped fixture without one — never a fabricated 0.0"
        ),
        dtype="float",
        read_paths=_INSPECTOR_EMITTERS,
        spec_ref="Program 17 Wave 1 · W1.4",
        notes=(
            "Intra-class Gini [0.0, 1.0] — a real pre-existing engine field, newly EXPOSED on "
            "this endpoint by W1.4 (unlike agitation, which the payload already carried). The "
            "deliberately-unregistered sibling class_position/class_position_mock is a badged "
            "MOCK, not an observable — mocks are never seam-declared."
        ),
    ),
    SeamEntry(
        payload="circuit_flows",
        wire_keys=("circuit_flows",),
        scope=SeamScope.INSPECTOR,
        owner_layer="bridge-derived (_build_circuit_flows, engine_bridge.py :913)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "requires social_class nodes seeded for at least one adjacent pair of the 4 "
            "circuit roles (periphery_proletariat/comprador_bourgeoisie/core_bourgeoisie/"
            "labor_aristocracy) AND a real EXPLOITATION/TRIBUTE/WAGES edge between them; a "
            "role/edge a scenario does not seed is OMITTED from nodes/links (never "
            "fabricated) — wayne_county, e.g., has no comprador_bourgeoisie role at all"
        ),
        dtype="json",
        nullable=False,
        read_paths=_INSPECTOR_EMITTERS,
        derivation_site="web/game/engine_bridge.py::_build_circuit_flows (:913)",
        spec_ref="Program 17 Wave 1 · W1.6",
        notes=(
            "Graph-wide 4-node imperial-circuit mini-Sankey ({nodes, links}) attached to "
            "every social_class inspector payload, not scoped to the clicked node. The "
            "container itself is always a dict (possibly {nodes: [], links: []}); only its "
            "contents are conditional."
        ),
    ),
)

#: The declared observable-field contract. Populated per build phase.
SEAM_REGISTRY: tuple[SeamEntry, ...] = _MAP_METRICS + _INSPECTOR_METRICS
