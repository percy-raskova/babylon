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
    # --- Wave 2 W2.4 (owner ruling 1 + delegated rulings, 2026-07-14) ---
    SeamEntry(
        payload="tick_throughput_position",
        wire_keys=("throughput_position",),
        scope=SeamScope.MAP,
        owner_layer="domain.economics.throughput (DefaultThroughputCalculator)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            f"{_YEAR_BOUNDARY}; also requires the session to carry real county FIPS AND "
            "_bridge_economics_overrides to have wired a throughput_calculator (owner ruling 1) "
            "— before that fix this stamped the engine's frozen bootstrap constant 1.0 forever, "
            "a value that even probes as 'live' to a naive liveness check"
        ),
        dtype="float",
        read_paths=_MAP_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · owner ruling 1",
        notes=(
            "π = τ_through / τ_national (Feature 014, Domestic Value Geography). Rides "
            "hex_latest's JSONB attributes column like habitability/solidarity_index — no "
            "dedicated column. Population-weighted MEAN at county zoom (owner ruling 4)."
        ),
    ),
    SeamEntry(
        payload="agitation_index",
        wire_keys=("agitation",),
        scope=SeamScope.MAP,
        owner_layer="bridge-derived (_agitation_index_by_territory)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "non-zero once IdeologySystem processes a falling-wage/rent/Φ/g33 crisis tick — "
            "it is LEGITIMATELY 0.0 at tick 0 in every shipped scenario, never warmed up to "
            "look more alive than the engine has actually made it"
        ),
        dtype="float",
        read_paths=_MAP_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · W2.4 delegated ruling",
        notes=(
            "Population-weighted mean IdeologicalProfile.agitation over the territory's "
            "TENANCY-linked social_class members — the Revolutionary Potential Index. "
            "Rides hex_latest's JSONB attributes column like habitability/solidarity_index."
        ),
    ),
    SeamEntry(
        payload="territory_type",
        wire_keys=("territory_type",),
        scope=SeamScope.MAP,
        owner_layer="engine (Territory.territory_type, TerritoryType enum)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="enum:TerritoryType",
        read_paths=_MAP_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · W2.4 delegated ruling",
        notes=(
            "The real TerritoryType enum (CORE/PERIPHERY plus the Necropolitical Triad "
            "RESERVATION/PENAL_COLONY/CONCENTRATION_CAMP), a required Territory field with a "
            "default — always present, never fabricated. Shipped scenarios seed only "
            "CORE/PERIPHERY; the Triad renders once a scenario seeds one (Amendment R / task "
            "#49). Population-weighted MODE at county zoom, deterministic tie-break "
            "lexicographically-greatest on the value (same convention as dominant_class). Do "
            "NOT confuse with stub_bridge.py's legacy 'URBAN/SUBURBAN/PERIURBAN' vocabulary "
            "(a different, pre-existing mock field on the unrelated territories snapshot list)."
        ),
    ),
    # --- Audit Wave 4 straggler (task #76, 2026-07-15) ---
    SeamEntry(
        payload="org_network_centrality",
        wire_keys=("centrality",),
        scope=SeamScope.MAP,
        owner_layer="bridge-derived (_centrality_by_territory / _org_network_centrality)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "non-null only for a territory carrying a PRESENCE/HOUSES edge from at least one "
            "organization/institution in the org network — sparse today: only wayne_county "
            "seeds real Organization rows (_legacy_wayne.py), so every other shipped scenario "
            "(us/high_tension/imperial_circuit/labor_aristocracy/two_node) is honestly empty "
            "for this lens"
        ),
        dtype="float",
        read_paths=_MAP_EMITTERS,
        spec_ref="Epochs audit · Wave 4 · task #76",
        notes=(
            "A territory's own degree-centrality within the org-network topology — reuses the "
            "NETWORK-scope 'centrality' entry's underlying _org_network_centrality formula, "
            "computed unfiltered (whole-session org network, not one request's scoped view) so "
            "readings are comparable across the map. Distinct from NETWORK-scope 'centrality' "
            "(per-node dict keyed by scope.wire_key — SeamScope docstring): this MAP row is one "
            "float per territory, rides hex_latest's JSONB attributes column like "
            "agitation/solidarity_index. Verified non-degenerate on wayne_county's 3 "
            "PRESENCE-linked territories (0.25/0.5/0.5 degree split)."
        ),
    ),
    # --- Wave 5 receptivity lens pair (Epistemic Horizon Phase 1 honest-display,
    # 2026-07-15). Both are conditionally-present, unlike territory_type: they
    # are honest-null (III.11) for a tenant-less territory OR before
    # EpistemicHorizonSystem has ever run this session (engine position 27 —
    # only executes inside a tick, so the seeded tick-0 graph never carries
    # them). mass_receptivity additionally can be LEGITIMATELY exactly 0.0 in
    # real gameplay (e.g. a territory tenanted only by a role absent from the
    # corpus's class-factor table, class_factor_default=0.0 — see
    # EpistemicHorizonSystem's own worked test), which is indistinguishable
    # from Sensor 2's dark_default probe — the deciding reason both stay
    # DECLARED_CONDITIONAL rather than territory_type's MUST_BE_LIVE, even
    # though every wayne_county territory happened to get a real value this
    # Phase-1 pass (65 desert / 16 mud / 0 water, 81/81 covered).
    # ---------------------------------------------------------------------------
    SeamEntry(
        payload="mass_receptivity",
        wire_keys=("mass_receptivity",),
        scope=SeamScope.MAP,
        owner_layer="engine (EpistemicHorizonSystem, babylon.engine.systems.epistemic_horizon)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "requires at least one TENANCY-linked social_class member with positive "
            "population (Constitution III.11 honest-null — EpistemicHorizonSystem skips a "
            "tenant-less territory entirely, writing none of the three shadow attrs) AND "
            "resolve_tick to have run at least once this session (the system is engine "
            "position 27, last — the seeded tick-0 graph has never been stepped). Separately: "
            "M_r can be LEGITIMATELY exactly 0.0 (a role absent from the corpus's class-factor "
            "table falls to class_factor_default=0.0), a real value Sensor 2's dark_default "
            "probe cannot distinguish from 'never computed' — unlike territory_type's non-empty "
            "enum, so this is DECLARED_CONDITIONAL, not MUST_BE_LIVE"
        ),
        dtype="float",
        write_site=(
            "src/babylon/engine/systems/epistemic_horizon.py::"
            "compute_epistemic_horizon (graph.update_node)"
        ),
        read_paths=_MAP_EMITTERS,
        spec_ref="project/research/epistemic-horizon-program-proposal.md · Phase 1",
        notes=(
            "M_r = population-weighted mean over TENANCY-linked tenant classes of "
            "(1 - p_acquiescence) * class_consciousness * C_f. A NATIVE per-territory graph "
            "attr (unlike agitation/solidarity_index, which are TENANCY-projected "
            "aggregations of a per-class value) — rides straight off _serialize_territory's "
            "own key, same shape as habitability/throughput_position. "
            "_carry_epistemic_horizon re-injects it onto the web bridge's post-round-trip "
            "graph (the same altitude-gap fix _carry_tick_dynamics_flows applies to "
            "TickDynamicsSystem's tick_*/flow_* attrs). Population-weighted MEAN at county "
            "zoom, partial-coverage-aware (same pattern as agitation/throughput_position)."
        ),
    ),
    SeamEntry(
        payload="vision_state",
        wire_keys=("vision_state",),
        scope=SeamScope.MAP,
        owner_layer="engine (EpistemicHorizonSystem, babylon.engine.systems.epistemic_horizon)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "requires at least one TENANCY-linked social_class member with positive "
            "population (Constitution III.11 honest-null, same gate as mass_receptivity above) "
            "AND resolve_tick to have run at least once this session (engine position 27, "
            "last). Unlike mass_receptivity, vision_state is a non-empty enum string "
            "('desert'/'mud'/'water') whenever WRITTEN, so it would probe LIVE the same way "
            "territory_type does once present — but its PRESENCE, not its value, is what stays "
            "conditional: territory_type is a required, defaulted Territory MODEL field "
            "(unconditionally present on every territory node); vision_state is derived, "
            "written only when M_r itself was honestly computable. That conditional absence, "
            "not a fabricated default, is why this stays DECLARED_CONDITIONAL despite its "
            "categorical MUST_BE_LIVE-style non-emptiness"
        ),
        dtype="enum:str",
        write_site=(
            "src/babylon/engine/systems/epistemic_horizon.py::"
            "compute_epistemic_horizon (graph.update_node)"
        ),
        read_paths=_MAP_EMITTERS,
        spec_ref="project/research/epistemic-horizon-program-proposal.md · Phase 1",
        notes=(
            "The corpus's fog-of-war three-state partition (ai/epochs/epoch3/fog-of-war.yaml "
            "'desert'/M_r<0.2, 'water'/M_r>=0.8, 'mud' between — EpistemicHorizonDefines "
            "desert_threshold/water_threshold), derived from mass_receptivity above. A NATIVE "
            "per-territory graph attr (like mass_receptivity), also re-injected by "
            "_carry_epistemic_horizon. Population-weighted MODE at county zoom, same "
            "deterministic lexicographically-greatest tie-break as dominant_class/"
            "territory_type. Phase 1 finding (wayne_county): 65 desert / 16 mud / 0 water — "
            "C_p=0 everywhere (no is_player org marker) means water is unreached today, not "
            "structurally impossible."
        ),
    ),
    # --- Feature 021 lens pair (System #5 ReserveArmySystem / System #10
    # DispossessionEventSystem, registered 2026-07-15). Both are NATIVE
    # per-territory graph attrs (like habitability/mass_receptivity), and
    # both are presence-conditional in the SAME way org_network_centrality
    # is: the writing system skips a territory entirely (writes no attr at
    # all) rather than write a fabricated 0.0, so DECLARED_CONDITIONAL is
    # about the ATTR'S PRESENCE, not merely its value being legitimately
    # zero (contrast mass_receptivity, which is always written once a
    # territory has TENANCY-linked tenants, but can be a real 0.0).
    # ---------------------------------------------------------------------------
    SeamEntry(
        payload="wage_pressure",
        wire_keys=("wage_pressure",),
        scope=SeamScope.MAP,
        owner_layer="engine (ReserveArmySystem, babylon.engine.systems.reserve_army)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "non-null only for a territory whose reserve_ratio > 0.0 AND whose bounded-sigmoid "
            "wage_pressure is itself > 0.0 this tick (reserve_army.py:69-76) — ReserveArmySystem "
            "writes no wage_pressure attr at all for a territory with no reserve-army pressure, "
            "never a fabricated 0.0"
        ),
        dtype="float",
        write_site=(
            "src/babylon/engine/systems/reserve_army.py::ReserveArmySystem.step "
            "(protocol.update_node)"
        ),
        read_paths=_MAP_EMITTERS,
        spec_ref="Feature 021 · System #5",
        notes=(
            "Reserve Army of Labor wage-discipline coefficient (DefaultWagePressureCalculator's "
            "bounded sigmoid over reserve_ratio) — rides hex_latest's JSONB attributes column "
            "like habitability/mass_receptivity. Population-weighted MEAN at county zoom, "
            "partial-coverage-aware."
        ),
    ),
    SeamEntry(
        payload="dispossession_intensity",
        wire_keys=("dispossession_intensity",),
        scope=SeamScope.MAP,
        owner_layer="engine (DispossessionEventSystem, babylon.engine.systems.dispossession_events)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "non-null only for a territory with at least one of foreclosure_rate/eviction_rate/"
            "displacement_rate > 0.0 this tick (dispossession_events.py:73-74) — "
            "DispossessionEventSystem writes no dispossession_intensity attr at all absent any "
            "dispossession activity, never a fabricated 0.0"
        ),
        dtype="float",
        read_paths=_MAP_EMITTERS,
        spec_ref="Feature 021 · System #10",
        notes=(
            "Composite carceral/eviction intensity (DispossessionIntensityCalculator's weighted "
            "foreclosure/eviction/displacement/tax-sale/eminent-domain blend) — rides "
            "hex_latest's JSONB attributes column like habitability/mass_receptivity. "
            "Population-weighted MEAN at county zoom, partial-coverage-aware."
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
# ``tick_throughput_position``/``tick_supply_chain_depth`` were deliberately
# EXCLUDED from this Round-1 list — owner ruling 1 wires them for real in
# Round 2, alongside the throughput calculator, rather than registering them
# as frozen constants here only to re-register them days later. They are
# registered below now that the wiring has landed (see
# ``_bridge_economics_overrides``'s ``throughput_calculator``), as a Group A
# variant: genuinely live (not frozen), DECLARED_CONDITIONAL on the session
# having real county FIPS + the calculator wired + a year boundary.
# ---------------------------------------------------------------------------

_TERRITORY_EMITTERS: tuple[str, ...] = ("web/game/engine_bridge.py::_serialize_territory (:6218)",)

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
        owner_layer="domain.economics.tick (SQLiteBLSUnemploymentSource, LAUS U-3)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="float",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · Wave 6 D8",
        notes=(
            "Wave 6 D8: per-county BLS LAUS U-3 via services.unemployment_source "
            "(wired in _bridge_economics_overrides + headless "
            "_build_economics_overrides); falls back to the 0.05 prev-carry "
            "default only when the county/year row is absent (honest None)."
        ),
    ),
    SeamEntry(
        payload="tick_median_wage",
        wire_keys=("tick_median_wage",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (QCEW p50 bootstrap + wage-pressure dynamics)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="float",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · owner item 60",
        notes=(
            "Item 60 (2026-07-15): the bootstrap is now the employment-weighted "
            "p50 estimator over QCEW 6-digit industry wages via "
            "services.wage_source (a genuine median approximation — the raw "
            "QCEW county mean was NOT wired precisely because it is a mean). "
            "ENDOGENOUS after tick 1: wage-pressure/compression dynamics own "
            "the trajectory; the source seeds only the initial condition. "
            "21.0 $/hr remains the documented unwired/absent-row bootstrap. "
            "Wire key deliberately kept tick_-prefixed (not 'median_wage') to avoid "
            "colliding with the real, distinct Territory.median_wage field "
            "(Feature 021) already on the same _serialize_territory payload."
        ),
    ),
    # --- Round 2 (owner ruling 1, 2026-07-14): throughput_position/
    # supply_chain_depth wired for real — genuinely live (not a Group-B frozen
    # constant) once a session has real county FIPS + throughput_calculator ---
    SeamEntry(
        payload="tick_throughput_position",
        wire_keys=("throughput_position",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.throughput (DefaultThroughputCalculator)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            f"{_YEAR_BOUNDARY}; also requires the session to carry real county FIPS AND "
            "_bridge_economics_overrides to have wired a throughput_calculator (owner ruling 1)"
        ),
        dtype="float",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · owner ruling 1",
        notes=(
            "π = τ_through / τ_national (Feature 014). Genuinely live now — distinct from "
            "Group B above, which stays FROZEN pending a named unwired service; this attr's "
            "gap was pure engineering (the calculator was never constructed), now fixed."
        ),
    ),
    SeamEntry(
        payload="tick_supply_chain_depth",
        wire_keys=("supply_chain_depth",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.throughput (DefaultSupplyChainAnalyzer)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            f"{_YEAR_BOUNDARY}; also requires the session to carry real county FIPS AND "
            "_bridge_economics_overrides to have wired a throughput_calculator (owner ruling 1)"
        ),
        dtype="float",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · owner ruling 1",
        notes="D, employment-weighted NAICS supply-chain depth (0-5 scale), Feature 014.",
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
    # --- Wave 5 receptivity lens pair, territory-serializer/inspector rows
    # (2026-07-15). mass_receptivity/vision_state mirror their MAP-scope
    # siblings above — same payload, same DECLARED_CONDITIONAL reasoning,
    # different observable surface (_serialize_territory + get_inspector_hex
    # rather than the /map/ hex/county features). intel_confidence joins
    # them here ONLY: it deliberately has NO MAP-scope row (no lens) — it is
    # uniformly 0.1 in every scenario verified so far (C_p=0 everywhere; see
    # the program report's Phase-1 findings), so a flat lens would be
    # decorative, but the real per-territory value is still honestly
    # exposed on the drill-down surfaces.
    SeamEntry(
        payload="mass_receptivity",
        wire_keys=("mass_receptivity",),
        scope=SeamScope.TERRITORY,
        owner_layer="engine (EpistemicHorizonSystem, babylon.engine.systems.epistemic_horizon)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "same TENANCY-population + resolve_tick-has-run gate as the MAP-scope "
            "'map.mass_receptivity' row; M_r can also be legitimately exactly 0.0 (see that "
            "row's liveness_condition for the full reasoning)"
        ),
        dtype="float",
        write_site=(
            "src/babylon/engine/systems/epistemic_horizon.py::"
            "compute_epistemic_horizon (graph.update_node)"
        ),
        read_paths=(
            *_TERRITORY_EMITTERS,
            "web/game/engine_bridge.py::EngineBridge.get_inspector_hex",
        ),
        spec_ref="project/research/epistemic-horizon-program-proposal.md · Phase 1",
        notes=(
            "Read via _territory_graph_attr, same shape as habitability/throughput_position "
            "on this surface. None for a tenant-less territory or before the graph has ever "
            "been stepped this session."
        ),
    ),
    SeamEntry(
        payload="intel_confidence",
        wire_keys=("intel_confidence",),
        scope=SeamScope.TERRITORY,
        owner_layer="engine (EpistemicHorizonSystem, babylon.engine.systems.epistemic_horizon)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "same TENANCY-population + resolve_tick-has-run gate as mass_receptivity above "
            "(I_c is derived FROM M_r — EpistemicHorizonSystem writes all three shadow attrs "
            "together or not at all)"
        ),
        dtype="float",
        write_site=(
            "src/babylon/engine/systems/epistemic_horizon.py::"
            "compute_epistemic_horizon (graph.update_node)"
        ),
        read_paths=(
            *_TERRITORY_EMITTERS,
            "web/game/engine_bridge.py::EngineBridge.get_inspector_hex",
        ),
        spec_ref="project/research/epistemic-horizon-program-proposal.md · Phase 1",
        notes=(
            "I_c = B_o + (C_p * M_r), clamped [0, 1]. Deliberately has NO MAP-scope sibling "
            "row — verified uniformly 0.1 across wayne_county's 81 territories this Phase-1 "
            "pass (C_p=0 everywhere: no Organization subtype outside PoliticalFaction carries "
            "an is_player marker — new ruling 6 in the program report, prereq for Phase 2), so "
            "a flat map lens would be purely decorative. Still a real, honestly-computed "
            "per-territory value on this drill-down surface, not fabricated."
        ),
    ),
    SeamEntry(
        payload="vision_state",
        wire_keys=("vision_state",),
        scope=SeamScope.TERRITORY,
        owner_layer="engine (EpistemicHorizonSystem, babylon.engine.systems.epistemic_horizon)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "same TENANCY-population + resolve_tick-has-run gate as the MAP-scope "
            "'map.vision_state' row (see that row's liveness_condition for the full "
            "present-vs-value-conditional reasoning)"
        ),
        dtype="enum:str",
        write_site=(
            "src/babylon/engine/systems/epistemic_horizon.py::"
            "compute_epistemic_horizon (graph.update_node)"
        ),
        read_paths=(
            *_TERRITORY_EMITTERS,
            "web/game/engine_bridge.py::EngineBridge.get_inspector_hex",
        ),
        spec_ref="project/research/epistemic-horizon-program-proposal.md · Phase 1",
        notes=(
            "Read via _territory_graph_attr, same shape as mass_receptivity on this surface. "
            "None for a tenant-less territory or before the graph has ever been stepped this "
            "session."
        ),
    ),
    # --- Feature 021 lens pair, territory-serializer rows (2026-07-15).
    # wage_pressure/dispossession_intensity mirror their MAP-scope siblings
    # above — same payload, same DECLARED_CONDITIONAL reasoning (presence-
    # conditional, not merely value-conditional), different observable
    # surface (_serialize_territory rather than the /map/ hex/county
    # features).
    SeamEntry(
        payload="wage_pressure",
        wire_keys=("wage_pressure",),
        scope=SeamScope.TERRITORY,
        owner_layer="engine (ReserveArmySystem, babylon.engine.systems.reserve_army)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "same reserve_ratio > 0.0 gate as the MAP-scope 'map.wage_pressure' row; "
            "ReserveArmySystem writes no attr at all for a territory with no reserve-army "
            "pressure this tick"
        ),
        dtype="float",
        write_site=(
            "src/babylon/engine/systems/reserve_army.py::ReserveArmySystem.step "
            "(protocol.update_node)"
        ),
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Feature 021 · System #5",
        notes=(
            "Read via _territory_graph_attr, same shape as habitability/mass_receptivity on "
            "this surface. None until ReserveArmySystem writes it (reserve_ratio > 0 this tick)."
        ),
    ),
    SeamEntry(
        payload="dispossession_intensity",
        wire_keys=("dispossession_intensity",),
        scope=SeamScope.TERRITORY,
        owner_layer="engine (DispossessionEventSystem, babylon.engine.systems.dispossession_events)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "same foreclosure/eviction/displacement-rate > 0.0 gate as the MAP-scope "
            "'map.dispossession_intensity' row; DispossessionEventSystem writes no attr at all "
            "absent any dispossession activity this tick"
        ),
        dtype="float",
        write_site=(
            "src/babylon/engine/systems/dispossession_events.py::DispossessionEventSystem.step "
            "(protocol.update_node)"
        ),
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Feature 021 · System #10",
        notes=(
            "Read via _territory_graph_attr, same shape as habitability/mass_receptivity on "
            "this surface. None until DispossessionEventSystem writes it (some dispossession "
            "rate > 0 this tick)."
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
        payload="reactionary_entitlement",
        wire_keys=("entitlement",),
        scope=SeamScope.INSPECTOR,
        owner_layer=(
            "engine (SocialClass.entitlement, babylon.models.entities.social_class — "
            "spec-071 Reactionary Subject, role-defaulted; read by FascistFactionSystem "
            "for Fascist_Pull)"
        ),
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "requires the node to carry an 'entitlement' graph attribute; null for a "
            "social_class-shaped fixture without one — never a fabricated 0.0"
        ),
        dtype="float",
        read_paths=_INSPECTOR_EMITTERS,
        spec_ref="AW3-R1 (epochs-vision-gap-audit.md Wave 3 item 2)",
        notes=(
            "Stake in the imperial order [0.0, 1.0] — a real pre-existing engine field "
            "(role-defaulted: P=0.2, C_la=0.8, C_pb=0.7, L_u=0.0), newly EXPOSED on this "
            "endpoint by this pass, same pattern as class_inequality (W1.4). Its sibling "
            "'chauvinism' (also spec-071 Reactionary Subject, FascistFactionSystem) is "
            "deliberately NOT registered here: it is real but lives on the org->LA "
            "MEMBERSHIP edge, not the social_class node, so there is no single per-class "
            "scalar to expose on this endpoint (see _social_class_inspector_fields's "
            "docstring)."
        ),
    ),
    SeamEntry(
        payload="reactionary_volatility",
        wire_keys=("volatility",),
        scope=SeamScope.INSPECTOR,
        owner_layer=(
            "engine (SocialClass.volatility, babylon.models.entities.social_class — "
            "spec-071 Reactionary Subject, role-defaulted; gates SPONTANEOUS_RIOT)"
        ),
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "requires the node to carry a 'volatility' graph attribute; null for a "
            "social_class-shaped fixture without one — never a fabricated 0.0"
        ),
        dtype="float",
        read_paths=_INSPECTOR_EMITTERS,
        spec_ref="AW3-R1 (epochs-vision-gap-audit.md Wave 3 item 2)",
        notes=(
            "Disorder propensity [0.0, 1.0] — a real pre-existing engine field "
            "(role-defaulted: L_u=0.8, else 0.0), newly EXPOSED on this endpoint by this "
            "pass, same pattern as class_inequality (W1.4)."
        ),
    ),
    SeamEntry(
        payload="survival_p_acquiescence",
        wire_keys=("p_acquiescence",),
        scope=SeamScope.INSPECTOR,
        owner_layer="engine (SurvivalSystem.step, babylon.engine.systems.survival)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
        write_site="src/babylon/engine/systems/survival.py::SurvivalSystem.step (:143)",
        read_paths=_INSPECTOR_EMITTERS,
        spec_ref="Program 17 Wave 2 · W2.5b",
        notes=(
            "P(S|A) — Sigmoid(wealth_per_capita - subsistence). A required SocialClass "
            "Probability field (default 0.0), so always present on a social_class node's "
            "graph attrs; a legitimate 0.0 at tick 0 (not-yet-computed) is still real, never "
            "fabricated — same status as agitation. The survival duel chart's P(S|A) series."
        ),
    ),
    SeamEntry(
        payload="survival_p_revolution",
        wire_keys=("p_revolution",),
        scope=SeamScope.INSPECTOR,
        owner_layer="engine (SurvivalSystem.step, babylon.engine.systems.survival)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
        write_site="src/babylon/engine/systems/survival.py::SurvivalSystem.step (:143)",
        read_paths=_INSPECTOR_EMITTERS,
        spec_ref="Program 17 Wave 2 · W2.5b",
        notes=(
            "P(S|R) — effective_organization / repression. Rupture condition is "
            "P(S|R) > P(S|A) (StruggleSystem, struggle.py:338); the crossing is only EVENTED "
            "(UPRISING/revolutionary_pressure) for the two struggling roles "
            "(PERIPHERY_PROLETARIAT/LUMPENPROLETARIAT) — this raw value is real for every "
            "social_class node regardless. The survival duel chart's P(S|R) series."
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

# ---------------------------------------------------------------------------
# FIELD_STATE scope — ``GET /api/games/{id}/field_state/`` (Program 19/20,
# Wave 3 Round 1, Backend-W3R1). The Systems #19/#20 contradiction-field
# stack: ContradictionFieldSystem @19 writes per-social_class
# ``contradiction_fields`` (``{"exploitation": float, "atomization": float}``
# in production — the opposition-sourced E0 repoint, no ``field_registry``
# wired); FieldDerivativeSystem @20 writes per-node ``field_derivatives``
# (per-field laplacian/df_dt/d2f_dt2), per-edge ``field_gradients``, and the
# graph-level ``principal_field``; ContradictionSystem @18 writes the
# graph-level ``dialectical_regime``; FascistFactionSystem writes per-node
# ``fascist_alignment``.
#
# CARRY LANDED (Program 19/20 Wave 3 Round 1, Backend field-derivative facade
# carry): FieldDerivativeSystem.step() now composes ONE graph-level
# ``field_stack`` snapshot (``{"nodes": {...}, "edges": [...]}``) at the end
# of every tick (``_build_field_stack``,
# ``babylon.engine.systems.field_derivative``). ``WorldState.to_graph()``/
# ``from_graph()`` carry this attr across the round trip ``resolve_tick``
# performs every real tick, AND re-stamp the per-node
# (``contradiction_fields``/``field_derivatives``) and per-edge
# (``field_gradients``) attrs the snapshot was built from onto the
# reconstructed graph (``WorldState._restamp_field_stack``) — closing the
# "bridge altitude vs bare-engine altitude" gap Sensor 2 found for the
# ``/map/`` ``MUST_BE_LIVE`` family (see ``test_seam_liveness.py``'s module
# docstring). Of the six payload/wire-key rows below: ``contradiction_fields``
# (``fields``), ``field_derivatives`` (``laplacian``), and ``field_gradients``
# (``gradient``) are unconditionally computed every tick for every applicable
# node/edge, so they are promoted to ``MUST_BE_LIVE`` (alongside the
# pre-existing ``fascist_alignment`` row). ``field_derivatives`` (``df_dt``),
# ``principal_field``, and ``dialectical_regime`` remain
# ``DECLARED_CONDITIONAL``: each has a genuine tick-history / opposition-state
# dependency the carry does not remove (see each row's own
# ``liveness_condition``) — ``df_dt`` additionally still needs a separate,
# NOT-fixed-here ``resolve_tick`` ``persistent_context`` fix before it is live
# on the WEB bridge specifically (it is unconditionally live on the headless
# runner, which never round-trips the graph mid-run — see
# ``headless_runner/runner.py::_run_tick_and_persist``).
# ---------------------------------------------------------------------------

_FIELD_STATE_NODE_EMITTERS: tuple[str, ...] = (
    "web/game/engine_bridge.py::EngineBridge.get_field_state",
    "web/game/engine_bridge.py::_build_field_state_nodes",
)
_FIELD_STATE_EDGE_EMITTERS: tuple[str, ...] = (
    "web/game/engine_bridge.py::EngineBridge.get_field_state",
    "web/game/engine_bridge.py::_build_field_state_edges",
)
_FIELD_STATE_GRAPH_EMITTERS: tuple[str, ...] = (
    "web/game/engine_bridge.py::EngineBridge.get_field_state",
)

_FIELD_STACK_CARRY: str = (
    "LIVE as of Program 19/20 Wave 3 Round 1 (Backend field-derivative facade "
    "carry): FieldDerivativeSystem.step() composes a graph-level "
    "``field_stack`` snapshot every tick; WorldState.to_graph()/from_graph() "
    "carry it across the round trip resolve_tick performs and re-stamp the "
    "per-node/edge attrs it was built from "
    "(babylon.models.world_state.WorldState._restamp_field_stack), so this "
    "payload reads real on every real resolve_tick."
)

_DF_DT_CONDITION: str = (
    f"{_FIELD_STACK_CARRY} Still DECLARED_CONDITIONAL, not MUST_BE_LIVE: needs "
    ">= 2 ticks of contradiction_history (persistent_data), and "
    "resolve_tick's persistent_context is a fresh {} per HTTP call today — a "
    "separate, NOT-fixed-here gap (contradiction_history never accumulates "
    "across web ticks), independent of the round-trip carry."
)

_PRINCIPAL_FIELD_CONDITION: str = (
    f"{_FIELD_STACK_CARRY} The graph attr itself is now always present once "
    "FieldDerivativeSystem runs, but its field_name is legitimately null "
    "until >= 1 tick establishes a df/dt-derived principal (same history "
    "dependency as field_derivatives' df_dt above) — DECLARED_CONDITIONAL, "
    "not MUST_BE_LIVE."
)

_DIALECTICAL_REGIME_CONDITION: str = (
    f"{_FIELD_STACK_CARRY} The graph attr is legitimately absent until a "
    "capital_labor (or principal) OppositionState exists — "
    "ContradictionSystem._classify_regime returns without writing it "
    "otherwise — so this stays DECLARED_CONDITIONAL, not MUST_BE_LIVE."
)

_FIELD_STATE_METRICS: tuple[SeamEntry, ...] = (
    SeamEntry(
        payload="contradiction_fields",
        wire_keys=("fields",),
        scope=SeamScope.FIELD_STATE,
        owner_layer=(
            "engine (ContradictionFieldSystem @19, babylon.engine.systems.contradiction_field)"
        ),
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="json",
        write_site=(
            "src/babylon/engine/systems/contradiction_field.py::"
            "ContradictionFieldSystem._step_from_oppositions (:191, graph.update_node)"
        ),
        read_paths=_FIELD_STATE_NODE_EMITTERS,
        derivation_site="web/game/engine_bridge.py::_build_field_state_nodes",
        spec_ref="Program 19/20 · Wave 3 Round 1 (Backend-W3R1 + field-derivative facade carry)",
        notes=(
            "Per-social_class {field_name: value}; production sources "
            "'exploitation' (mean fresh EXPLOITATION/WAGES/TENANCY edge tension) "
            "and 'atomization' (global opposition gap) from the E0 "
            "opposition-layer repoint, not a field_registry (dormant in "
            "production). Honest-omission: a node with no contradiction_fields "
            "at all is dropped from the nodes list entirely, never a fabricated "
            "empty-fields entry. MUST_BE_LIVE: unconditionally computed for "
            "every active social_class node every tick, and now survives the "
            "WorldState round trip via the field_stack carry (this row's "
            "liveness_class was STRUCTURALLY_IMPOSSIBLE before that carry "
            "landed — see the FIELD_STATE scope comment above)."
        ),
    ),
    SeamEntry(
        payload="field_derivatives",
        wire_keys=("laplacian",),
        scope=SeamScope.FIELD_STATE,
        owner_layer=("engine (FieldDerivativeSystem @20, babylon.engine.systems.field_derivative)"),
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="json",
        write_site=(
            "src/babylon/engine/systems/field_derivative.py::"
            "_compute_node_derivatives (:228, graph.update_node)"
        ),
        read_paths=_FIELD_STATE_NODE_EMITTERS,
        derivation_site="web/game/engine_bridge.py::_build_field_state_nodes",
        spec_ref="Program 19/20 · Wave 3 Round 1 (Backend-W3R1 + field-derivative facade carry)",
        notes=(
            "Per-field weighted Laplacian sum_j(w_j * (f(j) - f(i))) over "
            "incident edges; 0.0 for an isolated node is a real value (EC-002), "
            "never a fabricated placeholder. Sibling row 'field_state.df_dt' "
            "shares this same engine write-site (field_derivatives is one dict "
            "with laplacian/df_dt/d2f_dt2 sub-keys); d2f_dt2 is deliberately NOT "
            "part of this endpoint's declared contract (out of scope for W3R1). "
            "MUST_BE_LIVE: computed unconditionally for every node carrying "
            "contradiction_fields (isolated-node 0.0 counts as live, per "
            "EC-002), and now survives the WorldState round trip via the "
            "field_stack carry — unlike sibling 'df_dt' below, laplacian has "
            "no additional history dependency."
        ),
    ),
    SeamEntry(
        payload="field_derivatives",
        wire_keys=("df_dt",),
        scope=SeamScope.FIELD_STATE,
        owner_layer=("engine (FieldDerivativeSystem @20, babylon.engine.systems.field_derivative)"),
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_DF_DT_CONDITION,
        dtype="json",
        write_site=(
            "src/babylon/engine/systems/field_derivative.py::"
            "_compute_node_derivatives (:228, graph.update_node)"
        ),
        read_paths=_FIELD_STATE_NODE_EMITTERS,
        derivation_site="web/game/engine_bridge.py::_build_field_state_nodes",
        spec_ref="Program 19/20 · Wave 3 Round 1 (Backend-W3R1 + field-derivative facade carry)",
        notes=(
            "Per-field temporal derivative f(t) - f(t-1) from the 3-tick "
            "rolling history in persistent_data; needs >= 2 history points or "
            "the field is None and honestly omitted from this dict (distinct "
            "from the field_derivatives container itself, which can be present "
            "with only laplacian populated). The field_stack carry fixes the "
            "round-trip evaporation, but this row stays DECLARED_CONDITIONAL: "
            "resolve_tick's persistent_context is STILL a fresh {} per HTTP "
            "call today, so contradiction_history never accumulates on the web "
            "bridge specifically — a separate, NOT-fixed-here gap (see "
            "liveness_condition)."
        ),
    ),
    SeamEntry(
        payload="fascist_alignment",
        wire_keys=("fascist_alignment",),
        scope=SeamScope.FIELD_STATE,
        owner_layer="engine (FascistFactionSystem, babylon.engine.systems.reactionary)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
        write_site=(
            "src/babylon/engine/systems/reactionary.py::"
            "FascistFactionSystem._process_drift (:136, graph.update_node)"
        ),
        read_paths=_FIELD_STATE_NODE_EMITTERS,
        derivation_site="web/game/engine_bridge.py::_build_field_state_nodes",
        spec_ref="Program 19/20 · Wave 3 Round 1 (Backend-W3R1)",
        notes=(
            "A required SocialClass Intensity field (default=0.0), so — unlike "
            "its 3 field-stack siblings above — it is a genuine model field and "
            "survives the WorldState round-trip intact; always present on every "
            "social_class node's graph attrs. A legitimate 0.0 (no drift "
            "accumulated) is real, never fabricated — same status as "
            "survival_p_acquiescence/survival_p_revolution (INSPECTOR scope)."
        ),
    ),
    SeamEntry(
        payload="principal_field",
        wire_keys=("principal_field",),
        scope=SeamScope.FIELD_STATE,
        owner_layer="engine (FieldDerivativeSystem._identify_principal_contradiction)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_PRINCIPAL_FIELD_CONDITION,
        dtype="str",
        write_site=(
            "src/babylon/engine/systems/field_derivative.py::"
            "_identify_principal_contradiction (:352, graph.set_graph_attr)"
        ),
        read_paths=_FIELD_STATE_GRAPH_EMITTERS,
        derivation_site="web/game/engine_bridge.py::EngineBridge.get_field_state",
        spec_ref="Program 19/20 · Wave 3 Round 1 (Backend-W3R1 + field-derivative facade carry)",
        notes=(
            "The engine graph attr is a dict ({field_name, max_abs_df_dt, "
            "changed}), NOT a bare string — the field-stack's "
            "fastest-developing FIELD (max |df/dt|), deliberately distinct "
            "from ContradictionSystem @18's Maoist principal OPPOSITION (E0 "
            "rename) so the two never fight. get_field_state extracts just "
            "field_name for the wire; a null field_name (no principal "
            "identified yet) is passed through as null, same as an absent "
            "graph attr. The field_stack carry fixes the round-trip "
            "evaporation of the graph attr itself, but field_name inherits "
            "field_derivatives.df_dt's history dependency (max |df/dt| is "
            "undefined with < 2 ticks), so this row stays DECLARED_CONDITIONAL."
        ),
    ),
    SeamEntry(
        payload="dialectical_regime",
        wire_keys=("dialectical_regime",),
        scope=SeamScope.FIELD_STATE,
        owner_layer=(
            "engine (ContradictionSystem._classify_regime @18, "
            "babylon.engine.systems.contradiction)"
        ),
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_DIALECTICAL_REGIME_CONDITION,
        dtype="json",
        write_site=(
            "src/babylon/engine/systems/contradiction.py::"
            "ContradictionSystem._classify_regime (:359, graph.set_graph_attr)"
        ),
        read_paths=_FIELD_STATE_GRAPH_EMITTERS,
        spec_ref="Program 19/20 · Wave 3 Round 1 (Backend-W3R1 + field-derivative facade carry)",
        notes=(
            "Passed through verbatim ({regime, opposition, rate}). SAME graph "
            "attr as get_contradiction_snapshot/get_journal_objectives read "
            "(DIALECTICAL_REGIME_ATTR) — those callers default a missing/falsy "
            "value to the string 'reproduction' and are not yet registered "
            "under their own scope by this round; field_state is the honest "
            "sibling that passes null through instead of defaulting, per this "
            "endpoint's brief. The distinct FIELD_STATE scope keeps this row's "
            "key from colliding with a future registration of that other read "
            "of the same graph attr. The field_stack carry fixes the "
            "round-trip evaporation, but _classify_regime only writes the "
            "attr once a capital_labor/principal OppositionState exists, so "
            "this row stays DECLARED_CONDITIONAL, not MUST_BE_LIVE."
        ),
    ),
    SeamEntry(
        payload="field_gradients",
        wire_keys=("gradient",),
        scope=SeamScope.FIELD_STATE,
        owner_layer=("engine (FieldDerivativeSystem @20, babylon.engine.systems.field_derivative)"),
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="json",
        write_site=(
            "src/babylon/engine/systems/field_derivative.py::"
            "_compute_edge_gradients (:148, graph.update_edge)"
        ),
        read_paths=_FIELD_STATE_EDGE_EMITTERS,
        derivation_site="web/game/engine_bridge.py::_build_field_state_edges",
        spec_ref="Program 19/20 · Wave 3 Round 1 (Backend-W3R1 + field-derivative facade carry)",
        notes=(
            "gradient = f(target) - f(source) per field, on every edge whose "
            "two endpoints both carry contradiction_fields (in production, "
            "exclusively social_class<->social_class edges — any edge touching "
            "a non-social_class node has an empty contradiction_fields on that "
            "end and is skipped by the engine). One 'edges' list entry per "
            "(source, target, field); territory-anchored via the bridge's "
            "existing _tenancy_members_by_territory "
            "(source_territory/target_territory keep-key-use-null when "
            "unresolvable, matching _serialize_territory's "
            "dominant_class/solidarity_index convention). MUST_BE_LIVE: "
            "contradiction_fields is unconditionally computed for every "
            "active social_class node, so every EXPLOITATION/WAGES/TENANCY "
            "edge between two social_class nodes gets a gradient every tick, "
            "and now survives the WorldState round trip via the field_stack "
            "carry + WorldState._restamp_field_stack re-stamping "
            "field_gradients back onto the edge."
        ),
    ),
)

# ---------------------------------------------------------------------------
# MAP-history replay scope — ``GET /api/games/{id}/map/history/`` (Program 17
# Wave 3, Backend-W3R3). Registered under TERRITORY scope, not a fresh
# SeamScope member (adding one touches types.py, outside this row's file
# budget) — these are, like the rest of TERRITORY, per-territory/per-county
# quantities the bridge reads back, distinct from the live MAP-scope
# ``/map/`` feature emission above.
#
# Verified against a running canonical session (2026-07-15, tick 987 — a
# live ``territory_snapshot`` SELECT and a live
# ``view_runtime_trace_emission`` SELECT, not assumed): only 4 of the 13
# ``MAP_METRIC_PROPERTIES`` have a genuine append-only per-tick historical
# source — ``heat``/``population`` off ``territory_snapshot`` (dense,
# written every resolve by ``_persist_snapshots_safe``), and
# ``profit_rate``/``exploitation_rate`` off ``view_runtime_trace_emission``
# (the spec-089 hex-delta fill-forward view). The other 9 exist ONLY in
# ``hex_latest``, a current-tick-only cache (PK game_id+h3_index,
# overwritten every tick by ``_persist_hex_state_safe``) with no historical
# table at all — GET /map/history/ 422s for them (Constitution III.11:
# never a frame of fabricated/permanent nulls).
#
# A separate, real finding this section flags but does NOT fix: even
# ``occ``/``imperial_rent`` — declared ``territory_snapshot`` COLUMNS —
# persist as NULL on every row today, because ``_persist_snapshots_safe``
# (engine_bridge.py :6044-ish, ``_persist_snapshots_safe``) calls
# ``_serialize_territory(t)`` WITHOUT the ``graph=`` kwarg its
# ``tick_occ``/``tick_phi_hour`` reads need — confirmed via a live
# ``territory_snapshot`` SELECT (every row's profit_rate/exploitation_rate/
# occ/imperial_rent is blank). The live MAP-scope rows above are
# unaffected: they read the graph-carrying
# ``_serialize_territory(t, graph=new_graph)`` call
# (``_state_to_snapshot`` -> ``_persist_hex_state_safe``) instead.
#
# ``throughput_position`` is deliberately NOT re-registered here: it
# already has a TERRITORY-scope row above (Wave 2 owner ruling 1) and this
# registry's ``key`` (``scope.wire_key``) would collide. It is equally
# STRUCTURALLY_IMPOSSIBLE for map-history replay (same hex_latest-only
# status as the 9 metrics below) — GET /map/history/ 422s for it too.
# ---------------------------------------------------------------------------

_MAP_HISTORY_EMITTERS: tuple[str, ...] = (
    "web/game/engine_bridge.py::EngineBridge.get_map_history",
)

_MAP_HISTORY_NOT_PERSISTED: str = (
    "STRUCTURALLY_IMPOSSIBLE for map-history replay: computed only at live serialize time "
    "into hex_latest (PK game_id+h3_index — a current-tick cache _persist_hex_state_safe "
    "overwrites every tick), never landing in any append-only per-tick table. "
    "GET /map/history/ 422s rather than serving a frame of fabricated nulls "
    "(Constitution III.11)."
)

_MAP_HISTORY_METRICS: tuple[SeamEntry, ...] = (
    SeamEntry(
        payload="territory_snapshot.heat",
        wire_keys=("heat",),
        scope=SeamScope.TERRITORY,
        owner_layer="web-bridge (territory_snapshot, _territory_snapshot_rows)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
        read_paths=_MAP_HISTORY_EMITTERS,
        spec_ref="Program 17 Wave 3 · Backend-W3R3",
        notes=(
            "Real per-(tick, county_fips) heat, direct Territory.heat field (no graph needed). "
            "Grain caveat (pre-existing, documented on get_territory_history): territory_snapshot's "
            "composite PK is (game_id, tick, county_fips) with ON CONFLICT ... DO NOTHING, so a "
            "hex-resolution scenario's many same-county territories collapse onto whichever one "
            "wrote first each tick — not a true county aggregate, unlike profit_rate/"
            "exploitation_rate below."
        ),
    ),
    SeamEntry(
        payload="territory_snapshot.pop_total",
        wire_keys=("population",),
        scope=SeamScope.TERRITORY,
        owner_layer="web-bridge (territory_snapshot, _territory_snapshot_rows)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="int",
        read_paths=_MAP_HISTORY_EMITTERS,
        spec_ref="Program 17 Wave 3 · Backend-W3R3",
        notes=(
            "Real per-(tick, county_fips) population (direct Territory.population field). Same "
            "one-hex-per-county grain caveat as heat above."
        ),
    ),
    SeamEntry(
        payload="view_runtime_trace_emission.profit_rate",
        wire_keys=("profit_rate",),
        scope=SeamScope.TERRITORY,
        owner_layer="persistence view (spec-089 hex-delta fill-forward, 0030_views_current.sql)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "requires the session's hex economics to be wired (dynamic_hex_state rows for the "
            "county) — absent for abstract scenarios (two_node, imperial_circuit) with no h3 "
            "territories; confirmed real non-null on a running canonical session (SUM(s)/"
            "(SUM(c)+SUM(v)) per county, 987 ticks observed)"
        ),
        dtype="float",
        read_paths=_MAP_HISTORY_EMITTERS,
        spec_ref="Program 17 Wave 3 · Backend-W3R3",
        notes=(
            "A genuine county-wide SUM aggregate over every hex (unlike territory_snapshot's "
            "one-hex-per-county grain above) — distinct source from MAP-scope profit_rate "
            "(tick_profit_rate, year-boundary-only, and NULL in territory_snapshot today per "
            "the section header's flagged wiring gap)."
        ),
    ),
    SeamEntry(
        payload="view_runtime_trace_emission.exploitation_rate",
        wire_keys=("exploitation_rate",),
        scope=SeamScope.TERRITORY,
        owner_layer="persistence view (spec-089 hex-delta fill-forward, 0030_views_current.sql)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "same condition as view_runtime_trace_emission.profit_rate above "
            "(SUM(s)/SUM(v) per county)"
        ),
        dtype="float",
        read_paths=_MAP_HISTORY_EMITTERS,
        spec_ref="Program 17 Wave 3 · Backend-W3R3",
        notes="Genuine county-wide SUM aggregate, sibling of profit_rate above.",
    ),
    SeamEntry(
        payload="hex_latest.occ",
        wire_keys=("occ",),
        scope=SeamScope.TERRITORY,
        owner_layer="web-bridge (hex_latest current-tick cache only)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="float",
        read_paths=_MAP_HISTORY_EMITTERS,
        spec_ref="Program 17 Wave 3 · Backend-W3R3",
        notes=(
            _MAP_HISTORY_NOT_PERSISTED + " Also NULL in territory_snapshot's own `occ` column "
            "today (section header wiring gap)."
        ),
    ),
    SeamEntry(
        payload="hex_latest.imperial_rent",
        wire_keys=("imperial_rent",),
        scope=SeamScope.TERRITORY,
        owner_layer="web-bridge (hex_latest current-tick cache only)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="float",
        read_paths=_MAP_HISTORY_EMITTERS,
        spec_ref="Program 17 Wave 3 · Backend-W3R3",
        notes=(
            _MAP_HISTORY_NOT_PERSISTED + " Also NULL in territory_snapshot's own "
            "`imperial_rent` column today (same wiring gap)."
        ),
    ),
    SeamEntry(
        payload="hex_latest.org_count",
        wire_keys=("org_presence",),
        scope=SeamScope.TERRITORY,
        owner_layer="web-bridge (hex_latest current-tick cache only)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="int",
        read_paths=_MAP_HISTORY_EMITTERS,
        spec_ref="Program 17 Wave 3 · Backend-W3R3",
        notes=_MAP_HISTORY_NOT_PERSISTED,
    ),
    SeamEntry(
        payload="hex_latest.attributes.habitability",
        wire_keys=("habitability",),
        scope=SeamScope.TERRITORY,
        owner_layer="web-bridge (hex_latest current-tick cache only)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="float",
        read_paths=_MAP_HISTORY_EMITTERS,
        spec_ref="Program 17 Wave 3 · Backend-W3R3",
        notes=_MAP_HISTORY_NOT_PERSISTED,
    ),
    SeamEntry(
        payload="hex_latest.dominant_class",
        wire_keys=("dominant_class",),
        scope=SeamScope.TERRITORY,
        owner_layer="web-bridge (hex_latest current-tick cache only)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="enum:SocialRole",
        read_paths=_MAP_HISTORY_EMITTERS,
        spec_ref="Program 17 Wave 3 · Backend-W3R3",
        notes=_MAP_HISTORY_NOT_PERSISTED,
    ),
    SeamEntry(
        payload="hex_latest.attributes.solidarity_index",
        wire_keys=("solidarity_index",),
        scope=SeamScope.TERRITORY,
        owner_layer="web-bridge (hex_latest current-tick cache only)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="float",
        read_paths=_MAP_HISTORY_EMITTERS,
        spec_ref="Program 17 Wave 3 · Backend-W3R3",
        notes=_MAP_HISTORY_NOT_PERSISTED,
    ),
    SeamEntry(
        payload="hex_latest.attributes.agitation",
        wire_keys=("agitation",),
        scope=SeamScope.TERRITORY,
        owner_layer="web-bridge (hex_latest current-tick cache only)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="float",
        read_paths=_MAP_HISTORY_EMITTERS,
        spec_ref="Program 17 Wave 3 · Backend-W3R3",
        notes=(
            _MAP_HISTORY_NOT_PERSISTED + " Distinct from INSPECTOR-scope agitation (per-class "
            "raw ideology.agitation) — this is the MAP-scope territory-level "
            "population-weighted mean (_agitation_index_by_territory)."
        ),
    ),
    SeamEntry(
        payload="hex_latest.attributes.territory_type",
        wire_keys=("territory_type",),
        scope=SeamScope.TERRITORY,
        owner_layer="web-bridge (hex_latest current-tick cache only)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="enum:TerritoryType",
        read_paths=_MAP_HISTORY_EMITTERS,
        spec_ref="Program 17 Wave 3 · Backend-W3R3",
        notes=_MAP_HISTORY_NOT_PERSISTED,
    ),
)

