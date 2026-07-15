"""Single source of truth for the ``/map/`` metric contract (spec-109 A3).

Before this module existed the contract had three divergent copies:
``api.VALID_MAP_LAYERS`` advertised 11 layers, the map snapshot's
``metadata.available_metrics`` advertised 6, and the emitted feature
properties defined the truth. Requesting a lens for a never-emitted metric
(``consciousness``/``wealth``/``rent``/``biocapacity``) filtered features
down to no value key at all — a silently blank overlay, which Constitution
III.11 forbids.

The rule: **every name below is emitted as a property on both hex- and
county-zoom ``/map/`` features** (``_hex_feature_properties`` /
``EngineBridge._aggregate_hex_features``), advertised via
``metadata.available_metrics``, and accepted by the API's ``lens`` filter.
A metric that is not actually emitted MUST NOT be listed. ``habitability``
joins this tuple when its ``hex_latest`` column + serializer projection land
(spec-109 A2). Every entry is a numeric ramp EXCEPT ``dominant_class``
(spec-113 Lane D) and ``territory_type`` (Wave 2 W2.4) — both categorical
strings, the non-numeric members of this contract.

Kept dependency-free so both ``api`` and ``engine_bridge`` can import it at
module level without Django/engine import weight.
"""

from __future__ import annotations

MAP_METRIC_PROPERTIES: tuple[str, ...] = (
    "profit_rate",
    "exploitation_rate",
    "occ",
    "imperial_rent",
    "heat",
    "org_presence",
    "population",
    # Spec-109 A2: MetabolismSystem's Sovereign-driven habitability, read
    # live off the graph node (Territory model excludes it — see
    # TERRITORY_EXCLUDED_FIELDS) and projected into hex_latest's JSONB
    # ``attributes`` column (no dedicated column needed).
    "habitability",
    # Spec-113 Lane D: dominant_class (the population-weighted-majority
    # SocialRole among the territory's TENANCY-linked social_class members
    # — HexState's own ``dominant_class`` column) and solidarity_index (mean
    # live-SOLIDARITY-edge incidence over those same TENANCY-linked members
    # — rides hex_latest's JSONB ``attributes`` column like habitability).
    # Both computed in engine_bridge.py's ``_tenancy_members_by_territory``/
    # ``_dominant_class_by_territory``/``_solidarity_index_by_territory``.
    "dominant_class",
    "solidarity_index",
    # Wave 2 W2.4 (owner ruling 1 + delegated rulings): throughput_position
    # (π — real once a session has FIPS + a throughput_calculator wired, see
    # _bridge_economics_overrides — rides hex_latest's JSONB ``attributes``
    # column like habitability), agitation (population-weighted mean
    # ideology.agitation over TENANCY-linked social_class members — the
    # Revolutionary Potential Index; legitimately 0.0 at tick 0, never
    # warmed up — see _agitation_index_by_territory), and territory_type
    # (the real TerritoryType enum — CORE/PERIPHERY in shipped scenarios,
    # the Necropolitical Triad when a scenario seeds one — population-
    # weighted MODE at county zoom, mirroring dominant_class).
    "throughput_position",
    "agitation",
    "territory_type",
    # Audit Wave 4 straggler (task #76 — "critical-nodes/centrality map
    # lens"): a territory's own degree-centrality within the org-network
    # topology (organizations/institutions/territories linked by
    # PRESENCE/HOUSES edges — see EngineBridge._org_network_centrality,
    # AW4-R1 commit c312e62d). Territory nodes ARE literal nodes in that
    # network, so this rides their own real reading — no TENANCY projection
    # needed, unlike agitation/solidarity_index (which read social_class
    # members that never enter the org network at all). Rides hex_latest's
    # JSONB attributes column like habitability/agitation. Honest null for
    # any territory absent from the org network (no org/institution has a
    # PRESENCE edge there) — sparse today: only wayne_county seeds real
    # Organization rows (_legacy_wayne.py), so every other shipped scenario
    # is honestly empty for this lens.
    "centrality",
    # Wave 5 receptivity lens pair (Epistemic Horizon Phase 1 honest-display,
    # program: project/research/epistemic-horizon-program-proposal.md):
    # mass_receptivity (M_r) is a NATIVE per-territory graph attr written
    # directly by EpistemicHorizonSystem (engine position 27, last) — unlike
    # agitation/solidarity_index it needs no TENANCY-projection aggregation
    # of its own, it rides straight off _serialize_territory's own key (same
    # shape as habitability/throughput_position). Population-weighted MEAN
    # at county zoom. vision_state is the companion categorical lens (the
    # corpus's desert/mud/water three-state partition, threshold-derived
    # from M_r) — population-weighted MODE at county zoom, same deterministic
    # lexicographic-greatest tie-break as dominant_class/territory_type. Both
    # rides hex_latest's JSONB attributes column like territory_type — no
    # dedicated column. Honest null for a territory with no TENANCY-linked
    # social_class members carrying positive population (Constitution III.11
    # — EpistemicHorizonSystem writes all three shadow attrs together or not
    # at all), and for a graph that has never been stepped (this system runs
    # only inside a tick). intel_confidence (I_c) deliberately does NOT join
    # this contract: it is uniformly 0.1 in every scenario verified so far
    # (C_p=0 everywhere — no org model outside PoliticalFaction carries a
    # player marker yet, see the program report's Phase-1 findings), so a
    # flat lens would be decorative; it rides the territory serializer/
    # inspector payload only.
    "mass_receptivity",
    "vision_state",
    # Feature 021 lens pair (System #5 ReserveArmySystem / System #10
    # DispossessionEventSystem): wage_pressure (the Reserve Army's bounded-
    # sigmoid wage-discipline coefficient — reserve_ratio pushes median_wage
    # down) and dispossession_intensity (DispossessionIntensityCalculator's
    # composite foreclosure/eviction/displacement/tax-sale/eminent-domain
    # weighted intensity). Both are NATIVE per-territory graph attrs — same
    # shape as habitability/mass_receptivity, no TENANCY-projection
    # aggregation needed — rides straight off _serialize_territory's own
    # key. Population-weighted MEAN at county zoom. Honest null (III.11):
    # ReserveArmySystem/DispossessionEventSystem write no attr at all for a
    # territory with no reserve-army pressure / no dispossession activity
    # this tick (never a fabricated 0.0 standing in for "not computed").
    "wage_pressure",
    "dispossession_intensity",
)

