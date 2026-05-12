# Implementation Plan: Real Backend Wire-Up

**Branch**: `061-real-backend-wireup` | **Date**: 2026-05-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/home/user/projects/game/babylon/specs/061-real-backend-wireup/spec.md`

## Summary

Replace the v2 frontend's hard-coded fixture data with live engine state served through Django by:

1. Reconciling the `document_chunk` schema/code mismatch and pinning a canonical 768-dim embedding model (Constitution III.6).
2. Hardening engine bridge boot with a 3-attempt exponential-backoff retry that hard-exits on persistent failure (per spec FR-007 and orchestrator restart loop on systemd).
3. Splitting the existing `/health/` endpoint into a public liveness probe + a staff-gated `/health/detail/` diagnostic endpoint.
4. Expanding `EngineBridge` serializer output with the missing 36 fixture-equivalent fields (player ownership flag, short org name, OODA phase enum, legitimacy/opacity, hyperedge memberships, expanded event narrative, expanded territory and edge metrics).
5. Implementing the currently-stubbed bridge methods (`get_game_timeseries`, `get_communities_dashboard`, five inspector endpoints, `get_economy_summary`).
6. Wiring each of the six v2 pages (Briefing, Orgs, Verb, Intel, Results, Analysis) to call the live API via the existing Zustand store + fetch wrapper, replacing fixture imports.
7. Wrapping per-tick snapshot writes in a single Postgres transaction (FR-003) and adding monotonic-idempotent guards on `action_result` and `simulation_event` (FR-004, FR-005).
8. Cutover migration that deletes all pre-existing `game_session` rows (cascading via FK), drops `sim.hex_states`, and removes `MockEngineBridge`/`mock_defines`/`seed_mock_game`/`BABYLON_MOCK_MODE`.

## Technical Context

**Language/Version**: Python 3.12+ (backend, engine, persistence); TypeScript 5.7 (frontend)
**Primary Dependencies**:
- Backend: Django 5.x, Django REST Framework, psycopg 3.x + psycopg_pool 3.x, NetworkX 3.x, Pydantic 2.x, SQLAlchemy 2.x (reference data), `sentence-transformers` (NEEDS CLARIFICATION — specific model_id required by Constitution III.6; spec says "MiniLM/MPNet family, 768-dim" — must pin one)
- Frontend: React 19, Zustand 5, deck.gl 9, MapLibre GL 5, Vite 6, vitest, Playwright (e2e)
**Storage**: PostgreSQL 16+ with PostGIS, pgvector, uuid-ossp extensions; SQLite for reference data only (`marxist-data-3NF.sqlite`)
**Testing**: pytest with markers (math/ledger/topology/integration/ai/unit), vitest (frontend unit), Playwright (e2e), Hypothesis (property tests)
**Target Platform**: Linux server (Hetzner), behind Cloudflare; systemd as sole supervisor (Constitution X.4)
**Project Type**: Web application — multi-tier (engine `src/babylon/`, web `web/babylon_web/` + `web/game/`, frontend `web/frontend/`)
**Performance Goals**: SC-012 — action submission to result visibility under 10s p95 for single-tick resolution on a typical session; no measurable regression vs current path
**Constraints**:
- Hybrid retry boot: 3 attempts with exponential backoff, then non-zero exit (FR-007; clarified)
- Per-tick snapshot writes atomic across 7 tables (FR-003)
- Resolved ticks immutable; race-safe re-resolution rejection (FR-005, clarified)
- Public `/health/` returns up/down only; auth-gated `/health/detail/` returns bridge identity / retry count / version (FR-009, clarified)
- Embedding dimension canonical 768 across DDL, code, fixtures (FR-001, clarified)
- No Docker, no containerization (Constitution X.1) — note: existing `deploy/ansible/roles/app/templates/docker-compose.yml.j2` is legacy tech debt outside this spec's scope
**Scale/Scope**:
- Single playthrough per player; multiple concurrent sessions per process; alpha-tier deployment (single-digit to low-double-digit concurrent active players in target deployment)
- 6 v2 pages × ~52 distinct fixture fields to wire
- 33 functional requirements, 7 user stories, 12 success criteria
- Cutover migration purges all existing game_session rows (clarified — fixture-era state is not preserved)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### P0 Principles (Never Drop)

| Principle | Relevance | Status |
|---|---|---|
| **I.19 Dialectic Primitive** | Engine produces dialectic state; this spec only wires it through to the API. No new dialectic semantics. | ✅ PASS |
| **I.20 Spatial Substrate** | Cleanup migration drops orphan `sim.hex_states` (no political-claim or substrate mutation). New cutover migration only purges game-session data. No substrate mutation. | ✅ PASS |
| **II.9 Morphism Dyadic** | No new morphisms or N-ary structures introduced. Hyperedge memberships are read-only serialization (FR-015). | ✅ PASS |
| **III.7 Determinism Hash** | FR-023 mandates byte-identical action results across replays for same `(session, seed, action sequence)`. FR-024 requires the seed to be threaded into every RNG-consuming engine call. | ✅ PASS — codified in spec |
| **III.8 Aleksandrov Test** | No new operators or formalisms; spec is plumbing-only. | ✅ PASS (N/A) |
| **V Verb Atomicity** | FR-025 requires unsupported verbs to be rejected at submission OR removed from available-actions list. Silent no-op forbidden. | ✅ PASS — codified |

### P1 Principles (Domain-Mandatory)

| Principle | Relevance | Status |
|---|---|---|
| **II.5 AI Observes, Never Controls** | This spec touches no AI/RAG runtime path. Embedding store fix is schema reconciliation only (RAG retrieval pipeline behavior unchanged). | ✅ PASS |
| **II.6 State is Data, Engine is Transformation** | FR-003 requires per-tick snapshot writes to be atomic — no partial state visible. Engine remains pure (no DB I/O during tick); persistence still happens after tick computation completes. | ✅ PASS |
| **II.8 Client as Presentation Layer** | Spec explicitly requires the frontend to consume `observe()` projections via JSON envelope and emit player intents via JSON. No simulation logic moves to the client. | ✅ PASS — central to feature |
| **II.11 Subsystem Table Ownership** | Bridge layer continues to be the sole declared interface to engine-owned tables. Cutover migration touches only `game_session`-rooted data (engine-owned, accessed via the engine's persistence layer). Cleanup migration drops orphan `sim.hex_states` (no owner). | ✅ PASS |
| **III.6 Model Pinning** | The embedding model must be pinned to a specific `model_id` (not "MiniLM/MPNet family"). | ⚠️ NEEDS RESEARCH — Phase 0 R1 |
| **IV Michigan Test Case** | Cutover purges existing fixture sessions; smoke testing the wire-up should use the constitutional test case (Wayne County → Michigan statewide). Not a gate; a test design constraint. | ✅ PASS — incorporated into quickstart |

### P2 Principles (Elaboration — checked but not load-bearing)

- **VII Visual Design Principles** — Frontend wire-up does not change visual design; it swaps fixture data for live data in existing components. Color tokens, palette, typography unchanged. ✅
- **VIII Anti-Patterns** — VIII.9 (Community as Pairwise Edge): hyperedge serialization (FR-015) MUST surface XGI hyperedges as N-ary memberships, not pairwise edges. Will be enforced in data-model.md. ✅
- **X Deployment Infrastructure** — X.4 (systemd as sole supervisor): the hybrid retry-then-exit boot pattern relies on systemd `Restart=on-failure` + `RestartSec` exponential backoff. Will be specified in research.md. Existing `docker-compose.yml.j2` in `deploy/ansible/roles/app/templates/` is legacy and out of scope. ✅
- **X.6 Solo-Developer Constraint** — Health endpoint expansion uses Django built-ins (no new monitoring infrastructure); no Prometheus / Grafana / Vault introduced. ✅

### IX.3 AI Decision Procedure Application

- **Read and Proceed**: Most spec requirements map directly to existing constitutional constraints (atomicity, determinism, dyadic morphisms preserved, no AI control path).
- **Read and Ask**: Health endpoint shape (FR-009) was clarified in spec session. Embedding model pinning (III.6) is the one Read-and-Ask item that becomes Phase 0 research.
- **Escalate to Amendment**: None required. No new primitives, no relaxed prohibitions.
- **Transition State Protocol — Read-Only Access Rationale (per /speckit.analyze remediation)**:
  - **II.7 Edges vs Hyperedges** is `[TRANSITION STATE]` per pending Amendment D. The constitution says "an agent MUST treat it as blocked. It MAY propose a spec to resolve the transition state, but it MUST NOT implement code that **depends on** the unresolved principle." FR-015 + tasks T068, T069 surface hyperedge memberships in the snapshot. **This work does not depend on Amendment D's resolution**: it reads existing XGI hypergraph state already produced by the engine and emits it through serializers. It introduces no new hyperedge primitive, no new edge↔hyperedge interaction logic, and no new dyadic-vs-N-ary morphism semantics. If Amendment D later changes how hyperedges are represented, the only files affected are the serializers (which read from whatever shape the engine emits) — the read-only contract is invariant under the underlying-representation change. ✅
  - **I.17 OODA Loop** is `[TRANSITION STATE]` per pending Amendment C (deferred to v2.8.0). FR-011 + tasks T066, T067 surface the OODA decision-phase enum. **This work does not depend on Amendment C's resolution**: it reads the existing `OodaProfile` four-float state already attached to each `Organization` and surfaces the dominant component as an enum via a computed property. It introduces no new OODA semantics, no new placement decision (poles vs morphism metadata vs registry), and no new tick-level OODA logic. If Amendment C later relocates OODA profiles, only the computed-property source location changes — the read-only contract is invariant. ✅

### Initial Gate Result

**PASS with 1 Phase 0 research item** (embedding model pinning).

## Project Structure

### Documentation (this feature)

```text
specs/061-real-backend-wireup/
├── plan.md              # This file
├── research.md          # Phase 0 output (embedding model selection, atomic write patterns, systemd retry pattern)
├── data-model.md        # Phase 1 output (new fields, serializer shapes, health payload schema)
├── quickstart.md        # Phase 1 output (cutover walkthrough, smoke test against Wayne County)
├── contracts/           # Phase 1 output (OpenAPI for /health/, /health/detail/, expanded snapshot endpoints)
│   ├── health.yaml
│   ├── snapshot.yaml
│   ├── timeseries.yaml
│   ├── communities.yaml
│   └── inspectors.yaml
├── checklists/
│   └── requirements.md  # Already created by /speckit.specify
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

