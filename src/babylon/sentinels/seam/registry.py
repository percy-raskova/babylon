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
            "'imperial_rent' STOCK (imperial_rent_pool) — scope keeps them distinct. "
            "Owner ruling (2026-07-14, Wave 2): county-zoom aggregation of this metric is a "
            "SUM by design, not the pop-weighted mean used for the intensive rate lenses "
            "(profit_rate/exploitation_rate/occ) — Φ is an EXTENSIVE flow, so the county "
            "total is the meaningful number (summing an intensive rate would be "
            "nonsensical; summing this extensive one is not). Documented as a decision, "
            "not an accident. All NEW numeric lenses use population-weighted mean; "
            "categorical lenses use population-weighted mode with a deterministic tie-break."
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
# TERRITORY scope — the ``tick_*`` graph attrs ``write_tick_state_to_graph``
# stamps onto territory nodes at year boundaries
# (``src/babylon/domain/economics/tick/graph_bridge.py``, one
# ``graph.update_node`` call per territory, lines 102-195). Wave 2 Gap-1
# (Epochs audit; owner ruling 2, 2026-07-14) registers 24 of the 26
# previously-undeclared attrs in that call:
#
# * Group A (5, DECLARED_CONDITIONAL) — the crisis-detector family, genuinely
#   live and now read by ``_serialize_territory``.
# * Group B (3, DECLARED_CONDITIONAL) — real, non-null, but FROZEN at their
#   ``CountyEconomicState``/seed bootstrap constants until the named
#   calculator is wired (never silently relabeled as "live" data).
# * Group C (7, STRUCTURALLY_IMPOSSIBLE) — the circulation layer, dead until
#   ``turnover_profile_source`` is wired (gate:
#   ``domain/economics/tick/system/__init__.py:1050``).
# * Group D (9, STRUCTURALLY_IMPOSSIBLE) — the financial-distribution layer,
#   dead until ``interest_calculator`` is wired (gate: same file, :1248).
#
# ``tick_throughput_position``/``tick_supply_chain_depth`` are deliberately
# EXCLUDED — owner ruling 1 wires them for real in Round 2, alongside the
# throughput calculator, rather than registering them as frozen constants
# here only to re-register them days later.
# ---------------------------------------------------------------------------

_TERRITORY_EMITTERS: tuple[str, ...] = ("web/game/engine_bridge.py::_serialize_territory (:6009)",)

#: Groups C/D reach no serializer — that is the point (STRUCTURALLY_IMPOSSIBLE).
#: ``read_paths`` honestly cites the one place these attrs exist at all: the
#: engine's own write-site, not a bridge/serializer read call that doesn't exist.
_TICK_WRITE_SITE: tuple[str, ...] = (
    "src/babylon/domain/economics/tick/graph_bridge.py::write_tick_state_to_graph "
    "(year-boundary graph.update_node call, :102-195)",
)

_TURNOVER_GATE: str = (
    "STRUCTURALLY_IMPOSSIBLE: gated on the unwired `turnover_profile_source` service "
    "(domain/economics/tick/system/__init__.py:1050) — the circulation layer never "
    "computes this without a real turnover-profile source. Reaches no serializer; "
    "the observatory tells the truth about the gap instead of carrying silent debt."
)

_INTEREST_GATE: str = (
    "STRUCTURALLY_IMPOSSIBLE: gated on the unwired `interest_calculator` service "
    "(domain/economics/tick/system/__init__.py:1248) — the financial distribution "
    "layer never computes this without a real interest calculator. Reaches no "
    "serializer; the observatory tells the truth about the gap instead of carrying "
    "silent debt."
)

