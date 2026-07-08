# Implementation Brief — fix/web-session-hygiene (C.13 resolving-watchdog + session-scoped defines)

Scouted at branch `chore/test-infra-rearm` (= dev @ 9101dddf + test-infra edits outside this area). All line numbers verified against the current working tree on 2026-07-08.

## Part 0 — Verified seams (quoted from current code)

### Seam 1: the `resolving` wedge — `web/game/api.py:1001-1053`

Who sets `resolving` (the ONLY writer repo-wide, confirmed via `rg -n "resolving" web/`):

```python
# web/game/api.py:1014-1023
    if session.status != "active":
        return _error(f"Cannot resolve tick for game in '{session.status}' status")

    # T018: Atomic idempotency guard — lock the row and set status to "resolving"
    try:
        with transaction.atomic():
            locked = GameSession.objects.select_for_update().get(id=session.id, status="active")
            GameSession.objects.filter(id=locked.id).update(status="resolving")
    except GameSession.DoesNotExist:
        return _error("Game is already being resolved or is no longer active", http_status=409)
```

Who clears it — only in-process paths:

```python
# web/game/api.py:1028-1038
    try:
        snapshot = resolve_game_tick(bridge, uuid.UUID(str(session.id)))
    except Exception:
        # Restore status on failure so the game can be retried
        GameSession.objects.filter(id=session.id).update(status="active")
        logger.exception("Tick resolution failed session=%s", session.id)
        return _error("Tick resolution failed", http_status=500)

    # Update session tick and restore active status
    new_tick = snapshot.get("tick", session.current_tick + 1)
    GameSession.objects.filter(id=session.id).update(current_tick=new_tick, status="active")
```

**The wedge**: if the worker dies (OOM/SIGKILL/deploy restart) after the atomic block commits `status="resolving"` but before line 1032/1038 runs, no surviving process ever restores the status. Every subsequent request is then rejected: resolve → api.py:1014 (`'resolving'` != `'active'`, HTTP 400); pause → api.py:327; verb submission → api.py:1139 (`BaseVerbActionView.post`: `if session.status != "active": return _error_with_code(..., "ACTION_GAME_NOT_ACTIVE")`); resume → api.py:340 requires `'paused'`. The session is permanently unplayable. `tick_resolver.resolve_game_tick` (web/game/tick_resolver.py:13-32) is a thin pass-through with no status logic — everything lives in this view.

### Seam 2: global metadata read — `web/game/engine_bridge.py:1911-1919`

```python
# web/game/engine_bridge.py:1910-1919 (inside EngineBridge.resolve_tick)
        state, graph = self.hydrate_state(session_id)

        # Load defines from the session's stored config
        metadata_raw = self._persistence.get_metadata("game_defines_json")
        if metadata_raw is not None:
            import json

            game_defines = GameDefines(**json.loads(metadata_raw))
        else:
            game_defines = GameDefines()
```

`RuntimePersistence.get_metadata(key)` takes NO session_id (src/babylon/persistence/protocols.py:219-228). The Postgres implementation is truly global — a sentinel-session JSONB blob shared by every session in the database:

```python
# src/babylon/persistence/postgres_runtime/_legacy.py:376-396 (set_metadata; get_metadata mirrors at 398-420)
    def set_metadata(self, key: str, value: str) -> None:
        """Store a key-value metadata pair.

        Uses a sentinel session row in tick_log at tick=-1 to store metadata
        as a JSONB dict, accumulating key-value pairs.
        ...
        """
        _sentinel = UUID("00000000-0000-0000-0000-000000000000")
```

**Metadata table schema**: there is NO session-scoped metadata table. But session-scoped storage for defines already exists — the `game_session.game_defines_json` JSONB column:

```sql
-- src/babylon/persistence/postgres_schema.py:40-53
CREATE TABLE IF NOT EXISTS game_session (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ...
    game_defines_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ...
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
)
```

It is WRITTEN at creation (engine_bridge.py:777-783 → `create_session(... game_defines_json=game_defines.model_dump() ...)`; INSERT at _legacy.py:979-996) and READABLE via `PostgresRuntime.get_session` (`SELECT * FROM game_session WHERE id = %s`, _legacy.py:1031-1036, returns dict — psycopg maps JSONB→dict) — but never read back at resolve time.