This feature spans three existing top-level trees. No new packages, no new top-level structure.

```text
src/babylon/                                # Engine (Python)
├── persistence/
│   ├── postgres_schema.py                  # MODIFY: reconcile DOCUMENT_CHUNK_DDL with pgvector_store.py
│   ├── pgvector_store.py                   # MODIFY: dimension default → 768; preflight check
│   ├── postgres_runtime/
│   │   └── _legacy.py                      # MODIFY: wrap persist_full_tick in single transaction;
│   │                                        #         add monotonic-idempotent guards on action_result/simulation_event
│   └── runtime_schema.py                   # NO CHANGE
├── rag/
│   └── __init__.py                         # MODIFY: pin canonical model_id from research.md
└── (engine systems untouched)

web/                                        # Django app
├── babylon_web/
│   ├── settings/
│   │   ├── base.py                         # MODIFY: remove BABYLON_MOCK_MODE setting (Phase final)
│   │   └── stub.py                         # MODIFY: remove BABYLON_MOCK_MODE = True
│   ├── urls.py                             # MODIFY: add /health/detail/ route
│   └── (new health-detail view)
├── game/
│   ├── apps.py                             # MODIFY: replace silent except with retry loop + sys.exit
│   ├── api.py                              # MODIFY: add /health/detail/, expand inspector endpoints,
│   │                                        #         wire ActionResultSerializer to outcome string
│   ├── engine_bridge.py                    # MODIFY: implement get_game_timeseries, get_communities_dashboard,
│   │                                        #         5 inspectors, get_economy_summary; expand _state_to_snapshot
│   │                                        #         with player_controlled/short/ooda_phase/legitimacy/opacity/
│   │                                        #         hyperedge_memberships fields
│   ├── serializers.py                      # MODIFY: expand OrganizationSerializer, EventSerializer,
│   │                                        #         TerritorySerializer, EdgeSerializer
│   ├── mock_bridge.py                      # DELETE (Phase final)
│   ├── mock_defines.py                     # DELETE (Phase final)
│   ├── stub_bridge.py                      # KEEP (used in stub_create_tables dev path)
│   ├── management/commands/
│   │   ├── seed_mock_game.py               # DELETE (Phase final)
│   │   └── seed_hex_data.py                # MODIFY: fix docstring (it targets hex_latest, not sim.hex_states)
│   └── migrations/
│       ├── 0006_drop_sim_hex_states.py     # NEW: drop orphan sim.hex_states + schema
│       ├── 0007_purge_fixture_sessions.py  # NEW: cutover migration — DELETE all game_session rows
│       └── 0008_drop_snapshot_json.py      # NEW (optional, post-cutover): drop snapshot_json column
└── frontend/src/
    ├── api/
    │   └── client.ts                        # NO CHANGE (envelope conventions preserved)
    ├── stores/
    │   └── gameStore.ts                     # MODIFY: add fetch actions for new endpoints (timeseries,
    │                                         #         communities, inspectors)
    ├── hooks/
    │   ├── useTimeseries.ts                 # NEW: poll /timeseries/
    │   ├── useCommunities.ts                # NEW: fetch /communities/
    │   └── useInspector.ts                  # NEW: fetch /<inspector>/{id}/
    ├── types/
    │   └── game.ts                          # MODIFY: align field names to engine output (or document chosen direction)
    ├── fixtures/
    │   └── v2-mock-data.ts                  # DELETE (after all 6 pages wired) OR move to test/
    └── components/pages/
        ├── BriefingPage.tsx                 # MODIFY: replace fixture imports with store calls
        ├── OrgsPage.tsx                     # MODIFY: same
        ├── VerbPage.tsx                     # MODIFY: same + wire submit button
        ├── IntelPageV2.tsx                  # MODIFY: same
        ├── ResultsPage.tsx                  # MODIFY: same
        └── AnalysisPage.tsx                 # MODIFY: same

deploy/ansible/roles/web/templates/
└── gunicorn_start.j2                        # MODIFY: ensure systemd Restart=on-failure with
                                              #         RestartSec exponential pattern (per X.4)

tests/
├── unit/persistence/
│   ├── test_pgvector_store.py               # MODIFY: replace mocked-cursor tests with schema-honest fixtures
│   └── test_postgres_runtime.py             # MODIFY: add atomic tick-write tests
├── integration/
│   ├── test_engine_bridge_boot.py           # NEW: assert retry-then-exit on unreachable DB
│   ├── test_health_detail.py                # NEW: assert public/auth-gated split
│   ├── test_tick_immutability.py            # NEW: race-safe re-resolution
│   └── test_snapshot_field_coverage.py      # NEW: assert all 36 missing fields surface
└── e2e/
    └── test_v2_pages_live_data.spec.ts      # NEW (Playwright): smoke test all 6 pages
                                              #   against a real engine in a stub-table session
```

