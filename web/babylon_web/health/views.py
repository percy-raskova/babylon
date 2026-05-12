"""Auth-gated ``/health/detail/`` diagnostic endpoint (spec 061 US2, FR-009)."""

from __future__ import annotations

import datetime as _dt
import logging
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from babylon.config.llm_config import (
    CANONICAL_EMBEDDING_DIM,
    CANONICAL_EMBEDDING_MODEL_ID,
)
from babylon_web.health.permissions import IsStaff

if TYPE_CHECKING:
    from rest_framework.request import Request

logger = logging.getLogger(__name__)

_LAST_TICK_CACHE_S = 30.0
_VERSION_CACHE: dict[str, str | None] = {}


def _read_pyproject_version() -> str | None:
    """Read ``project.version`` (or ``tool.poetry.version``) from pyproject.toml.

    Cached after the first read because pyproject.toml never changes at runtime.
    """
    if "version" in _VERSION_CACHE:
        return _VERSION_CACHE["version"]
    try:
        # web/babylon_web/health/views.py → repo root is 3 dirs up.
        pyproject = Path(__file__).resolve().parents[3] / "pyproject.toml"
        if not pyproject.exists():
            _VERSION_CACHE["version"] = None
            return None
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        version = data.get("project", {}).get("version") or data.get("tool", {}).get(
            "poetry", {}
        ).get("version")
        _VERSION_CACHE["version"] = str(version) if version else None
    except Exception:  # noqa: BLE001 — diagnostic field, never blocks request
        logger.exception("Failed to read pyproject.toml version for /health/detail/")
        _VERSION_CACHE["version"] = None
    return _VERSION_CACHE["version"]


def _read_git_sha() -> str | None:
    """Read the current HEAD commit SHA from ``.git/HEAD`` + the referenced ref.

    Returns None on any IO error (the field is diagnostic — never blocks
    the request). Not cached: HEAD can move between calls in a long-lived
    dev process.
    """
    try:
        # web/babylon_web/health/views.py → repo root is 3 dirs up.
        head = Path(__file__).resolve().parents[3] / ".git" / "HEAD"
        if not head.exists():
            return None
        content = head.read_text(encoding="utf-8").strip()
        if content.startswith("ref:"):
            ref = content.removeprefix("ref:").strip()
            ref_path = head.parent / ref
            if ref_path.exists():
                return ref_path.read_text(encoding="utf-8").strip()[:12]
            return None
        # Detached HEAD — the file contains the SHA directly.
        return content[:12]
    except Exception:  # noqa: BLE001
        logger.exception("Failed to read git SHA for /health/detail/")
        return None


class HealthDetailView(APIView):
    """Diagnostic state for operators: bridge identity, boot history,
    database reachability, embedding-model pin, app version + git SHA.

    Spec 061 FR-009 (clarified): only authenticated staff users see
    this payload. Everyone else gets a uniform 404 (handled by
    :func:`babylon_web.health.exceptions.health_obscuring_exception_handler`)
    so the endpoint's existence is not disclosed.

    Cadence note: ``last_tick_resolved_at`` is cached for 30 seconds
    on the view class (per-process) so this endpoint stays cheap to
    poll from monitoring systems.
    """

    permission_classes = [IsAuthenticated, IsStaff]

    # Per-process cache for the last_tick_resolved_at query.
    _last_tick_cache: dict[str, float | str | None] = {
        "value": None,
        "expires_at": 0.0,
    }

    def get(self, request: Request, *_args: Any, **_kwargs: Any) -> Response:  # noqa: ARG002 — DRF protocol
        payload = {
            "status": "ok",
            "engine": self._engine_state(),
            "database": self._database_state(),
            "embedding_model": {
                "model_id": CANONICAL_EMBEDDING_MODEL_ID,
                "dimension": CANONICAL_EMBEDDING_DIM,
            },
            "version": _read_pyproject_version(),
            "git_sha": _read_git_sha(),
        }
        return Response(payload)

    def _engine_state(self) -> dict[str, Any]:
        # Local imports keep this module loadable when game/apps.py is
        # being patched in tests, and isolate the bridge identity from
        # other modules' import time.
        from game import api as game_api
        from game.apps import GameConfig

        bridge = game_api._bridge_instance
        boot_succeeded_at = GameConfig.boot_succeeded_at
        return {
            "implementation": type(bridge).__name__ if bridge is not None else None,
            "boot_attempts": GameConfig.last_boot_attempts,
            "boot_succeeded_at": (boot_succeeded_at.isoformat() if boot_succeeded_at else None),
            "last_tick_resolved_at": self._last_tick_resolved_at(),
        }

    def _database_state(self) -> dict[str, Any]:
        from game import api as game_api

        bridge = game_api._bridge_instance
        if bridge is None:
            return {"reachable": False, "pool_size": None}

        persistence = getattr(bridge, "_persistence", None)
        pool = getattr(persistence, "_pool", None) if persistence is not None else None
        if pool is None:
            return {"reachable": False, "pool_size": None}

        reachable = False
        pool_size: int | None = None
        try:
            stats = pool.get_stats()
            pool_size = int(stats.get("pool_size", 0)) if isinstance(stats, dict) else None
        except Exception:  # noqa: BLE001
            pool_size = None
        try:
            with pool.connection() as conn:
                conn.execute("SELECT 1")
            reachable = True
        except Exception:  # noqa: BLE001
            reachable = False
        return {"reachable": reachable, "pool_size": pool_size}

    @classmethod
    def _last_tick_resolved_at(cls) -> str | None:
        now = _dt.datetime.now(_dt.UTC).timestamp()
        expires_at_raw = cls._last_tick_cache.get("expires_at") or 0.0
        expires_at = float(expires_at_raw) if isinstance(expires_at_raw, int | float) else 0.0
        if now < expires_at:
            cached = cls._last_tick_cache.get("value")
            if cached is None or isinstance(cached, str):
                return cached
            return str(cached)

        fresh: str | None = None
        try:
            from game import api as game_api

            bridge = game_api._bridge_instance
            persistence = getattr(bridge, "_persistence", None) if bridge else None
            pool = getattr(persistence, "_pool", None) if persistence else None
            if pool is not None:
                with pool.connection() as conn, conn.cursor() as cur:
                    cur.execute(
                        "SELECT max(updated_at) FROM game_session WHERE updated_at IS NOT NULL"
                    )
                    row = cur.fetchone()
                    raw = row[0] if row else None
                    if raw is not None:
                        fresh = raw.isoformat() if hasattr(raw, "isoformat") else str(raw)
        except Exception:  # noqa: BLE001
            fresh = None

        cls._last_tick_cache["value"] = fresh
        cls._last_tick_cache["expires_at"] = now + _LAST_TICK_CACHE_S
        return fresh
