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

from babylon.models.enums.events import EventType
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
    # --- Program 23 Phase 2 (ADR078): the per-county scissors' map reading.
    # NATIVE per-territory graph attr like wage_pressure, presence-
    # conditional AND null-able: the projector writes the county's price_log
    # when a county axis exists, an explicit None on de-positioning (the
    # sigma-channel rule), and nothing at all for a territory whose county
    # never carried a paid-worker value substrate.
    # ---------------------------------------------------------------------------
    SeamEntry(
        payload="price_divergence",
        wire_keys=("price_divergence",),
        scope=SeamScope.MAP,
        owner_layer="engine (MarketScissorsSystem, babylon.engine.systems.market_scissors)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "non-null only for an active territory whose county_fips carries a market_county "
            "axis this tick (market_scissors.py::_project_price_divergence) — the projector "
            "writes the county price_log, an honest None on de-positioning, and no attr at all "
            "for a county with no paid-worker (w_paid, v_produced) substrate, never a "
            "fabricated 0.0"
        ),
        dtype="float",
        write_site=(
            "src/babylon/engine/systems/market_scissors.py::"
            "MarketScissorsSystem._project_price_divergence (graph.update_node)"
        ),
        read_paths=_MAP_EMITTERS,
        spec_ref="Program 23 Phase 2 · ADR078 · spec-115",
        notes=(
            "SIGNED log price-to-value ratio of the territory's county (range ±max_abs_log, "
            "0 = prices at values) — the map lens uses a diverging ramp with a special "
            "normalization branch in mapLensLayers.ts (raw range is [-2, 2], not [0, 1]). "
            "Rides hex_latest's JSONB attributes column; population-weighted MEAN at county "
            "zoom, partial-coverage-aware."
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
# * Group C (7, DECLARED_CONDITIONAL) — the circulation layer, now genuinely
#   live: Task 20b (spec-116) wires a real ``turnover_profile_source`` service
#   (gate: ``domain/economics/tick/system/__init__.py:1167``) into
#   ``_bridge_economics_overrides``. Before this, registered
#   ``NOT_YET_COMPUTED`` by the Task 20 de-mock correction (and, before THAT,
#   a false ``STRUCTURALLY_IMPOSSIBLE`` ruling) while the FRED-backed sibling
#   implementation (``DefaultTurnoverProfileSource``,
#   ``domain/economics/factory.py``) existed but sat unwired.
# * Group D (9 total; 8 DECLARED_CONDITIONAL + 1 still NOT_YET_COMPUTED) — the
#   financial-distribution layer. Task 20b also wires a real
#   ``interest_calculator`` service (gate: same file, :1365), lighting 8 of
#   the 9 attrs the same way. ``tick_ground_rent`` is the lone holdout: it
#   stays ``NOT_YET_COMPUTED`` on a SECOND, independent gate —
#   ``_DefaultCountyRentalAdapter`` (``domain/economics/factory.py``)
#   unconditionally returns ``None`` for agricultural/resource/urban rent, an
#   honest data-absence (no county rental series in the reference DB), not a
#   mock to launder (Constitution III.11).
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

#: Groups C/D ride the same two emitters regardless of liveness: the write
#: site stamps a value (real or fallback) at every year boundary, and
#: ``_serialize_territory`` reads it through unmodified. Task 20b (spec-116)
#: wires the gating services for 15 of the 16 rows below (``_CIRCULATION_LIVE``/
#: ``_FINANCIAL_LIVE``), leaving only ``tick_ground_rent`` genuinely dark on a
#: second, independent gate.
_TICK_WRITE_SITE: tuple[str, ...] = (
    "src/babylon/domain/economics/tick/graph_bridge.py::write_tick_state_to_graph "
    "(year-boundary graph.update_node call, :102-195)",
)

_TICK_DARK_EMITTERS: tuple[str, ...] = _TICK_WRITE_SITE + _TERRITORY_EMITTERS

_CIRCULATION_LIVE: str = (
    "Genuinely live (Task 20b, spec-116): _bridge_economics_overrides wires a real "
    "turnover_profile_source (domain.economics.factory.create_circulation_services) over "
    "the same reference-DB session_factory melt/gamma/leontief/throughput above already "
    "use, so the `services.turnover_profile_source is None` gate "
    "(domain/economics/tick/system/__init__.py:1167) no longer holds. Distinct from this "
    "attr's prior NOT_YET_COMPUTED state (Task 20 de-mock correction) — that gap was pure "
    "engineering (the calculator was never constructed), now fixed."
)

_FINANCIAL_LIVE: str = (
    "Genuinely live (Task 20b, spec-116): _bridge_economics_overrides wires a real "
    "interest_calculator (domain.economics.factory.create_financial_services) over the "
    "same reference-DB session_factory melt/gamma/leontief/throughput above already use, "
    "so the `services.interest_calculator is None` gate "
    "(domain/economics/tick/system/__init__.py:1365) no longer holds. Distinct from this "
    "attr's prior NOT_YET_COMPUTED state (Task 20 de-mock correction) — that gap was pure "
    "engineering (the calculator was never constructed), now fixed."
)

_CIRCULATION_LIVENESS_CONDITION: str = (
    f"{_YEAR_BOUNDARY}; also requires _bridge_economics_overrides to have wired a "
    "turnover_profile_source (Task 20b) AND the county to carry capital_stock > 0 "
    "(domain/economics/tick/system/__init__.py:1260, inside "
    "_compute_county_circulation_state)"
)

_FINANCIAL_LIVENESS_CONDITION: str = (
    f"{_YEAR_BOUNDARY}; also requires _bridge_economics_overrides to have wired an "
    "interest_calculator (Task 20b) AND the county's tensor-derived total_surplus > 0 "
    "(domain/economics/tick/system/__init__.py:1448, inside "
    "_compute_county_financial_state via distribution_calculator)"
)

#: Task 21b (spec-116): _bridge_economics_overrides now wires a real
#: reserve_army_data_source (domain.economics.factory.create_vol1_services)
#: over the same reference-DB session_factory the rows above already use, so
#: the `services.reserve_army_data_source is None` gate
#: (domain/economics/tick/system/__init__.py:1100) no longer short-circuits
#: `_compute_vol1_layer` unconditionally. Unlike Groups C/D, tick_median_wage
#: was never NULL either side of this wiring (the QCEW wage_source bootstrap,
#: Item 60, always seeds a real value) — what changes is whether that
#: bootstrap is the WHOLE story or genuinely endogenous afterward, so this is
#: a liveness_condition/notes correction on an already-DECLARED_CONDITIONAL
#: row, not a liveness_class promotion.
_WAGE_PRESSURE_LIVENESS_CONDITION: str = (
    f"{_YEAR_BOUNDARY}; the bootstrap (QCEW p50, owner item 60) is live regardless — this "
    "condition covers only whether the value is ALSO genuinely endogenous after tick 1: "
    "requires _bridge_economics_overrides to have wired a reserve_army_data_source (Task 21b) "
    "AND get_unemployment_decomposition(fips, year) to return non-None (UNRATE present for "
    "the year in fact_fred_national, domain/economics/tick/system/__init__.py:1139) — a "
    "territory outside that coverage carries the bootstrap-only value forward unadjusted, "
    "never a fabricated compression (Constitution III.11)."
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
        payload="tick_renter_share",
        wire_keys=("renter_share",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (SQLiteCensusHousingSource, ACS housing tenure)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="float",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · item 165 · Wave 6 C2",
        notes=(
            "Real ACS housing tenure via services.housing_source (wired in "
            "_bridge_economics_overrides); honest 0.0 default when unwired or "
            "the county-year row is absent — never a fabricated share."
        ),
    ),
    SeamEntry(
        payload="tick_bracket_ratio",
        wire_keys=("bracket_ratio",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (SQLiteCensusIncomeSource, ACS B19001)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="float",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · item 167 · Wave 6 C3",
        notes=(
            "Wave 6 C3: per-county top/bottom ACS B19001 income-bracket "
            "household ratio via services.income_source (wired in "
            "_bridge_economics_overrides); falls back to the 0.0 prev-carry "
            "not-computed default only when the county/year row or the "
            "race='Total' aggregate is absent (honest None)."
        ),
    ),
    SeamEntry(
        payload="tick_median_wage",
        wire_keys=("tick_median_wage",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (QCEW p50 bootstrap + wage-pressure dynamics)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_WAGE_PRESSURE_LIVENESS_CONDITION,
        dtype="float",
        read_paths=_TERRITORY_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · owner item 60 · spec-116 Task 21b",
        notes=(
            "Item 60 (2026-07-15): the bootstrap is now the employment-weighted "
            "p50 estimator over QCEW 6-digit industry wages via "
            "services.wage_source (a genuine median approximation — the raw "
            "QCEW county mean was NOT wired precisely because it is a mean). "
            "ENDOGENOUS after tick 1 (Task 21b, spec-116): wage-pressure/"
            "compression dynamics now genuinely own the trajectory for a "
            "county with UNRATE coverage for the year — "
            "_bridge_economics_overrides wires a real reserve_army_data_source "
            "(domain.economics.factory.create_vol1_services), opening the "
            "`services.reserve_army_data_source is None` gate "
            "(domain/economics/tick/system/__init__.py:1100). Before Task "
            "21b this ENDOGENOUS claim was aspirational only: no runner ever "
            "constructed that service, so the wage-pressure sigmoid never "
            "fired in a web session and the QCEW bootstrap was the whole "
            "story every tick. 21.0 $/hr remains the documented unwired/"
            "absent-row bootstrap — never a fabricated compression when "
            "UNRATE is absent for the year (Constitution III.11). Wire key "
            "deliberately kept tick_-prefixed (not 'median_wage') to avoid "
            "colliding with the real, distinct Territory.median_wage field "
            "(Feature 021) already on the same _serialize_territory payload."
        ),
    ),
    SeamEntry(
        payload="tick_real_wage_deflator",
        wire_keys=("real_wage_deflator", "tick_real_median_wage"),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.melt (SQLiteCPISource, FRED CPIAUCSL)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_YEAR_BOUNDARY,
        dtype="float",
        read_paths=_TERRITORY_EMITTERS,
        derivation_site="web/game/engine_bridge.py::_compute_real_median_wage",
        spec_ref="Epochs audit · Wave 6 C4 (wages never naked)",
        notes=(
            "Wave 6 C4 (2026-07-16): real-wage CPI deflation — every wage "
            "figure this payload exposed before was nominal-only. "
            "services.cpi_source.get_cpi_deflator(year) = CPI(2015)/CPI(year) "
            "over the FRED CPIAUCSL series; 2015 matches this codebase's de "
            "facto reference year (tick/types.py + initializer.py "
            "examples/seed data), distinct from melt.data_sources."
            "CPIDataSource's still-unwired 2024 V_reproduction base — a "
            "different consumer of the same national series. "
            "tick_real_wage_deflator (wire_keys[0], a genuine engine write "
            "via graph_bridge.write_tick_state_to_graph) is FROZEN at 1.0 "
            "(nominal == real) when cpi_source is unwired or the year's CPI "
            "row is absent — never a fabricated ratio. tick_real_median_wage "
            "(wire_keys[1]) is the bridge-derived composite "
            "tick_median_wage x deflator, honest-None unless BOTH inputs "
            "are present (Constitution III.11)."
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
    # --- Group C: circulation layer, gated on turnover_profile_source (:1167)
    # — LIT by Task 20b (spec-116): _bridge_economics_overrides now wires a
    # real turnover_profile_source, so all 7 rows move from NOT_YET_COMPUTED
    # to DECLARED_CONDITIONAL. ---
    SeamEntry(
        payload="tick_liquidity_ratio",
        wire_keys=("tick_liquidity_ratio",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CirculationState.circuit_state)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_CIRCULATION_LIVENESS_CONDITION,
        dtype="float",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=_CIRCULATION_LIVE,
    ),
    SeamEntry(
        payload="tick_commodity_overhang",
        wire_keys=("tick_commodity_overhang",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CirculationState.circuit_state)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_CIRCULATION_LIVENESS_CONDITION,
        dtype="float",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=_CIRCULATION_LIVE,
    ),
    SeamEntry(
        payload="tick_replacement_cycle",
        wire_keys=("tick_replacement_cycle",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (DepreciationFundState.replacement_cycle_position)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_CIRCULATION_LIVENESS_CONDITION,
        dtype="enum:ReplacementCyclePosition",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=_CIRCULATION_LIVE,
    ),
    SeamEntry(
        payload="tick_inventory_diagnosis",
        wire_keys=("tick_inventory_diagnosis",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (InventoryState.inventory_problem)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_CIRCULATION_LIVENESS_CONDITION,
        dtype="enum:InventoryDiagnosis",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=_CIRCULATION_LIVE,
    ),
    SeamEntry(
        payload="tick_realization_crisis",
        wire_keys=("tick_realization_crisis",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CirculationAssessment)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_CIRCULATION_LIVENESS_CONDITION,
        dtype="bool",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=_CIRCULATION_LIVE,
    ),
    SeamEntry(
        payload="tick_turnover_crisis",
        wire_keys=("tick_turnover_crisis",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CirculationAssessment)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_CIRCULATION_LIVENESS_CONDITION,
        dtype="bool",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=_CIRCULATION_LIVE,
    ),
    SeamEntry(
        payload="tick_reproduction_crisis",
        wire_keys=("tick_reproduction_crisis",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (CirculationAssessment)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_CIRCULATION_LIVENESS_CONDITION,
        dtype="bool",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=_CIRCULATION_LIVE,
    ),
    # --- Group D: financial distribution, gated on interest_calculator (:1365)
    # — LIT by Task 20b (spec-116): _bridge_economics_overrides now wires a
    # real interest_calculator, so 8 of 9 rows move from NOT_YET_COMPUTED to
    # DECLARED_CONDITIONAL. tick_ground_rent is the exception: it STAYS
    # NOT_YET_COMPUTED — a second, independent gate (_DefaultCountyRentalAdapter
    # unconditionally returning None) still keeps it dark. ---
    SeamEntry(
        payload="tick_interest_burden",
        wire_keys=("tick_interest_burden",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (SurplusDistribution.interest_payments)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_FINANCIAL_LIVENESS_CONDITION,
        dtype="float",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=_FINANCIAL_LIVE,
    ),
    SeamEntry(
        payload="tick_ground_rent",
        wire_keys=("tick_ground_rent",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (SurplusValueDistribution.ground_rent)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_FINANCIAL_LIVENESS_CONDITION,
        dtype="float",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="vol3-money-scissors U1 (2026-07-18); supersedes spec-116 Task 20b",
        notes=(
            "U1 repoint: was permanently NOT_YET_COMPUTED because "
            "write_tick_state_to_graph read RentExtraction.total_rent (Path "
            "B, _DefaultCountyRentalAdapter unconditionally returns None — "
            "no county rental series in the reference DB). Repointed to "
            "SurplusValueDistribution.ground_rent (Path A, real FRED "
            "B230RC0Q173SBEA rental income via DefaultDistributionCalculator), "
            "which was always live wherever distribution_calculator + "
            "tensor_registry are wired — same condition as tick_interest_burden. "
            "The 3-way agricultural/resource/urban rent split (Path B) has no "
            "data source and stays honestly absent as its own field "
            "(rent_extraction), just no longer the source of this graph attr."
        ),
    ),
    SeamEntry(
        payload="tick_rentier_share",
        wire_keys=("tick_rentier_share",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (SurplusDistribution.rentier_share)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_FINANCIAL_LIVENESS_CONDITION,
        dtype="float",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=_FINANCIAL_LIVE,
    ),
    SeamEntry(
        payload="tick_profit_of_enterprise",
        wire_keys=("tick_profit_of_enterprise",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (SurplusDistribution.profit_of_enterprise)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_FINANCIAL_LIVENESS_CONDITION,
        dtype="float",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=(
            f"{_FINANCIAL_LIVE} Can be negative (a debt-spiral signal) — never clamp "
            "to 0 now that this is genuinely lit."
        ),
    ),
    SeamEntry(
        payload="tick_financialization_share",
        wire_keys=("tick_financialization_share",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (SurplusDistribution.financialization_share)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_FINANCIAL_LIVENESS_CONDITION,
        dtype="float",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=_FINANCIAL_LIVE,
    ),
    SeamEntry(
        payload="tick_accumulated_debt",
        wire_keys=("tick_accumulated_debt",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (DebtAccumulation.accumulated_debt)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_FINANCIAL_LIVENESS_CONDITION,
        dtype="float",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=_FINANCIAL_LIVE,
    ),
    SeamEntry(
        payload="tick_claims_exceed_surplus",
        wire_keys=("tick_claims_exceed_surplus",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (SurplusDistribution.claims_exceed_surplus)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_FINANCIAL_LIVENESS_CONDITION,
        dtype="bool",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=_FINANCIAL_LIVE,
    ),
    SeamEntry(
        payload="tick_housing_fictitious_fraction",
        wire_keys=("tick_housing_fictitious_fraction",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (HousingValueDecomposition.fictitious_fraction)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_FINANCIAL_LIVENESS_CONDITION,
        dtype="float",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=(
            f"{_FINANCIAL_LIVE} The only Group D attr with an honest None write-side "
            "fallback (graph_bridge.py already writes None, not 0.0, when "
            "housing_decomposition is absent)."
        ),
    ),
    SeamEntry(
        payload="tick_financial_crisis_signals",
        wire_keys=("tick_financial_crisis_signals",),
        scope=SeamScope.TERRITORY,
        owner_layer="domain.economics.tick (FinancialCrisisSignals.active_signals)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_FINANCIAL_LIVENESS_CONDITION,
        dtype="int",
        read_paths=_TICK_DARK_EMITTERS,
        spec_ref="Epochs audit · Wave 2 · Gap-1 · spec-116 Task 20b",
        notes=f"{_FINANCIAL_LIVE} Count of active signals, int in [0, 4].",
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

# --- DOCTRINE scope (ADR073 Units 4-7; scope enum added 2026-07-16) ---
# The 2026-07-16 copacetic audit found the inverse of an orphan declaration:
# get_doctrine_tree -> endpoints.ts doctrineTree -> DoctrineTakeover.tsx is a
# real, wired, player-observable surface the Observatory never declared.
# These rows retire that gap. Sensor 1's gating checks do not scan this
# surface — rows are the declarative contract, same as NETWORK's.

_DOCTRINE_EMITTERS: tuple[str, ...] = ("web/game/engine_bridge.py::EngineBridge.get_doctrine_tree",)

_DOCTRINE_METRICS: tuple[SeamEntry, ...] = (
    SeamEntry(
        payload="acquired_doctrine_ids",
        wire_keys=("acquired_ids",),
        scope=SeamScope.DOCTRINE,
        owner_layer="engine (DoctrineSystem @14.7 — Party Congress acquisitions)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        dtype="json",
        write_site=(
            "src/babylon/engine/systems/doctrine.py::DoctrineSystem.step "
            "(Unit 5 Party Congress: seeded-RNG acquisition weighted by tag "
            "deltas; a real Organization model field, so it survives the "
            "WorldState round trip — D2 snapshot->hydrate proof)"
        ),
        read_paths=_DOCTRINE_EMITTERS,
        derivation_site="web/game/engine_bridge.py::EngineBridge.get_doctrine_tree",
        spec_ref="ADR073 Doctrine Tree · Units 4-6 (PR #190)",
        notes=(
            "The player faction's acquired doctrine-node ids. "
            "DECLARED_CONDITIONAL: live only when the scenario seeds a player "
            "faction and a Congress has fired; honest [] before then "
            "(never fabricated partial progress, Constitution III.11)."
        ),
    ),
    SeamEntry(
        payload="doctrine_tags",
        wire_keys=("tags",),
        scope=SeamScope.DOCTRINE,
        owner_layer="engine (DoctrineSystem @14.7 — decaying tag accumulator)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        dtype="json",
        write_site=(
            "src/babylon/engine/systems/doctrine.py::DoctrineSystem.step "
            "(per-tick upkeep decay toward parent + acquisition tag_deltas)"
        ),
        read_paths=_DOCTRINE_EMITTERS,
        derivation_site="web/game/engine_bridge.py::EngineBridge.get_doctrine_tree",
        spec_ref="ADR073 Doctrine Tree · Units 4-6 (PR #190)",
        notes=(
            "The wire itself is never null — with no player faction the "
            "bridge serves starting_tags() (the MVP corpus's declared "
            "starting position, NOT compute_tags over an empty set). The "
            "declared CONDITION governs when the values reflect live per-org "
            "accumulator state instead of that static starting position."
        ),
    ),
    SeamEntry(
        payload="theoretical_labor",
        wire_keys=("theoretical_labor",),
        scope=SeamScope.DOCTRINE,
        owner_layer="engine (DoctrineSystem @14.7 — per-tick TL accrual)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        dtype="float",
        write_site=(
            "src/babylon/engine/systems/doctrine.py::DoctrineSystem.step "
            "(accrue_theoretical_labor per tick from cadre + study allocation)"
        ),
        read_paths=_DOCTRINE_EMITTERS,
        derivation_site="web/game/engine_bridge.py::EngineBridge.get_doctrine_tree",
        spec_ref="ADR073 Doctrine Tree · Units 4-6 (PR #190)",
        notes=(
            "TL accrues 0.0-up once a player faction exists; 0.0 before then "
            "(the honest starting position, never fabricated progress)."
        ),
    ),
    SeamEntry(
        payload="study_target_id",
        wire_keys=("study_target_id",),
        scope=SeamScope.DOCTRINE,
        owner_layer="the Study verb (Unit 7b POST — player-set org state)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        dtype="str",
        write_site=(
            "the Unit 7b study POST sets Organization.study_target_id (the "
            "player's standing Educate(Doctrine) order); DoctrineSystem.step "
            "reads it to direct TL accrual"
        ),
        read_paths=_DOCTRINE_EMITTERS,
        derivation_site="web/game/engine_bridge.py::EngineBridge.get_doctrine_tree",
        spec_ref="ADR073 Doctrine Tree · Unit 7b (PR #190)",
        notes=(
            "Honest null until the player issues a Study order (the canvas "
            "then stays read-only rather than offering an unactionable "
            "affordance). Split from the theoretical_labor row (PR #196 "
            "Copilot review): one payload per wire key so each dtype is "
            "declared honestly (str|null here, float there)."
        ),
    ),
    SeamEntry(
        payload="faction_id",
        wire_keys=("faction_id",),
        scope=SeamScope.DOCTRINE,
        owner_layer="bridge (player-faction resolution at serialization time)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        dtype="str",
        write_site=(
            "none — resolved per request by "
            "EngineBridge._player_doctrine_org (prefers the is_player "
            "faction; falls back to any org that has begun acquiring)"
        ),
        read_paths=_DOCTRINE_EMITTERS,
        derivation_site="web/game/engine_bridge.py::EngineBridge._player_doctrine_org",
        spec_ref="ADR073 Doctrine Tree · Unit 7b (PR #190)",
        notes=(
            "The acting faction the canvas submits Educate(Doctrine) for. "
            "Honest null when no player faction exists (III.11). Declared "
            "post-merge (PR #196 Copilot review): it is emitted by "
            "get_doctrine_tree, so leaving it undeclared would recreate the "
            "exact inverse-orphan gap this scope was added to close."
        ),
    ),
)

# --- ENDGAME scope (spec-116 Playability Spine, Task 4) ---
# The per-tick "how close" HUD signal: EndgameDetector's axis_progress() /
# recognized_pattern / pattern_since_tick, composed with the bridge-derived
# horizon_tick/locked into resolve_tick's snapshot['endgame_progress']. The
# ENDGAME scope enum member predates this row (its docstring already named
# `get_endgame_state`'s `outcome` field) — this is the first ENDGAME-scope
# row actually registered; backfilling the rest of get_endgame_state's wire
# keys is a separate, pre-existing gap (Seam Phase 3's remit), not this
# task's scope.

_ENDGAME_PROGRESS_EMITTERS: tuple[str, ...] = (
    "web/game/engine_bridge.py::EngineBridge.resolve_tick (per-tick snapshot['endgame_progress'])",
    "web/game/engine_bridge.py::EngineBridge.get_journal_objectives (axes read back off graph_attrs)",
)

_ENDGAME_METRICS: tuple[SeamEntry, ...] = (
    SeamEntry(
        payload="endgame_progress",
        wire_keys=("endgame_progress",),
        scope=SeamScope.ENDGAME,
        owner_layer=(
            "babylon.engine.observers.endgame_detector.EndgameDetector "
            "(axis_progress/recognized_pattern/pattern_since_tick) + "
            "bridge-derived horizon_tick/locked"
        ),
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="json",
        derivation_site=(
            "web/game/engine_bridge.py::EngineBridge.resolve_tick (assembled "
            "from the per-session-cached EndgameDetector, then stashed onto "
            "new_graph as a graph-level attribute before persist_tick so it "
            "survives worker restarts — same channel as "
            "ContradictionSystem's contradiction_frames)"
        ),
        read_paths=_ENDGAME_PROGRESS_EMITTERS,
        nullable=False,
        spec_ref="spec-116 Playability Spine · Task 4 (FR-116-1)",
        notes=(
            "Every tick's {axes: {5 GameOutcome keys -> [0,1] progress}, "
            "pattern, since_tick, horizon_tick, locked} block. Owner ruling "
            "2026-07-17: patterns are recognized, never adjudicated — this "
            "is the live 'how close' HUD signal. get_journal_objectives "
            "reads these same persisted axes (not the in-process detector "
            "cache), so objective progress survives a worker restart."
        ),
    ),
)

# --- EVENT scope (spec-116 Playability Spine, Task 4) ---
# pattern_shift is the lone EVENT-scope row today: no other EventType member
# is individually registered here yet (a pre-existing gap awaiting the Seam
# Phase 3 bridge-serialization sweep). This row exists because Task 4
# introduces the wire key, not because it retroactively closes that gap.

_PATTERN_SHIFT_EMITTERS: tuple[str, ...] = (
    "web/game/engine_bridge.py::EngineBridge.resolve_tick (PatternShiftEvent appended to new_state.events on a recognized-pattern change)",
)

_PATTERN_SHIFT_METRICS: tuple[SeamEntry, ...] = (
    SeamEntry(
        payload="pattern_shift",
        wire_keys=("pattern_shift",),
        scope=SeamScope.EVENT,
        owner_layer=(
            "bridge-derived (web/game/engine_bridge.py::EngineBridge.resolve_tick, "
            "from EndgameDetector.recognized_pattern deltas)"
        ),
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "fires only on the tick the recognized pattern changes (including "
            "dissolving to None); absent on every other tick"
        ),
        dtype="json",
        event_type=EventType.PATTERN_SHIFT,
        read_paths=_PATTERN_SHIFT_EMITTERS,
        spec_ref="spec-116 Playability Spine · Task 4 (FR-116-1)",
        notes=(
            "PatternShiftEvent: pattern/previous/since_tick. Distinct from "
            "EndgameEvent (endgame_reached), which fires once, at the fixed "
            "century horizon — recognizing a pattern never ends the game."
        ),
    ),
)

# ---------------------------------------------------------------------------
# ENDGAME scope — spec-116 FR-116-4.2 epilogue keys on the
# ``get_endgame_state`` payload (GET /api/games/{id}/endgame/).
# Pre-existing keys (tick/outcome/headline/summary/stats) predate the
# registry; only the Playability Spine's NEW wire keys are declared here.
#
# NOTE: named ``_ENDGAME_EPILOGUE_METRICS`` (not ``_ENDGAME_METRICS``) — Task
# 4 already claimed the ``_ENDGAME_METRICS`` Python name above for the
# ``endgame_progress`` row. Reusing that name here would silently rebind it
# and drop Task 4's row out of the ``SEAM_REGISTRY`` sum (Python module-level
# names, not the SeamEntry ``key`` property, are what collide); this section
# is summed in under its own distinct name instead.
# ---------------------------------------------------------------------------

_ENDGAME_EPILOGUE_READ_PATHS: tuple[str, ...] = (
    "web/game/engine_bridge.py::EngineBridge.get_endgame_state",
    "src/frontend/src/components/takeovers/chronicle/EndStateScreen.tsx",
)

_ENDGAME_EPILOGUE_METRICS: tuple[SeamEntry, ...] = (
    SeamEntry(
        payload="epilogue",
        wire_keys=("epilogue",),
        scope=SeamScope.ENDGAME,
        owner_layer="web bridge (game.epilogues data module)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "non-empty only once the durable ENDGAME tick_event row exists "
            "(horizon or player-accept); '' while the campaign runs"
        ),
        dtype="str",
        write_site="web/game/epilogues.py::EPILOGUES (data module, render-time lookup)",
        derivation_site="web/game/engine_bridge.py::EngineBridge.get_endgame_state",
        read_paths=_ENDGAME_EPILOGUE_READ_PATHS,
        nullable=False,
        spec_ref="specs/116-playability-spine/spec.md · FR-116-4.2",
        notes=(
            "Deterministic 2-4 sentence epilogue body, pairwise distinct across "
            "all six GameOutcome values incl. 'unresolved'. Deliberately separate "
            "from the LLM epitaph channel (NarrationRecord Scope.ENDGAME): the "
            "engine adjudicates, copy is data, AI narrates."
        ),
    ),
    SeamEntry(
        payload="palette",
        wire_keys=("palette",),
        scope=SeamScope.ENDGAME,
        owner_layer="web bridge (game.epilogues data module)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "same durable-ENDGAME-row gate as 'endgame.epilogue'; '' while the campaign runs"
        ),
        dtype="enum:EpiloguePalette",
        write_site="web/game/epilogues.py::EPILOGUES (data module, render-time lookup)",
        derivation_site="web/game/engine_bridge.py::EngineBridge.get_endgame_state",
        read_paths=_ENDGAME_EPILOGUE_READ_PATHS,
        nullable=False,
        spec_ref="specs/116-playability-spine/spec.md · FR-116-4.2",
        notes=(
            "One of 'rupture' | 'defeat' | 'unresolved' — drives the three "
            "end-screen palette families (six texts, three palettes)."
        ),
    ),
    SeamEntry(
        payload="accepted_at_tick",
        wire_keys=("accepted_at_tick",),
        scope=SeamScope.ENDGAME,
        owner_layer="web bridge (accept-outcome endpoint stamp)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "present only when the player accepted a locked pattern via "
            "POST /api/games/{id}/accept-outcome/ (FR-116-5); null for horizon "
            "termination and while in progress"
        ),
        dtype="int",
        write_site=(
            "web/game/api.py::game_accept_outcome (calls "
            "EngineBridge.accept_outcome, which stamps "
            "detail['accepted_at_tick'])"
        ),
        derivation_site="web/game/engine_bridge.py::_accepted_tick_from_endgame_row",
        read_paths=_ENDGAME_EPILOGUE_READ_PATHS,
        nullable=True,
        spec_ref="specs/116-playability-spine/spec.md · FR-116-5",
        notes="Accepted-at-tick framing on the end screen for player-accepted outcomes.",
    ),
)

# ---------------------------------------------------------------------------
# ACTION scope — per-target expected deltas on the verb-target rows
# (spec-116 FR-116-4.4). One row for the shared sub-object across its three
# emitters; the axis a verb has no formula for is an honest null.
# ---------------------------------------------------------------------------

_ACTION_EMITTERS: tuple[str, ...] = (
    "web/game/engine_bridge.py::EngineBridge.get_educate_targets",
    "web/game/engine_bridge.py::EngineBridge.get_aid_targets (population_targets)",
    "web/game/engine_bridge.py::EngineBridge.get_attack_targets (organizations+institutions)",
)

_ACTION_METRICS: tuple[SeamEntry, ...] = (
    SeamEntry(
        payload="verb_target_expected_deltas",
        wire_keys=("expected_deltas", "consciousness_delta", "heat_delta"),
        scope=SeamScope.ACTION,
        owner_layer=(
            "bridge-derived (babylon.ooda.action_effects.compute_consciousness_delta via "
            "_preview_consciousness_delta; OODADefines.attack_self_heat_gain)"
        ),
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "consciousness_delta live only on educate/aid population rows (the resolvers' "
            "own CI math, INCLUDING the Step-7.5 doctrine theory bonus (ADR073) on educate "
            "rows — _preview_consciousness_delta mirrors resolve_educate's own "
            "doctrine=services.defines.doctrine call; aid rows correctly omit the bonus, "
            "matching resolve_aid which never passes doctrine); heat_delta live only on "
            "attack rows (the resolver's self-heat define); the opposite axis is an honest "
            "null, never a fabricated 0.0"
        ),
        dtype="json",
        read_paths=_ACTION_EMITTERS,
        derivation_site="web/game/engine_bridge.py::_preview_consciousness_delta",
        spec_ref="spec-116 FR-116-4.4",
        notes=(
            "Rendered as TargetPicker per-row chips (no blind picks). Campaign rows here are "
            "snapshot-sourced (its targets GET 405s) and carry none; investigate/move/"
            "negotiate/reproduce rows carry none (no per-target resolver math). Note: the "
            "separate preview_action single-target endpoint (not in _ACTION_EMITTERS above) "
            "shares _preview_consciousness_delta and DOES exercise the CAMPAIGN/PROPAGANDIZE "
            "path there, which also mirrors resolve_campaign's doctrine= call."
        ),
    ),
)

# ---------------------------------------------------------------------------
# ECONOMY scope — the ``tick_summary`` history series behind ``/timeseries/``
# (Playability Spine Task 19, spec-116 4d.5). Wire keys are the parallel
# arrays ``EngineBridge.get_game_timeseries`` emits; each is a county-deduped
# aggregate ``_build_tick_summary`` persists per tick. First use of the
# ECONOMY scope.
# ---------------------------------------------------------------------------

_TIMESERIES_EMITTERS: tuple[str, ...] = (
    "web/game/engine_bridge.py::EngineBridge.get_game_timeseries",
    "src/frontend/src/components/chrome/CrisisTimeline.tsx (history sparkline)",
    "src/frontend/src/components/chrome/BifurcationGauge.tsx (history sparkline)",
)

_SERIES_CADENCE: str = (
    "non-null only for ticks persisted after the first year boundary this "
    "session stamped county tick_* state; carried forward between boundaries "
    "— a step-function series with a NULL head (weekly campaign = yearly "
    "points; honest sparse, never smoothed; Constitution III.11)"
)

_ECONOMY_SERIES_METRICS: tuple[SeamEntry, ...] = (
    SeamEntry(
        payload="crisis_pop_share",
        wire_keys=("crisis_pop_share",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (county-deduped aggregate of tick_crisis_phase)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_SERIES_CADENCE,
        dtype="float",
        write_site=(
            "web/game/engine_bridge.py::_county_tick_series_aggregates "
            "-> tick_summary.crisis_pop_share"
        ),
        read_paths=_TIMESERIES_EMITTERS,
        spec_ref="spec-116 4d.5 · ADR079",
        notes="Population share [0, 1] of counties in an active crisis phase (onset/early/deep).",
    ),
    SeamEntry(
        payload="bifurcation_score_mean",
        wire_keys=("bifurcation_score_mean",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (county-deduped aggregate of tick_bifurcation_score)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_SERIES_CADENCE,
        dtype="float",
        write_site=(
            "web/game/engine_bridge.py::_county_tick_series_aggregates "
            "-> tick_summary.bifurcation_score_mean"
        ),
        read_paths=_TIMESERIES_EMITTERS,
        spec_ref="spec-116 4d.5 · ADR079",
        notes=(
            "Population-weighted county mean of the political trajectory "
            "[-1 revolutionary, +1 fascist] (Feature 018 FR-011)."
        ),
    ),
    SeamEntry(
        payload="wage_compression_mean",
        wire_keys=("wage_compression_mean",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (county-deduped aggregate of tick_wage_compression)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_SERIES_CADENCE,
        dtype="float",
        write_site=(
            "web/game/engine_bridge.py::_county_tick_series_aggregates "
            "-> tick_summary.wage_compression_mean"
        ),
        read_paths=_TIMESERIES_EMITTERS,
        spec_ref="spec-116 4d.5 · ADR079",
        notes="Population-weighted county mean of cumulative wage compression [0, 1].",
    ),
    SeamEntry(
        payload="capital_stock_total",
        wire_keys=("capital_stock_total",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (county-deduped SUM of tick_capital_stock)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_SERIES_CADENCE,
        dtype="float",
        write_site=(
            "web/game/engine_bridge.py::_county_tick_series_aggregates "
            "-> tick_summary.capital_stock_total"
        ),
        read_paths=_TIMESERIES_EMITTERS,
        spec_ref="spec-116 4d.5 · ADR079",
        notes=(
            "EXTENSIVE: one term per county (never per territory — the "
            "_county_flow_snapshot N-fold hazard); a falling total is devaluation."
        ),
    ),
    SeamEntry(
        payload="unemployment_rate_mean",
        wire_keys=("unemployment_rate_mean",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (county-deduped aggregate of tick_unemployment_rate)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=_SERIES_CADENCE,
        dtype="float",
        write_site=(
            "web/game/engine_bridge.py::_county_tick_series_aggregates "
            "-> tick_summary.unemployment_rate_mean"
        ),
        read_paths=_TIMESERIES_EMITTERS,
        spec_ref="spec-116 4d.5 · ADR079",
        notes="Population-weighted county mean of the BLS LAUS unemployment rate.",
    ),
)

# ---------------------------------------------------------------------------
# ECONOMY scope — the ``get_economy_dashboard`` graph-wide dashboard payload
# (spec-109 A4). T2-2 (Slice 2, 2026-07-18): the 5-row block above only covers
# the ``/timeseries/`` history series (Program 23 ADR079); this block covers
# the *dashboard* surface's own wire keys, each verified against a real
# Postgres session (``tests/integration/web/test_dashboards.py::
# TestEconomyDashboard``, ``tests/unit/web/test_engine_bridge.py::
# TestMeanTerritoryAttr``) — never declared from a code reading alone.
# ---------------------------------------------------------------------------

_ECONOMY_DASHBOARD_EMITTERS: tuple[str, ...] = (
    "web/game/engine_bridge.py::EngineBridge.get_economy_dashboard (:3019)",
    "src/frontend/src/components/economy/EconomyDashboard.tsx",
)

_ECONOMY_DASHBOARD_METRICS: tuple[SeamEntry, ...] = (
    SeamEntry(
        payload="economy_dashboard.value_produced",
        wire_keys=("value_produced",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (_aggregate_graph_economy, graph-wide sum of wealth)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "a real 0.0 on a tick-0 graph with no wealth yet is honest, not fabricated — the "
            "ONLY null reason before G4 — but veil-masked to None below the player org's "
            "Veil-of-Money Tier 1 (web/game/veil.py::gate_value_axis_fields, G4 leak closure); "
            "the two null reasons are indistinguishable on the wire by design"
        ),
        dtype="float",
        write_site="web/game/engine_bridge.py::_aggregate_graph_economy (:910)",
        read_paths=_ECONOMY_DASHBOARD_EMITTERS,
        spec_ref="spec-109 A4 · spec-117 §5d (G4 veil gate)",
        notes=(
            "sum(wealth) over every social_class/organization node (rounded) — confirmed by "
            "test_dashboards.py's post-create/post-resolve assertions. G4: reclassified from "
            "MUST_BE_LIVE — the veil can now legitimately null this field regardless of real "
            "economic activity (TestEconomyDashboardVeil/TestVeilGating pin both null reasons). "
            "NOTE the wire-key collision: persisted_tick_summary.total_v below "
            "(get_game_timeseries's ``value_produced`` array) is a DIFFERENT, currently-DEAD "
            "payload sharing this exact (scope, wire_key) — see that row for the discovered "
            "defect."
        ),
    ),
    SeamEntry(
        payload="economy_dashboard.profit_rate",
        wire_keys=("profit_rate",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (_mean_territory_attr over tick_profit_rate, graph-wide mean)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            _YEAR_BOUNDARY + "; a graph-wide MEAN over every territory carrying the attr "
            "(_mean_territory_attr), distinct from the MAP-scope per-feature reading and from "
            "the dead persisted_tick_summary.profit_rate column below. G4: ALSO veil-masked "
            "below Tier 1 (gate_value_axis_fields) — a s/(c+v) value relation, gated identically "
            "to exploitation_rate."
        ),
        dtype="float",
        write_site="web/game/engine_bridge.py::_mean_territory_attr (:7984)",
        read_paths=_ECONOMY_DASHBOARD_EMITTERS,
        spec_ref="spec-109 A4 · Program-17 item-25 · spec-117 §5d (G4 veil gate)",
        notes=(
            "Confirmed real: test_dashboards.py pins it None at tick 0 (no boundary crossed "
            "yet). NOTE the wire-key collision with the dead "
            "persisted_tick_summary.profit_rate column below."
        ),
    ),
    SeamEntry(
        payload="economy_dashboard.occ",
        wire_keys=("occ",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (_mean_territory_attr over tick_occ, graph-wide mean)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            _YEAR_BOUNDARY + "; graph-wide MEAN, same pattern as profit_rate above. G4: ALSO "
            "veil-masked below Tier 1 (gate_value_axis_fields) — a c/v value relation."
        ),
        dtype="float",
        write_site="web/game/engine_bridge.py::_mean_territory_attr (:7984)",
        read_paths=_ECONOMY_DASHBOARD_EMITTERS,
        spec_ref="spec-109 A4 · Program-17 item-25 · spec-117 §5d (G4 veil gate)",
        notes="Confirmed real: test_dashboards.py pins it None at tick 0 (no boundary crossed yet).",
    ),
    SeamEntry(
        payload="economy_dashboard.tick",
        wire_keys=("tick",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (EngineBridge.hydrate_state, WorldState.tick)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="int",
        nullable=False,
        write_site="web/game/engine_bridge.py::EngineBridge.get_economy_dashboard (:3120)",
        read_paths=_ECONOMY_DASHBOARD_EMITTERS,
        spec_ref="spec-109 A4",
        notes=(
            "G4 (Track-2(ii) seam-contract closure): one of the 4 rows the audit found "
            "missing for a LIVE chip field — always the hydrated state's real tick, never "
            "None. Confirmed by every test in test_engine_bridge.py::TestEconomyDashboard*."
        ),
    ),
    SeamEntry(
        payload="economy_dashboard.has_data",
        wire_keys=("has_data",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (_aggregate_graph_economy, value_produced > 0 or rent_extracted > 0)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="bool",
        nullable=False,
        write_site="web/game/engine_bridge.py::_aggregate_graph_economy (:900)",
        read_paths=_ECONOMY_DASHBOARD_EMITTERS,
        spec_ref="spec-109 A4",
        notes=(
            "G4: the other 3 missing rows the audit found. Always a real bool (never None) — "
            "the honest 'no economic activity recorded' gate EconomyDashboard.tsx reads before "
            "rendering any chip."
        ),
    ),
    SeamEntry(
        payload="economy_dashboard.rent_extracted",
        wire_keys=("rent_extracted",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (_aggregate_graph_economy, sum of EXTRACTIVE/ANTAGONISTIC edge value_flow)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "always a float (0.0 is an honest 'no extractive edges yet', not fabricated) UNLESS "
            "veil-masked to None below the player org's Veil-of-Money Tier 1 (G4, "
            "web/game/veil.py::gate_value_axis_fields — imperial-rent family) — the two null "
            "reasons are NOT distinguishable on the wire by design, same as veil.value_produced"
        ),
        dtype="float",
        write_site="web/game/engine_bridge.py::_aggregate_graph_economy (:900)",
        read_paths=_ECONOMY_DASHBOARD_EMITTERS,
        spec_ref="spec-109 A4 · spec-117 §5d (G4 veil gate)",
        notes=(
            "G4: sibling of value_produced/exploitation_rate above — same "
            "_aggregate_graph_economy computation, now gated by the SAME veil tier via "
            "gate_value_axis_fields (Task A's leak closure). Was live-but-unregistered before "
            "this row; the veil gate is why it is DECLARED_CONDITIONAL rather than "
            "MUST_BE_LIVE now."
        ),
    ),
    SeamEntry(
        payload="economy_dashboard.exploitation_rate",
        wire_keys=("exploitation_rate",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (_aggregate_graph_economy, calculate_unequal_exchange_rate)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "None when value_produced <= 0 (an honest 'no basis for the ratio', pre-existing) "
            "OR veil-masked below Tier 1 (G4 — the wage-vs-value-produced axis itself); the two "
            "null reasons are indistinguishable on the wire by design"
        ),
        dtype="float",
        write_site="web/game/engine_bridge.py::_aggregate_graph_economy (:900)",
        read_paths=_ECONOMY_DASHBOARD_EMITTERS,
        spec_ref="spec-109 A4 · spec-117 §5d (G4 veil gate)",
        notes=(
            "G4: the LEGACY top-level twin of veil.exploitation_rate (see the veil row below) "
            "— both fields now gated by the exact same tier (Task A's leak closure); a prior "
            "version of this payload left this top-level field ungated while only the nested "
            "veil.* copy was gated — the leak this program closed."
        ),
    ),
    SeamEntry(
        payload="global_economy.imperial_rent_pool",
        wire_keys=("imperial_rent_pool",),
        scope=SeamScope.ECONOMY,
        owner_layer="babylon.engine.systems.economic.ImperialRentSystem (_save_economy)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "GlobalEconomy.imperial_rent_pool is a required WorldState.economy field (default "
            "100.0) — always present pre-G4. G4: now ALSO veil-masked below Tier 1 "
            "(gate_value_axis_fields — imperial-rent family), so the wire value can be None "
            "regardless of the underlying field's real presence."
        ),
        dtype="float",
        write_site="src/babylon/engine/systems/economic.py::ImperialRentSystem._save_economy (:804)",
        read_paths=_ECONOMY_DASHBOARD_EMITTERS,
        spec_ref="spec-109 A4 · spec-117 §5d (G4 veil gate)",
        notes=(
            "GlobalEconomy.imperial_rent_pool is a required WorldState.economy field (default "
            "100.0, models/entities/economy.py:63) — confirmed by test_dashboards.py at tick 0 "
            "and tick 2. Distinct wire key from MAP-scope imperial_rent (the Leontief flow rate) "
            "and TERRITORY-scope hex_latest.imperial_rent — this is the accumulated STOCK. G4: "
            "reclassified from MUST_BE_LIVE — the veil can now legitimately null this field."
        ),
    ),
    SeamEntry(
        payload="global_economy.current_super_wage_rate",
        wire_keys=("current_super_wage_rate",),
        scope=SeamScope.ECONOMY,
        owner_layer="babylon.engine.systems.economic.ImperialRentSystem (_save_economy)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
        write_site="src/babylon/engine/systems/economic.py::ImperialRentSystem._save_economy (:805)",
        read_paths=_ECONOMY_DASHBOARD_EMITTERS,
        spec_ref="spec-109 A4",
        notes=(
            "GlobalEconomy.current_super_wage_rate is a required field (default 0.20, "
            "models/entities/economy.py:68) — always present, same MUST_BE_LIVE basis as "
            "imperial_rent_pool above."
        ),
    ),
    SeamEntry(
        payload="wage_flow_total",
        wire_keys=("wage_flow_total",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (_sum_edge_value_flow_by_mode, EdgeType.WAGES)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
        write_site="web/game/engine_bridge.py::_sum_edge_value_flow_by_mode (:936)",
        read_paths=_ECONOMY_DASHBOARD_EMITTERS,
        spec_ref="spec-109 A4",
        notes=(
            "Sum starts at 0.0 and is never None (an honest 0.0 in a graph with no WAGES edges "
            "is real, not fabricated) — confirmed live and non-fabricated by "
            "test_dashboards.py::test_economy_dashboard_wage_flow_after_resolves against the "
            "wayne_county WAGES edge."
        ),
    ),
    SeamEntry(
        payload="tribute_flow_total",
        wire_keys=("tribute_flow_total",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (_sum_edge_value_flow_by_mode, EdgeType.TRIBUTE)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
        write_site="web/game/engine_bridge.py::_sum_edge_value_flow_by_mode (:936)",
        read_paths=_ECONOMY_DASHBOARD_EMITTERS,
        spec_ref="spec-109 A4",
        notes="Sibling of wage_flow_total above, filtered to EdgeType.TRIBUTE instead of WAGES.",
    ),
    SeamEntry(
        payload="wealth_by_class_role",
        wire_keys=("wealth_by_class_role",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (_wealth_by_class_role, SocialClass.wealth grouped by SocialRole)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="json",
        nullable=False,
        write_site="web/game/engine_bridge.py::_wealth_by_class_role (:1056)",
        read_paths=(
            "web/game/engine_bridge.py::EngineBridge.get_economy_dashboard (:3020)",
            "src/frontend/src/components/circuit/CircuitPage.tsx",
        ),
        spec_ref="spec-109 A4",
        notes=(
            "The container is always a dict (possibly {} on a classless graph, never None) — "
            "confirmed non-empty for wayne_county by test_dashboards.py. Rendered as the "
            "BreakdownBar composition chart — RELOCATED (Track 2 T2-7, D2: 'no god-dashboard') "
            "from EconomyDashboard.tsx onto CircuitPage.tsx; the payload itself is unchanged."
        ),
    ),
    SeamEntry(
        payload="county_flow",
        wire_keys=("county_flow",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (_county_flow_snapshot, first territory carrying carried flow state)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "the container ({year, phi_accrued_this_year, wage_accrued_this_year}) is always a "
            "dict, but every field inside is None until at least one territory has carried "
            "flow_wage_accrued state this session (i.e. crossed a year boundary) — confirmed "
            "live by test_static_economy_flow.py's cross-tick county_flow movement assertions"
        ),
        dtype="json",
        nullable=False,
        write_site="web/game/engine_bridge.py::_county_flow_snapshot (:8012)",
        read_paths=_ECONOMY_DASHBOARD_EMITTERS,
        spec_ref="owner item 30, point 5",
        notes=(
            "SERIALIZED BUT UNRENDERED (verified 2026-07-18): the frontend types this shape "
            "(types/game.ts CountyFlowSnapshot) and exercises it in test fixtures/MSW handlers, "
            "but no shipped .tsx component reads county_flow — a real backend value with no "
            "current UI consumer. Not fabricated, just not yet wired to a view."
        ),
    ),
    SeamEntry(
        payload="economy_dashboard.imperial_rent_gap",
        wire_keys=("imperial_rent_gap",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (get_economy_dashboard, wage_flow_total - value_produced)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "always a float pre-G4 (both addends default 0.0, never fabricated-absent). G4: now "
            "ALSO veil-masked to None below Tier 1 (gate_value_axis_fields — imperial-rent "
            "family) — the two null reasons are indistinguishable on the wire by design."
        ),
        dtype="float",
        write_site="web/game/engine_bridge.py::EngineBridge.get_economy_dashboard (:3120)",
        read_paths=_ECONOMY_DASHBOARD_EMITTERS,
        spec_ref="spec-117 T2-6a (Fundamental Theorem, W_c - V_c = Phi) · §5d (G4 veil gate)",
        notes=(
            "T2-6a (Slice A): graph-wide promotion of the per-class imperial_rent_gap already "
            "computed for the inspector popup (see the INSPECTOR-scope row below) — Sigma core "
            "wages paid (wage_flow_total) minus Sigma value produced (value_produced), both "
            "EXTENSIVE totals summed graph-wide (never averaged), so this carries none of the "
            "unweighted-mean-of-a-ratio risk a naive per-region average would -- confirmed by "
            "test_engine_bridge.py::TestEconomyDashboardFundamentalTheorem. G4: reclassified "
            "from MUST_BE_LIVE — the veil can now legitimately null this field."
        ),
    ),
    SeamEntry(
        payload="economy_dashboard.imperial_rent_gap_by_region",
        wire_keys=("imperial_rent_gap_by_region",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (_imperial_rent_gap_by_region, ScaleAdjunction.aggregate_intensive)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "the container is always a list, but stays empty ([]) until at least one territory "
            "has a positive-population TENANCY-linked tenant social_class this session "
            "(Constitution III.11 — never a fabricated per-capita row for an all-zero-population "
            "region) OR below the veil's Tier 1 (G4, gate_value_axis_fields masks this field to "
            "[] too) — the two empty-list reasons are indistinguishable on the wire by design"
        ),
        dtype="json",
        nullable=False,
        write_site="web/game/engine_bridge.py::_imperial_rent_gap_by_region (:1823)",
        read_paths=_ECONOMY_DASHBOARD_EMITTERS,
        spec_ref="spec-117 T2-6b (per-region Fundamental Theorem, population-share-weighted)",
        notes=(
            "T2-6b (Slice A), net-new: one {territory_id, population, wc_per_capita, "
            "vc_per_capita, gap_per_capita} row per positive-population TENANCY region. "
            "gap_per_capita is a population-SHARE-WEIGHTED MEAN via "
            "ScaleAdjunction.aggregate_intensive (domain/dialectics/instances/scale.py) — never "
            "an unweighted mean of the per-class ratio, the known intensive-aggregation bug "
            "documented in domain/dialectics/instances/catalog.py's _mean_asymmetry — confirmed "
            "by test_engine_bridge.py::TestImperialRentGapByRegion + "
            "TestEconomyDashboardFundamentalTheorem."
        ),
    ),
    SeamEntry(
        payload="veil",
        wire_keys=("veil",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (compute_veil_status, game.veil — Track 2 T2-8/T2-9, spec-117 §5d)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "the container ({tier, next_unlock_node_id, next_unlock_label, value_produced, "
            "exploitation_rate}) is always a dict with tier always non-null; "
            "next_unlock_node_id/next_unlock_label are null only at tier 2 (fully unlocked); "
            "value_produced/exploitation_rate are null below tier 1 BY DESIGN (the veil "
            "itself, not a data gap) — every combination confirmed by "
            "tests/unit/web/test_engine_bridge.py::TestEconomyDashboardVeil and the "
            "monotonicity property test in tests/unit/web/test_veil.py"
        ),
        dtype="json",
        nullable=False,
        write_site=(
            "web/game/engine_bridge.py::EngineBridge.get_economy_dashboard (:3020), "
            "via game.veil.compute_veil_status"
        ),
        read_paths=(
            "web/game/engine_bridge.py::EngineBridge.get_economy_dashboard (:3020)",
            "src/frontend/src/components/circuit/CircuitPage.tsx",
        ),
        spec_ref="spec-117 §5d (D7)",
        notes=(
            "The Veil of Money's tier status — gates value_produced/exploitation_rate "
            "visibility on the player org's REAL acquired_doctrine_ids (append-only "
            "membership test, never the decaying doctrine_tags accumulator or the "
            "spendable theoretical_labor balance — see game/veil.py's module docstring "
            "for why those would violate the spec's monotonicity requirement). Distinct "
            "from the always-live top-level value_produced/exploitation_rate rows above: "
            "those are EconomyDashboard/BottomDrawer's unrelated pre-existing surface, "
            "deliberately out of this program's scope."
        ),
    ),
)

# ---------------------------------------------------------------------------
# ECONOMY scope — the Program 23 Market-Scissors columns behind
# ``get_game_timeseries`` that the original 5-row block didn't cover (T2-2,
# Slice 2). Three are real (the ``state.market`` axis, gated on paid-worker
# accounting); three are a DISCOVERED DEFECT verified against the live
# ``babylon_test`` DB (430 persisted ``tick_summary`` rows: 0 with a non-null
# ``total_v``/``total_s``/``profit_rate``, 19 with non-null
# ``price_log``/``fictitious_log``/``market_corrections`` — the real trio).
# ``_build_tick_summary`` (:8747-8753) hardcodes ``total_c``/``total_v``/
# ``total_s``/``exploitation_rate``/``profit_rate`` to ``None``
# UNCONDITIONALLY — no other call site ever writes them — despite this
# module's own ``get_game_timeseries`` docstring (:2924) claiming
# ``value_produced``/``surplus``/``profit_rate`` are "real substrate".
# ---------------------------------------------------------------------------

_ECONOMY_TIMESERIES_SCISSORS_METRICS: tuple[SeamEntry, ...] = (
    SeamEntry(
        payload="persisted_tick_summary.price_log",
        wire_keys=("price_index",),
        scope=SeamScope.ECONOMY,
        owner_layer="babylon.models.market.MarketState (MarketScissorsSystem @17.8)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "MarketState exists only once a paid-worker node (both w_paid and v_produced "
            "attrs) is present (MarketScissorsSystem._aggregate_wage_value); None on graphs "
            "with no wage-relation accounting — confirmed live on the babylon_test DB (19/430 "
            "tick_summary rows non-null)"
        ),
        dtype="float",
        write_site="src/babylon/engine/systems/market_scissors.py::MarketScissorsSystem.step (:165)",
        derivation_site="web/game/engine_bridge.py::get_game_timeseries (exp(price_log), :2981)",
        read_paths=_TIMESERIES_EMITTERS,
        spec_ref="Program 23 · ADR077",
        notes=(
            "exp(price_log) so 1.0 = price at value. Rendered by ScissorsChart.tsx. Real "
            "substrate — NOT the dead trio below."
        ),
    ),
    SeamEntry(
        payload="persisted_tick_summary.fictitious_log",
        wire_keys=("fictitious_ratio",),
        scope=SeamScope.ECONOMY,
        owner_layer="babylon.models.market.MarketState (MarketScissorsSystem @17.8)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "same MarketState condition as price_index above — confirmed live (19/430 rows)"
        ),
        dtype="float",
        write_site="src/babylon/engine/systems/market_scissors.py::MarketScissorsSystem.step (:165)",
        derivation_site=(
            "web/game/engine_bridge.py::get_game_timeseries (exp(fictitious_log), :2982)"
        ),
        read_paths=_TIMESERIES_EMITTERS,
        spec_ref="Program 23 · ADR077",
        notes=(
            "exp(fictitious_log) so 1.0 = fictitious capitalization at real. Rendered by "
            "ScissorsChart.tsx."
        ),
    ),
    SeamEntry(
        payload="persisted_tick_summary.market_corrections",
        wire_keys=("market_corrections",),
        scope=SeamScope.ECONOMY,
        owner_layer="babylon.models.market.MarketState.corrections (ADR078 correction snap)",
        liveness_class=LivenessClass.DECLARED_CONDITIONAL,
        liveness_condition=(
            "same MarketState condition as price_index above — confirmed live (19/430 rows); "
            "the field itself is a monotonic int counter, 0 until the first correction snap"
        ),
        dtype="int",
        write_site="src/babylon/engine/systems/market_scissors.py::MarketScissorsSystem.step (:165)",
        derivation_site="web/game/engine_bridge.py::get_game_timeseries (:2987)",
        read_paths=_TIMESERIES_EMITTERS,
        spec_ref="Program 23 · ADR078",
        notes="Cumulative snap count; the cockpit derives correction ticks from increments.",
    ),
    SeamEntry(
        payload="persisted_tick_summary.total_s",
        wire_keys=("surplus",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (_build_tick_summary — hardcoded None, never wired)",
        liveness_class=LivenessClass.NOT_YET_COMPUTED,
        dtype="float",
        write_site="web/game/engine_bridge.py::_build_tick_summary (:8751, unconditional None)",
        read_paths=_TIMESERIES_EMITTERS,
        spec_ref="Program 23 · ADR077",
        notes=(
            "DISCOVERED DEFECT (T2-2, 2026-07-18): _build_tick_summary hardcodes total_s=None "
            "unconditionally regardless of graph/state — no other call site ever populates the "
            "tick_summary.total_s DB column. Empirically 0/430 non-null on the live "
            "babylon_test DB. The get_game_timeseries docstring (:2924) calls this 'real "
            "substrate' — that claim is false as shipped. A real total_s exists elsewhere in "
            "the engine (the substrate tensor's total_s, see "
            "tests/integration/test_marx_identities.py) but is never threaded into this "
            "persistence row — computed-but-never-consumed-AT-THIS-SEAM, not a fabricated "
            "value (the wire key does emit; it just never emits non-null). NOT_YET_COMPUTED, "
            "not DECLARED_CONDITIONAL, because no condition in today's code produces a value."
        ),
    ),
    SeamEntry(
        payload="persisted_tick_summary.total_v",
        wire_keys=("value_produced",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (_build_tick_summary — hardcoded None, never wired)",
        liveness_class=LivenessClass.NOT_YET_COMPUTED,
        dtype="float",
        write_site="web/game/engine_bridge.py::_build_tick_summary (:8750, unconditional None)",
        read_paths=_TIMESERIES_EMITTERS,
        spec_ref="Program 23 · ADR077",
        notes=(
            "DISCOVERED DEFECT, same root cause as persisted_tick_summary.total_s above — see "
            "that row. Shares its wire key + scope with the LIVE "
            "economy_dashboard.value_produced row above (a real, working, DIFFERENT "
            "computation: _aggregate_graph_economy's sum(wealth), read live off the graph, "
            "never persisted) — a genuine (scope, wire_key) collision today's SeamScope "
            "taxonomy does not resolve, since ECONOMY covers both the dashboard and the "
            "timeseries surfaces (candidate follow-up: split into distinct scopes). Also "
            "unconsumed on the frontend: no .tsx component reads the timeseries "
            "value_produced array (EconomyDashboard.tsx reads the dashboard scalar only)."
        ),
    ),
    SeamEntry(
        payload="persisted_tick_summary.profit_rate",
        wire_keys=("profit_rate",),
        scope=SeamScope.ECONOMY,
        owner_layer="bridge (_build_tick_summary — hardcoded None, never wired)",
        liveness_class=LivenessClass.NOT_YET_COMPUTED,
        dtype="float",
        write_site="web/game/engine_bridge.py::_build_tick_summary (:8753, unconditional None)",
        read_paths=_TIMESERIES_EMITTERS,
        spec_ref="Program 23 · ADR077",
        notes=(
            "DISCOVERED DEFECT, same root cause as persisted_tick_summary.total_s above. "
            "Shares its wire key + scope with the LIVE economy_dashboard.profit_rate row above "
            "(a real, different computation: _mean_territory_attr over tick_profit_rate) and "
            "with the MAP-scope tick_profit_rate row (a per-feature reading) — three payloads, "
            "one wire-key string, only this one is dead."
        ),
    ),
)

# ---------------------------------------------------------------------------
# INSPECTOR scope — ``imperial_rent_gap`` (T2-2, Slice 2). Genuinely ungated:
# absent from SEAM_REGISTRY entirely (unlike circuit_flows, already registered
# above at the INSPECTOR block, and the ternary-consciousness/agitation rows
# covering the rest of _social_class_inspector_fields's Program 17 Wave 1
# additions).
# ---------------------------------------------------------------------------

_INSPECTOR_IMPERIAL_RENT_GAP_METRICS: tuple[SeamEntry, ...] = (
    SeamEntry(
        payload="imperial_rent_gap",
        wire_keys=("imperial_rent_gap",),
        scope=SeamScope.INSPECTOR,
        owner_layer="bridge-derived (_social_class_inspector_fields, core_wages - wealth)",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
        derivation_site="web/game/engine_bridge.py::_social_class_inspector_fields (:2026)",
        read_paths=_INSPECTOR_EMITTERS,
        spec_ref="Fundamental Theorem (W_c - V_c = Phi)",
        notes=(
            "Signed Phi per social_class node: core_wages (incoming WAGES flow) minus wealth "
            "(value produced). Always a float (both operands default 0.0, never None) — "
            "confirmed real and signed both directions by test_engine_bridge_inspectors.py "
            "(positive subsidy gap +0.35, negative exploited gap -0.15, not clamped). Rendered "
            "by the inspector's Imperial Rent Gap row (lib/inspect/adapters/node.ts)."
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
    + _DOCTRINE_METRICS
    + _ENDGAME_METRICS
    + _PATTERN_SHIFT_METRICS
    + _ENDGAME_EPILOGUE_METRICS  # spec-116 FR-116-4.2: epilogue/palette/accepted_at_tick
    + _ACTION_METRICS  # spec-116 FR-116-4.4: per-target expected_deltas
    + _ECONOMY_SERIES_METRICS  # Program 23 ADR079: crisis/bifurcation/wage/capital/unemployment
    + _ECONOMY_DASHBOARD_METRICS  # T2-2: get_economy_dashboard's 9 wire keys (Slice 2)
    + _ECONOMY_TIMESERIES_SCISSORS_METRICS  # T2-2: scissors trio + 3 discovered-dead siblings
    + _INSPECTOR_IMPERIAL_RENT_GAP_METRICS  # T2-2: imperial_rent_gap, genuinely ungated
)