**Structure Decision**: This is a multi-tier web application with three existing top-level source trees (`src/babylon/`, `web/`, `web/frontend/`). The plan uses the existing structure with no new packages. New files are confined to migrations (3), frontend hooks (3), and test files (5). Deletions are confined to the mock scaffolding (3 files) and the v2 fixture module (1 file).

## Phase 0: Research

The Phase 0 outputs are consolidated in `research.md`. Three research items must complete before Phase 1:

| ID | Item | Driver |
|---|---|---|
| R1 | Canonical embedding model selection (768-dim, sentence-transformers family) with specific `model_id`, hash, and license | Constitution III.6 (Model Pinning); spec FR-001 |
| R2 | Atomic multi-table snapshot write pattern in `psycopg` 3.x with `ConnectionPool` (transaction wrapping `executemany` across seven tables) — Context7 `psycopg` docs | Spec FR-003; Constitution II.6 (no DB I/O during tick — but persistence after tick must be atomic) |
| R3 | systemd unit pattern for retry-on-failure with exponential `RestartSec` backoff for Django app boot — needs to interact with the in-process 3-retry loop without crash-looping | Spec FR-007 (clarified); Constitution X.4 (systemd as sole supervisor); Constitution X.6 (solo-developer constraint) |
| R4 | Django 5.x `AppConfig.ready()` patterns for boot-time initialization with retry — Context7 `django` docs (specifically the `RUN_MAIN` interaction) | Spec FR-006, FR-007 |
| R5 | DRF auth-gated endpoint returning 404 instead of 401 (security through obscurity for `/health/detail/`) — Context7 `djangorestframework` docs | Spec FR-009 (clarified) |

