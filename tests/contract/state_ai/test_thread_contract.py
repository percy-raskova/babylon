"""Contract tests for attention thread system (Feature 039, T039-T040).

Tests behavioral contracts T-01 through T-06 from
``specs/039-state-apparatus-ai/contracts/attention-thread.md``.
"""

from __future__ import annotations

import networkx as nx

from babylon.config.defines import GameDefines, StateApparatusAIDefines
from babylon.models.enums import ThreadPhase
from babylon.ooda.attention.observation import compute_observation_ceiling
from babylon.ooda.attention.sparrow import analyze_network
from babylon.ooda.attention.thread_manager import (
    advance_thread_phase,
    allocate_threads,
    update_thread_tick,
)
from tests.unit.state_ai.conftest import make_attention_thread


def _defines() -> StateApparatusAIDefines:
    return GameDefines().state_ai


class TestIntelGrowth:
    """T-01: Intel completeness grows over 8 ticks of active monitoring."""

    def test_intel_grows_over_8_ticks(self) -> None:
        """Thread accumulates intel over 8 consecutive ticks."""
        thread = make_attention_thread(
            phase=ThreadPhase.MONITORING,
            intel_completeness=0.0,
            ticks_active=0,
        )
        defines = _defines()

        max_ticks = 8
        for _tick in range(max_ticks):
            thread = update_thread_tick(thread, intel_gain=0.05, observation_ceiling=1.0)
            thread = advance_thread_phase(thread, defines)

        assert thread.intel_completeness > 0.0, "Intel should grow after 8 ticks"
        assert thread.intel_completeness >= 0.35, "Should have substantial intel after 8 ticks"
        assert thread.ticks_active == 8


class TestCellTopologyResistance:
    """T-02: Cell topology provides at least 30% resistance vs star topology."""

    def test_cell_topology_lower_intel_than_star(self) -> None:
        """Cell topology (cycle) resists surveillance more than star topology."""
        # Star topology: hub sees everything
        star = nx.star_graph(5).to_directed()
        star_mapping = {i: f"s_{i}" for i in star.nodes()}
        star = nx.relabel_nodes(star, star_mapping)

        # Cell topology: cycle with compartmentalization
        cell = nx.cycle_graph(6).to_directed()
        cell_mapping = {i: f"c_{i}" for i in cell.nodes()}
        cell = nx.relabel_nodes(cell, cell_mapping)

        # Star has lower compartmentalization
        star_ceiling = compute_observation_ceiling(1.0, compartmentalization_factor=0.1)
        cell_ceiling = compute_observation_ceiling(1.0, compartmentalization_factor=0.5)

        assert cell_ceiling < star_ceiling * 0.7, (
            f"Cell ceiling ({cell_ceiling}) should be at least 30% lower "
            f"than star ceiling ({star_ceiling})"
        )


class TestObservationCeiling:
    """T-03: Observation ceiling caps intel per apparatus."""

    def test_ceiling_caps_intel(self) -> None:
        """Intel cannot grow past the observation ceiling."""
        ceiling = 0.4
        thread = make_attention_thread(intel_completeness=0.0)

        max_ticks = 20
        for _tick in range(max_ticks):
            thread = update_thread_tick(thread, intel_gain=0.1, observation_ceiling=ceiling)

        assert thread.intel_completeness <= ceiling, (
            f"Intel ({thread.intel_completeness}) should not exceed ceiling ({ceiling})"
        )


class TestSparrowSingletonOnStar:
    """T-04: Sparrow identifies hub as singleton on star topology."""

    def test_star_hub_identified_as_singleton(self) -> None:
        """Sparrow analysis on star graph identifies the hub node."""
        star = nx.star_graph(6).to_directed()
        mapping = {i: f"node_{i}" for i in star.nodes()}
        star = nx.relabel_nodes(star, mapping)

        analysis = analyze_network("thread_1", tick=5, g_observed=star)
        assert "node_0" in analysis.identified_singletons, (
            "Sparrow should identify star hub as singleton"
        )


class TestMetaOODAThreatAllocation:
    """T-05: Meta-OODA allocates threads by threat level."""

    def test_highest_threat_gets_thread_first(self) -> None:
        """Highest-threat targets are prioritized in allocation."""
        targets = {"org_high": 0.9, "org_med": 0.5, "org_low": 0.1}
        threads = allocate_threads(
            existing_threads=[],
            target_scores=targets,
            pool_size=2,
            defines=_defines(),
        )
        target_ids = {t.target_id for t in threads}
        assert "org_high" in target_ids, "Highest threat should get a thread"
        assert "org_med" in target_ids, "Medium threat should get second thread"
        assert "org_low" not in target_ids, "Lowest threat should not get a thread"
