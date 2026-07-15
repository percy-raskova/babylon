"""Spec-111: LLM narrator service at the bridge boundary.

Constitution II.5 (AI narrates, never adjudicates) + III.6 (model pinning)
+ III.11 (loud failure, no fabricated values).

No live LLM calls anywhere in this file — the provider is always a mock
(``babylon.intelligence.ai.llm_provider.MockLLM`` for the DRY-reuse happy path, or
``MagicMock(spec=LLMProvider)`` for the degradation path per tests/README.md).
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from babylon.config import LLMConfig
from babylon.intelligence.ai.llm_provider import LLMProvider, MockLLM
from babylon.models import EdgeType, Relationship, SocialClass, SocialRole, WorldState
from babylon.models.entity_registry import COMPRADOR_ID, PERIPHERY_WORKER_ID
from babylon.models.events import TransmissionEvent, UprisingEvent
from game.models import GameSession
from game.narrative_service import (
    FEATURE_FLAG_ENV,
    PROMPT_VERSION,
    NarrativeResult,
    NarrativeService,
    is_enabled,
)

# --------------------------------------------------------------------------- #
# Fixtures — mirrors tests/unit/ai/test_dual_narrative.py's WorldState setup
# --------------------------------------------------------------------------- #


@pytest.fixture
def worker() -> SocialClass:
    return SocialClass(
        id=PERIPHERY_WORKER_ID,
        name="Worker",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=0.5,
        ideology=0.0,
        organization=0.1,
        repression_faced=0.5,
        subsistence_threshold=0.3,
    )


@pytest.fixture
def owner() -> SocialClass:
    return SocialClass(
        id=COMPRADOR_ID,
        name="Owner",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=10.0,
        ideology=0.5,
        organization=0.7,
        repression_faced=0.1,
        subsistence_threshold=0.1,
    )


@pytest.fixture
def exploitation_edge() -> Relationship:
    return Relationship(
        source_id=PERIPHERY_WORKER_ID,
        target_id=COMPRADOR_ID,
        edge_type=EdgeType.EXPLOITATION,
        value_flow=0.0,
        tension=0.0,
    )


@pytest.fixture
def previous_state(
    worker: SocialClass, owner: SocialClass, exploitation_edge: Relationship
) -> WorldState:
    return WorldState(
        tick=0,
        entities={PERIPHERY_WORKER_ID: worker, COMPRADOR_ID: owner},
        relationships=[exploitation_edge],
    )


@pytest.fixture
def uprising_event() -> UprisingEvent:
    return UprisingEvent(
        tick=1,
        node_id=PERIPHERY_WORKER_ID,
        trigger="spark",
        agitation=0.9,
        repression=0.7,
    )


@pytest.fixture
def new_state_with_uprising(
    previous_state: WorldState, uprising_event: UprisingEvent
) -> WorldState:
    return previous_state.model_copy(update={"tick": 1, "events": [uprising_event]})


@pytest.fixture
def new_state_no_events(previous_state: WorldState) -> WorldState:
    return previous_state.model_copy(update={"tick": 1, "events": []})


@pytest.fixture
def new_state_non_significant(previous_state: WorldState) -> WorldState:
    """A tick whose only event is not in NarrativeDirector.SIGNIFICANT_EVENT_TYPES."""
    event = TransmissionEvent(
        tick=1,
        target_id=PERIPHERY_WORKER_ID,
        source_id=COMPRADOR_ID,
        delta=0.05,
        solidarity_strength=0.5,
    )
    return previous_state.model_copy(update={"tick": 1, "events": [event]})


@pytest.fixture
def session_id() -> uuid.UUID:
    return uuid.uuid4()


# --------------------------------------------------------------------------- #
# Feature flag
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestFeatureFlag:
    def test_default_off(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(FEATURE_FLAG_ENV, raising=False)
        # Django is configured in this test session with BABYLON_LLM_NARRATOR
        # sourced from the (unset) env var — see web/babylon_web/settings/base.py.
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", False, raising=False)
        assert is_enabled() is False

    def test_django_setting_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", True, raising=False)
        assert is_enabled() is True

    def test_django_setting_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", False, raising=False)
        assert is_enabled() is False

    @pytest.mark.parametrize("value", ["1", "true", "True", "yes", "on"])
    def test_env_var_true_values(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        """The Django-independent env-var reader recognizes all truthy spellings.

        (``is_enabled()`` itself always prefers the Django setting when
        Django is configured — which it always is inside web/ — so this
        exercises ``_env_flag_enabled`` directly rather than faking Django's
        read-only ``settings.configured`` property.)
        """
        from game.narrative_service import _env_flag_enabled

        monkeypatch.setenv(FEATURE_FLAG_ENV, value)
        assert _env_flag_enabled() is True

    def test_env_var_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from game.narrative_service import _env_flag_enabled

        monkeypatch.delenv(FEATURE_FLAG_ENV, raising=False)
        assert _env_flag_enabled() is False


# --------------------------------------------------------------------------- #
# schedule() — flag off is a true no-op
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestScheduleFlagOff:
    def test_schedule_returns_none_when_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        session_id: uuid.UUID,
        previous_state: WorldState,
        new_state_with_uprising: WorldState,
    ) -> None:
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", False, raising=False)
        service = NarrativeService(llm=MockLLM(default_response="should never be seen"))

        future = service.schedule(session_id, previous_state, new_state_with_uprising)

        assert future is None
        assert service.get_result(session_id, tick=1) is None

    def test_augment_feed_unchanged_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch, session_id: uuid.UUID
    ) -> None:
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", False, raising=False)
        service = NarrativeService()
        feed = {"meta": {}, "index": [], "euphemisms": {}, "story": None, "filters": []}

        result = service.augment_feed(feed, session_id, tick=1)

        assert result == feed
        assert result is feed, "flag-off must return the identical object (no copy needed)"


# --------------------------------------------------------------------------- #
# schedule() — flag on, happy path
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestScheduleHappyPath:
    @pytest.mark.django_db(transaction=True)
    def test_generates_dual_narrative_for_significant_event(
        self,
        monkeypatch: pytest.MonkeyPatch,
        session_id: uuid.UUID,
        previous_state: WorldState,
        new_state_with_uprising: WorldState,
    ) -> None:
        """``transaction=True``: ``schedule()`` runs generation (including
        the task-B4 persistence step) on a background thread. pytest-django's
        default rollback-based isolation leaves the row-creating transaction
        open on the main thread's connection, which the worker thread's own
        connection then sees as locked rather than committed — verified
        empirically. ``transaction=True`` commits for real instead, which is
        what a genuinely separate thread needs to see the row.
        """
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", True, raising=False)
        GameSession.objects.create(id=session_id, scenario="narrative-service-test")
        mock_llm = MockLLM(responses=["Corporate narrative", "Liberated narrative"])
        service = NarrativeService(llm=mock_llm)

        future = service.schedule(session_id, previous_state, new_state_with_uprising)
        assert future is not None
        future.result(timeout=5)  # block the TEST (not resolve_tick) until it lands

        result = service.get_result(session_id, tick=1)
        assert result is not None
        assert result.degraded is False
        assert result.tick == 1
        assert result.prompt_version == PROMPT_VERSION
        assert result.model_id  # non-empty — Constitution III.6 model pin
        assert result.corporate == "Corporate narrative"
        assert result.liberated == "Liberated narrative"
        assert result.error is None

    def test_no_significant_event_is_not_a_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
        session_id: uuid.UUID,
        previous_state: WorldState,
        new_state_no_events: WorldState,
    ) -> None:
        """Empty domain != failure (III.11): a quiet tick degrades=False."""
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", True, raising=False)
        service = NarrativeService(llm=MockLLM(default_response="unused"))

        future = service.schedule(session_id, previous_state, new_state_no_events)
        assert future is not None
        future.result(timeout=5)

        result = service.get_result(session_id, tick=1)
        assert result is not None
        assert result.degraded is False
        assert result.corporate is None
        assert result.liberated is None

    def test_non_significant_event_is_not_a_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
        session_id: uuid.UUID,
        previous_state: WorldState,
        new_state_non_significant: WorldState,
    ) -> None:
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", True, raising=False)
        service = NarrativeService(llm=MockLLM(default_response="unused"))

        future = service.schedule(session_id, previous_state, new_state_non_significant)
        assert future is not None
        future.result(timeout=5)

        result = service.get_result(session_id, tick=1)
        assert result is not None
        assert result.degraded is False


# --------------------------------------------------------------------------- #
# schedule() — flag on, degradation path (III.11 loud failure)
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestScheduleDegradation:
    def test_provider_failure_produces_explicit_degraded_marker(
        self,
        monkeypatch: pytest.MonkeyPatch,
        session_id: uuid.UUID,
        previous_state: WorldState,
        new_state_with_uprising: WorldState,
    ) -> None:
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", True, raising=False)

        failing_llm = MagicMock(spec=LLMProvider)
        failing_llm.name = "FailingProvider"
        failing_llm.generate.side_effect = RuntimeError("simulated timeout")
        service = NarrativeService(llm=failing_llm)

        future = service.schedule(session_id, previous_state, new_state_with_uprising)
        assert future is not None
        future.result(timeout=5)  # the future itself must not raise

        result = service.get_result(session_id, tick=1)
        assert result is not None
        assert result.degraded is True
        assert result.corporate is None
        assert result.liberated is None
        assert result.error is not None
        assert "simulated timeout" in result.error

    def test_schedule_never_raises_on_provider_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
        session_id: uuid.UUID,
        previous_state: WorldState,
        new_state_with_uprising: WorldState,
    ) -> None:
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", True, raising=False)

        failing_llm = MagicMock(spec=LLMProvider)
        failing_llm.name = "FailingProvider"
        failing_llm.generate.side_effect = RuntimeError("boom")
        service = NarrativeService(llm=failing_llm)

        # schedule() itself must not raise even though generation will fail
        # on the background thread.
        future = service.schedule(session_id, previous_state, new_state_with_uprising)
        assert future is not None
        future.result(timeout=5)


# --------------------------------------------------------------------------- #
# schedule() — async, non-blocking
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestScheduleNonBlocking:
    def test_schedule_returns_before_generation_completes(
        self,
        monkeypatch: pytest.MonkeyPatch,
        session_id: uuid.UUID,
        previous_state: WorldState,
        new_state_with_uprising: WorldState,
    ) -> None:
        """schedule() must return immediately — narrative lands later."""
        import threading

        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", True, raising=False)

        release = threading.Event()

        class _BlockingLLM:
            name = "BlockingProvider"

            def generate(
                self,
                prompt: str,
                system_prompt: str | None = None,
                temperature: float = 0.7,
            ) -> str:
                release.wait(timeout=5)
                return "delayed narrative"

        service = NarrativeService(llm=_BlockingLLM())

        future = service.schedule(session_id, previous_state, new_state_with_uprising)
        assert future is not None

        # The result must NOT be ready yet — schedule() did not block on
        # the (still-waiting) generate() call.
        assert service.get_result(session_id, tick=1) is None
        assert future.done() is False

        release.set()
        future.result(timeout=5)

        assert service.get_result(session_id, tick=1) is not None


# --------------------------------------------------------------------------- #
# _resolve_llm() — provider factory wiring (program-20 Track B)
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestProviderFactoryWiring:
    """No injected llm= → the provider comes from build_llm_provider().

    Program 20 Track B rewired NarrativeService._resolve_llm from a
    hardcoded DeepSeekClient() to build_llm_provider() (selects on
    LLMConfig.PROVIDER). With PROVIDER monkeypatched to "mock", the
    factory-built MockLLM's fixed default response landing in the cached
    NarrativeResult proves the factory is actually consulted.
    """

    @pytest.mark.django_db(transaction=True)
    def test_unset_llm_resolves_via_factory(
        self,
        monkeypatch: pytest.MonkeyPatch,
        session_id: uuid.UUID,
        previous_state: WorldState,
        new_state_with_uprising: WorldState,
    ) -> None:
        """``transaction=True`` — see the docstring on
        ``TestScheduleHappyPath.test_generates_dual_narrative_for_significant_event``
        for why a background-thread persistence write needs it.
        """
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", True, raising=False)
        monkeypatch.setattr(LLMConfig, "PROVIDER", "mock")
        GameSession.objects.create(id=session_id, scenario="narrative-service-test")
        service = NarrativeService()  # deliberately NO llm= — exercises the factory path

        # Direct check: the lazily-resolved provider is the factory's MockLLM,
        # not a hardcoded DeepSeekClient (which would raise LLM_001 here —
        # no API key is configured in the test environment).
        assert service._resolve_llm().name == "MockLLM"

        # End-to-end: the full schedule/_generate path uses the factory-built
        # provider, and its canonical default response lands in the result.
        future = service.schedule(session_id, previous_state, new_state_with_uprising)
        assert future is not None
        future.result(timeout=5)

        result = service.get_result(session_id, tick=1)
        assert result is not None
        assert result.degraded is False
        assert result.corporate == "Mock LLM response"
        assert result.liberated == "Mock LLM response"


# --------------------------------------------------------------------------- #
# augment_feed()
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestAugmentFeed:
    _FEED = {"meta": {"tick": 1}, "index": [], "euphemisms": {}, "story": None, "filters": []}

    def test_no_result_yet_leaves_feed_unchanged(
        self, monkeypatch: pytest.MonkeyPatch, session_id: uuid.UUID
    ) -> None:
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", True, raising=False)
        service = NarrativeService()

        result = service.augment_feed(dict(self._FEED), session_id, tick=1)

        assert "llm_narrative" not in result
        assert result["meta"] == self._FEED["meta"]

    def test_healthy_result_adds_llm_narrative_key(
        self, monkeypatch: pytest.MonkeyPatch, session_id: uuid.UUID
    ) -> None:
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", True, raising=False)
        service = NarrativeService()
        service._results[(session_id, 1)] = NarrativeResult(
            tick=1,
            model_id="deepseek-chat",
            prompt_version=PROMPT_VERSION,
            degraded=False,
            corporate="corp text",
            liberated="lib text",
        )

        result = service.augment_feed(dict(self._FEED), session_id, tick=1)

        assert result["llm_narrative"]["degraded"] is False
        assert result["llm_narrative"]["corporate"] == "corp text"
        assert result["llm_narrative"]["liberated"] == "lib text"
        assert result["llm_narrative"]["model_id"] == "deepseek-chat"
        assert result["llm_narrative"]["prompt_version"] == PROMPT_VERSION
        # Deterministic feed's own fields are untouched.
        assert result["index"] == self._FEED["index"]
        assert result["story"] == self._FEED["story"]

    def test_degraded_result_adds_explicit_marker_without_touching_feed(
        self, monkeypatch: pytest.MonkeyPatch, session_id: uuid.UUID
    ) -> None:
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", True, raising=False)
        service = NarrativeService()
        service._results[(session_id, 1)] = NarrativeResult(
            tick=1,
            model_id="deepseek-chat",
            prompt_version=PROMPT_VERSION,
            degraded=True,
            error="simulated timeout",
        )
        original_feed = dict(self._FEED)

        result = service.augment_feed(dict(self._FEED), session_id, tick=1)

        assert result["llm_narrative"]["degraded"] is True
        assert result["llm_narrative"]["error"] == "simulated timeout"
        assert result["llm_narrative"]["corporate"] is None
        assert result["llm_narrative"]["liberated"] is None
        # The deterministic feed itself is the fallback — untouched.
        for key in original_feed:
            assert result[key] == original_feed[key]