**Severity note (see drift alerts)**: repo-wide, NOTHING ever calls `set_metadata("game_defines_json", ...)` (all `set_metadata` callers: `engine/observers/session_recorder.py:111-147` and `persistence_observer.py:86-125`, keys `config`/`start_tick`/`status`/`end_tick`). So in production `metadata_raw` is always `None` → per-session defines are silently DISCARDED and library defaults run every tick. The cross-session contamination channel is real but currently dormant; the live bug is defines-ignored. Both are fixed by the same change.

### Seam 3: GameSession timestamps — `web/game/models.py:24-41`

```python
# web/game/models.py:27-34
    current_tick = models.IntegerField(default=0)
    status = models.CharField(max_length=16, default="active")
    ...
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

`updated_at` exists (model + Postgres DDL + apps.py:129 stub DDL + both test conftest DDLs). **Load-bearing caveat**: every status write in api.py uses `QuerySet.update()` (lines 329, 342, 1021, 1032, 1038), which BYPASSES Django's `auto_now`, and the Postgres table has no `ON UPDATE` trigger — so `updated_at` is frozen at INSERT time in the web flow. (`_legacy.py:1038-1044 update_session_status` does `SET updated_at = now()` but the web layer never calls it.) A staleness threshold on `updated_at` only works if the resolve transitions stamp it explicitly. `USE_TZ = True` (web/babylon_web/settings/base.py:135) — use `django.utils.timezone.now()`.

### Seam 4: routing + view + command conventions

- URL style: `path("games/<str:game_id>/pause/", api.game_pause, name="game-pause")` — web/game/urls.py:26-27. Recover route slots after line 27.
- View pattern to copy — `game_resume`, api.py:333-343: `@api_view(["POST"])` + `@permission_classes([IsAuthenticated])` + `_get_session_or_none(game_id, request.user.id)` (api.py:1096-1106, owner-scoped) + `_error()` / `_envelope()` (api.py:108-140) + `log_game_event` (web/game/log_handler.py:25).
- Event categories: `GameEventLog.EventCategory` (models.py:90-99) has GAME_CREATE/GAME_PAUSE/GAME_RESUME/TICK_RESOLVE/... — no recover category yet. `GameEventLog` IS Django-managed (migrations exist, latest is `0011_communitysnapshot_economicsummary_edgesnapshot_and_more.py`), so adding a choice produces migration `0012_*` (metadata-only AlterField).
- Management commands live in `web/game/management/commands/` (NO `__init__.py` in either dir — match that). Convention per `seed_initial_game.py:25-97`: module docstring with `Usage::`, `class Command(BaseCommand)` with class docstring, `help`, typed `add_arguments(self, parser: Any)`, `handle(self, *_args: object, **options: Any) -> None`, late imports inside `handle`, `self.stdout.write(self.style.SUCCESS(...))`.
- Command tests: `tests/unit/web/test_seed_hex_data.py` — plain pytest functions, `db` fixture, `from django.core.management import call_command`.
- Test env: pytest ini sets `DJANGO_SETTINGS_MODULE = "babylon_web.settings.testing"` and `pythonpath = ["src", "web"]` (pyproject.toml:131-136). `tests/unit/web/conftest.py:88-93` flips the unmanaged models to `managed=True` and creates the tables (session-scoped autouse fixture at :178-189; game_session DDL incl. `updated_at` at :96-108).

## Part 1 — Design

Two independent fixes on one branch, committed separately (per repo commit-per-unit rule).

**Fix A (metadata scoping)**: `EngineBridge.resolve_tick` reads defines from the session's own `game_session.game_defines_json` via the persistence layer's `get_session`, using the same `getattr`-guard pattern already used in `hydrate_state` (engine_bridge.py:819-826: `session_getter = getattr(self._persistence, "get_session", None)` / `if callable(session_getter)`). Falls back to `GameDefines()` when the store lacks `get_session` (StubEngineBridge path) or the row/column is missing. Handles both dict (psycopg JSONB) and str (SQLite TEXT) payloads. The global `get_metadata("game_defines_json")` read is deleted.

**Fix B (resolving watchdog)**:
1. Every status transition in `resolve_tick` (and pause/resume for consistency) explicitly stamps `updated_at=timezone.now()` so `updated_at` becomes an honest "last transition" clock.
2. `POST /api/games/{id}/recover/` — owner-scoped; only valid from `status == "resolving"`; refuses (409) while the session has been resolving for less than `RESOLVING_STALE_SECONDS` (default 120 s, overridable via Django setting `GAME_RESOLVING_STALE_SECONDS`) so it cannot race a live in-flight resolve; resets to `active`, logs a `game_recover` event.
3. `python manage.py sweep_stale_sessions [--threshold-seconds 120] [--dry-run]` — bulk variant for cron/post-deploy; resets all sessions with `status="resolving", updated_at < now - threshold`.

Threshold rationale: a real tick resolve is seconds (single-county) to low tens of seconds; 120 s is comfortably past any legitimate resolve while short enough that a player can self-serve recovery. The conditional filter `.filter(id=..., status="resolving").update(...)` makes recovery race-safe against a resolve that completes concurrently (the completing resolve will have already set `active`; the recover update then matches 0 rows — harmless).

## Part 2 — Implementation steps (TDD: write Part 3 RED tests first)

### Step A1 — `web/game/engine_bridge.py`: session-scoped defines helper

Add `import json` to the module import block (engine_bridge.py:14 area; it is currently only imported inline at :1915 — remove that inline import when replacing the block). Then add a module-level helper directly after `_fetch_session_rng_seed_from_pool` (after line 129), matching its docstring/degrade style:

```python
def _fetch_session_game_defines(persistence: Any, session_id: UUID) -> GameDefines:
    """Read this session's GameDefines from its ``game_session`` row (C.13).

    Defines are stored per-session in ``game_session.game_defines_json``
    at creation (see :meth:`EngineBridge.create_game`). The old code read
    the GLOBAL ``get_metadata("game_defines_json")`` blob — a key nothing
    ever wrote, and one shared by every session in the database — so
    per-session defines were silently ignored. Falls back to library
    defaults when the persistence layer has no session store
    (StubEngineBridge / SQLite dev) or the row is missing.
    """
    session_getter = getattr(persistence, "get_session", None)
    if not callable(session_getter):
        return GameDefines()
    try:
        row = session_getter(session_id)
    except Exception:  # noqa: BLE001 — non-fatal; defaults are safe
        logger.exception("Failed to read game_defines_json for session %s", session_id)
        return GameDefines()
    if not isinstance(row, dict):
        return GameDefines()
    raw = row.get("game_defines_json")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            logger.exception("Malformed game_defines_json for session %s", session_id)
            return GameDefines()
    if isinstance(raw, dict) and raw:
        return GameDefines(**raw)
    return GameDefines()
