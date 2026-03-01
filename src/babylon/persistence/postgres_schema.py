"""PostgreSQL schema DDL for simulation runtime state (Feature 037).

Defines 19 tables across 6 layers:

1. Game Management (3): game_session, game_turn, action_result
2. Simulation State (10): node_state, edge_state, graph_metadata,
   community_state, community_membership, contradiction_field,
   edge_curvature, simulation_event, tick_log, tick_summary
3. Spatial (3): hex_cell, hex_state, hex_terrain_state
4. Infrastructure (1): infrastructure_link_state
5. Trace (1): trace_log (UNLOGGED, partitioned by session_id)
6. Semantic (1): document_chunk (pgvector)

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

# ─── Layer 5: Trace Logging ─────────────────────────────────────────

TRACE_LOG_DDL = """
CREATE UNLOGGED TABLE IF NOT EXISTS trace_log (
    id              BIGSERIAL,
    session_id      UUID NOT NULL,
    tick            INTEGER NOT NULL,
    system_name     VARCHAR(48) NOT NULL,
    level           VARCHAR(8) NOT NULL,
    event           VARCHAR(48) NOT NULL,
    node_id         VARCHAR(64),
    data            JSONB NOT NULL DEFAULT '{}'::jsonb,
    ts              TIMESTAMPTZ NOT NULL DEFAULT now()
) PARTITION BY LIST (session_id)
"""

# ─── Layer 6: Semantic Search (pgvector) ────────────────────────────

DOCUMENT_CHUNK_DDL = """
CREATE TABLE IF NOT EXISTS document_chunk (
    id              VARCHAR(128) PRIMARY KEY,
    session_id      UUID REFERENCES game_session(id) ON DELETE SET NULL,
    source_file     VARCHAR(256) NOT NULL,
    chunk_index     INTEGER NOT NULL,
    content         TEXT NOT NULL,
    embedding       vector(768) NOT NULL,
    metadata        JSONB,
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
    "CREATE INDEX IF NOT EXISTS idx_document_chunk_session ON document_chunk(session_id)",
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
    # Layer 4: Infrastructure
    INFRASTRUCTURE_LINK_STATE_DDL,
    # Layer 5: Trace
    TRACE_LOG_DDL,
    # Layer 6: Semantic
    DOCUMENT_CHUNK_DDL,
    # Indexes
    *INDEXES_DDL,
]

# Partition management DDL templates

TRACE_PARTITION_CREATE_TEMPLATE = """
CREATE UNLOGGED TABLE IF NOT EXISTS trace_log_{session_hex}
    PARTITION OF trace_log
    FOR VALUES IN ('{session_id}')
"""

TRACE_PARTITION_DROP_TEMPLATE = """
DROP TABLE IF EXISTS trace_log_{session_hex}
"""


def get_trace_partition_name(session_id_hex: str) -> str:
    """Return the partition table name for a given session.

    Args:
        session_id_hex: Session UUID as hex string (no dashes).

    Returns:
        Partition table name like ``trace_log_abc123...``.
    """
    return f"trace_log_{session_id_hex}"


__all__ = [
    "INDEXES_DDL",
    "POSTGRES_SCHEMA_DDL",
    "TRACE_PARTITION_CREATE_TEMPLATE",
    "TRACE_PARTITION_DROP_TEMPLATE",
    "get_trace_partition_name",
]