# Backend-W3R3 (Program 17 Wave 3): the MAP_METRIC_PROPERTIES subset
# genuinely backed by an append-only per-tick persisted store, so
# ``GET /api/games/{id}/map/history/`` can replay it honestly (Constitution
# III.11 — the other 10 exist only in ``hex_latest``, a current-tick-only
# cache overwritten every tick by ``_persist_hex_state_safe``, with no
# historical table at all). Verified against a running canonical session
# (2026-07-15, tick 987): ``heat``/``population`` off ``territory_snapshot``
# (dense, written every resolve — ``_territory_snapshot_rows``);
# ``profit_rate``/``exploitation_rate`` off ``view_runtime_trace_emission``
# (the spec-089 hex-delta fill-forward view — a genuine county-wide SUM
# aggregate, confirmed real non-null across 987 ticks by direct SELECT).
# Separately-flagged finding (see EngineBridge.get_map_history's docstring):
# even ``occ``/``imperial_rent`` — declared ``territory_snapshot`` COLUMNS —
# persist as NULL on every row today, because ``_persist_snapshots_safe``
# calls ``_serialize_territory(t)`` without the ``graph=`` kwarg those
# columns' ``tick_occ``/``tick_phi_hour`` reads need; that gap is reported,
# not fixed here, so this tuple stays at 4, not 6.
MAP_HISTORY_REPLAYABLE_METRICS: frozenset[str] = frozenset(
    {"heat", "population", "profit_rate", "exploitation_rate"}
)