Phase 0 dispatches research-agent + Context7 lookups in parallel; consolidates findings into `research.md` with the standard Decision/Rationale/Alternatives format.

## Phase 1: Design & Contracts

**Prerequisites:** `research.md` complete

### data-model.md will document

1. **New / modified field shapes**:
   - `Organization.short_name` (str, ≤16 chars; derived from `name` if absent)
   - `OodaProfile.phase` (`Literal["observe","orient","decide","act"]`)
   - `Organization.legitimacy` (Probability)
   - `Organization.opacity` (Probability)
   - Snapshot `event[].id` (str), `event[].severity` (`Literal["critical","warning","informational"]`), `event[].title` (str), `event[].body` (str)
   - Snapshot `organization[].player_controlled` (bool, derived from session.player_id ∋ org.controlling_player_id)
   - Snapshot `organization[].hyperedge_memberships` (list[{hyperedge_id, role, strength}])
   - Snapshot `territory[].consciousness`, `territory[].solidarity`, `territory[].wealth`, `territory[].dominant_community` (added)
   - Snapshot `edge[].rate_of_profit`, `edge[].rent_burden`, `edge[].age_ticks` (added when available)

2. **Validation rules**:
   - `short_name` truncation deterministic
   - `ooda_phase` enum validated at serializer boundary
   - `severity` enum validated at serializer boundary
   - `player_controlled` derivation rule explicit (no heuristics — exact ownership check)

