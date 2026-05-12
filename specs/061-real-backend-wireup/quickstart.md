# Quickstart: Real Backend Wire-Up Validation

**Feature**: 061-real-backend-wireup
**Audience**: Implementer validating the cutover end-to-end
**Updated**: 2026-05-11

This quickstart walks through the validation steps that prove the wire-up is complete. It targets the constitutional test case (Constitution IV: Wayne County → Michigan statewide). Each step maps to one or more spec acceptance scenarios and success criteria.

## Prerequisites

- Postgres 16+ reachable on localhost or via env vars (`POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`)
- PostGIS, pgvector, uuid-ossp extensions installed
- Python 3.12+ with project deps (`poetry install`)
- Node 20+ with frontend deps (`mise run web:install`)
- The pinned embedding model available locally: `sentence-transformers/all-mpnet-base-v2` (Apache 2.0, 768-dim, ~438MB; downloaded by `sentence_transformers` cache on first run — see `research.md` R1 for revision SHA pin)

## Cutover step-by-step

### 1. Backup any non-test data (one-time, only if upgrading a real deployment)

```bash
pg_dump --table=game_session --table=game_turn --table=action_result \
        --data-only --file=pre_cutover_backup.sql babylon
```

The cutover migration will purge these tables. Per FR-033 (clarified): pre-cutover sessions are not migrated forward — they are deleted. The backup is for paranoia, not recovery.

### 2. Run the cutover migration set

```bash
mise run web:migrate
```

This applies, in order:

- `0006_drop_sim_hex_states.py` — drops the orphan `sim.hex_states` table and its schema (FR-030).
- `0007_purge_fixture_sessions.py` — `DELETE FROM game_session;` cascading to all session-scoped tables (FR-033).
- `0008_drop_snapshot_json.py` — drops the now-unused `snapshot_json` column on `game_session`.
- `0009_action_result_unique.py` — adds idempotency constraints (FR-004).
- `0010_document_chunk_reconciliation.py` — drops and recreates `document_chunk` with the corrected DDL (FR-001).

Verify:

```bash
psql babylon -c "\dt sim.*"            # → "Did not find any relation named sim.*"
psql babylon -c "SELECT count(*) FROM game_session;"  # → 0
psql babylon -c "\d document_chunk"    # → columns chunk_id, collection, content, embedding (vector(768)), metadata, source, chunk_index, created_at
```

### 3. Confirm the embedding store works (US1, SC-006)

```bash
poetry run python - <<'EOF'
from psycopg_pool import ConnectionPool
from babylon.persistence.pgvector_store import PgVectorStore

pool = ConnectionPool("dbname=babylon", min_size=1, max_size=2)
store = PgVectorStore(pool, collection="quickstart")

# Add five embeddings (US1 acceptance #1).
embeddings = [[0.1] * 768 for _ in range(5)]
store.add_chunks(
    ids=[f"chunk-{i}" for i in range(5)],
    contents=[f"sample content {i}" for i in range(5)],
    embeddings=embeddings,
    metadatas=[{"src": "quickstart"} for _ in range(5)],
)

# Query (US1 acceptance #2).
ids, docs, embs, metas, dists = store.query_similar(
    query_embedding=[0.1] * 768,
    k=3,
)
assert len(ids) == 3, f"expected 3 results, got {len(ids)}"
print("OK: pgvector roundtrip succeeded")

# Wrong-dimension write must raise at the application layer (US1 acceptance #3).
import pytest
with pytest.raises(Exception):  # EmbeddingDimensionError
    store.add_chunks(
        ids=["bad"],
        contents=["x"],
        embeddings=[[0.0] * 384],  # wrong dim
        metadatas=[{}],
    )
print("OK: dimension preflight rejects 384-dim input")
EOF
```

### 4. Boot the application and confirm bridge identity (US2)

```bash
mise run web:dev
```

Expected log line:

```text
INFO  game.apps  EngineBridge initialized via GameConfig.ready (attempt 1/3)
```

Confirm via the auth-gated health endpoint:

