# Phase 0 Research: Real Backend Wire-Up

**Feature**: 061-real-backend-wireup
**Status**: ✅ COMPLETE
**Updated**: 2026-05-11

This document consolidates Phase 0 research findings. Each item follows the canonical Decision / Rationale / Alternatives format and cites the source materials consulted.

Sources consulted:

- Context7 docs: `/websites/psycopg_psycopg3` (1248 snippets, score 83.94, High reputation)
- Context7 docs: `/websites/djangoproject_en_5_2` (13187 snippets, score 80.54, High reputation)
- Context7 docs: `/encode/django-rest-framework` (876 snippets, score 85.6, High reputation)
- Web research dispatched to `web-search-researcher` agent (R1 model selection, R3 systemd patterns, plus cross-validation of R2/R4/R5)

---

## R1 — Canonical 768-dim sentence-transformers embedding model selection

### Decision

Pin `sentence-transformers/all-mpnet-base-v2` (Apache 2.0, 768-dim, MTEB average ~57.78) as the canonical embedding model. Record the model_id and the HuggingFace `main` branch revision SHA in `src/babylon/config/llm_config.py` as a frozen module-level constant.

### Rationale

`all-mpnet-base-v2` is the de facto stable reference model in the sentence-transformers ecosystem for 768-dim English semantic retrieval:

1. **License**: Apache 2.0, unconditionally permissive — no commercial-use riders, no provenance constraints.
2. **Training corpus alignment**: fine-tuned on 1.17 billion training pairs from 28+ diverse datasets (Reddit, Stack Exchange, MS MARCO, S2ORC citations, WikiAnswers). The corpus skews toward theory-dense, heterogeneous text — well-aligned with Babylon's Marx/Lenin/Mao RAG corpus and with scenario narrative fragments.
3. **Stability signals**: 36 million downloads in the last 30 days (May 2026), 100+ active HuggingFace Spaces, 375+ community fine-tunes. No deprecation announcements; model card last meaningfully updated for compatibility with newer sentence-transformers versions.
4. **MTEB score**: average 57.78 across 56 tasks. Higher-scoring 768-dim models exist (BGE, E5) but they require mandatory query-time prefixes that introduce operational coupling risk in a solo-maintained codebase (see Alternatives).
5. **No prefix discipline**: works as a "drop-in" symmetric embedding — same `model.encode(text)` call for both ingest and query. Lower operational risk.
6. **CPU performance**: hundreds of sentences/second on a single Hetzner VPS for batch RAG ingestion. Acceptable for the workload (Babylon does not require sub-100ms per-query latency).
7. **Constitution III.6**: pinning the `main` branch revision SHA satisfies the Model Pinning requirement.

Recorded as:

```python
# src/babylon/config/llm_config.py
CANONICAL_EMBEDDING_MODEL_ID = "sentence-transformers/all-mpnet-base-v2"
CANONICAL_EMBEDDING_DIM = 768
CANONICAL_EMBEDDING_REVISION = "<latest stable SHA from huggingface.co/sentence-transformers/all-mpnet-base-v2/commits/main>"
```

The exact SHA is captured at first deploy and pinned via the `revision=` argument to `SentenceTransformer.__init__`. Future model updates require an explicit constitutional change (per III.6 — no retroactive re-parsing).

### Alternatives considered

- **`BAAI/bge-base-en-v1.5`** (MIT, 768-dim, MTEB average 63.55, retrieval 53.25). Higher MTEB, MIT license. Rejected because it requires query-time instruction prefixes (`"Represent this sentence for searching relevant passages:"`) that must be applied consistently at both ingest and query time — a hidden operational coupling risk. Also published by a Chinese government-affiliated research org (BAAI), introducing supply-chain considerations outside the Apache/MIT ecosystem.
- **`intfloat/e5-base-v2`** (MIT, 768-dim). Also requires mandatory `query:` / `passage:` prefixes; omitting them silently degrades retrieval quality. Rejected for the same operational footgun.
- **`sentence-transformers/multi-qa-mpnet-base-cos-v1`** (Apache 2.0, 768-dim). Optimized for asymmetric QA retrieval — fits RAG in theory, but MTEB retrieval scores are marginally lower and adoption is ~3M downloads/month (vs 36M for `all-mpnet-base-v2`), indicating less stress-testing at scale.
- **`sentence-transformers/paraphrase-mpnet-base-v2`** (Apache 2.0, 768-dim). Optimized for paraphrase detection / symmetric similarity, not retrieval. Wrong tool.