```

(`except Exception: # noqa: BLE001` + `logger.exception` is the established degrade idiom in this file — see :127-129 and :176-178. `GameDefines(**{})` equals `GameDefines()`, so the empty-JSONB-default case is safe either way.)

Replace engine_bridge.py:1912-1919 (the comment + `metadata_raw` block quoted in Seam 2) with:

```python
        # Load defines from the session's own stored config (session-scoped;
        # the old global metadata key both leaked across sessions and was
        # never written, so stored defines were silently ignored)
        game_defines = _fetch_session_game_defines(self._persistence, session_id)
```

Nothing else consumes `get_metadata("game_defines_json")` (repo-wide rg confirmed), so no other call sites change.

### Step B1 — `web/game/api.py`: stamp `updated_at` + constant

Imports (api.py:17-25 block): add `from django.conf import settings as django_settings` and `from django.utils import timezone`. Module constant near the resolve section (or after `DEFAULT_ZOOM`, api.py:374, matching the existing module-constant style):

```python
# C.13: a worker killed mid-resolve leaves status='resolving' with no
# surviving process to restore it. Sessions resolving longer than this
# are considered wedged and eligible for recovery.
RESOLVING_STALE_SECONDS: int = getattr(django_settings, "GAME_RESOLVING_STALE_SECONDS", 120)
```

Edit the three `.update()` calls in `resolve_tick`:
- api.py:1021 → `GameSession.objects.filter(id=locked.id).update(status="resolving", updated_at=timezone.now())`
- api.py:1032 → `GameSession.objects.filter(id=session.id).update(status="active", updated_at=timezone.now())`
- api.py:1038 → `GameSession.objects.filter(id=session.id).update(current_tick=new_tick, status="active", updated_at=timezone.now())`

