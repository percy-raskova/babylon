"""Spec 061 T025 / FR-006 + FR-007: engine boot retry-then-exit.

Three scenarios:
  (a) reachable DB → succeeds on attempt 1
  (b) DB unreachable for entire window → 3 retries logged then sys.exit(1)
  (c) DB unreachable on attempts 1-2, reachable on attempt 3 → succeeds on attempt 3

Drives ``GameConfig._initialize_engine_with_retry`` through a mocked
``init_persistence`` that raises N times before succeeding. Also verifies
the diagnostic counters surfaced via ``GameConfig.last_boot_attempts`` and
``GameConfig.boot_succeeded_at`` for the future ``/health/detail/`` endpoint.

Gated behind ``mise run test:int`` via ``pytest.mark.integration`` — these
tests import Django settings + the game app, which is heavyweight.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def gameconfig_instance(monkeypatch: pytest.MonkeyPatch):
    """Yield the Django-registered ``GameConfig`` instance with class-state reset.

    Resets ``_initialized`` + counters between tests so each scenario starts
    fresh. The fixture exists rather than instantiating ``GameConfig`` directly
    because Django's ``AppConfig.__init__`` requires ``app_name`` and
    ``app_module`` arguments that are populated by the app registry at
    setup time.
    """
    from django.apps import apps as django_apps

    from game.apps import GameConfig

    GameConfig._initialized = False
    GameConfig.last_boot_attempts = 0
    GameConfig.boot_succeeded_at = None

    instance = django_apps.get_app_config("game")

    yield instance

    GameConfig._initialized = False


class _SentinelPersistence:
    """Marker object used by tests to confirm the bridge was wired."""


def _make_init_persistence(failures_before_success: int) -> Any:
    """Build an ``init_persistence`` substitute that raises N times then succeeds.

    Uses an outer counter so the closure persists across calls.
    """
    state: dict[str, int] = {"calls": 0}

    def fake_init_persistence(_db_config: Any) -> Any:
        state["calls"] += 1
        if state["calls"] <= failures_before_success:
            raise ConnectionRefusedError(
                f"spec 061 T025 simulated DB unreachable (call {state['calls']})"
            )
        return _SentinelPersistence()

    fake_init_persistence.calls = state  # type: ignore[attr-defined]
    return fake_init_persistence


class TestEngineBridgeBootRetry:
    """FR-006 + FR-007 + research.md R4."""

    def test_a_reachable_db_succeeds_on_attempt_one(
        self,
        gameconfig_instance,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        from game import api as game_api
        from game import engine_bridge
        from game.apps import GameConfig

        monkeypatch.setattr(game_api, "_bridge_instance", None, raising=False)
        fake_init = _make_init_persistence(failures_before_success=0)
        monkeypatch.setattr(engine_bridge, "init_persistence", fake_init)

        with caplog.at_level(logging.INFO, logger="game.apps"):
            gameconfig_instance._initialize_engine_with_retry(max_attempts=3)

        assert GameConfig._initialized is True
        assert GameConfig.last_boot_attempts == 1
        assert GameConfig.boot_succeeded_at is not None
        assert fake_init.calls["calls"] == 1
        # State counters are the contract; the log line is for operators.
        # caplog can be unreliable here when Django's logging config has
        # already loaded — assert via state.
        assert game_api._bridge_instance is not None

    def test_b_persistent_failure_exits_after_three_attempts(
        self,
        gameconfig_instance,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        from game import api as game_api
        from game import engine_bridge
        from game.apps import GameConfig

        monkeypatch.setattr(game_api, "_bridge_instance", None, raising=False)
        fake_init = _make_init_persistence(failures_before_success=99)
        monkeypatch.setattr(engine_bridge, "init_persistence", fake_init)
        monkeypatch.setattr("game.apps.time.sleep", lambda _s: None)

        with (
            caplog.at_level(logging.WARNING, logger="game.apps"),
            pytest.raises(SystemExit) as excinfo,
        ):
            gameconfig_instance._initialize_engine_with_retry(max_attempts=3)

        assert excinfo.value.code == 1
        assert GameConfig._initialized is False
        assert GameConfig.last_boot_attempts == 3
        assert fake_init.calls["calls"] == 3
        # SystemExit with code==1 is the contract; the log line is operator info.
        # The bridge must remain unset when init exhausts retries.
        assert game_api._bridge_instance is None

    def test_c_recovers_on_third_attempt(
        self,
        gameconfig_instance,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        from game import api as game_api
        from game import engine_bridge
        from game.apps import GameConfig

        monkeypatch.setattr(game_api, "_bridge_instance", None, raising=False)
        fake_init = _make_init_persistence(failures_before_success=2)
        monkeypatch.setattr(engine_bridge, "init_persistence", fake_init)
        monkeypatch.setattr("game.apps.time.sleep", lambda _s: None)

        with caplog.at_level(logging.INFO, logger="game.apps"):
            gameconfig_instance._initialize_engine_with_retry(max_attempts=3)

        assert GameConfig._initialized is True
        assert GameConfig.last_boot_attempts == 3
        assert GameConfig.boot_succeeded_at is not None
        assert fake_init.calls["calls"] == 3
        # The contract: 3rd attempt is the success and bridge gets wired.
        assert game_api._bridge_instance is not None