### Citations

- [sentence-transformers/all-mpnet-base-v2 model card](https://huggingface.co/sentence-transformers/all-mpnet-base-v2)
- [BAAI/bge-base-en-v1.5 model card](https://huggingface.co/BAAI/bge-base-en-v1.5)
- [intfloat/e5-base-v2 model card](https://huggingface.co/intfloat/e5-base-v2)
- [MTEB: Massive Text Embedding Benchmark](https://huggingface.co/blog/mteb)
- [Zilliz all-mpnet-base-v2 guide](https://zilliz.com/ai-models/all-mpnet-base-v2)
- Constitution III.6 (Model Pinning)

---

## R2 — Atomic multi-table snapshot writes in psycopg 3.x with `ConnectionPool`

### Decision

Acquire one connection from `pool.connection()` per tick resolution, wrap all seven `executemany()` calls in a single `conn.transaction()` block, rely on psycopg 3's automatic rollback on exception, and use `ON CONFLICT DO NOTHING` against explicit unique constraints on the append-only result tables for retry idempotency. For the immutability check (FR-005), use a unique-index pattern: `INSERT ... ON CONFLICT (session_id, tick) DO NOTHING RETURNING id` against `tick_log`.

```python
def persist_full_tick(self, *, game_id, tick, snapshots):
    with self._pool.connection() as conn:           # Single pool acquisition
        with conn.transaction():                     # BEGIN ... COMMIT (or ROLLBACK on raise)
            cur = conn.cursor()
            cur.executemany(
                "INSERT INTO territory_snapshot ... VALUES (%s, ...) "
                "ON CONFLICT (game_id, tick, county_fips) DO NOTHING",
                territory_rows,
            )
            cur.executemany(
                "INSERT INTO org_snapshot ... ON CONFLICT (game_id, tick, org_id) DO NOTHING",
                org_rows,
            )
            # ... five more tables, all on the same cur, same transaction ...
        # COMMIT here on clean exit; ROLLBACK on any raise inside the block.
    # Connection returned to pool here.
```

### Rationale

Three psycopg 3.x mechanisms make this the canonical pattern:

1. **`with conn.transaction()` semantics**: the docs (`psycopg.org/psycopg3/docs/basic/transactions.html`) define the contract directly: "Transaction contexts, created using `with Connection.transaction()`, provide a transparent way to manage transaction finalization. When entering the context, a transaction starts, and upon exiting, it is committed. If an exception occurs within the block, the transaction is rolled back." This matches FR-003's all-or-nothing requirement exactly.

2. **Single connection scope**: psycopg's `ConnectionPool.connection()` context manager checks out one connection for the duration of the `with` block, then returns it to the pool on exit — clean or exceptional. Doing all seven writes inside one outer `with self._pool.connection() as conn` block guarantees all operations share the same backend session and the same transaction.

3. **`ON CONFLICT DO NOTHING` for idempotency**: the canonical Postgres pattern for "insert if absent, no-op if duplicate." Combined with the `UNIQUE` constraints added in migration `0009_action_result_unique.py` on `(session_id, tick, action_id)` for `action_result` and `(session_id, tick, event_type, entity_id)` for `simulation_event`, this makes retried tick resolutions safe per FR-004.

For the FR-005 race-safe immutability check on `tick_log`: the PK uniqueness check on `(session_id, tick)` is the database-level atomic guard. Two concurrent resolution attempts at the same tick will both try to INSERT; one wins (the row appears via `RETURNING id`), the other gets nothing back from `RETURNING` and the resolver raises `TickAlreadyResolved`. No advisory locks needed, no `SELECT FOR UPDATE`, no application-level coordination.

The agent's research confirmed this against PostgreSQL advisory-lock alternatives:
- `SELECT ... FOR UPDATE` requires a pre-existing parent row to lock — not applicable when the first writer creates the parent row inside the same transaction.
- `pg_advisory_xact_lock` is *advisory* (Postgres does not enforce; every code path must cooperate) and adds operational fragility for no benefit on a solo-server, single-writer system.

### Alternatives considered

- **Per-table connection acquisition with savepoints** — current code; the bug being fixed. Splits one logical transaction across seven connection scopes, allowing partial commits. Rejected.
- **`SELECT ... FOR UPDATE` on `game_session`** — would serialize all writes to the same session. Rejected: heavier than necessary; the PK uniqueness on `tick_log` is sufficient.
- **PostgreSQL advisory locks** — would serialize concurrent resolutions across a session. Rejected: adds a non-obvious coordination mechanism with no benefit over the schema constraint.
- **Pipeline mode** (`with conn.pipeline():`) — would batch all SQL into a single network round-trip. Rejected for now: seven snapshot writes per tick is low-frequency; pipeline complexity isn't justified. Worth revisiting if profiling shows network round-trip is a bottleneck. Note: psycopg's `executemany()` already uses implicit pipeline mode internally.

### Citations

- [psycopg 3.x — Transaction contexts](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
- [psycopg 3.x — Connection pool](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)
- [psycopg 3.x — Pool API reference](https://www.psycopg.org/psycopg3/docs/api/pool.html)
- [PostgreSQL `INSERT ... ON CONFLICT`](https://www.postgresql.org/docs/16/sql-insert.html#SQL-ON-CONFLICT)
- [Postgres advisory locks practical guide](https://www.ines-panker.com/2024/12/17/advisory-locks.html)
- [Advisory locks vs SELECT FOR UPDATE](https://www.kostolansky.sk/posts/postgresql-advisory-locks/)
- Constitution II.6 (state is data — persistence after tick), II.11 (subsystem table ownership), III.7 (determinism)

---

## R3 — systemd unit pattern for retry-on-failure with exponential backoff

### Decision

Use systemd 254+ native exponential backoff: `Restart=on-failure`, `RestartSec=5s`, `RestartSteps=4`, `RestartMaxDelaySec=60s` in `[Service]`; `StartLimitIntervalSec=300`, `StartLimitBurst=5` in `[Unit]`. The in-process 3-attempt retry inside `apps.py:GameConfig.ready()` handles transient sub-minute failures; systemd handles persistent failures requiring longer cool-down.

```ini
# /etc/systemd/system/babylon-web.service
[Unit]
Description=Babylon Gunicorn Application Server
After=network.target postgresql.service
Wants=postgresql.service
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=notify
User=babylon
Group=babylon
WorkingDirectory=/opt/babylon/web
ExecStart=/opt/babylon/.venv/bin/gunicorn babylon_web.wsgi:application \
          --bind 127.0.0.1:8000 \
          --workers 4
Restart=on-failure
RestartSec=5s
RestartSteps=4
RestartMaxDelaySec=60s

[Install]
WantedBy=multi-user.target
```

### Rationale

systemd v254 (shipped in Debian 13 / Ubuntu 24.04 and later) added native exponential restart backoff:

1. **`RestartSteps=4`** — "the number of exponential steps to take to increase the interval of auto-restarts from `RestartSec=` to `RestartMaxDelaySec=`" (systemd.service(5)). With `RestartSec=5s` and `RestartMaxDelaySec=60s`, the sequence is approximately 5s → 10s → 20s → 40s → 60s (capped), then constant at 60s. Acceptable latency for transient DB unavailability without crash-looping.
2. **`Restart=on-failure`** — restarts only on non-zero exit (the spec's hybrid retry-then-exit path) or watchdog timeout. Does NOT restart on `systemctl stop` or clean exit.
3. **Crash-loop guard (`[Unit]` section)** — `StartLimitIntervalSec=300` (5 min window), `StartLimitBurst=5`. Mathematical constraint: `StartLimitIntervalSec > RestartSec × StartLimitBurst` (5×5=25, well under 300). Well-known footgun: these directives MUST be in `[Unit]`, not `[Service]` — putting them in `[Service]` silently makes them inert.
4. **Application/systemd separation of concerns** — the in-process 3-retry loop (1s, 2s backoff) handles transient blips during boot (e.g., Postgres still starting). systemd's exponential restart loop handles persistent failures (DB down for minutes). Two layers, two timescales.
5. **Gunicorn integration** — Gunicorn's master process exits non-zero (exit code 3 — `HaltServer`) when workers repeatedly fail to boot. This triggers systemd's `Restart=on-failure`. Gunicorn does not expose its own exponential retry on boot; that's the application's responsibility.
6. **Constitution X.1 / X.4 compliance** — bare-metal Ansible deployment, systemd as sole supervisor. No Docker, no PID supervisor competition. The Ansible `web` role's existing `gunicorn_start.j2` template needs the new `[Unit]`/`[Service]` directives added; no new tools introduced.

### Alternatives considered

- **`Restart=always`** — restarts even on clean exit (`systemctl stop`). Inappropriate for a web server where intentional stops should be terminal.
- **Fixed `RestartSec=30s` without `RestartSteps`** — wastes 30s of recovery time on every transient blip; provides no upper cap beyond that. Strictly worse than exponential once v254 is available.
- **Wrapper shell script with `sleep` loop** — adds a moving part, breaks systemd's `Type=notify` protocol, interferes with future socket activation. Strictly inferior.
- **Pure systemd retry without in-process retry** — would pay full systemd restart latency (5s → 10s → 20s ...) on every transient sub-second blip. The in-process layer handles those cheaply.
- **Pure in-process retry without systemd** — would deadlock on persistent failures requiring longer cool-down than the in-process budget. Need both layers.

### Citations

- [systemd.service(5) — Debian unstable](https://manpages.debian.org/unstable/systemd/systemd.service.5.en.html) — `Restart=`, `RestartSteps`, `RestartMaxDelaySec`
- [How systemd exponential restart delay works (2024)](https://enotty.pipebreaker.pl/posts/2024/01/how-systemd-exponential-restart-delay-works/)
- [systemd v254 release notes](https://github.com/systemd/systemd/releases/tag/v254)
- [systemd indefinite service restarts (Stapelberg, 2024)](https://michael.stapelberg.ch/posts/2024-01-17-systemd-indefinite-service-restarts/) — on `[Unit]` placement of `StartLimit*`
- [systemd RFE issue #6129 — exponential RestartSec](https://github.com/systemd/systemd/issues/6129)
- Constitution X.4 (systemd as sole supervisor), X.6 (solo-developer constraint)

---

## R4 — Django 5.x `AppConfig.ready()` patterns for boot-time initialization

### Decision

Keep the existing `AppConfig.ready()` pattern in `web/game/apps.py`. Replace the silent `except Exception` swallow with a 3-attempt retry loop calling `sys.exit(1)` on persistent failure. Preserve the `RUN_MAIN` autoreloader guard (still works in Django 5.x). Add a class-level idempotency flag to handle multiple `ready()` invocations in test contexts. Do **not** use Gunicorn `--preload-app` (fork-safety issue with DB connections).

```python
# web/game/apps.py
import logging
import os
import sys
import time

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class GameConfig(AppConfig):
    name = "game"
    _initialized = False  # Class-level idempotency flag (Django docs recommend).

    def ready(self):
        if GameConfig._initialized:
            return
        if getattr(settings, "STUB_CREATE_TABLES", False):
            self._create_stub_tables()
        if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
            return
        db = settings.DATABASES.get("default", {})
        engine = str(db.get("ENGINE", ""))
        if "postgresql" not in engine and "postgis" not in engine:
            return

        from game import api as game_api
        from game.engine_bridge import init_persistence

        if game_api._bridge_instance is not None:
            GameConfig._initialized = True
            return

        self._initialize_engine_with_retry()

    def _initialize_engine_with_retry(self, max_attempts: int = 3) -> None:
        from game import api as game_api
        from game.engine_bridge import init_persistence
        db = settings.DATABASES.get("default", {})
        for attempt in range(1, max_attempts + 1):
            try:
                persistence = init_persistence(db)
                game_api.init_bridge(persistence)
                GameConfig._initialized = True
                logger.info("EngineBridge initialized (attempt %d/%d)", attempt, max_attempts)
                return
            except Exception:
                logger.exception(
                    "EngineBridge init failed (attempt %d/%d); backing off",
                    attempt, max_attempts,
                )
                if attempt == max_attempts:
                    logger.error("Worker exiting with status 1 — engine init exhausted retries")
                    sys.exit(1)
                time.sleep(2 ** (attempt - 1))  # 1s, 2s
```

### Rationale

1. **`AppConfig.ready()` is the documented hook** for boot-time initialization (Stage 3 of Django's application registry initialization, per Django 5.2 docs `/ref/applications/`). Quoted: "Django runs the `ready()` method of each application configuration."

2. **`RUN_MAIN` guard is still valid in Django 5.x.** Django's autoreloader (`django/utils/autoreload.py`) sets `RUN_MAIN=true` in the child process via `restart_with_reloader()`. The parent (which would double-execute `ready()`) does NOT have it set. Stable across Django 2.x through 5.x. Production Gunicorn does not use Django's autoreloader, so this branch is a no-op in production.

3. **Idempotency flag is Django-recommended.** Quoted from Django 5.2 ref: "in some corner cases (particularly in tests), `ready()` might be called more than once, so write idempotent methods or use a flag to prevent rerunning code that should execute exactly once."

4. **`sys.exit(1)` from `ready()` terminates the worker correctly.** `ready()` runs synchronously during `django.setup()`. `sys.exit(1)` raises `SystemExit`, which propagates through Django's setup, through Gunicorn's WSGI app import, and Gunicorn's master process exits non-zero (code 3, `HaltServer`). systemd's `Restart=on-failure` then fires (R3).

5. **Per-worker init under Gunicorn (not `--preload-app`).** Without `--preload-app`, Gunicorn forks workers after binding; each worker independently imports the WSGI app and runs `ready()`. With `--preload-app`, the master imports first and workers inherit via copy-on-write — but file descriptors (DB connections, sockets) created before the fork are shared across workers under copy-on-write semantics, causing all workers to multiplex on the same Postgres socket. This breaks under load. **Decision: do NOT use `--preload-app`** for connection-holding init. Accept that `ready()` runs N times for N workers; the design is safe for this (each worker creates its own pool).

6. **In-process retry preferred for fast-recovery cases.** Three quick retries (1s, 2s) inside the worker handle transient DB unavailability (e.g., Postgres restart) without paying systemd's full restart latency. systemd handles persistent failures.

### Alternatives considered

- **Move initialization to a Gunicorn `on_starting` hook** — runs once in the master before forking. Rejected: requires a separate `gunicorn.conf.py`, splits init logic across two files, harder to test.
- **Lazy initialization on first request** — defer engine init until the first API call. Rejected: pushes failure into request paths instead of surfacing at startup; first request would either block or 503.
- **Background thread/asyncio init** — run init in a daemon thread so `ready()` returns immediately. Rejected: adds concurrency complexity for no gain (engine init takes <1s when DB reachable; latency is dominated by failure-path retries that we want to surface at boot).
- **Use `--preload-app`** — would init once in master, save ~1s × N workers of boot time. Rejected: copy-on-write file descriptor sharing across workers is unsafe for connection pools.

### Citations

- [Django 5.2 — Applications](https://docs.djangoproject.com/en/5.2/ref/applications/)
- [Django 5.2 — django.setup() initialization stages](https://docs.djangoproject.com/en/5.2/ref/applications/)
- [Django ticket #14606 — autoreloader double import](https://code.djangoproject.com/ticket/14606)
- [Django autoreload.py source — RUN_MAIN](https://github.com/django/django/blob/main/django/utils/autoreload.py)
- [Gunicorn discussion #3202 — startup initialization](https://github.com/benoitc/gunicorn/discussions/3202)
- [Gunicorn settings reference](https://gunicorn.org/reference/settings/)
- [ScoutAPM blog — cold start with Gunicorn workers](https://www.scoutapm.com/blog/91c01d86-66df-11ef-8102-ae8f0e20b517)
- Constitution III.7 (determinism — bridge identity observable at boot), X.4 (systemd)

---

## R5 — DRF auth-gated endpoint returning 404 instead of 401

### Decision

Use a custom DRF exception handler (registered via `REST_FRAMEWORK['EXCEPTION_HANDLER']`) that intercepts `NotAuthenticated` and `PermissionDenied` exceptions for the specific health-detail view class and returns the standard DRF 404 body `{"detail": "Not found."}` so the response is indistinguishable from any other DRF 404. Do **not** raise `Http404` from inside a `has_permission()` method — that pattern is broken in `BrowsableAPIRenderer` (DRF issue #7529).

```python
# web/babylon_web/health/exceptions.py
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .views import HealthDetailView


def health_obscuring_exception_handler(exc, context):
    """
    Map auth/permission failures on HealthDetailView to a standard DRF 404
    so the endpoint's existence is not disclosed to unauthenticated callers.
    """
    if isinstance(exc, (NotAuthenticated, PermissionDenied)):
        if isinstance(context.get("view"), HealthDetailView):
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
    return exception_handler(exc, context)
```

```python
# web/babylon_web/settings/base.py
REST_FRAMEWORK = {
    # ... existing settings ...
    "EXCEPTION_HANDLER": "babylon_web.health.exceptions.health_obscuring_exception_handler",
}
```

`HealthDetailView` uses standard DRF permission classes (`IsAuthenticated`, plus a staff check):

```python
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.views import APIView


class IsStaff(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class HealthDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]
    # ... GET handler returns the diagnostic payload ...
```

### Rationale

1. **The exception-handler approach is the correct interception point.** DRF's exception handler receives all three exception categories (`APIException` subclasses, Django's `Http404`, Django's `PermissionDenied`). The context dict includes `context['view']`, allowing the handler to filter by view class. Quote from DRF docs: "Custom exception handlers can be configured globally."

2. **The permission-class-raises-`Http404` approach is broken.** DRF issue #7529 confirms that `BrowsableAPIRenderer.show_form_for_method` re-checks permissions with a narrower exception handler that only catches `APIException` — if `Http404` is raised at that point, it bypasses the API renderer and renders Django's standard error page instead of a JSON 404. This is a known unfixed bug in DRF as of 3.14.x. **My initial draft of `IsStaffOrHide` raising `NotFound` from `has_permission()` would have hit this bug.** Replaced.

3. **Standard 404 body is the right choice.** DRF's default 404 body is `{"detail": "Not found."}`. Returning the same body matches what an unrelated 404 (e.g., `/api/games/<nonexistent>/`) returns — they are byte-identical. An empty 404 body would create a unique fingerprint for the health-detail endpoint, undermining the security-through-obscurity goal.

4. **Local override over global default behavior change.** The handler filters by `isinstance(context['view'], HealthDetailView)` so only this one view's auth failures are remapped to 404. Every other endpoint preserves DRF's standard 401/403 behavior. Minimum blast radius.

5. **Testable in isolation.** A unit test asserts: `response.status_code == 404 and response.data == {"detail": "Not found."}` for unauthenticated GET to `/health/detail/`. A separate test confirms staff users get 200 with the diagnostic payload.

### Alternatives considered

- **Custom permission class raising `Http404` from `has_permission()`** — broken in `BrowsableAPIRenderer` per DRF issue #7529. My initial draft. Rejected.
- **Custom permission class raising `rest_framework.exceptions.NotFound`** — produces `{"detail": "Not found."}` body which matches generic 404s but the BrowsableAPIRenderer bug still applies in some renderer paths. Custom exception handler avoids both edge cases.
- **`Response(status=404)` with empty body from the exception handler** — creates a unique fingerprint (empty body) that distinguishes `/health/detail/` from other 404s. Defeats the security-through-obscurity goal. Rejected.
- **`dispatch()` override on the view** — works but more boilerplate per view; not reusable; harder to discover during code review.
- **Django middleware before DRF** — operates before authentication resolves; must couple to URL patterns; adds non-DRF dependency. Over-engineered for one endpoint.

### Citations

- [DRF — Exception handling](https://www.django-rest-framework.org/api-guide/exceptions/)
- [DRF — Permissions](https://www.django-rest-framework.org/api-guide/permissions/)
- [DRF issue #7529 — Http404 from has_permission breaks BrowsableAPIRenderer](https://github.com/encode/django-rest-framework/issues/7529)
- [DRF discussion #7794 — Http404 detail message overridden](https://github.com/encode/django-rest-framework/discussions/7794)
- [DRF issue #7172 — Http404 detail loss](https://github.com/encode/django-rest-framework/issues/7172)
- Spec FR-009 (clarified)

---

## Summary table

| Item | Status | Decision |
|---|---|---|
| R1 — Embedding model pin | ✅ COMPLETE | `sentence-transformers/all-mpnet-base-v2` (Apache 2.0, 768-dim, MTEB 57.78) |
| R2 — Atomic multi-table writes | ✅ COMPLETE | `with conn.transaction():` over single pool connection; `ON CONFLICT DO NOTHING` for idempotency; `tick_log` PK as race-safe immutability check |
| R3 — systemd retry pattern | ✅ COMPLETE | `Restart=on-failure` + `RestartSteps=4` + `RestartMaxDelaySec=60s` (systemd 254+); in-process 3-retry loop layered on top |
| R4 — Django AppConfig.ready | ✅ COMPLETE | Existing pattern + 3-retry loop + `sys.exit(1)` on exhaustion + `_initialized` class flag; no `--preload-app` |
| R5 — DRF 404-on-unauth | ✅ COMPLETE | Custom exception handler returning standard `{"detail": "Not found."}` body; do not raise `Http404` from `has_permission()` (DRF #7529) |

All five research items resolved with citation-grounded decisions. Phase 1 design has been authored against these decisions in `data-model.md`, `contracts/`, and `quickstart.md`. The data-model.md draft already references the standard DRF 404 body shape (no change needed); the model_id pin and systemd configuration are now ready to be applied to the implementation files in Phase 2.