Also stamp pause (api.py:329) and resume (api.py:342) the same way — cheap, keeps the clock honest for any future status-based tooling.

### Step B2 — `web/game/api.py`: recover view (insert after `game_resume`, i.e. after line 343)

```python
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def game_recover(request: Request, game_id: str) -> JsonResponse:
    """POST /api/games/{id}/recover/ — Recover a session wedged in 'resolving'.

    A worker killed mid-resolve (OOM, SIGKILL, deploy restart) commits
    status='resolving' and never restores it (C.13). Once the staleness
    threshold passes, the owner can reset the session to 'active' and retry.
    """
    session = _get_session_or_none(game_id, request.user.id)
    if session is None:
        return _error("Game not found", http_status=404)
    if session.status != "resolving":
        return _error(f"Cannot recover game in '{session.status}' status")
    age_seconds = (timezone.now() - session.updated_at).total_seconds()
    if age_seconds < RESOLVING_STALE_SECONDS:
        return _error(
            "Tick resolution appears to be in progress; retry later",
            http_status=409,
        )
    GameSession.objects.filter(id=session.id, status="resolving").update(
        status="active", updated_at=timezone.now()
    )
    logger.warning(
        "Recovered wedged session=%s (resolving for %.0fs)", session.id, age_seconds
    )
    log_game_event(
        category="game_recover",
        message=f"Recovered from wedged 'resolving' after {age_seconds:.0f}s",
        session_id=session.id,
        user_id=request.user.id,
        tick=session.current_tick,
        correlation_id=getattr(request, "correlation_id", None),
    )
    return _envelope({"status": "active"}, session_id=str(session.id))
```

### Step B3 — `web/game/urls.py`: route (insert after line 27)

```python
    path("games/<str:game_id>/recover/", api.game_recover, name="game-recover"),
```

### Step B4 — `web/game/models.py`: event category + migration

After `GAME_RESUME` (models.py:93): `GAME_RECOVER = "game_recover", "Game Recovered"`. Then `cd web && poetry run python manage.py makemigrations game` → commit the generated `0012_*` (AlterField on `category` choices — metadata only, no SQL DDL change; choices are not DB-enforced but the migration keeps model state consistent).

### Step B5 — `web/game/management/commands/sweep_stale_sessions.py` (new file, conventions per seed_initial_game.py)

```python
"""Management command: reset sessions wedged in 'resolving' (C.13 watchdog).

A worker killed mid-resolve (OOM, SIGKILL, deploy restart) leaves
``game_session.status='resolving'`` with no surviving process to restore
it; every subsequent resolve/pause/action request is rejected. This
sweeper resets sessions that have been 'resolving' longer than the
threshold back to 'active'. Run periodically (cron/systemd timer) or
once after a crashed deploy.

Usage::

    python manage.py sweep_stale_sessions [--threshold-seconds 120] [--dry-run]
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    """Reset game sessions stuck in 'resolving' back to 'active'."""

    help = "Reset game sessions wedged in 'resolving' status (C.13 watchdog)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--threshold-seconds",
            type=int,
            default=120,
            help="Age in seconds before a 'resolving' session counts as wedged (default: 120)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report wedged sessions without modifying them",
        )

    def handle(self, *_args: object, **options: Any) -> None:
        from game.log_handler import log_game_event
        from game.models import GameSession

        cutoff = timezone.now() - dt.timedelta(seconds=options["threshold_seconds"])
        stale = list(
            GameSession.objects.filter(status="resolving", updated_at__lt=cutoff)
        )
        if not stale:
            self.stdout.write("No wedged sessions found")
            return
        for session in stale:
            age = (timezone.now() - session.updated_at).total_seconds()
            if options["dry_run"]:
                self.stdout.write(
                    f"[dry-run] would recover {session.id} (resolving for {age:.0f}s)"
                )
                continue
            GameSession.objects.filter(id=session.id, status="resolving").update(
                status="active", updated_at=timezone.now()
            )
            log_game_event(
                category="game_recover",
                message=f"Sweeper recovered wedged session after {age:.0f}s",
                session_id=session.id,
                tick=session.current_tick,
            )
            self.stdout.write(self.style.SUCCESS(f"Recovered {session.id}"))
```

