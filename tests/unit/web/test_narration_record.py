"""NarrationRecord persistence (program-20 Track B, task B4).

Two layers:

* Model-level (``TestNarrationRecordModel``): plain ORM roundtrip + the
  ``(session, tick, beat_id)`` uniqueness constraint — the brief's Step 1.
* Wiring-level (``TestNarrativeServicePersistence``): ``NarrativeService``
  actually writes ``NarrationRecord`` rows on both the success and
  degraded completion paths, keyed idempotently, with the documented
  loud-missing-session behavior for the success path (III.11).

Wiring tests call ``NarrativeService._generate`` directly (same thread as
the test) rather than going through ``schedule()``'s background thread
pool: cross-thread DB visibility under pytest-django's default
transactional test isolation requires ``django_db(transaction=True)``
(verified empirically — the rollback-based default leaves the writing
transaction open, so a second thread's connection sees the row as locked,
not merely absent). Calling ``_generate`` synchronously sidesteps that
entirely and is sufficient to exercise the persistence wiring itself;
``test_narrative_service.py`` separately exercises the real
``schedule()``/thread-pool path (with ``transaction=True`` where it now
touches the database).
"""

from __future__ import annotations

import uuid

import pytest

from game.models import GameSession, NarrationRecord


@pytest.mark.django_db
class TestNarrationRecordModel:
    def test_record_roundtrip(self) -> None:
        session = GameSession.objects.create(scenario="test")
        rec = NarrationRecord.objects.create(
            session=session,
            tick=3,
            beat_id="wire-3",
            scope="tick",
            subject_ref=None,
            headline="RENT EXTRACTED",
            body="…",
            register="wire",
            model_id="@cf/openai/gpt-oss-20b",
            prompt_version="sha256:abc123def456",
        )
        assert list(session.narration_records.all()) == [rec]

    def test_unique_beat_per_session_tick(self) -> None:
        from django.db import IntegrityError

        session = GameSession.objects.create(scenario="test")
        kwargs = {
            "session": session,
            "tick": 1,
            "beat_id": "wire-1",
            "scope": "tick",
            "headline": "h",
            "body": "b",
            "register": "wire",
            "model_id": "m",
            "prompt_version": "v",
        }
        NarrationRecord.objects.create(**kwargs)
        with pytest.raises(IntegrityError):
            NarrationRecord.objects.create(**kwargs)

    def test_ordering_is_tick_then_beat_id(self) -> None:
        session = GameSession.objects.create(scenario="test")
        NarrationRecord.objects.create(
            session=session,
            tick=2,
            beat_id="wire-2",
            scope="tick",
            headline="h2",
            body="b",
            register="wire",
            model_id="m",
            prompt_version="v",
        )
        NarrationRecord.objects.create(
            session=session,
            tick=1,
            beat_id="analysis-1",
            scope="tick",
            headline="h1a",
            body="b",
            register="analysis",
            model_id="m",
            prompt_version="v",
        )
        NarrationRecord.objects.create(
            session=session,
            tick=1,
            beat_id="wire-1",
            scope="tick",
            headline="h1w",
            body="b",
            register="wire",
            model_id="m",
            prompt_version="v",
        )

        ordered = list(session.narration_records.values_list("beat_id", flat=True))
        assert ordered == ["analysis-1", "wire-1", "wire-2"]


