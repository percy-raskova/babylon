"""Frozen-Pydantic-model tests for spec 062 audit + envelope models.

Verifies T016 / T019: ConservationAuditRow and PerTickTransactionEnvelope
use model_config = ConfigDict(frozen=True) and raise on mutation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from babylon.persistence.audit_models import AuditSeverity, ConservationAuditRow
from babylon.persistence.envelope import PerTickTransactionEnvelope


@pytest.mark.cross_scale
class TestConservationAuditRowFrozen:
    def test_can_construct(self) -> None:
        row = ConservationAuditRow(
            session_id=uuid4(),
            tick=0,
            scale="county",
            invariant_name="hex_to_county_sum_c",
            computed_value=10.0,
            expected_value=10.0,
            residual=0.0,
            severity=AuditSeverity.OK,
            determinism_hash="a" * 64,
            created_at_utc=datetime.now(tz=UTC),
        )
        assert row.severity is AuditSeverity.OK

    def test_mutation_raises(self) -> None:
        row = ConservationAuditRow(
            session_id=uuid4(),
            tick=0,
            scale="county",
            invariant_name="hex_to_county_sum_c",
            computed_value=10.0,
            expected_value=10.0,
            residual=0.0,
            severity=AuditSeverity.OK,
            determinism_hash="a" * 64,
            created_at_utc=datetime.now(tz=UTC),
        )
        with pytest.raises(ValidationError):
            row.tick = 1  # type: ignore[misc]


@pytest.mark.cross_scale
class TestPerTickTransactionEnvelopeFrozen:
    def test_can_construct_empty(self) -> None:
        env = PerTickTransactionEnvelope(session_id=uuid4(), tick=0, determinism_hash="b" * 64)
        assert env.hex_state_rows == []
        assert env.audit_log_rows == []

    def test_mutation_raises(self) -> None:
        env = PerTickTransactionEnvelope(session_id=uuid4(), tick=0, determinism_hash="b" * 64)
        with pytest.raises(ValidationError):
            env.tick = 1  # type: ignore[misc]

    def test_determinism_hash_length_enforced(self) -> None:
        with pytest.raises(ValidationError):
            PerTickTransactionEnvelope(session_id=uuid4(), tick=0, determinism_hash="too-short")