(Loop is bounded by the queryset size — same pattern as every queryset iteration in this app.)

## Part 3 — Tests

### Existing coverage of this area (do not break)

- `tests/unit/web/test_api.py:280-311` `TestIdempotencyGuard::test_resolve_rejects_resolving_status` — pins the 400/409 rejection of a `resolving` session (this IS the wedge behavior; keep it, it remains correct pre-threshold).
- `tests/unit/web/test_api.py:16-114` `TestURLRouting` — reverse/resolve URL pins; add recover here.
- `tests/unit/web/test_engine_bridge.py:170-231` `TestEngineBridgeResolveTick` + helpers `_make_mock_persistence` (:21-32 — note `mock.get_metadata.return_value = None`, `mock.get_session.return_value = {"scenario": "default"}`) and `_make_mock_new_state` (:379-392). Fix A must keep all green (they will pass: `get_session` returns no `game_defines_json` key → defaults).
- `tests/integration/web/test_game_lifecycle.py` — postgres-gated (`requires_postgres` + `POSTGRES_HOST` env, :17-23), bridge-level, no status-flow coverage.
- **Skipped tests to un-skip: none.** `rg "skip|xfail" tests/unit/web/` finds no skip markers in this area (only a test *named* `test_ready_skips_for_non_postgres` and the env-gated integration module, which stays env-gated).

### NEW tests — write these first, confirm RED, then implement

**1. `tests/unit/web/test_engine_bridge.py` — new class (RED against Fix A):**

```python
@pytest.mark.unit
class TestSessionScopedDefines:
    """C.13: resolve_tick must read GameDefines from the session's own
    game_session row, never from the global metadata blob."""

    @patch("game.engine_bridge.step")
    def test_resolve_tick_uses_session_defines(self, mock_step: MagicMock) -> None:
        """Defines stored on the session row must reach step()."""
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_session.return_value = {
            "scenario": "default",
            "game_defines_json": {"economy": {"extraction_efficiency": 0.5}},
        }
        mock_step.return_value = _make_mock_new_state()
        bridge = EngineBridge(mock_persistence)

        bridge.resolve_tick(uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))

        defines = mock_step.call_args.kwargs["defines"]
        assert defines.economy.extraction_efficiency == 0.5

    @patch("game.engine_bridge.step")
    def test_resolve_tick_ignores_global_metadata_blob(self, mock_step: MagicMock) -> None:
        """Another session's defines in the global metadata key must NOT leak in."""
        import json as json_mod

        mock_persistence = _make_mock_persistence()
        mock_persistence.get_metadata.return_value = json_mod.dumps(
            {"economy": {"extraction_efficiency": 0.1}}
        )
        mock_persistence.get_session.return_value = {
            "scenario": "default",
            "game_defines_json": {},
        }
        mock_step.return_value = _make_mock_new_state()
        bridge = EngineBridge(mock_persistence)

        bridge.resolve_tick(uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))

        defines = mock_step.call_args.kwargs["defines"]
        assert defines.economy.extraction_efficiency == 0.8  # library default, not 0.1

    @patch("game.engine_bridge.step")
    def test_resolve_tick_parses_string_defines(self, mock_step: MagicMock) -> None:
        """SQLite TEXT storage returns a JSON string — must still parse."""
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_session.return_value = {
            "scenario": "default",
            "game_defines_json": '{"economy": {"extraction_efficiency": 0.5}}',
        }
        mock_step.return_value = _make_mock_new_state()
        bridge = EngineBridge(mock_persistence)

        bridge.resolve_tick(uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))

        assert mock_step.call_args.kwargs["defines"].economy.extraction_efficiency == 0.5

    @patch("game.engine_bridge.step")
    def test_resolve_tick_defaults_when_row_missing(self, mock_step: MagicMock) -> None:
        mock_persistence = _make_mock_persistence()
        mock_persistence.get_session.return_value = None
        mock_step.return_value = _make_mock_new_state()
        bridge = EngineBridge(mock_persistence)

        bridge.resolve_tick(uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))

        assert mock_step.call_args.kwargs["defines"].economy.extraction_efficiency == 0.8
```

