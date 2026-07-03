"""Unit tests for AttentionThread and SparrowAnalysis models (Feature 039, T010).

Tests frozen Pydantic validation, target_type constraints, phase enum usage,
surveillance method lists, and immutability.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.enums import SurveillanceMethod, ThreadPhase
from tests.constants import TestConstants
from tests.unit.state_ai.conftest import make_attention_thread, make_sparrow_analysis

TC = TestConstants


class TestAttentionThreadConstruction:
    """T010: AttentionThread model validation."""

    def test_valid_monitoring_thread(self) -> None:
        thread = make_attention_thread()
        assert thread.phase == ThreadPhase.MONITORING
        assert thread.target_type == "organization"

    def test_dormant_thread(self) -> None:
        thread = make_attention_thread(
            phase=ThreadPhase.DORMANT,
            intensity=0.0,
            intel_completeness=0.0,
            surveillance_methods=[],
            ticks_active=0,
        )
        assert thread.phase == ThreadPhase.DORMANT

    def test_active_investigation_thread(self) -> None:
        thread = make_attention_thread(
            phase=ThreadPhase.ACTIVE_INVESTIGATION,
            intensity=0.6,
            intel_completeness=0.45,
            surveillance_methods=[SurveillanceMethod.SIGNALS, SurveillanceMethod.FINANCIAL],
        )
        assert thread.phase == ThreadPhase.ACTIVE_INVESTIGATION
        assert len(thread.surveillance_methods) == 2

    def test_disruption_thread(self) -> None:
        thread = make_attention_thread(
            phase=ThreadPhase.DISRUPTION,
            intensity=0.9,
            intel_completeness=0.75,
            surveillance_methods=[
                SurveillanceMethod.SIGNALS,
                SurveillanceMethod.FINANCIAL,
                SurveillanceMethod.INFORMANT,
            ],
        )
        assert thread.phase == ThreadPhase.DISRUPTION

    def test_invalid_target_type_rejected(self) -> None:
        with pytest.raises(ValidationError, match="target_type"):
            make_attention_thread(target_type="invalid_type")

    def test_valid_target_types(self) -> None:
        """All three valid target types accepted."""
        for target_type in ("organization", "territory", "community"):
            thread = make_attention_thread(target_type=target_type)
            assert thread.target_type == target_type

    def test_negative_ticks_active_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_attention_thread(ticks_active=-1)

    def test_intensity_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_attention_thread(intensity=1.5)

    def test_intel_completeness_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_attention_thread(intel_completeness=-0.1)


class TestAttentionThreadImmutability:
    """T010: Frozen model enforcement."""

    def test_frozen(self) -> None:
        thread = make_attention_thread()
        with pytest.raises(ValidationError):
            thread.phase = ThreadPhase.DISRUPTION  # type: ignore[misc]

    def test_observed_node_ids_is_frozenset(self) -> None:
        thread = make_attention_thread(observed_node_ids=frozenset({"node_a", "node_b"}))
        assert isinstance(thread.observed_node_ids, frozenset)
        assert len(thread.observed_node_ids) == 2

    def test_observed_edge_ids_is_frozenset(self) -> None:
        thread = make_attention_thread(observed_edge_ids=frozenset({("a", "b"), ("b", "c")}))
        assert isinstance(thread.observed_edge_ids, frozenset)
        assert len(thread.observed_edge_ids) == 2

    def test_model_copy_produces_new_instance(self) -> None:
        thread = make_attention_thread()
        thread2 = thread.model_copy(
            update={
                "phase": ThreadPhase.ACTIVE_INVESTIGATION,
                "intel_completeness": 0.45,
            }
        )
        assert thread2.phase == ThreadPhase.ACTIVE_INVESTIGATION
        assert thread.phase == ThreadPhase.MONITORING  # Original unchanged


class TestSparrowAnalysisConstruction:
    """T011: SparrowAnalysis model validation."""

    def test_valid_analysis(self) -> None:
        analysis = make_sparrow_analysis()
        assert analysis.thread_id == "thread_001"
        assert analysis.tick == 5
        assert len(analysis.centrality_rankings) == 2
        assert len(analysis.equivalence_classes) == 2

    def test_confidence_within_probability_range(self) -> None:
        analysis = make_sparrow_analysis(confidence=0.0)
        assert analysis.confidence == 0.0

        analysis2 = make_sparrow_analysis(confidence=1.0)
        assert analysis2.confidence == 1.0

    def test_confidence_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_sparrow_analysis(confidence=1.5)

    def test_negative_tick_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_sparrow_analysis(tick=-1)

    def test_frozen(self) -> None:
        analysis = make_sparrow_analysis()
        with pytest.raises(ValidationError):
            analysis.confidence = 0.9  # type: ignore[misc]

    def test_singletons_are_frozenset(self) -> None:
        analysis = make_sparrow_analysis()
        assert isinstance(analysis.identified_singletons, frozenset)

    def test_cutsets_are_list_of_frozensets(self) -> None:
        analysis = make_sparrow_analysis()
        assert isinstance(analysis.known_cutsets, list)
        for cutset in analysis.known_cutsets:
            assert isinstance(cutset, frozenset)
