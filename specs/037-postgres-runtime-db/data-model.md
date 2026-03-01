# Data Model: Postgres Runtime Database

**Feature**: 037-postgres-runtime-db
**Date**: 2026-03-01

## Entity Catalog

19 entities organized into 6 layers: Game Management (3), Simulation State (10), Spatial (3), Infrastructure (1), Trace (1), Semantic (1).

## Layer 1: Game Management (Django ORM)

### game_session

Represents a single playthrough. Scopes all other entities via session_id FK.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| id | UUID | PK, default gen_random_uuid() | Generated |
| player_id | INTEGER | FK auth_user.id, NOT NULL | Django auth |
| scenario | VARCHAR(64) | NOT NULL | Scenario factory name (e.g., `detroit_tri_county`) |
| current_tick | INTEGER | NOT NULL, default 0 | Engine increments |
| status | VARCHAR(16) | NOT NULL, default 'active' | Lifecycle: active, paused, completed, abandoned, archived |
| config_json | JSONB | NOT NULL | `SimulationConfig.model_dump(mode="json")` |
| game_defines_json | JSONB | NOT NULL | `GameDefines.model_dump(mode="json")` |
| trace_level | VARCHAR(8) | NOT NULL, default 'NONE' | NONE, SUMMARY, DEBUG, TRACE |
| rng_seed | BIGINT | NOT NULL | For deterministic replay |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, auto-update | |

Indexes: `(player_id, status)`

### game_turn

Player action submission. One per organization per tick.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| id | BIGSERIAL | PK | |
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| org_id | VARCHAR(64) | NOT NULL | Acting organization |
| verb | VARCHAR(16) | NOT NULL | One of 9 player verbs (Constitution V) |
| action_type | VARCHAR(32) | | Resolved ActionType enum (Feature 032) |
| target_id | VARCHAR(64) | | Target node (nullable) |
| target_community | VARCHAR(32) | | Target CommunityType |
| params_json | JSONB | | Verb-specific parameters |
| submitted_at | TIMESTAMPTZ | NOT NULL, default now() | |
| resolved | BOOLEAN | NOT NULL, default FALSE | Set TRUE after tick execution |

Indexes: `(session_id, tick)`. Unique: `(session_id, tick, org_id)`.

### action_result

Resolution outcome of a player action (Feature 032 OODA).

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| id | BIGSERIAL | PK | |
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| org_id | VARCHAR(64) | NOT NULL | |
| action_type | VARCHAR(32) | NOT NULL | ActionType enum |
| target_id | VARCHAR(64) | | |
| target_community | VARCHAR(32) | | |
| initiative_score | FLOAT | NOT NULL | |
| action_cost | FLOAT | NOT NULL | Action points consumed |
| success | BOOLEAN | NOT NULL | |
| consciousness_delta | FLOAT | | CI change applied |
| heat_delta | FLOAT | | Heat change applied |
| details | JSONB | | Full resolution details |

Indexes: `(session_id, tick)`, `(session_id, org_id)`.

## Layer 2: Simulation State (psycopg raw SQL)

### node_state

Per-tick snapshot of each graph node. Covers all 4 `_node_type` values from `WorldState.to_graph()`.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| node_id | VARCHAR(64) | NOT NULL | |
| node_type | VARCHAR(16) | NOT NULL | social_class, territory, organization, key_figure |
| attributes | JSONB | NOT NULL | Full `model_dump()` |
| wealth | NUMERIC | | Promoted: SocialClass |
| consciousness | FLOAT | | Promoted: SocialClass (ideology.class_consciousness) |
| organization_level | FLOAT | | Promoted: SocialClass |
| class_position | VARCHAR(32) | | Promoted: SocialClass (ClassPosition enum) |
| population | INTEGER | | Promoted: Territory |
| profit_rate | FLOAT | | Promoted: Territory |
| sector_type | VARCHAR(32) | | Promoted: Territory (SectorType enum) |
| org_type | VARCHAR(32) | | Promoted: Organization (OrgType discriminator) |
| class_character | VARCHAR(32) | | Promoted: Organization |
| cohesion | FLOAT | | Promoted: Organization |
| legal_standing | VARCHAR(16) | | Promoted: Organization |
| is_institution | BOOLEAN | | Promoted: Organization |