3. **State transitions** (preserved, not new):
   - GameSession: `active → paused → active → resolving → active`
   - PlayerAction: `pending → resolved`
   - Tick: `unresolved → resolved` (immutable per FR-005)

4. **Embedding store schema reconciliation**:
   - Final `document_chunk` columns: `chunk_id` (PK), `collection`, `content`, `embedding vector(768)`, `metadata jsonb`, `source`, `chunk_index`, `created_at`
   - Drop `id`, `session_id`, `source_file` (replaced by `chunk_id`/`source`/`metadata` keying)
   - HNSW index on `embedding`
   - Migration sequence: drop old table → create new table (or `ALTER TABLE` if data preservation needed; see research)

5. **Health endpoint payloads**:
   - Public `/health/`: `{"status": "ok"}` (existing) — unchanged response shape
   - Auth-gated `/health/detail/`: `{"engine": {"implementation": "EngineBridge", "boot_attempts": 1, "boot_succeeded_at": "ISO8601"}, "database": {"reachable": true}, "version": "0.x.y", "git_sha": "abc1234"}`

### contracts/ will contain

OpenAPI 3.1 fragments covering the changed endpoints:

- **`health.yaml`** — Public `GET /health/` (200 returns `{"status":"ok"}`), auth-gated `GET /health/detail/` (200 returns the diagnostic payload, 404 for unauthenticated callers per security requirement).
- **`snapshot.yaml`** — Updated `GET /api/games/{id}/state/` schema with all expanded fields (player_controlled, short_name, ooda_phase, legitimacy, opacity, severity/title/body on events, hyperedge_memberships).
- **`timeseries.yaml`** — `GET /api/games/{id}/timeseries/` returns 6 named arrays (imperial_rent, consciousness, solidarity, heat, wealth, biocapacity) with `tick` x-axis.
- **`communities.yaml`** — `GET /api/games/{id}/communities/` returns per-community ternary consciousness, member count, contradiction-partner ID.
- **`inspectors.yaml`** — `GET /api/games/{id}/{type}/{id}/` for `node`, `org`, `community`, `edge`, `hex` — populated detail object.

