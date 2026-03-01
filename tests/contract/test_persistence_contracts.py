"""Contract compliance tests for persistence protocols (Feature 037).

Verifies that all concrete implementations satisfy their ``@runtime_checkable``
Protocol interfaces via ``isinstance()`` checks.

See Also:
    :mod:`babylon.persistence.protocols`: Protocol definitions.
"""

from __future__ import annotations

from uuid import UUID

import networkx as nx
import pytest

from babylon.persistence.protocols import (
    RuntimePersistence,
    TraceCollector,
    TraceLevel,
    VectorStoreProtocol,
)


@pytest.mark.unit
class TestRuntimePersistenceCompliance:
    """Verify RuntimePersistence implementations via isinstance()."""

    def test_runtime_database_satisfies_protocol(self) -> None:
        """SQLite RuntimeDatabase satisfies RuntimePersistence protocol."""
        from babylon.persistence.runtime_db import RuntimeDatabase

        with RuntimeDatabase(in_memory=True) as db:
            assert isinstance(db, RuntimePersistence)

    def test_runtime_database_persist_tick_accepts_session_id(self) -> None:
        """RuntimeDatabase.persist_tick accepts optional session_id kwarg."""
        from babylon.persistence.runtime_db import RuntimeDatabase

        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("test", type="Test")
        session_id = UUID("12345678-1234-5678-1234-567812345678")

        with RuntimeDatabase(in_memory=True) as db:
            # Should not raise - session_id is accepted but ignored
            db.persist_tick(tick=0, graph=graph, session_id=session_id)

    def test_runtime_database_hydrate_graph_accepts_session_id(self) -> None:
        """RuntimeDatabase.hydrate_graph accepts optional session_id kwarg."""
        from babylon.persistence.runtime_db import RuntimeDatabase

        session_id = UUID("12345678-1234-5678-1234-567812345678")

        with RuntimeDatabase(in_memory=True) as db:
            # Should not raise
            db.hydrate_graph(tick=0, session_id=session_id)

    def test_runtime_database_log_tick_accepts_session_id_and_timings(self) -> None:
        """RuntimeDatabase.log_tick accepts session_id and system_timings kwargs."""
        from babylon.persistence.runtime_db import RuntimeDatabase

        session_id = UUID("12345678-1234-5678-1234-567812345678")

        with RuntimeDatabase(in_memory=True) as db:
            # Should not raise
            db.log_tick(
                tick=0,
                wall_time_ms=100,
                system_timings={"ImperialRentSystem": 12},
                session_id=session_id,
            )


@pytest.mark.unit
class TestTraceCollectorCompliance:
    """Verify TraceCollector implementations via isinstance()."""

    def test_trace_recorder_satisfies_protocol(self) -> None:
        """TraceRecorder satisfies TraceCollector protocol."""
        from babylon.persistence.trace_recorder import TraceRecorder

        recorder = TraceRecorder(level=TraceLevel.DEBUG)
        assert isinstance(recorder, TraceCollector)

    def test_noop_tracer_satisfies_protocol(self) -> None:
        """NoopTracer (level=NONE) satisfies TraceCollector protocol."""
        from babylon.persistence.trace_recorder import TraceRecorder

        noop = TraceRecorder(level=TraceLevel.NONE)
        assert isinstance(noop, TraceCollector)


@pytest.mark.unit
class TestVectorStoreProtocolCompliance:
    """Verify VectorStoreProtocol implementations via isinstance()."""

    def test_chromadb_vectorstore_satisfies_protocol(self) -> None:
        """Existing ChromaDB VectorStore satisfies VectorStoreProtocol."""
        from babylon.rag.retrieval import VectorStore

        # VectorStore has the 4 required methods
        assert issubclass(VectorStore, VectorStoreProtocol)