PK: `(session_id, tick, node_id)`.
Indexes: `(session_id, tick)`, `(session_id, node_id)`, `(session_id, tick, node_type)`, partial on `(session_id, tick, org_type) WHERE node_type = 'organization'`, GIN on `attributes`.

### edge_state

Per-tick snapshot of each graph edge. Covers all EdgeType values.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| source_id | VARCHAR(64) | NOT NULL | |
| target_id | VARCHAR(64) | NOT NULL | |
| edge_type | VARCHAR(32) | NOT NULL | EdgeType enum value (VARCHAR for extensibility) |
| edge_mode | VARCHAR(16) | | EdgeMode enum (EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC) |
| attributes | JSONB | NOT NULL | Full edge data from `Relationship.edge_data` |
| value_flow | NUMERIC | | Promoted: economic flow edges |
| tension | FLOAT | | Promoted: contradiction edges |
| solidarity_strength | FLOAT | | Promoted: SOLIDARITY edges |
| weight | FLOAT | | Promoted: MEMBERSHIP edges (population count) |

PK: `(session_id, tick, source_id, target_id, edge_type)`.
Indexes: `(session_id, tick)`, `(session_id, tick, edge_mode)`, `(session_id, tick, edge_type)`, `(session_id, tick, source_id)`.

### graph_metadata

Per-tick graph-level data. Persists `G.graph` dict from `WorldState.to_graph()`.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| economy | JSONB | NOT NULL | `GlobalEconomy.model_dump()` |
| state_finances | JSONB | NOT NULL | `{state_id: StateFinance.model_dump()}` |
| tick_dynamics | JSONB | | NationalTickParameters + SmoothedCoefficients (from persistent_context) |
| extra | JSONB | | Future graph-level metadata |

PK: `(session_id, tick)`.

### community_state

Per-tick hypergraph community data. 14 rows per tick (one per CommunityType).

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| community_type | VARCHAR(32) | NOT NULL | CommunityType enum |
| category | VARCHAR(32) | NOT NULL | HyperedgeCategory (1/2/3 per Constitution II.7) |
| heat | FLOAT | NOT NULL | |
| cohesion | FLOAT | NOT NULL | |
| infrastructure | FLOAT | NOT NULL | |
| visibility | FLOAT | NOT NULL | |
| legal_status | VARCHAR(32) | NOT NULL | LegalStatus enum |
| reproduction_cost_modifier | FLOAT | NOT NULL | |
| rent_access_modifier | FLOAT | NOT NULL | |
| collective_identity | FLOAT | NOT NULL | Feature 029 |
| dominant_tendency | VARCHAR(32) | NOT NULL | ConsciousnessTendency enum |
| ideological_contestation | FLOAT | NOT NULL | Feature 029 |
| infiltration_resistance | FLOAT | | Feature 029 (derived) |

PK: `(session_id, tick, community_type)`.

### community_membership

Per-tick hyperedge incidence records.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| agent_id | VARCHAR(64) | NOT NULL | |
| community_type | VARCHAR(32) | NOT NULL | |
| role | VARCHAR(32) | NOT NULL | MembershipRole enum |
| strength | FLOAT | NOT NULL | |
| visibility | FLOAT | NOT NULL | |
| overt | BOOLEAN | NOT NULL | |

PK: `(session_id, tick, agent_id, community_type)`.
Indexes: `(session_id, tick, community_type)`, `(session_id, tick, agent_id)`.

### contradiction_field

Per-tick dialectical field values at each node (Feature 002).

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| node_id | VARCHAR(64) | NOT NULL | |
| field_name | VARCHAR(32) | NOT NULL | exploitation, immiseration, imperial_rent, displacement |
| value | FLOAT | NOT NULL | Normalized [0, 1] via FieldRegistry |
| laplacian | FLOAT | | Graph Laplacian (FieldDerivativeSystem) |
| dt | FLOAT | | Temporal first derivative df/dt |
| d2t | FLOAT | | Temporal second derivative d2f/dt2 |

PK: `(session_id, tick, node_id, field_name)`.

