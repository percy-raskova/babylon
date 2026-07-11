"""PostgreSQL schema DDL for simulation runtime state (Feature 037).

Defines tables across 10 layers:

1. Game Management (3): game_session, game_turn, action_result
2. Simulation State (10): node_state, edge_state, graph_metadata,
   community_state, community_membership, contradiction_field,
   edge_curvature, simulation_event, tick_log, tick_summary
3. Spatial (3): hex_cell, hex_state, hex_terrain_state
3b. R8 Reference (2): hex_r8_reference, hex_r8_linear_features_reference
4. Infrastructure (1): infrastructure_link_state
5. Trace (1): trace_log (UNLOGGED, partitioned by session_id)
6. Semantic (1): document_chunk (pgvector)
7. Game-Journal Domain (2): hex_map, game_defines_snapshot
8. Game-Journal Snapshots (7): territory_snapshot, org_snapshot,
   edge_snapshot, community_snapshot, hex_activity,
   economic_summary, tick_event
8b. Multi-Resolution Hex Cache (2): hex_latest (R7 denormalized
    current-state cache), hex_substrate (R8 static terrain)
9. Composition Views (5): v_hex_economic, v_hex_mobilize,
   v_hex_aid, v_hex_heat, v_hex_intel

All tables are Django-ready: snake_case names, ``id`` PKs (BIGSERIAL for
data tables, UUID for game_session), ``created_at``/``updated_at``
TIMESTAMPTZ. No ``auth_user`` FK until Django auth module exists.
"""

from __future__ import annotations

# SQL DDL statements executed via psycopg (not ORM)

EXTENSIONS_DDL: list[str] = [
    "CREATE EXTENSION IF NOT EXISTS postgis",
    "CREATE EXTENSION IF NOT EXISTS vector",
    'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
]

# ─── Layer 1: Game Management ───────────────────────────────────────

