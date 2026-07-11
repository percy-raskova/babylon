"""Unit tests for SystemBase ABC (ADR-003 / Spec 059 US3).

Verifies the shared scaffolding lifted from the 22 System implementations:
- name ClassVar contract
- step() abstract enforcement
- _wrap_graph idempotency
- _read with required=True surfaces missing-attribute bugs at the read site
- _publish delegates to services.event_bus
"""

from __future__ import annotations

from typing import Any, ClassVar
from unittest.mock import MagicMock

import pytest

from babylon.engine.graph import BabylonGraph
from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import System
from babylon.models.graph import GraphNode


class _StubSystem(SystemBase):
    """Minimal SystemBase subclass for testing helpers."""

    name: ClassVar[str] = "stub"

    def step(self, graph: Any, services: Any, context: Any) -> None:
        pass


class TestSystemBaseAbstract:
    """ABC enforcement: step() must be implemented; instantiating raw SystemBase fails."""

    def test_systembase_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            SystemBase()  # type: ignore[abstract]

    def test_subclass_without_step_is_abstract(self) -> None:
        class IncompleteSystem(SystemBase):
            name: ClassVar[str] = "incomplete"

        with pytest.raises(TypeError):
            IncompleteSystem()  # type: ignore[abstract]

    def test_concrete_subclass_instantiates(self) -> None:
        s = _StubSystem()
        assert s.name == "stub"


class TestWrapGraph:
    """_wrap_graph: raw nx.DiGraph → GraphProtocol; idempotent on already-wrapped."""

    def test_wraps_raw_networkx(self) -> None:
        g = BabylonGraph()
        wrapped = SystemBase._wrap_graph(g)
        from babylon.kernel.graph_protocol import GraphProtocol

        assert isinstance(wrapped, GraphProtocol)

    def test_wrap_is_idempotent(self) -> None:
        g = BabylonGraph()
        wrapped_once = SystemBase._wrap_graph(g)
        wrapped_twice = SystemBase._wrap_graph(wrapped_once)
        assert wrapped_once is wrapped_twice


class TestReadRequired:
    """_read(required=True): raises KeyError naming both attribute and node id."""

    def _node(self, **attrs: Any) -> GraphNode:
        return GraphNode(id="N1", node_type="social_class", attributes=attrs)

    def test_read_present_required(self) -> None:
        node = self._node(wealth=42.0)
        assert SystemBase._read(node, "wealth", required=True) == 42.0

    def test_read_missing_required_raises_keyerror(self) -> None:
        node = self._node(wealth=42.0)
        with pytest.raises(KeyError) as exc:
            SystemBase._read(node, "missing_attr", required=True)
        # Diagnostic must name both attribute and node id (ADR-003 contract)
        assert "missing_attr" in str(exc.value)
        assert "N1" in str(exc.value)

    def test_read_missing_optional_returns_default(self) -> None:
        node = self._node(wealth=42.0)
        assert SystemBase._read(node, "missing_attr") is None
        assert SystemBase._read(node, "missing_attr", default=0.0) == 0.0

    def test_read_present_optional(self) -> None:
        node = self._node(wealth=42.0, organization=0.5)
        assert SystemBase._read(node, "organization", default=0.0) == 0.5


class TestPublish:
    """_publish: delegates to services.event_bus.publish."""

    def test_publish_calls_event_bus(self) -> None:
        services = MagicMock()
        event = MagicMock()
        SystemBase._publish(services, event)
        services.event_bus.publish.assert_called_once_with(event)


class TestProtocolStructuralTyping:
    """FR-010: System Protocol structural typing preserved for non-ABC mocks."""

    def test_subclass_satisfies_protocol(self) -> None:
        s = _StubSystem()
        assert isinstance(s, System)

    def test_non_abc_stub_satisfies_protocol(self) -> None:
        """Mocks that DON'T inherit from SystemBase must still satisfy System."""

        class DuckTypedStub:
            name = "duck_typed"

            def step(self, graph: Any, services: Any, context: Any) -> None:
                pass

        assert isinstance(DuckTypedStub(), System)