RED mechanics: today the first test gets 0.8 (get_metadata → None → defaults) and the second gets 0.1 (global blob honored). `extraction_efficiency` default 0.8 verified at `src/babylon/config/defines/economy_basic.py:155-160`; `GameDefines.economy` at `_assembler.py:127`. Note `step` is called with keyword `defines=` (engine_bridge.py:1965-1970), so `call_args.kwargs["defines"]` is safe.

**2. `tests/unit/web/test_api.py` — URL pin (RED: NoReverseMatch) in `TestURLRouting`:**

```python
    def test_game_recover_url(self) -> None:
        url = reverse(
            "game:game-recover",
            kwargs={"game_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert url == "/api/games/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/recover/"
```

**3. `tests/unit/web/test_api.py` — new class (RED: 404 until route+view exist):**

```python
@pytest.mark.unit
@pytest.mark.django_db
class TestRecoverEndpoint:
    """C.13: a session wedged in 'resolving' by a dead worker is recoverable."""

    def _make_session(self, status: str = "resolving") -> tuple[Any, Any]:
        import uuid as uuid_mod

        from django.contrib.auth.models import User
        from django.test import Client

        from game.models import GameSession

        user = User.objects.create_user(username="recuser", password="recpass")  # type: ignore[no-untyped-call]
        client = Client()
        client.login(username="recuser", password="recpass")
        session = GameSession.objects.create(
            id=uuid_mod.uuid4(),
            player_id=user.id,
            scenario="two_node",
            current_tick=3,
            status=status,
        )
        return client, session

    @staticmethod
    def _backdate(session: Any, seconds: int) -> None:
        import datetime as dt

        from django.utils import timezone

        from game.models import GameSession

        # QuerySet.update() bypasses auto_now — exactly why this works.
        GameSession.objects.filter(id=session.id).update(
            updated_at=timezone.now() - dt.timedelta(seconds=seconds)
        )

    def test_recover_resets_stale_resolving_session(self) -> None:
        client, session = self._make_session("resolving")
        self._backdate(session, 600)

        response = client.post(f"/api/games/{session.id}/recover/")

        assert response.status_code == 200
        session.refresh_from_db()
        assert session.status == "active"

    def test_recover_rejects_fresh_resolving_session(self) -> None:
        """A resolve younger than the threshold may still be in flight."""
        client, session = self._make_session("resolving")  # updated_at = now

        response = client.post(f"/api/games/{session.id}/recover/")

        assert response.status_code == 409
        session.refresh_from_db()
        assert session.status == "resolving"

    def test_recover_rejects_active_session(self) -> None:
        client, session = self._make_session("active")
        self._backdate(session, 600)

        response = client.post(f"/api/games/{session.id}/recover/")

        assert response.status_code == 400

    def test_recovered_session_can_resolve_again(self) -> None:
        """End-to-end wedge escape: recover, then resolve succeeds."""
        from unittest.mock import MagicMock

        import game.api

        client, session = self._make_session("resolving")
        self._backdate(session, 600)
        assert client.post(f"/api/games/{session.id}/recover/").status_code == 200

        mock_bridge = MagicMock()
        mock_bridge.resolve_tick.return_value = {"tick": 4, "events": []}
        game.api._bridge_instance = mock_bridge
        try:
            response = client.post(f"/api/games/{session.id}/resolve/")
        finally:
            game.api._bridge_instance = None

        assert response.status_code == 200
        session.refresh_from_db()
        assert session.status == "active"
        assert session.current_tick == 4
```

(Bridge patching via `game.api._bridge_instance` is the documented test seam — api.py:7 and existing usage at test_api.py:265-267. Reset to `None` in `finally` — the module singleton otherwise leaks across tests.)

**4. `tests/unit/web/test_api.py` — updated_at stamping (RED against Step B1):**

```python
@pytest.mark.unit
@pytest.mark.django_db
class TestResolveStampsUpdatedAt:
    """The staleness clock: every resolve transition must touch updated_at."""

    def test_successful_resolve_advances_updated_at(self) -> None:
        # ... create user/client/active session as above, backdate 600s ...
        # patch game.api._bridge_instance with MagicMock resolve_tick -> {"tick": 1}
        before = session_updated_at_after_backdate
        response = client.post(f"/api/games/{session.id}/resolve/")
        assert response.status_code == 200
        session.refresh_from_db()
        assert session.updated_at > before

    def test_failed_resolve_advances_updated_at(self) -> None:
        # same, but mock_bridge.resolve_tick.side_effect = RuntimeError("boom")
        # assert response.status_code == 500, status == "active", updated_at > before
```