# --- NETWORK scope (audit Wave 4; scope enum added post-AW4-R1, task #76) ---
# AW4-R1 deliberately left these unregistered rather than misclassify them
# under INSPECTOR/TERRITORY (its file scope excluded types.py). The
# ``SeamScope.NETWORK`` member now exists; these rows retire that documented
# gap. Sensor 1's gating checks do not scan this surface — rows are the
# declarative contract, same as FIELD_STATE's.

_ORG_NETWORK_EMITTERS: tuple[str, ...] = (
    "web/game/engine_bridge.py::EngineBridge.get_org_network",
    "web/game/engine_bridge.py::_build_org_network",
)

_NETWORK_METRICS: tuple[SeamEntry, ...] = (
    SeamEntry(
        payload="org_network_graph",
        wire_keys=("nodes", "edges"),
        scope=SeamScope.NETWORK,
        owner_layer="bridge (derived read of the hydrated session graph)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        dtype="json",
        write_site=(
            "engine scenario builders seed org/institution/territory nodes and "
            "their edges; the bridge only reads (no write of its own)"
        ),
        read_paths=_ORG_NETWORK_EMITTERS,
        derivation_site="web/game/engine_bridge.py::_build_org_network",
        spec_ref="audit Wave 4 R1 (Topology & the Gramscian Wire) · commit c312e62d",
        notes=(
            "OrgNetworkPayload nodes/edges, deterministically sorted. "
            "DECLARED_CONDITIONAL: live whenever the scenario seeds at least "
            "one organization (wayne_county seeds ORG001+ORG002 since AW3.3); "
            "an org-less synthetic scenario honestly serves empty lists. "
            "Contract facts verified AW4-R1: OrgNetworkNode.type has NO "
            "social_class member; MEMBERSHIP edges have zero production "
            "writers; CLIENT_STATE is a class-to-class subsidy edge."
        ),
    ),
    SeamEntry(
        payload="centrality",
        wire_keys=("centrality",),
        scope=SeamScope.NETWORK,
        owner_layer="bridge (pure topology analytics at bridge altitude)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        dtype="json",
        write_site=(
            "none — computed per request from the hydrated graph "
            "(babylon.topology.graph_algorithms degree/betweenness/closeness, "
            "the sparrow.analyze_network guard idiom)"
        ),
        read_paths=_ORG_NETWORK_EMITTERS,
        derivation_site="web/game/engine_bridge.py::_org_network_centrality",
        spec_ref="audit Wave 4 R1 · commit c312e62d",
        notes=(
            "Per-node {degree, betweenness?, closeness?}; observability read, "
            "never adjudication (Constitution: AI/presentation observes). "
            "Empty dict when the network has no nodes — honest, not fabricated."
        ),
    ),
    SeamEntry(
        payload="percolation_ratio",
        wire_keys=("percolation_ratio",),
        scope=SeamScope.NETWORK,
        owner_layer="bridge (pure topology analytics at bridge altitude)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        dtype="float",
        write_site=(
            "none — computed per request via "
            "babylon.engine.topology_monitor.extract_solidarity_subgraph + "
            "calculate_component_metrics"
        ),
        read_paths=_ORG_NETWORK_EMITTERS,
        derivation_site="web/game/engine_bridge.py::_solidarity_percolation_ratio",
        spec_ref="audit Wave 4 R1 · commit c312e62d",
        notes=(
            "Solidarity-subgraph percolation ratio; honest null when no "
            "SOLIDARITY edges exist (never a fabricated 0.0). Rendered by the "
            "Network takeover's HUD chip as an em-dash on null (AW4-R2)."
        ),
    ),
    SeamEntry(
        payload="community_memberships",
        wire_keys=("hyperedges",),
        scope=SeamScope.NETWORK,
        owner_layer="engine (CommunitySystem @6 — XGI hypergraph rebuild per tick)",
        liveness_class=LivenessClass.STRUCTURALLY_IMPOSSIBLE,
        dtype="json",
        write_site=(
            "src/babylon/engine/systems/community.py::CommunitySystem.step "
            "(no-ops every tick: no scenario builder assigns "
            "SocialClass.community_memberships anywhere in production)"
        ),
        read_paths=("web/game/engine_bridge.py::EngineBridge.get_hypergraph_communities",),
        derivation_site="web/game/engine_bridge.py::EngineBridge.get_hypergraph_communities",
        spec_ref="audit Wave 4 R1 · commit c312e62d (dead-route 500 fixed honestly)",
        notes=(
            "Permanently-empty hyperedges list until a data program seeds "
            "community_memberships (the hull/organization-gauge prerequisite "
            "deferred in reports/wave3-weather-implementation-map.md). "
            "STRUCTURALLY_IMPOSSIBLE by the hex_latest precedent: no runtime "
            "condition can light it — only a code/data change."
        ),
    ),
)

#: The declared observable-field contract. Populated per build phase.
SEAM_REGISTRY: tuple[SeamEntry, ...] = (
    _MAP_METRICS
    + _TERRITORY_TICK_METRICS
    + _INSPECTOR_METRICS
    + _FIELD_STATE_METRICS
    + _MAP_HISTORY_METRICS
    + _NETWORK_METRICS
)