GAME_SESSION_DDL = """
CREATE TABLE IF NOT EXISTS game_session (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id       INTEGER,
    scenario        VARCHAR(64) NOT NULL,
    current_tick    INTEGER NOT NULL DEFAULT 0,
    status          VARCHAR(16) NOT NULL DEFAULT 'active',
    config_json     JSONB NOT NULL DEFAULT '{}'::jsonb,
    game_defines_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    trace_level     VARCHAR(8) NOT NULL DEFAULT 'NONE',
    rng_seed        BIGINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

GAME_TURN_DDL = """
CREATE TABLE IF NOT EXISTS game_turn (
    id              BIGSERIAL PRIMARY KEY,
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    org_id          VARCHAR(64) NOT NULL,
    verb            VARCHAR(16) NOT NULL,
    action_type     VARCHAR(32),
    target_id       VARCHAR(64),
    target_community VARCHAR(32),
    params_json     JSONB,
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved        BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (session_id, tick, org_id)
)
"""

ACTION_RESULT_DDL = """
CREATE TABLE IF NOT EXISTS action_result (
    id              BIGSERIAL PRIMARY KEY,
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    org_id          VARCHAR(64) NOT NULL,
    action_type     VARCHAR(32) NOT NULL,
    target_id       VARCHAR(64),
    target_community VARCHAR(32),
    initiative_score FLOAT NOT NULL,
    action_cost     FLOAT NOT NULL,
    success         BOOLEAN NOT NULL,
    consciousness_delta FLOAT,
    heat_delta      FLOAT,
    details         JSONB
)
"""

# ─── Layer 2: Simulation State ──────────────────────────────────────

NODE_STATE_DDL = """
CREATE TABLE IF NOT EXISTS node_state (
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    node_id         VARCHAR(64) NOT NULL,
    node_type       VARCHAR(16) NOT NULL,
    attributes      JSONB NOT NULL DEFAULT '{}'::jsonb,
    wealth          NUMERIC,
    consciousness   FLOAT,
    organization_level FLOAT,
    class_position  VARCHAR(32),
    population      INTEGER,
    profit_rate     FLOAT,
    sector_type     VARCHAR(32),
    org_type        VARCHAR(32),
    class_character VARCHAR(32),
    cohesion        FLOAT,
    legal_standing  VARCHAR(16),
    is_institution  BOOLEAN,
    PRIMARY KEY (session_id, tick, node_id)
)
"""

EDGE_STATE_DDL = """
CREATE TABLE IF NOT EXISTS edge_state (
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    source_id       VARCHAR(64) NOT NULL,
    target_id       VARCHAR(64) NOT NULL,
    edge_type       VARCHAR(32) NOT NULL,
    edge_mode       VARCHAR(16),
    attributes      JSONB NOT NULL DEFAULT '{}'::jsonb,
    value_flow      NUMERIC,
    tension         FLOAT,
    solidarity_strength FLOAT,
    weight          FLOAT,
    PRIMARY KEY (session_id, tick, source_id, target_id, edge_type)
)
"""

GRAPH_METADATA_DDL = """
CREATE TABLE IF NOT EXISTS graph_metadata (
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    economy         JSONB NOT NULL DEFAULT '{}'::jsonb,
    state_finances  JSONB NOT NULL DEFAULT '{}'::jsonb,
    tick_dynamics   JSONB,
    extra           JSONB,
    PRIMARY KEY (session_id, tick)
)
"""

COMMUNITY_STATE_DDL = """
CREATE TABLE IF NOT EXISTS community_state (
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    community_type  VARCHAR(32) NOT NULL,
    category        VARCHAR(32) NOT NULL,
    heat            FLOAT NOT NULL DEFAULT 0.0,
    cohesion        FLOAT NOT NULL DEFAULT 0.0,
    infrastructure  FLOAT NOT NULL DEFAULT 0.0,
    visibility      FLOAT NOT NULL DEFAULT 0.0,
    legal_status    VARCHAR(32) NOT NULL DEFAULT 'LEGAL',
    reproduction_cost_modifier FLOAT NOT NULL DEFAULT 1.0,
    rent_access_modifier FLOAT NOT NULL DEFAULT 1.0,
    r               FLOAT NOT NULL DEFAULT 0.3,
    l               FLOAT NOT NULL DEFAULT 0.6,
    f               FLOAT NOT NULL DEFAULT 0.1,
    collective_identity FLOAT NOT NULL DEFAULT 0.0,
    dominant_tendency VARCHAR(32) NOT NULL DEFAULT 'NEUTRAL',
    ideological_contestation FLOAT NOT NULL DEFAULT 0.0,
    infiltration_resistance FLOAT,
    PRIMARY KEY (session_id, tick, community_type)
)
"""

COMMUNITY_MEMBERSHIP_DDL = """
CREATE TABLE IF NOT EXISTS community_membership (
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    agent_id        VARCHAR(64) NOT NULL,
    community_type  VARCHAR(32) NOT NULL,
    role            VARCHAR(32) NOT NULL DEFAULT 'MEMBER',
    strength        FLOAT NOT NULL DEFAULT 1.0,
    visibility      FLOAT NOT NULL DEFAULT 0.0,
    overt           BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (session_id, tick, agent_id, community_type)
)
"""

CONTRADICTION_FIELD_DDL = """
CREATE TABLE IF NOT EXISTS contradiction_field (
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    node_id         VARCHAR(64) NOT NULL,
    field_name      VARCHAR(32) NOT NULL,
    value           FLOAT NOT NULL,
    laplacian       FLOAT,
    dt              FLOAT,
    d2t             FLOAT,
    PRIMARY KEY (session_id, tick, node_id, field_name)
)
"""

EDGE_CURVATURE_DDL = """
CREATE TABLE IF NOT EXISTS edge_curvature (
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    source_id       VARCHAR(64) NOT NULL,
    target_id       VARCHAR(64) NOT NULL,
    curvature       FLOAT NOT NULL,
    gradient        JSONB,
    PRIMARY KEY (session_id, tick, source_id, target_id)
)
"""

SIMULATION_EVENT_DDL = """
CREATE TABLE IF NOT EXISTS simulation_event (
    id              BIGSERIAL PRIMARY KEY,
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    event_type      VARCHAR(48) NOT NULL,
    entity_id       VARCHAR(64),
    community_type  VARCHAR(32),
    details         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

TICK_LOG_DDL = """
CREATE TABLE IF NOT EXISTS tick_log (
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    rng_state       BYTEA,
    mutations_json  JSONB,
    invariant_checks JSONB,
    system_timings  JSONB,
    wall_time_ms    INTEGER,
    PRIMARY KEY (session_id, tick)
)
"""

TICK_SUMMARY_DDL = """
CREATE TABLE IF NOT EXISTS tick_summary (
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    year            INTEGER,
    total_c         NUMERIC,
    total_v         NUMERIC,
    total_s         NUMERIC,
    exploitation_rate FLOAT,
    profit_rate     FLOAT,
    imperial_rent   FLOAT,
    avg_consciousness FLOAT,
    solidarity_edge_count INTEGER,
    antagonistic_edge_count INTEGER,
    co_optive_edge_count INTEGER,
    org_count       INTEGER,
    player_org_count INTEGER,
    uprising_count  INTEGER,
    repression_count INTEGER,
    conservation_check BOOLEAN,
    PRIMARY KEY (session_id, tick)
)
"""

# ─── Layer 3: Spatial (PostGIS) ─────────────────────────────────────

HEX_CELL_DDL = """
CREATE TABLE IF NOT EXISTS hex_cell (
    h3_index        VARCHAR(15) PRIMARY KEY,
    county_fips     VARCHAR(5) NOT NULL,
    county_name     VARCHAR(100),
    bea_ea_code     VARCHAR(8),
    msa_code        VARCHAR(10),
    state_fips      VARCHAR(2) NOT NULL DEFAULT '26',
    res6_parent     VARCHAR(15) NOT NULL,
    res5_parent     VARCHAR(15) NOT NULL,
    geometry        geometry(Polygon, 4326) NOT NULL,
    centroid        geometry(Point, 4326) NOT NULL
)
"""

HEX_STATE_DDL = """
CREATE TABLE IF NOT EXISTS hex_state (
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    h3_index        VARCHAR(15) NOT NULL REFERENCES hex_cell(h3_index),
    constant_capital NUMERIC NOT NULL DEFAULT 0,
    variable_capital NUMERIC NOT NULL DEFAULT 0,
    surplus_value   NUMERIC NOT NULL DEFAULT 0,
    employment      FLOAT NOT NULL DEFAULT 0,
    dept_shares     FLOAT[4] NOT NULL DEFAULT '{0,0,0,0}',
    profit_rate     FLOAT NOT NULL DEFAULT 0,
    exploitation_rate FLOAT NOT NULL DEFAULT 0,
    PRIMARY KEY (session_id, tick, h3_index)
)
"""

HEX_TERRAIN_STATE_DDL = """
CREATE TABLE IF NOT EXISTS hex_terrain_state (
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    h3_index        VARCHAR(15) NOT NULL REFERENCES hex_cell(h3_index),
    terrain_type    VARCHAR(16) NOT NULL DEFAULT 'LAND',
    water_coverage  FLOAT NOT NULL DEFAULT 0.0,
    resource_coverage FLOAT NOT NULL DEFAULT 0.0,
    biocapacity_stocks JSONB NOT NULL DEFAULT '{}'::jsonb,
    internet_access BOOLEAN NOT NULL DEFAULT FALSE,
    internet_quality FLOAT NOT NULL DEFAULT 0.0,
    surveillance_coupling FLOAT NOT NULL DEFAULT 0.0,
    response_mode   VARCHAR(16) NOT NULL DEFAULT 'PERMIT',
    PRIMARY KEY (session_id, tick, h3_index)
)
"""

# ─── Layer 3b: R8 Geographic Substrate (Reference Data) ────────────

HEX_R8_REFERENCE_DDL = """
CREATE TABLE IF NOT EXISTS hex_r8_reference (
    h3_index        VARCHAR(17) PRIMARY KEY,
    parent_h3       VARCHAR(15) NOT NULL REFERENCES hex_cell(h3_index),
    county_fips     VARCHAR(5) NOT NULL,
    terrain_type    VARCHAR(16) NOT NULL DEFAULT 'LAND',
    water_fraction  FLOAT NOT NULL DEFAULT 0.0,
    elevation_m     FLOAT,
    has_water_service BOOLEAN NOT NULL DEFAULT TRUE,
    has_sewer       BOOLEAN NOT NULL DEFAULT TRUE,
    has_electric    BOOLEAN NOT NULL DEFAULT TRUE,
    has_gas         BOOLEAN NOT NULL DEFAULT TRUE,
    has_broadband   BOOLEAN NOT NULL DEFAULT TRUE
)
"""

HEX_R8_LINEAR_FEATURES_REFERENCE_DDL = """
CREATE TABLE IF NOT EXISTS hex_r8_linear_features_reference (
    id              BIGSERIAL PRIMARY KEY,
    h3_index        VARCHAR(17) NOT NULL REFERENCES hex_r8_reference(h3_index),
    feature_type    VARCHAR(32) NOT NULL,
    feature_name    VARCHAR(128),
    source_dataset  VARCHAR(64) NOT NULL,
    source_feature_id VARCHAR(64)
)
"""

# ─── Layer 4: Infrastructure ────────────────────────────────────────

INFRASTRUCTURE_LINK_STATE_DDL = """
CREATE TABLE IF NOT EXISTS infrastructure_link_state (
    session_id      UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick            INTEGER NOT NULL,
    source_h3       VARCHAR(15) NOT NULL,
    target_h3       VARCHAR(15) NOT NULL,
    link_id         VARCHAR(128) NOT NULL,
    infra_type      VARCHAR(32) NOT NULL,
    capacity        JSONB NOT NULL DEFAULT '{}'::jsonb,
    condition       FLOAT NOT NULL DEFAULT 1.0,
    owner_org_id    VARCHAR(64),
    PRIMARY KEY (session_id, tick, link_id)
)
"""

# ─── Layer 6: Semantic Search (pgvector) ────────────────────────────

DOCUMENT_CHUNK_DDL = """
CREATE TABLE IF NOT EXISTS document_chunk (
    chunk_id        VARCHAR(128) PRIMARY KEY,
    collection      VARCHAR(64) NOT NULL DEFAULT 'default',
    content         TEXT NOT NULL,
    embedding       vector(768) NOT NULL,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    source          VARCHAR(256),
    chunk_index     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

# ─── Indexes ────────────────────────────────────────────────────────

INDEXES_DDL: list[str] = [
    # Game Management
    "CREATE INDEX IF NOT EXISTS idx_game_session_player_status ON game_session(player_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_game_turn_session_tick ON game_turn(session_id, tick)",
    "CREATE INDEX IF NOT EXISTS idx_action_result_session_tick ON action_result(session_id, tick)",
    "CREATE INDEX IF NOT EXISTS idx_action_result_session_org ON action_result(session_id, org_id)",
    # Simulation State - node_state
    "CREATE INDEX IF NOT EXISTS idx_node_state_session_tick ON node_state(session_id, tick)",
    "CREATE INDEX IF NOT EXISTS idx_node_state_session_node ON node_state(session_id, node_id)",
    (
        "CREATE INDEX IF NOT EXISTS idx_node_state_session_tick_type "
        "ON node_state(session_id, tick, node_type)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_node_state_org_type "
        "ON node_state(session_id, tick, org_type) "
        "WHERE node_type = 'organization'"
    ),
    # Simulation State - edge_state
    "CREATE INDEX IF NOT EXISTS idx_edge_state_session_tick ON edge_state(session_id, tick)",
    (
        "CREATE INDEX IF NOT EXISTS idx_edge_state_session_tick_mode "
        "ON edge_state(session_id, tick, edge_mode)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_edge_state_session_tick_type "
        "ON edge_state(session_id, tick, edge_type)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_edge_state_session_tick_source "
        "ON edge_state(session_id, tick, source_id)"
    ),
    # Community
    (
        "CREATE INDEX IF NOT EXISTS idx_community_membership_type "
        "ON community_membership(session_id, tick, community_type)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_community_membership_agent "
        "ON community_membership(session_id, tick, agent_id)"
    ),
    # Events
    (
        "CREATE INDEX IF NOT EXISTS idx_simulation_event_session_tick "
        "ON simulation_event(session_id, tick)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_simulation_event_session_type "
        "ON simulation_event(session_id, event_type)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_simulation_event_community "
        "ON simulation_event(session_id, community_type) "
        "WHERE community_type IS NOT NULL"
    ),
    # Spatial
    "CREATE INDEX IF NOT EXISTS idx_hex_cell_county ON hex_cell(county_fips)",
    "CREATE INDEX IF NOT EXISTS idx_hex_cell_bea_ea ON hex_cell(bea_ea_code)",
    "CREATE INDEX IF NOT EXISTS idx_hex_cell_msa ON hex_cell(msa_code)",
    "CREATE INDEX IF NOT EXISTS idx_hex_cell_state ON hex_cell(state_fips)",
    "CREATE INDEX IF NOT EXISTS idx_hex_cell_geom ON hex_cell USING GIST (geometry)",
    "CREATE INDEX IF NOT EXISTS idx_hex_state_session_tick ON hex_state(session_id, tick)",
    "CREATE INDEX IF NOT EXISTS idx_hex_state_session_h3 ON hex_state(session_id, h3_index)",
    (
        "CREATE INDEX IF NOT EXISTS idx_hex_terrain_session_tick "
        "ON hex_terrain_state(session_id, tick)"
    ),
    # Infrastructure
    (
        "CREATE INDEX IF NOT EXISTS idx_infra_link_session_tick "
        "ON infrastructure_link_state(session_id, tick)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_infra_link_session_h3 "
        "ON infrastructure_link_state(session_id, tick, source_h3, target_h3)"
    ),
    # Semantic search
    (
        "CREATE INDEX IF NOT EXISTS idx_document_chunk_embedding "
        "ON document_chunk USING hnsw (embedding vector_cosine_ops)"
    ),
    "CREATE INDEX IF NOT EXISTS idx_document_chunk_collection ON document_chunk(collection)",
    # R8 Reference
    "CREATE INDEX IF NOT EXISTS idx_r8_ref_parent ON hex_r8_reference(parent_h3)",
    "CREATE INDEX IF NOT EXISTS idx_r8_ref_county ON hex_r8_reference(county_fips)",
    ("CREATE INDEX IF NOT EXISTS idx_r8_linear_h3 ON hex_r8_linear_features_reference(h3_index)"),
    (
        "CREATE INDEX IF NOT EXISTS idx_r8_linear_type "
        "ON hex_r8_linear_features_reference(feature_type)"
    ),
]

# ═══════════════════════════════════════════════════════════════════════
# Spec 037: Game-Journal Schema (append-only, tick-keyed snapshots)
# ═══════════════════════════════════════════════════════════════════════

# ─── Layer 7: Domain (Static, written once at game init) ────────────

HEX_MAP_DDL = """
CREATE TABLE IF NOT EXISTS hex_map (
    game_id       UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    h3_index      VARCHAR(16) NOT NULL,
    county_fips   VARCHAR(5) NOT NULL,
    county_name   VARCHAR(64) NOT NULL,
    state_fips    VARCHAR(2) NOT NULL,
    h3_resolution SMALLINT NOT NULL DEFAULT 7,
    center_lat    DOUBLE PRECISION NOT NULL,
    center_lng    DOUBLE PRECISION NOT NULL,
    geom          geometry(Polygon, 4326),

    PRIMARY KEY (game_id, h3_index)
)
"""

GAME_DEFINES_SNAPSHOT_DDL = """
CREATE TABLE IF NOT EXISTS game_defines_snapshot (
    game_id     UUID PRIMARY KEY REFERENCES game_session(id) ON DELETE CASCADE,
    defines     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

# ─── Layer 8: Snapshot (per-tick, append-only) ──────────────────────

TERRITORY_SNAPSHOT_DDL = """
CREATE TABLE IF NOT EXISTS territory_snapshot (
    game_id       UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick          INTEGER NOT NULL,
    county_fips   VARCHAR(5) NOT NULL,

    -- ValueTensor4x3: Departments I/IIa/IIb/III × c/v/s
    c_dept_i      NUMERIC,
    v_dept_i      NUMERIC,
    s_dept_i      NUMERIC,
    c_dept_iia    NUMERIC,
    v_dept_iia    NUMERIC,
    s_dept_iia    NUMERIC,
    c_dept_iib    NUMERIC,
    v_dept_iib    NUMERIC,
    s_dept_iib    NUMERIC,
    c_dept_iii    NUMERIC,
    v_dept_iii    NUMERIC,
    s_dept_iii    NUMERIC,

    -- Derived indicators
    profit_rate        FLOAT,
    exploitation_rate  FLOAT,
    occ                FLOAT,
    imperial_rent      NUMERIC,
    g33_visibility     FLOAT,

    -- Class distribution (Spec 033)
    pop_bourgeoisie         INTEGER,
    pop_petit_bourgeoisie   INTEGER,
    pop_labor_aristocracy   INTEGER,
    pop_proletariat         INTEGER,
    pop_lumpenproletariat   INTEGER,
    pop_total               INTEGER,

    -- Faction balance
    faction_finance_capital   FLOAT,
    faction_security_state    FLOAT,
    faction_settler_populist  FLOAT,

    -- Aggregate heat
    heat              FLOAT DEFAULT 0.0,

    -- Full state dump
    attributes        JSONB NOT NULL,

    PRIMARY KEY (game_id, tick, county_fips),
    CONSTRAINT ck_territory_tick_positive CHECK (tick >= 0),
    CONSTRAINT ck_territory_pop_nonneg CHECK (
        pop_total >= 0 AND pop_bourgeoisie >= 0 AND pop_proletariat >= 0
    )
)
"""

ORG_SNAPSHOT_DDL = """
CREATE TABLE IF NOT EXISTS org_snapshot (
    game_id       UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick          INTEGER NOT NULL,
    org_id        VARCHAR(64) NOT NULL,

    -- Type discrimination
    org_type      VARCHAR(24) NOT NULL,

    -- Spatial presence
    home_county   VARCHAR(5),
    home_hex      VARCHAR(16),

    -- OODA state (Spec 032)
    ooda_phase         VARCHAR(8),
    action_points      INTEGER,
    action_points_max  INTEGER,

    -- Resources
    cadre_count        INTEGER DEFAULT 0,
    sympathizer_count  INTEGER DEFAULT 0,
    cadre_labor        FLOAT DEFAULT 0.0,
    sympathizer_labor  FLOAT DEFAULT 0.0,
    material_resources FLOAT DEFAULT 0.0,

    -- Organizational health
    coherence       FLOAT,
    reputation      FLOAT,
    opsec           FLOAT,

    -- Ownership / control
    owner_type      VARCHAR(16),
    owner_id        VARCHAR(64),

    -- Full state dump
    attributes      JSONB NOT NULL,

    PRIMARY KEY (game_id, tick, org_id),
    CONSTRAINT ck_org_tick_positive CHECK (tick >= 0),
    CONSTRAINT ck_org_type_valid CHECK (
        org_type IN ('state_apparatus', 'business', 'political_faction', 'civil_society')
    )
)
"""

EDGE_SNAPSHOT_DDL = """
CREATE TABLE IF NOT EXISTS edge_snapshot (
    game_id       UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick          INTEGER NOT NULL,
    source_id     VARCHAR(64) NOT NULL,
    target_id     VARCHAR(64) NOT NULL,
    edge_type     VARCHAR(32) NOT NULL,

    -- Constitutional edge mode
    edge_mode     VARCHAR(16),

    -- Promoted flow values
    value_flow        NUMERIC,
    solidarity        FLOAT,
    tension           FLOAT,

    -- Full state dump
    attributes        JSONB NOT NULL,

    PRIMARY KEY (game_id, tick, source_id, target_id, edge_type),
    CONSTRAINT ck_edge_tick_positive CHECK (tick >= 0),
    CONSTRAINT ck_edge_mode_valid CHECK (
        edge_mode IN (
            'EXTRACTIVE', 'TRANSACTIONAL', 'SOLIDARISTIC',
            'ANTAGONISTIC', 'CO_OPTIVE'
        ) OR edge_mode IS NULL
    )
)
"""

COMMUNITY_SNAPSHOT_DDL = """
CREATE TABLE IF NOT EXISTS community_snapshot (
    game_id           UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick              INTEGER NOT NULL,
    community_id      VARCHAR(64) NOT NULL,

    -- Community taxonomy (Spec 029)
    community_type    VARCHAR(32) NOT NULL,
    hyperedge_category VARCHAR(24) NOT NULL,
    contradiction_axis VARCHAR(24),

    -- Territory scope
    county_fips       VARCHAR(5),

    -- Consciousness state
    collective_identity       FLOAT,
    ideological_contestation  FLOAT,
    dominant_tendency         VARCHAR(28),

    -- Material basis
    reproduction_cost_modifier FLOAT,
    rent_access_modifier       FLOAT,

    -- Membership count
    member_count      INTEGER,

    -- Full state dump
    attributes        JSONB NOT NULL,

    PRIMARY KEY (game_id, tick, community_id),
    CONSTRAINT ck_community_tick_positive CHECK (tick >= 0),
    CONSTRAINT ck_tendency_valid CHECK (
        dominant_tendency IN (
            'revolutionary', 'assimilationist_liberal', 'assimilationist_fascist'
        )
    ),
    CONSTRAINT ck_category_valid CHECK (
        hyperedge_category IN (
            'contradiction_pair', 'institutional_exclusion', 'lifecycle_phase'
        )
    )
)
"""

HEX_ACTIVITY_DDL = """
CREATE TABLE IF NOT EXISTS hex_activity (
    game_id       UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick          INTEGER NOT NULL,
    h3_index      VARCHAR(16) NOT NULL,

    -- Heat from player/state actions
    heat_delta    FLOAT DEFAULT 0.0,
    heat_total    FLOAT DEFAULT 0.0,

    -- Org presence
    org_ids       VARCHAR(64)[] DEFAULT '{}',
    org_count     SMALLINT DEFAULT 0,

    -- Action summary
    actions_taken SMALLINT DEFAULT 0,
    was_target    BOOLEAN DEFAULT FALSE,

    -- Full details
    attributes    JSONB,

    PRIMARY KEY (game_id, tick, h3_index)
)
"""

ECONOMIC_SUMMARY_DDL = """
CREATE TABLE IF NOT EXISTS economic_summary (
    game_id       UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick          INTEGER NOT NULL,

    -- Aggregate economic indicators
    avg_profit_rate        FLOAT,
    avg_exploitation_rate  FLOAT,
    avg_occ                FLOAT,
    total_imperial_rent    NUMERIC,
    avg_g33_visibility     FLOAT,

    -- Class totals
    total_bourgeoisie        INTEGER,
    total_petit_bourgeoisie  INTEGER,
    total_labor_aristocracy  INTEGER,
    total_proletariat        INTEGER,
    total_lumpenproletariat  INTEGER,
    total_population         INTEGER,

    -- Aggregate faction balance
    avg_faction_finance      FLOAT,
    avg_faction_security     FLOAT,
    avg_faction_settler      FLOAT,

    -- Game-level indicators
    total_heat              FLOAT,
    total_orgs              INTEGER,
    total_player_orgs       INTEGER,
    total_solidaristic_edges INTEGER,
    total_antagonistic_edges INTEGER,

    -- Bifurcation indicators
    percolation_ratio       FLOAT,
    fascist_convergence     BOOLEAN DEFAULT FALSE,

    -- Narrative
    narrative_text          TEXT,

    attributes              JSONB,

    PRIMARY KEY (game_id, tick)
)
"""

TICK_EVENT_DDL = """
CREATE TABLE IF NOT EXISTS tick_event (
    game_id       UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick          INTEGER NOT NULL,
    event_id      SERIAL,
    event_type    VARCHAR(48) NOT NULL,
    -- Widened 12->32 (spec-092 review Defect A / spec-061 T047): the
    -- serialization boundary's default severity string "informational"
    -- is 13 chars and overflowed VARCHAR(12), silently dropping every
    -- tick_event row for any tick containing an unmapped-severity event.
    -- See migrations/0032_widen_tick_event_severity.sql for the existing-DB
    -- migration path.
    severity      VARCHAR(32),
    source_id     VARCHAR(64),
    target_id     VARCHAR(64),
    county_fips   VARCHAR(5),
    h3_index      VARCHAR(16),

    -- Human-readable
    summary       TEXT NOT NULL,
    detail        JSONB,

    PRIMARY KEY (game_id, tick, event_id)
)
"""

# ─── Layer 8b: Multi-Resolution Hex Cache ───────────────────────────
#
# hex_latest: R7 denormalized current-state cache (frontend reads HERE).
# hex_substrate: R8 static terrain/infrastructure (written once at init).
#
# County economics live in territory_snapshot (~3,100 rows/tick).
# Hex-specific events live in hex_activity (sparse, ~5K rows/tick).
# hex_latest merges both via two-phase SQL UPSERT each tick.

HEX_LATEST_DDL = """
CREATE TABLE IF NOT EXISTS hex_latest (
    game_id       UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    h3_index      VARCHAR(16) NOT NULL,

    -- Which tick this row reflects
    tick          INTEGER NOT NULL,

    -- ─── Denormalized county economics (from territory_snapshot) ───
    county_fips   VARCHAR(5)  NOT NULL,
    county_name   VARCHAR(100) NOT NULL,
    bea_ea_code   VARCHAR(8),
    msa_code      VARCHAR(10),
    state_fips    VARCHAR(2)  NOT NULL DEFAULT '26',
    center_lat    DOUBLE PRECISION NOT NULL,
    center_lng    DOUBLE PRECISION NOT NULL,

    -- ValueTensor4x3 (from territory_snapshot)
    c_dept_i      NUMERIC,  v_dept_i      NUMERIC,  s_dept_i      NUMERIC,
    c_dept_iia    NUMERIC,  v_dept_iia    NUMERIC,  s_dept_iia    NUMERIC,
    c_dept_iib    NUMERIC,  v_dept_iib    NUMERIC,  s_dept_iib    NUMERIC,
    c_dept_iii    NUMERIC,  v_dept_iii    NUMERIC,  s_dept_iii    NUMERIC,

    -- Derived Marxian indicators (from territory_snapshot)
    profit_rate        FLOAT,
    exploitation_rate  FLOAT,
    occ                FLOAT,
    imperial_rent      NUMERIC,
    g33_visibility     FLOAT,

    -- Class distribution (from territory_snapshot)
    pop_bourgeoisie         INTEGER DEFAULT 0,
    pop_petit_bourgeoisie   INTEGER DEFAULT 0,
    pop_labor_aristocracy   INTEGER DEFAULT 0,
    pop_proletariat         INTEGER DEFAULT 0,
    pop_lumpenproletariat   INTEGER DEFAULT 0,
    pop_total               INTEGER DEFAULT 0,
    dominant_class          VARCHAR(24),

    -- Faction balance (from territory_snapshot)
    faction_finance_capital   FLOAT,
    faction_security_state    FLOAT,
    faction_settler_populist  FLOAT,

    -- ─── Hex-specific fields (from hex_activity) ───
    heat              FLOAT DEFAULT 0.0,
    heat_delta        FLOAT DEFAULT 0.0,
    org_ids           VARCHAR(64)[] DEFAULT '{}',
    org_count         SMALLINT DEFAULT 0,
    actions_taken     SMALLINT DEFAULT 0,
    was_target        BOOLEAN DEFAULT FALSE,

    -- ─── Aggregated R8 terrain (from hex_substrate) ───
    terrain_type      VARCHAR(16) DEFAULT 'LAND',
    water_coverage    FLOAT DEFAULT 0.0,
    internet_access   BOOLEAN DEFAULT FALSE,

    -- ─── Forward-compat ───
    attributes        JSONB DEFAULT '{}'::jsonb,

    PRIMARY KEY (game_id, h3_index)
)
"""

HEX_SUBSTRATE_DDL = """
CREATE TABLE IF NOT EXISTS hex_substrate (
    game_id           UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    h3_index          VARCHAR(16) NOT NULL,       -- R8 hex
    r7_parent         VARCHAR(16) NOT NULL,       -- R7 parent for aggregation
    county_fips       VARCHAR(5)  NOT NULL,

    -- Physical geography
    terrain_type      VARCHAR(16) NOT NULL DEFAULT 'LAND',
    water_coverage    FLOAT NOT NULL DEFAULT 0.0,
    resource_coverage FLOAT NOT NULL DEFAULT 0.0,
    elevation_m       FLOAT,

    -- Digital infrastructure
    internet_access   BOOLEAN NOT NULL DEFAULT FALSE,
    internet_quality  FLOAT NOT NULL DEFAULT 0.0,
    broadband_pct     FLOAT,

    -- Biocapacity
    biocapacity_stocks JSONB DEFAULT '{}'::jsonb,

    -- Coercive infrastructure
    surveillance_coupling FLOAT NOT NULL DEFAULT 0.0,
    response_mode         VARCHAR(16) NOT NULL DEFAULT 'PERMIT',

    PRIMARY KEY (game_id, h3_index)
)
"""

# ─── Layer 9: Composition Views (project from hex_latest) ───────────
#
# These are trivial column projections — no JOINs needed because
# hex_latest is already denormalized. The frontend reads these.

V_HEX_ECONOMIC_DDL = """
CREATE OR REPLACE VIEW v_hex_economic AS
SELECT game_id, tick, h3_index, center_lat, center_lng,
       county_fips, county_name,
       profit_rate, exploitation_rate, occ, imperial_rent,
       g33_visibility, pop_total, heat
FROM hex_latest
"""

V_HEX_MOBILIZE_DDL = """
CREATE OR REPLACE VIEW v_hex_mobilize AS
SELECT game_id, tick, h3_index, center_lat, center_lng,
       county_fips,
       pop_proletariat + pop_lumpenproletariat AS mobilizable_pop,
       pop_labor_aristocracy, heat,
       org_count AS org_presence, heat_delta AS hex_heat,
       org_ids
FROM hex_latest
"""

V_HEX_AID_DDL = """
CREATE OR REPLACE VIEW v_hex_aid AS
SELECT game_id, tick, h3_index, center_lat, center_lng,
       county_fips,
       pop_lumpenproletariat, pop_proletariat,
       imperial_rent, g33_visibility,
       attributes->'reproduction_deficit' AS reproduction_deficit
FROM hex_latest
"""

V_HEX_HEAT_DDL = """
CREATE OR REPLACE VIEW v_hex_heat AS
SELECT game_id, tick, h3_index, center_lat, center_lng,
       heat AS heat_total, heat_delta,
       org_count, was_target
FROM hex_latest
WHERE heat > 0
"""

V_HEX_INTEL_DDL = """
CREATE OR REPLACE VIEW v_hex_intel AS
SELECT game_id, tick, h3_index, center_lat, center_lng,
       county_fips, county_name,
       profit_rate, exploitation_rate, occ, imperial_rent,
       g33_visibility,
       pop_bourgeoisie, pop_petit_bourgeoisie,
       pop_labor_aristocracy, pop_proletariat,
       pop_lumpenproletariat, pop_total,
       heat,
       faction_finance_capital, faction_security_state,
       faction_settler_populist,
       org_ids, org_count,
       heat AS hex_heat
FROM hex_latest
"""

# ─── Spec 037 Indexes ──────────────────────────────────────────────

SPEC037_INDEXES_DDL: list[str] = [
    # hex_map
    "CREATE INDEX IF NOT EXISTS ix_hex_map_county ON hex_map (game_id, county_fips)",
    "CREATE INDEX IF NOT EXISTS ix_hex_map_geom ON hex_map USING GIST (geom)",
    # territory_snapshot
    "CREATE INDEX IF NOT EXISTS ix_territory_tick ON territory_snapshot (game_id, tick)",
    (
        "CREATE INDEX IF NOT EXISTS ix_territory_series "
        "ON territory_snapshot (game_id, county_fips, tick)"
    ),
    # org_snapshot
    "CREATE INDEX IF NOT EXISTS ix_org_tick ON org_snapshot (game_id, tick)",
    "CREATE INDEX IF NOT EXISTS ix_org_owner ON org_snapshot (game_id, tick, owner_type)",
    "CREATE INDEX IF NOT EXISTS ix_org_county ON org_snapshot (game_id, tick, home_county)",
    "CREATE INDEX IF NOT EXISTS ix_org_series ON org_snapshot (game_id, org_id, tick)",
    # edge_snapshot
    "CREATE INDEX IF NOT EXISTS ix_edge_snap_tick ON edge_snapshot (game_id, tick)",
    "CREATE INDEX IF NOT EXISTS ix_edge_snap_mode ON edge_snapshot (game_id, tick, edge_mode)",
    "CREATE INDEX IF NOT EXISTS ix_edge_snap_source ON edge_snapshot (game_id, tick, source_id)",
    (
        "CREATE INDEX IF NOT EXISTS ix_edge_snap_series "
        "ON edge_snapshot (game_id, source_id, target_id, edge_type, tick)"
    ),
    # community_snapshot
    ("CREATE INDEX IF NOT EXISTS ix_community_snap_tick ON community_snapshot (game_id, tick)"),
    (
        "CREATE INDEX IF NOT EXISTS ix_community_snap_type "
        "ON community_snapshot (game_id, tick, community_type)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS ix_community_snap_county "
        "ON community_snapshot (game_id, tick, county_fips)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS ix_community_snap_series "
        "ON community_snapshot (game_id, community_id, tick)"
    ),
    # hex_activity
    "CREATE INDEX IF NOT EXISTS ix_hex_activity_tick ON hex_activity (game_id, tick)",
    (
        "CREATE INDEX IF NOT EXISTS ix_hex_activity_hot "
        "ON hex_activity (game_id, tick, heat_total) WHERE heat_total > 0"
    ),
    # hex_latest (current-state cache — primary frontend read table)
    "CREATE INDEX IF NOT EXISTS ix_hex_latest_county ON hex_latest (game_id, county_fips)",
    ("CREATE INDEX IF NOT EXISTS ix_hex_latest_hot ON hex_latest (game_id, heat) WHERE heat > 0"),
    # hex_substrate (R8 static terrain)
    "CREATE INDEX IF NOT EXISTS ix_hex_substrate_r7 ON hex_substrate (game_id, r7_parent)",
    ("CREATE INDEX IF NOT EXISTS ix_hex_substrate_county ON hex_substrate (game_id, county_fips)"),
    # tick_event
    "CREATE INDEX IF NOT EXISTS ix_event_tick ON tick_event (game_id, tick)",
    "CREATE INDEX IF NOT EXISTS ix_event_type ON tick_event (game_id, tick, event_type)",
    "CREATE INDEX IF NOT EXISTS ix_event_source ON tick_event (game_id, source_id)",
]

# ─── Aggregated DDL list ────────────────────────────────────────────

POSTGRES_SCHEMA_DDL: list[str] = [
    *EXTENSIONS_DDL,
    # Layer 1: Game Management
    GAME_SESSION_DDL,
    GAME_TURN_DDL,
    ACTION_RESULT_DDL,
    # Layer 2: Simulation State
    NODE_STATE_DDL,
    EDGE_STATE_DDL,
    GRAPH_METADATA_DDL,
    COMMUNITY_STATE_DDL,
    COMMUNITY_MEMBERSHIP_DDL,
    CONTRADICTION_FIELD_DDL,
    EDGE_CURVATURE_DDL,
    SIMULATION_EVENT_DDL,
    TICK_LOG_DDL,
    TICK_SUMMARY_DDL,
    # Layer 3: Spatial
    HEX_CELL_DDL,
    HEX_STATE_DDL,
    HEX_TERRAIN_STATE_DDL,
    # Layer 3b: R8 Geographic Substrate (Reference Data)
    HEX_R8_REFERENCE_DDL,
    HEX_R8_LINEAR_FEATURES_REFERENCE_DDL,
    # Layer 4: Infrastructure
    INFRASTRUCTURE_LINK_STATE_DDL,
    # Layer 6: Semantic
    DOCUMENT_CHUNK_DDL,
    # Layer 7: Spec 037 Domain (static)
    HEX_MAP_DDL,
    GAME_DEFINES_SNAPSHOT_DDL,
    # Layer 8: Spec 037 Snapshots (per-tick, append-only)
    TERRITORY_SNAPSHOT_DDL,
    ORG_SNAPSHOT_DDL,
    EDGE_SNAPSHOT_DDL,
    COMMUNITY_SNAPSHOT_DDL,
    HEX_ACTIVITY_DDL,
    ECONOMIC_SUMMARY_DDL,
    TICK_EVENT_DDL,
    # Layer 8b: Multi-Resolution Hex Cache
    HEX_LATEST_DDL,
    HEX_SUBSTRATE_DDL,
    # Layer 9: Spec 037 Composition Views (project from hex_latest)
    V_HEX_ECONOMIC_DDL,
    V_HEX_MOBILIZE_DDL,
    V_HEX_AID_DDL,
    V_HEX_HEAT_DDL,
    V_HEX_INTEL_DDL,
    # Indexes (legacy + spec 037)
    *INDEXES_DDL,
    *SPEC037_INDEXES_DDL,
]


__all__ = [
    "INDEXES_DDL",
    "POSTGRES_SCHEMA_DDL",
    "SPEC037_INDEXES_DDL",
]