### edge_curvature

Ollivier-Ricci curvature per edge (Feature 002).

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| source_id | VARCHAR(64) | NOT NULL | |
| target_id | VARCHAR(64) | NOT NULL | |
| curvature | FLOAT | NOT NULL | Wasserstein-1 LP result |
| gradient | JSONB | | Per-field gradients along this edge |

PK: `(session_id, tick, source_id, target_id)`.

### simulation_event

Append-only event ledger.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| id | BIGSERIAL | PK | |
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| event_type | VARCHAR(48) | NOT NULL | EventType enum value |
| entity_id | VARCHAR(64) | | |
| community_type | VARCHAR(32) | | |
| details | JSONB | NOT NULL | Full event payload |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | |

Indexes: `(session_id, tick)`, `(session_id, event_type)`, partial `(session_id, community_type) WHERE community_type IS NOT NULL`.

### tick_log

Deterministic replay metadata + per-system timing.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| rng_state | BYTEA | | Serialized RNG state |
| mutations_json | JSONB | | Mutation summary |
| invariant_checks | JSONB | | Conservation checks |
| system_timings | JSONB | | `{"ImperialRentSystem": 12, ...}` (ms) |
| wall_time_ms | INTEGER | | Total tick execution time |

PK: `(session_id, tick)`.

### tick_summary

Pre-aggregated metrics per tick for time-series endpoints.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| year | INTEGER | | Simulation year |
| total_c | NUMERIC | | |
| total_v | NUMERIC | | |
| total_s | NUMERIC | | |
| exploitation_rate | FLOAT | | s/v |
| profit_rate | FLOAT | | s/(c+v) |
| imperial_rent | FLOAT | | Phi aggregate |
| avg_consciousness | FLOAT | | |
| solidarity_edge_count | INTEGER | | |
| antagonistic_edge_count | INTEGER | | |
| co_optive_edge_count | INTEGER | | |
| org_count | INTEGER | | |
| player_org_count | INTEGER | | |
| uprising_count | INTEGER | | |
| repression_count | INTEGER | | |
| conservation_check | BOOLEAN | | Did value conservation hold? |

PK: `(session_id, tick)`.

## Layer 3: Spatial (PostGIS)

### hex_cell

Static reference table. Generated once per scenario from TIGER/Line boundaries. Shared across sessions.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| h3_index | VARCHAR(15) | PK | H3 resolution 7 cell ID |
| county_fips | VARCHAR(5) | NOT NULL | |
| res6_parent | VARCHAR(15) | NOT NULL | |
| res5_parent | VARCHAR(15) | NOT NULL | |
| geometry | GEOMETRY(POLYGON, 4326) | NOT NULL | PostGIS |
| centroid | GEOMETRY(POINT, 4326) | NOT NULL | PostGIS |

Indexes: GiST on `geometry`, `county_fips`.

### hex_state

Per-tick economic state of each hex. ~1,500 rows per tick.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| h3_index | VARCHAR(15) | FK hex_cell.h3_index, NOT NULL | |
| constant_capital | NUMERIC | NOT NULL | c |
| variable_capital | NUMERIC | NOT NULL | v |
| surplus_value | NUMERIC | NOT NULL | s |
| employment | FLOAT | NOT NULL | |
| dept_shares | FLOAT[4] | NOT NULL | Dept I, IIa, IIb, III |
| profit_rate | FLOAT | NOT NULL | |
| exploitation_rate | FLOAT | NOT NULL | |

PK: `(session_id, tick, h3_index)`.
Indexes: `(session_id, tick)`, `(session_id, h3_index)`.

### hex_terrain_state

Per-tick terrain classification and biocapacity for each hex (Feature 036). Combines terrain and biocapacity into one table since both are per-hex.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| h3_index | VARCHAR(15) | FK hex_cell.h3_index, NOT NULL | |
| terrain_type | VARCHAR(16) | NOT NULL | LAND, WATER, RESOURCE |
| water_coverage | FLOAT | NOT NULL | [0, 1] |
| resource_coverage | FLOAT | NOT NULL | [0, 1] |
| biocapacity_stocks | JSONB | NOT NULL | `{stock_type: {initial, current, depleted, history}}` |
| internet_access | BOOLEAN | NOT NULL | FCC broadband threshold |
| internet_quality | FLOAT | NOT NULL | [0, 1] |
| surveillance_coupling | FLOAT | NOT NULL | [0, 1] |
| response_mode | VARCHAR(16) | NOT NULL | PERMIT, THROTTLE, SEVER |