### quickstart.md will walk through

1. Run cutover migration on a fresh DB.
2. Create a Wayne County session via the seed command (after rename from `seed_mock_game` to `seed_initial_game`).
3. Observe `/health/detail/` reports `EngineBridge` (after authenticating).
4. Resolve three ticks via the API.
5. Load each of the six v2 pages and assert: tick number changes, sparklines have ≥3 distinct points, player-controlled orgs match seeded data, each verb page submits successfully.
6. Submit a known action sequence twice, assert byte-identical action results (Constitution III.7 / spec SC-004).

### Agent context update

The `update-agent-context.sh claude` script will append this feature's tech notes to `CLAUDE.md` between the managed markers. Specifically:

- 061-real-backend-wireup: Real-engine wire-up replacing mock fixtures across the 6 v2 pages; adds `/health/detail/`; pins embedding model 768-dim sentence-transformers (model_id from R1); cutover migration purges all pre-existing game_session rows.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitutional violations. The Phase 0 research item (R1: model pinning) is the resolution path for an existing P1 requirement (III.6), not a violation.

Two pre-existing infrastructure items are noted but explicitly out of scope for this spec:

| Pre-existing tech debt | Constitution principle | Out of scope rationale |
|---|---|---|
| `deploy/ansible/roles/app/templates/docker-compose.yml.j2` exists | X.1 (Bare Metal, Ansible-Managed — no Docker) | This spec wires the existing Django app; does not modify deployment topology. Should be addressed in a separate "deploy modernization" spec. |
| `deploy/ansible/roles/celery/templates/supervisor_*.conf.j2` use supervisor | X.4 (systemd as sole supervisor) | Same as above — Celery deployment topology is outside this spec's scope. |

These are flagged in the post-Phase-1 Constitution re-check report so future planners can see them; they do NOT block this feature.

## Post-Design Constitution Re-Check (after Phase 1)

Re-evaluating the Phase 0/1 outputs against the constitution after research and design artifacts are complete:

### P0 (Never Drop)