```bash
# Public endpoint (no auth needed):
curl -s http://localhost:8000/health/ | jq
# → {"status": "ok"}

# Auth-gated endpoint (must log in first to set session cookie):
curl -s -c cookies.txt -b cookies.txt -X POST http://localhost:8000/accounts/login/ \
  -d "username=admin&password=admin"
curl -s -b cookies.txt http://localhost:8000/health/detail/ | jq '.engine.implementation'
# → "EngineBridge"
```

If `implementation` reports anything other than `"EngineBridge"`, the wire-up has not been applied or the boot sequence failed silently — re-check `apps.py:GameConfig.ready` and the Phase 1 migration set.

Test 404-on-unauthenticated (US2 acceptance #6):

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health/detail/
# → 404
```

NOT 401, NOT 403. If this returns 401 or 403, the custom permission class is not properly wired (see `data-model.md` §4 for the IsStaffOrHide pattern).

### 5. Test the engine retry-then-exit pattern (US2 acceptance #2)

In a separate terminal, stop Postgres:

```bash
sudo systemctl stop postgresql
```

Restart the worker:

```bash
mise run web:stop && mise run web:dev
```

Expected log sequence:

```text
WARN  game.apps  EngineBridge init failed (attempt 1/3): ConnectionRefused; backing off ...
WARN  game.apps  EngineBridge init failed (attempt 2/3): ConnectionRefused; backing off ...
WARN  game.apps  EngineBridge init failed (attempt 3/3): ConnectionRefused; exiting non-zero
ERROR game.apps  Worker exiting with status 1
```

The worker process exits. systemd restarts it (with its own backoff). When Postgres comes back up, the next boot attempt succeeds.

```bash
sudo systemctl start postgresql
# Wait a few seconds for systemd to retry; check:
journalctl -u babylon-web.service -n 50
```

### 6. Seed a Wayne County session (Constitution IV.2 — tri-county acceptance criterion)

```bash
mise run web:manage seed_initial_game --scenario wayne_county --player admin
```

(Note: `seed_mock_game` was renamed to `seed_initial_game` in this feature per FR-032.)

Capture the session UUID from the command output.

### 7. Walk the six v2 pages with live data (US3, US4, US6)

Open the browser to `http://localhost:5173/games/<session_uuid>`.

For each page, verify the listed acceptance items:

| Page | Verify |
|---|---|
| **Briefing** | Tick badge displays current tick; player-org name appears in subtitle; Priority Dispatch shows session events (not the static fixture set); sparklines have ≥1 point initially. (US3 acceptance #1, #4) |
| **Orgs** | Player-controlled tab shows exactly the orgs seeded for the player; NPC tab shows the others; selecting an org reveals real cohesion / OODA phase / vanguard resources. (US4 all acceptance scenarios) |
| **Verb (any)** | Actor list contains exactly the player's orgs with real `short` names; target list populates from the verb-specific endpoint. (US5 acceptance #1) |
| **Intel** | Territory detail shows real heat / population / rent for Wayne County hexes. (US6 acceptance #1, #4) |
| **Results** | Initially empty (no actions resolved yet). |
| **Analysis** | Sparklines display the seed tick's values (1 point each). |

### 8. Submit a deterministic action sequence (US5, SC-003, SC-004)

```bash
SESSION=<uuid_from_step_6>
ORG=<player_org_id_from_orgs_page>

# Submit Educate ×3 against same target.
for i in 1 2 3; do
  curl -s -b cookies.txt -X POST \
    http://localhost:8000/api/games/$SESSION/actions/educate/ \
    -H "Content-Type: application/json" \
    -d "{\"org_id\": \"$ORG\", \"target_id\": \"terr-wayne-detroit-central\"}" \
    -H "X-CSRFToken: $(grep csrftoken cookies.txt | awk '{print $7}')"
done
```

Resolve the tick:

```bash
curl -s -b cookies.txt -X POST http://localhost:8000/api/games/$SESSION/resolve/ | jq
```

Reload Results page; confirm three rows visible with non-zero outcome deltas.

### 9. Verify determinism (SC-004)

Create a fresh session with the same `rng_seed`:

```bash
SEED=42
SESSION_A=$(curl -s -b cookies.txt -X POST http://localhost:8000/api/games/ \
  -H "Content-Type: application/json" \
  -d "{\"scenario\": \"wayne_county\", \"rng_seed\": $SEED}" | jq -r '.data.session_id')

# Replay identical action sequence...
# (Submit same actions in same order against the same orgs/targets.)

# Compare action_result rows:
psql babylon -c "
  SELECT consciousness_delta, heat_delta, success
  FROM action_result
  WHERE session_id = '$SESSION_A'
  ORDER BY id;
" > replay_a.txt

# Then create SESSION_B with the same seed and submit the same sequence; compare.
diff replay_a.txt replay_b.txt
# → empty diff (byte-identical results)
```

### 10. Verify atomic snapshot writes (SC-011)

In a separate terminal, kill Postgres mid-resolution:

```bash
# Run a long-tick session, then:
sudo systemctl stop postgresql &
mise run web:resolve --session $SESSION
```

After Postgres recovers, query each of the seven snapshot tables for the failed tick:

```bash
psql babylon -c "
  SELECT 'territory' as tbl, count(*) FROM territory_snapshot WHERE game_id = '$SESSION' AND tick = $FAILED_TICK
  UNION ALL SELECT 'org', count(*) FROM org_snapshot WHERE game_id = '$SESSION' AND tick = $FAILED_TICK
  UNION ALL SELECT 'edge', count(*) FROM edge_snapshot WHERE game_id = '$SESSION' AND tick = $FAILED_TICK
  UNION ALL SELECT 'community', count(*) FROM community_snapshot WHERE game_id = '$SESSION' AND tick = $FAILED_TICK
  UNION ALL SELECT 'hex_act', count(*) FROM hex_activity WHERE game_id = '$SESSION' AND tick = $FAILED_TICK
  UNION ALL SELECT 'econ_sum', count(*) FROM economic_summary WHERE game_id = '$SESSION' AND tick = $FAILED_TICK
  UNION ALL SELECT 'tick_evt', count(*) FROM tick_event WHERE game_id = '$SESSION' AND tick = $FAILED_TICK;
"
```

Expected: every row reports `0` (the entire tick rolled back). If any row reports >0 while another reports 0, the transactional wrap is broken.

### 11. Verify mock sunset (SC-010)

```bash
grep -rn "MockEngineBridge\|mock_defines\|seed_mock_game\|BABYLON_MOCK_MODE" \
  src/ web/ specs/ 2>/dev/null \
  | grep -v "^specs/061-real-backend-wireup/"   # spec docs reference these by name
```

Expected: zero matches outside the spec directory.

```bash
ls web/game/mock_bridge.py web/game/mock_defines.py 2>/dev/null
# → "ls: cannot access '...': No such file or directory"
```

### 12. End-to-end Playwright smoke test

```bash
mise run web:test e2e/test_v2_pages_live_data.spec.ts
```

Expected: green across all six v2 pages.

## Constitutional cross-check

| Step | Constitution principle exercised |
|---|---|
| Step 4 (bridge identity) | III.7 (determinism — boot identity is observable) |
| Step 5 (retry-then-exit) | X.4 (systemd as sole supervisor — restart loop is systemd's job) |
| Step 6 (Wayne County) | IV.2 (tri-county backward-compat acceptance) |
| Step 9 (determinism) | III.7 (same seed + same actions → same hash) |
| Step 10 (atomic writes) | II.6 (state is data — partial state forbidden) |
| Step 11 (mock sunset) | I.16 (Organizations are the agents — no mock substrate confusion) |

## Failure recovery

If any step fails, the recovery is **always**:

1. Roll back the migrations: `mise run web:manage migrate game 0005`
2. Revert the relevant code changes
3. File a bug against the failing step's acceptance scenario in the spec

Per spec FR-033 and the cutover migration design, there is **no** "partial cutover" recovery path — either all migrations have run or none have. Don't try to manually patch.
