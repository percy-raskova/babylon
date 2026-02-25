"""Tests for ContradictionFieldSystem (Feature 002 - System #14).

TDD RED phase: Tests define the contract for contradiction field computation.

Reference: specs/002-dialectical-field-topology/contracts/contradiction_field_system.py
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.engine.field_registry import DefaultFieldRegistry
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction_field import ContradictionFieldSystem


@pytest.mark.unit
class TestContradictionFieldSystemBasic:
    """Basic behavior for ContradictionFieldSystem."""

    def test_system_has_name(self) -> None:
        """System should have the correct name."""
        system = ContradictionFieldSystem()
        assert system.name == "contradiction_field"

    def test_writes_contradiction_fields_to_node(self) -> None:
        """System writes contradiction_fields dict to social_class nodes."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=20.0,
            population=1000,
            s_bio=5.0,
            s_class=2.0,
            unearned_increment=0.0,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}
        system = ContradictionFieldSystem()

        system.step(graph, services, context)

        fields = graph.nodes["C001"].get("contradiction_fields")
        assert fields is not None
        assert isinstance(fields, dict)
        assert "exploitation" in fields
        assert "immiseration" in fields
        assert "imperial_rent" in fields
        assert "displacement" in fields

    def test_field_values_in_bounds(self) -> None:
        """All field values are in [0.0, 10.0] after normalization (EC-007)."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=0.0,  # Extreme case: destitute
            population=1000,
            s_bio=5.0,
            s_class=2.0,
            unearned_increment=100.0,  # Extreme case: high rent
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}
        system = ContradictionFieldSystem()

        system.step(graph, services, context)

        fields = graph.nodes["C001"]["contradiction_fields"]
        for field_name, value in fields.items():
            assert 0.0 <= value <= 10.0, f"Field {field_name} = {value} out of bounds"

    def test_skips_non_social_class_nodes(self) -> None:
        """System only processes social_class nodes, not territory nodes."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("T001", _node_type="territory", heat=0.5)
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=10.0,
            population=1000,
            s_bio=5.0,
            s_class=0.0,
            unearned_increment=0.0,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}
        system = ContradictionFieldSystem()

        system.step(graph, services, context)

        assert "contradiction_fields" not in graph.nodes["T001"]
        assert "contradiction_fields" in graph.nodes["C001"]


@pytest.mark.unit
class TestContradictionFieldHistory:
    """Tests for contradiction_history in persistent_data."""

    def test_stores_history_in_persistent_data(self) -> None:
        """System stores field values in persistent_data contradiction_history."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=10.0,
            population=1000,
            s_bio=5.0,
            s_class=0.0,
            unearned_increment=0.0,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        persistent_data: dict[str, object] = {}
        context: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}
        system = ContradictionFieldSystem()

        system.step(graph, services, context)

        history = persistent_data.get("contradiction_history")
        assert history is not None
        assert "C001" in history  # type: ignore[operator]
        # Each field should have a list with one entry
        c001_history = history["C001"]  # type: ignore[index]
        assert "exploitation" in c001_history

    def test_history_rolling_window_max_3(self) -> None:
        """History window never exceeds 3 entries per node per field."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=10.0,
            population=1000,
            s_bio=5.0,
            s_class=0.0,
            unearned_increment=0.0,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        persistent_data: dict[str, object] = {}

        system = ContradictionFieldSystem()

        # Run 5 ticks to test window
        max_ticks = 5
        for tick in range(max_ticks):
            context: dict[str, object] = {
                "tick": tick,
                "persistent_data": persistent_data,
            }
            system.step(graph, services, context)

        history = persistent_data["contradiction_history"]
        c001_history = history["C001"]  # type: ignore[index]
        for _field_name, values in c001_history.items():  # type: ignore[union-attr]
            assert len(values) <= 3, f"History window exceeded 3 for {_field_name}"

    def test_injects_previous_wealth_for_immiseration(self) -> None:
        """System injects _previous_wealth so immiseration can compute decline."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=20.0,
            population=1000,
            s_bio=5.0,
            s_class=0.0,
            unearned_increment=0.0,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        persistent_data: dict[str, object] = {}

        system = ContradictionFieldSystem()

        # Tick 1: wealth=20
        context1: dict[str, object] = {"tick": 1, "persistent_data": persistent_data}
        system.step(graph, services, context1)

        # Change wealth for tick 2
        graph.nodes["C001"]["wealth"] = 10.0
        context2: dict[str, object] = {"tick": 2, "persistent_data": persistent_data}
        system.step(graph, services, context2)

        # Immiseration should be positive (wealth dropped from 20 to 10)
        fields = graph.nodes["C001"]["contradiction_fields"]
        assert fields["immiseration"] > 0.0

    def test_exploitation_destitute_worker(self) -> None:
        """Destitute worker (wealth=0) has high exploitation field."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=0.0,
            population=500,
            s_bio=5.0,
            s_class=2.0,
            unearned_increment=0.0,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}
        system = ContradictionFieldSystem()

        system.step(graph, services, context)

        fields = graph.nodes["C001"]["contradiction_fields"]
        # Destitute worker should have high exploitation
        assert fields["exploitation"] > 5.0

    def test_wealthy_node_low_exploitation(self) -> None:
        """Wealthy node (wealth > subsistence) has low exploitation."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=50.0,  # Well above subsistence
            population=1000,
            s_bio=5.0,
            s_class=2.0,
            unearned_increment=0.0,
        )

        registry = DefaultFieldRegistry.with_defaults()
        services = ServiceContainer.create(field_registry=registry)
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}
        system = ContradictionFieldSystem()

        system.step(graph, services, context)

        fields = graph.nodes["C001"]["contradiction_fields"]
        # Wealthy node should have low or zero exploitation
        assert fields["exploitation"] == 0.0


@pytest.mark.unit
class TestContradictionFieldNoRegistry:
    """Behavior when no field registry is provided."""

    def test_no_registry_skips_computation(self) -> None:
        """System is a no-op when services.field_registry is None."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=10.0,
            population=1000,
        )

        services = ServiceContainer.create()  # No field_registry
        context: dict[str, object] = {"tick": 1, "persistent_data": {}}
        system = ContradictionFieldSystem()

        system.step(graph, services, context)

        assert "contradiction_fields" not in graph.nodes["C001"]
