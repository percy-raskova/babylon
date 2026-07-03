"""Unit tests for session-partition helpers (spec-088 FR-005).

Pure identifier-shaping tests; Postgres behavior is covered by
``tests/integration/test_session_partitioning.py``.
"""

from __future__ import annotations

from uuid import UUID

from babylon.persistence.partitioning import (
    PARTITIONED_TABLES,
    partition_name,
)

_SESSION = UUID("01234567-89ab-cdef-0123-456789abcdef")


class TestPartitionedTablesRegistry:
    def test_all_per_tick_families_registered(self) -> None:
        """8 spec-088 conversions + tick_commit (born partitioned, spec-089)."""
        assert set(PARTITIONED_TABLES) == {
            "dynamic_hex_state",
            "dynamic_external_node_state",
            "boundary_flow_register",
            "conservation_audit_log",
            "dynamic_consciousness_state",
            "dynamic_demographics_state",
            "dynamic_employment_state",
            "dynamic_relationship_state",
            "tick_commit",
        }


class TestPartitionName:
    def test_uses_uuid_hex_without_dashes(self) -> None:
        name = partition_name("dynamic_hex_state", _SESSION)
        assert name == "dynamic_hex_state_p_0123456789abcdef0123456789abcdef"

    def test_deterministic(self) -> None:
        assert partition_name("boundary_flow_register", _SESSION) == partition_name(
            "boundary_flow_register", _SESSION
        )

    def test_within_postgres_identifier_limit(self) -> None:
        """NAMEDATALEN is 64 → identifiers truncate at 63 bytes."""
        for table in PARTITIONED_TABLES:
            assert len(partition_name(table, _SESSION)) <= 63