| Principle | Phase 1 verification | Status |
|---|---|---|
| **I.19 Dialectic Primitive** | data-model.md adds no new dialectic types; engine state surfaces unchanged | ✅ PASS |
| **I.20 Spatial Substrate** | Migration 0006 drops orphan `sim.hex_states`; migration 0007 purges only session-scoped data; no substrate mutation. Hex grid + county data untouched. | ✅ PASS |
| **II.9 Morphism Dyadic** | Hyperedge serialization (FR-015) is read-only surfacing of XGI state; no new N-ary morphisms; II.7 transition-state respected | ✅ PASS |
| **III.7 Determinism Hash** | R2 (atomic transactions) + R4 (boot reproducibility via `_initialized` flag) + FR-024 (RNG seed threading) all preserve determinism | ✅ PASS |
| **III.8 Aleksandrov Test** | No new operators introduced | ✅ PASS (N/A) |
| **V Verb Atomicity** | FR-025 (verbs without handler reject at submission) preserved | ✅ PASS |

### P1 (Domain-Mandatory)

| Principle | Phase 1 verification | Status |
|---|---|---|
| **II.5 AI Observes** | Embedding store fix (R1) is schema reconciliation; no new AI control-path | ✅ PASS |
| **II.6 State is Data** | R2 transactional wrap means persistence remains atomic and post-tick; no DB I/O during tick computation | ✅ PASS |
| **II.8 Client as Presentation** | All snapshot.yaml fields are `observe()` projections; frontend receives JSON, emits intents | ✅ PASS |
| **II.11 Subsystem Table Ownership** | data-model.md changes touch only engine-owned tables (snapshots, tick_log, document_chunk) and Django-owned tables (game_session admin metadata). Cross-subsystem reads still flow through bridge layer. | ✅ PASS |
| **III.6 Model Pinning** | R1 pins `sentence-transformers/all-mpnet-base-v2` with revision SHA in `llm_config.py` constants. Was the only Phase 0 NEEDS CLARIFICATION; now resolved. | ✅ PASS — was ⚠️ pre-research |
| **IV Michigan Test Case** | quickstart.md step 6 uses Wayne County (Constitution IV.2 tri-county acceptance) | ✅ PASS |

### P2 (Elaboration)

| Principle | Phase 1 verification | Status |
|---|---|---|
| **VII Visual Design** | No frontend visual changes; data swap only | ✅ PASS |
| **VIII.10 Asymmetric Communities** | contracts/communities.yaml documents `contradiction_partner_id` as nullable per Constitution VIII.10 (Category 2 hyperedges have no paired oppressor) | ✅ PASS — explicitly surfaced |
| **VIII.9 Community as Hyperedge** | snapshot.yaml `Hyperedge` schema is N-ary (member_ids array), not pairwise | ✅ PASS |
| **X.1 Bare Metal** | R3 systemd unit file targets bare-metal Ansible deployment; no Docker introduced. Pre-existing `docker-compose.yml.j2` flagged as out of scope. | ✅ PASS (with noted tech debt) |
| **X.4 systemd Sole Supervisor** | R3 systemd unit + Gunicorn pattern; no new supervisor introduced. Pre-existing `supervisor_*.conf.j2` for Celery flagged as out of scope. | ✅ PASS (with noted tech debt) |
| **X.6 Solo-Developer Constraint** | Two health endpoints + standard Django auth + standard systemd directives. No Prometheus, no Grafana, no Vault, no service mesh introduced. | ✅ PASS |

### Final gate result

**PASS — All constitutional gates clear after Phase 1 design.**

All five Phase 0 research items are resolved with citation-grounded decisions. R1 (model pinning) was the only originally-flagged P1 NEEDS CLARIFICATION; it is now resolved and codified in `data-model.md` §1, `contracts/health.yaml`, and the quickstart prerequisite. R5 was reconciled mid-flight: the initial "permission class raises NotFound" approach was discarded after the agent's research surfaced DRF issue #7529; the spec now uses a custom DRF exception handler instead.

No constitutional amendments required. No transition-state principles violated.

## Phase 2 — Tasks (NOT generated by `/speckit.plan`)

The next command is `/speckit.tasks` which will produce a numbered, dependency-ordered `tasks.md` from this plan. Per the speckit workflow, `/speckit.plan` does not generate tasks.md; that is `/speckit.tasks`'s responsibility.