**5. `tests/unit/web/test_sweep_stale_sessions.py` (new file, RED: unknown command). Follow test_seed_hex_data.py style:**

```python
"""Tests for the sweep_stale_sessions watchdog command (C.13)."""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from django.core.management import call_command
from django.utils import timezone

from game.models import GameEventLog, GameSession


def _make_session(status: str, age_seconds: int) -> GameSession:
    session = GameSession.objects.create(
        id=uuid.uuid4(), scenario="two_node", current_tick=1, status=status
    )
    GameSession.objects.filter(id=session.id).update(
        updated_at=timezone.now() - dt.timedelta(seconds=age_seconds)
    )
    session.refresh_from_db()
    return session


@pytest.mark.unit
@pytest.mark.django_db
def test_sweeper_recovers_stale_resolving_session() -> None:
    stale = _make_session("resolving", 600)
    fresh = _make_session("resolving", 10)

    call_command("sweep_stale_sessions", "--threshold-seconds", "120")

    stale.refresh_from_db()
    fresh.refresh_from_db()
    assert stale.status == "active"
    assert fresh.status == "resolving"


@pytest.mark.unit
@pytest.mark.django_db
def test_sweeper_ignores_non_resolving_sessions() -> None:
    active = _make_session("active", 600)
    paused = _make_session("paused", 600)

    call_command("sweep_stale_sessions", "--threshold-seconds", "120")

    active.refresh_from_db()
    paused.refresh_from_db()
    assert active.status == "active"
    assert paused.status == "paused"


@pytest.mark.unit
@pytest.mark.django_db
def test_sweeper_dry_run_changes_nothing() -> None:
    stale = _make_session("resolving", 600)

    call_command("sweep_stale_sessions", "--threshold-seconds", "120", "--dry-run")

    stale.refresh_from_db()
    assert stale.status == "resolving"


@pytest.mark.unit
@pytest.mark.django_db
def test_sweeper_logs_recovery_event() -> None:
    stale = _make_session("resolving", 600)

    call_command("sweep_stale_sessions", "--threshold-seconds", "120")

    assert GameEventLog.objects.filter(
        session_id=stale.id, category="game_recover"
    ).exists()
```

## Part 4 — Verification

```bash
# RED phase (before implementing) — expect the new tests to fail:
poetry run pytest tests/unit/web/test_engine_bridge.py -k SessionScopedDefines -vv
poetry run pytest tests/unit/web/test_api.py -k "recover or StampsUpdatedAt" -vv
poetry run pytest tests/unit/web/test_sweep_stale_sessions.py -vv

# GREEN phase — full scoped suite (mise variant writes reports/test-results/):
mise run test:q -- tests/unit/web
poetry run pytest tests/unit/web -vv

# Regression pins that must stay green:
poetry run pytest tests/unit/web/test_api.py::TestIdempotencyGuard -vv
poetry run pytest tests/unit/web/test_engine_bridge.py::TestEngineBridgeResolveTick -vv

# Migration for the EventCategory choice:
cd web && poetry run python manage.py makemigrations game && cd ..
poetry run pytest tests/unit/web/test_models.py -vv   # model pins, if any drift

# Quality gate (mise typecheck runs `mypy src`; web is covered by the
# pre-commit mypy hook with django-stubs — use the hook-safe commit task):
mise run check:quick
mise run commit -- "fix(web): session-scoped GameDefines in resolve_tick (C.13 metadata scoping)"
mise run commit -- "fix(web): recover endpoint + stale-resolving sweeper watchdog (C.13)"

# Optional live proof against Postgres (env-gated integration leg):
POSTGRES_HOST=localhost poetry run pytest tests/integration/web/ -m requires_postgres -vv
```

Commit split: (1) Fix A + its engine_bridge tests; (2) Fix B api/urls/models/migration/command + its tests. Both conventional-commit formatted as above.