_TERRITORY_TICK_METRICS: tuple[SeamEntry, ...] = (
    # --- Group A: crisis-detector family (DECLARED_CONDITIONAL, year-boundary) ---
    SeamEntry(
        payload="tick_crisis_phase",
        wire_keys=("crisis_phase",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CrisisState via MultiPeriodCrisisDetector)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="enum:CrisisPhase",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes="Crisis lifecycle phase: normal|onset|early|deep|recovery (Feature 018 FR-003).",
    ),
    SeamEntry(
        payload="tick_crisis_duration",
        wire_keys=("crisis_duration",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CrisisState via MultiPeriodCrisisDetector)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="int",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes="Periods in active crisis (ONSET through DEEP); 0 in NORMAL/RECOVERY.",
    ),
    SeamEntry(
        payload="tick_bifurcation_score",
        wire_keys=("bifurcation_score",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (BifurcationRiskCalculator)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="float",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=(
            "Political trajectory [-1, +1] — -1 revolutionary, +1 fascist (Feature 018 FR-011)."
        ),
    ),
    SeamEntry(
        payload="tick_wage_compression",
        wire_keys=("wage_compression",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CrisisState)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="float",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes="Cumulative wage compression applied during crisis, [0, 1].",
    ),
    SeamEntry(
        payload="tick_capital_stock",
        wire_keys=("capital_stock",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CapitalStockCalculator)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            f"{_YEAR_BOUNDARY}; real (non-degenerate) only when the session has real "
            "county FIPS codes wired to a capital_calculator (owner item 25 Fix B) — "
            "0.0 otherwise, never a fabricated nonzero"
        ),
        dtype="float",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes="Capital stock K; the same K that feeds map.profit_rate/map.occ.",
    ),
    # --- Group B: frozen-constant family (DECLARED_CONDITIONAL; real, non-null, static) ---
    SeamEntry(
        payload="tick_class_distribution",
        wire_keys=("class_distribution",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (ClassDistribution seed shares)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="json",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=(
            "Five-class share dict — real and non-null, but FROZEN at the bootstrap "
            "seed shares: the transition_engine is unwired, so no simulated class "
            "mobility moves these shares tick to tick."
        ),
    ),
    SeamEntry(
        payload="tick_unemployment_rate",
        wire_keys=("unemployment_rate",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CountyEconomicState bootstrap default)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="float",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=(
            "Real and non-null, but FROZEN at 0.05 — no unemployment data source is "
            "wired (no reserve_army_data_source in _bridge_economics_overrides)."
        ),
    ),
    SeamEntry(
        payload="tick_median_wage",
        wire_keys=("tick_median_wage",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CountyEconomicState bootstrap default)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="float",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=(
            "Real and non-null, but FROZEN at 21.0 $/hr — no wage data source is "
            "wired (DefaultWagePressureCalculator has no reserve_army_data_source). "
            "Wire key deliberately kept tick_-prefixed (not 'median_wage') to avoid "
            "colliding with the real, distinct Territory.median_wage field "
            "(Feature 021) already on the same _serialize_territory payload."
        ),
    ),
    # --- Group C: circulation layer, gated on turnover_profile_source (:1050) ---
    SeamEntry(
        payload="tick_liquidity_ratio",
        wire_keys=("tick_liquidity_ratio",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CirculationState.circuit_state)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="float",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=_TURNOVER_GATE,
    ),
    SeamEntry(
        payload="tick_commodity_overhang",
        wire_keys=("tick_commodity_overhang",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CirculationState.circuit_state)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="float",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=_TURNOVER_GATE,
    ),
    SeamEntry(
        payload="tick_replacement_cycle",
        wire_keys=("tick_replacement_cycle",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (DepreciationFundState.replacement_cycle_position)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="enum:ReplacementCyclePosition",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=_TURNOVER_GATE,
    ),
    SeamEntry(
        payload="tick_inventory_diagnosis",
        wire_keys=("tick_inventory_diagnosis",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (InventoryState.inventory_problem)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="enum:InventoryDiagnosis",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=_TURNOVER_GATE,
    ),
    SeamEntry(
        payload="tick_realization_crisis",
        wire_keys=("tick_realization_crisis",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CirculationAssessment)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="bool",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=_TURNOVER_GATE,
    ),
    SeamEntry(
        payload="tick_turnover_crisis",
        wire_keys=("tick_turnover_crisis",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CirculationAssessment)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="bool",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=_TURNOVER_GATE,
    ),
    SeamEntry(
        payload="tick_reproduction_crisis",
        wire_keys=("tick_reproduction_crisis",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CirculationAssessment)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="bool",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=_TURNOVER_GATE,
    ),
    # --- Group D: financial distribution, gated on interest_calculator (:1248) ---
    SeamEntry(
        payload="tick_interest_burden",
        wire_keys=("tick_interest_burden",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (SurplusDistribution.interest_payments)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="float",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=_INTEREST_GATE,
    ),
    SeamEntry(
        payload="tick_ground_rent",
        wire_keys=("tick_ground_rent",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (RentExtraction.total_rent)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="float",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=(
            f"{_INTEREST_GATE} Second wall even if wired: _DefaultCountyRentalAdapter "
            "returns None, so this stays dark past the interest_calculator gate too."
        ),
    ),
    SeamEntry(
        payload="tick_rentier_share",
        wire_keys=("tick_rentier_share",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (SurplusDistribution.rentier_share)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="float",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=_INTEREST_GATE,
    ),
    SeamEntry(
        payload="tick_profit_of_enterprise",
        wire_keys=("tick_profit_of_enterprise",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (SurplusDistribution.profit_of_enterprise)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="float",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=(
            f"{_INTEREST_GATE} Can be negative (a debt-spiral signal) once wired — "
            "never clamp to 0 if this is ever lit."
        ),
    ),
    SeamEntry(
        payload="tick_financialization_share",
        wire_keys=("tick_financialization_share",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (SurplusDistribution.financialization_share)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="float",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=_INTEREST_GATE,
    ),
    SeamEntry(
        payload="tick_accumulated_debt",
        wire_keys=("tick_accumulated_debt",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (DebtAccumulation.accumulated_debt)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="float",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=_INTEREST_GATE,
    ),
    SeamEntry(
        payload="tick_claims_exceed_surplus",
        wire_keys=("tick_claims_exceed_surplus",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (SurplusDistribution.claims_exceed_surplus)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="bool",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=_INTEREST_GATE,
    ),
    SeamEntry(
        payload="tick_housing_fictitious_fraction",
        wire_keys=("tick_housing_fictitious_fraction",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (HousingValueDecomposition.fictitious_fraction)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="float",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=(
            f"{_INTEREST_GATE} The only Group D attr with an honest None write-side "
            "fallback (graph_bridge.py already writes None, not 0.0, when "
            "housing_decomposition is absent)."
        ),
    ),
    SeamEntry(
        payload="tick_financial_crisis_signals",
        wire_keys=("tick_financial_crisis_signals",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (FinancialCrisisSignals.active_signals)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="int",
        read_paths=_TICK_WRITE_SITE,
        spec_ref="Epochs audit · Wave 2 · Gap-1",
        notes=f"{_INTEREST_GATE} Count of active signals, int in [0, 4].",
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
SEAM_REGISTRY: tuple[SeamEntry, ...] = _MAP_METRICS + _TERRITORY_TICK_METRICS + _INSPECTOR_METRICS