# --------------------------------------------------------------------------- #
# Wiring: NarrativeService._generate persists both success and degraded
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
class TestNarrativeServicePersistence:
    """``NarrativeService._generate`` writes durable ``NarrationRecord`` rows.

    Uses the same WorldState/event fixtures as ``test_narrative_service.py``
    (an uprising event is a ``SIGNIFICANT_EVENT_TYPES`` member, so it
    drives ``NarrativeDirector`` to actually produce dual narrative text).
    """

    @pytest.fixture(autouse=True)
    def _flag_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from django.conf import settings as django_settings

        monkeypatch.setattr(django_settings, "BABYLON_LLM_NARRATOR", True, raising=False)

    def _states(self):
        from babylon.models import EdgeType, Relationship, SocialClass, SocialRole, WorldState
        from babylon.models.entity_registry import COMPRADOR_ID, PERIPHERY_WORKER_ID
        from babylon.models.events import UprisingEvent

        worker = SocialClass(
            id=PERIPHERY_WORKER_ID,
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.5,
            ideology=0.0,
            organization=0.1,
            repression_faced=0.5,
            subsistence_threshold=0.3,
        )
        owner = SocialClass(
            id=COMPRADOR_ID,
            name="Owner",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=10.0,
            ideology=0.5,
            organization=0.7,
            repression_faced=0.1,
            subsistence_threshold=0.1,
        )
        edge = Relationship(
            source_id=PERIPHERY_WORKER_ID,
            target_id=COMPRADOR_ID,
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )
        previous_state = WorldState(
            tick=0,
            entities={PERIPHERY_WORKER_ID: worker, COMPRADOR_ID: owner},
            relationships=[edge],
        )
        event = UprisingEvent(
            tick=1,
            node_id=PERIPHERY_WORKER_ID,
            trigger="spark",
            agitation=0.9,
            repression=0.7,
        )
        new_state = previous_state.model_copy(update={"tick": 1, "events": [event]})
        return previous_state, new_state

    def test_success_persists_wire_and_analysis_records(self) -> None:
        from babylon.intelligence.ai.llm_provider import MockLLM
        from game.narrative_service import NarrativeService

        session = GameSession.objects.create(scenario="test")
        previous_state, new_state = self._states()
        service = NarrativeService(
            llm=MockLLM(responses=["Corporate narrative", "Liberated narrative"])
        )

        service._generate(session.id, previous_state, new_state)

        records = list(NarrationRecord.objects.filter(session=session, tick=1).order_by("beat_id"))
        assert [r.beat_id for r in records] == ["analysis-1", "wire-1"]
        analysis, wire = records
        assert wire.register == "wire"
        assert wire.headline == "Tick 1"  # single-line text has no natural headline split
        assert wire.body == "Corporate narrative"
        assert wire.degraded is False
        assert analysis.register == "analysis"
        assert analysis.body == "Liberated narrative"
        assert analysis.scope == "tick"
        assert analysis.subject_ref is None

    def test_degraded_persists_one_visible_record(self) -> None:
        from unittest.mock import MagicMock

        from babylon.intelligence.ai.llm_provider import LLMProvider
        from game.narrative_service import NarrativeService

        session = GameSession.objects.create(scenario="test")
        previous_state, new_state = self._states()
        failing_llm = MagicMock(spec=LLMProvider)
        failing_llm.name = "FailingProvider"
        failing_llm.generate.side_effect = RuntimeError("simulated timeout")
        service = NarrativeService(llm=failing_llm)

        service._generate(session.id, previous_state, new_state)

        records = list(NarrationRecord.objects.filter(session=session, tick=1))
        assert len(records) == 1
        rec = records[0]
        assert rec.degraded is True
        assert rec.register == "wire"
        assert rec.beat_id == "wire-1"
        assert rec.headline == "NARRATOR DEGRADED"
        assert "simulated timeout" in rec.body
        assert "simulated timeout" in rec.error

    def test_idempotent_replay_updates_not_duplicates(self) -> None:
        """A replayed/re-scheduled generation for the same (session, tick)
        UPDATES its existing records rather than duplicating them.

        Uses ``default_response`` (not a ``responses`` queue) so every LLM
        call within a round returns the same fixed text regardless of how
        many times ``NarrativeDirector.on_tick`` calls ``generate()`` per
        tick (it calls it three times: CORPORATE, LIBERATED, and the
        legacy main-narrative log) — round 1 and round 2 use distinct
        services/providers so the two rounds are unambiguous.
        """
        from babylon.intelligence.ai.llm_provider import MockLLM
        from game.narrative_service import NarrativeService

        session = GameSession.objects.create(scenario="test")
        previous_state, new_state = self._states()

        service_round1 = NarrativeService(llm=MockLLM(default_response="Round 1 text"))
        service_round1._generate(session.id, previous_state, new_state)

        records_after_round1 = list(NarrationRecord.objects.filter(session=session, tick=1))
        assert len(records_after_round1) == 2
        ids_after_round1 = {r.id for r in records_after_round1}

        service_round2 = NarrativeService(llm=MockLLM(default_response="Round 2 text"))
        service_round2._generate(session.id, previous_state, new_state)

        records_after_round2 = list(NarrationRecord.objects.filter(session=session, tick=1))
        assert len(records_after_round2) == 2  # not 4 — update_or_create, not create
        assert {r.id for r in records_after_round2} == ids_after_round1  # same rows, updated
        wire = NarrationRecord.objects.get(session=session, tick=1, beat_id="wire-1")
        assert wire.body == "Round 2 text"

    def test_missing_session_on_success_path_degrades_loudly(self) -> None:
        """III.11: a caller-supplied session_id with no backing row is a real
        bug, not a soft-skip — persistence failure turns an otherwise-healthy
        generation into an explicit ``degraded`` result rather than silently
        losing the beat or logging-and-continuing as if nothing happened.
        """
        from babylon.intelligence.ai.llm_provider import MockLLM
        from game.narrative_service import NarrativeService

        ghost_session_id = uuid.uuid4()
        previous_state, new_state = self._states()
        service = NarrativeService(
            llm=MockLLM(responses=["Corporate narrative", "Liberated narrative"])
        )

        service._generate(ghost_session_id, previous_state, new_state)

        result = service.get_result(ghost_session_id, tick=1)
        assert result is not None
        assert result.degraded is True
        assert "GameSession" in (result.error or "") or "matching query does not exist" in (
            result.error or ""
        )
        assert NarrationRecord.objects.filter(tick=1).count() == 0

    def test_no_significant_event_persists_nothing(self) -> None:
        """Empty domain (no SIGNIFICANT_EVENT_TYPES this tick) is not a
        failure and produces no narrative text — persisting a record here
        would fabricate a beat that was never generated (III.11).
        """
        from babylon.intelligence.ai.llm_provider import MockLLM
        from game.narrative_service import NarrativeService

        session = GameSession.objects.create(scenario="test")
        previous_state, new_state = self._states()
        quiet_new_state = previous_state.model_copy(update={"tick": 1, "events": []})
        service = NarrativeService(llm=MockLLM(default_response="unused"))

        service._generate(session.id, previous_state, quiet_new_state)

        assert NarrationRecord.objects.filter(session=session, tick=1).count() == 0