PK: `(session_id, tick, h3_index)`.
Indexes: `(session_id, tick)`.

## Layer 4: Infrastructure (psycopg raw SQL)

### infrastructure_link_state

Per-tick infrastructure links on graph edges (Feature 036).

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| session_id | UUID | FK game_session.id, NOT NULL | |
| tick | INTEGER | NOT NULL | |
| source_h3 | VARCHAR(15) | NOT NULL | |
| target_h3 | VARCHAR(15) | NOT NULL | |
| link_id | VARCHAR(128) | NOT NULL | |
| infra_type | VARCHAR(32) | NOT NULL | InfrastructureType enum |
| capacity | JSONB | NOT NULL | `{FlowCategory: float}` |
| condition | FLOAT | NOT NULL | [0, 1] |
| owner_org_id | VARCHAR(64) | | |

PK: `(session_id, tick, link_id)`.
Indexes: `(session_id, tick)`, `(session_id, tick, source_h3, target_h3)`.

## Layer 5: Trace Logging (UNLOGGED, partitioned)

### trace_log

Structured execution trace events. UNLOGGED (no WAL). Partitioned by session_id.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| id | BIGSERIAL | PK | |
| session_id | UUID | NOT NULL | |
| tick | INTEGER | NOT NULL | |
| system_name | VARCHAR(48) | NOT NULL | |
| level | VARCHAR(8) | NOT NULL | SUMMARY, DEBUG, TRACE |
| event | VARCHAR(48) | NOT NULL | formula_eval, edge_mode_transition, alpha_smooth, etc. |
| node_id | VARCHAR(64) | | |
| data | JSONB | NOT NULL | Structured trace payload |
| ts | TIMESTAMPTZ | NOT NULL, default now() | |

Per-partition indexes: `(session_id, tick, event)`, GIN on `data`.

## Layer 6: Semantic Search (pgvector)

### document_chunk

Document chunks with vector embeddings for RAG.

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| id | VARCHAR(128) | PK | SHA-256 hash of content + chunk_index |
| session_id | UUID | FK game_session.id | Nullable (global theory corpus) |
| source_file | VARCHAR(256) | NOT NULL | |
| chunk_index | INTEGER | NOT NULL | |
| content | TEXT | NOT NULL | |
| embedding | vector(768) | NOT NULL | Default dim for embeddinggemma |
| metadata | JSONB | | |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | |

Indexes: HNSW on `embedding` with cosine distance, `session_id`.

## Sizing Estimates

Per game session, per tick (tri-county Detroit):

| Table | Rows/tick | Row size | Per tick |
|-------|-----------|----------|----------|
| node_state | ~35 | ~2 KB | ~70 KB |
| edge_state | ~55 | ~1 KB | ~55 KB |
| graph_metadata | 1 | ~5 KB | ~5 KB |
| community_state | 14 | ~300 B | ~4 KB |
| community_membership | ~200 | ~100 B | ~20 KB |
| hex_state | ~1,500 | ~200 B | ~300 KB |
| hex_terrain_state | ~1,500 | ~300 B | ~450 KB |
| infrastructure_link_state | ~100 | ~200 B | ~20 KB |
| contradiction_field | ~80 | ~100 B | ~8 KB |
| edge_curvature | ~50 | ~100 B | ~5 KB |
| action_result | ~10-30 | ~500 B | ~15 KB |
| simulation_event | ~5-20 | ~500 B | ~10 KB |
| tick_summary | 1 | ~200 B | ~200 B |
| tick_log | 1 | ~1 KB | ~1 KB |

**Game state per tick** (excluding traces): ~960 KB (up from ~490 KB due to infrastructure tables).
**Over 260 ticks**: ~245 MB per session.
**After Parquet export**: ~25-30 MB per session (zstd compression).
