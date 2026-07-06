"""Unit tests for hash-chain structural verification (spec-099, US2, no DB)."""

from __future__ import annotations

from typing import Any

import pytest

from observatory.deep_queries import verify_chain

pytestmark = pytest.mark.unit


def _row(tick: int, *, checkpoint: bool | None = None, hash_len: int = 64) -> dict[str, Any]:
    return {
        "tick": tick,
        "determinism_hash": "a" * hash_len,
        "hex_rows_written": 0,
        "is_checkpoint": (tick % 52 == 0) if checkpoint is None else checkpoint,
    }


class TestVerifyChain:
    def test_empty_chain_is_valid(self) -> None:
        result = verify_chain([])
        assert result["valid"] is True
        assert result["tick_count"] == 0
        assert result["anomalies"] == []

    def test_well_formed_chain(self) -> None:
        rows = [_row(t) for t in range(105)]  # 0..104, checkpoints at 0,52,104
        result = verify_chain(rows)
        assert result["valid"] is True
        assert result["min_tick"] == 0
        assert result["max_tick"] == 104
        assert result["tick_count"] == 105
        assert result["checkpoint_ticks"] == [0, 52, 104]
        assert result["anomalies"] == []

    def test_single_tick_valid(self) -> None:
        result = verify_chain([_row(0)])
        assert result["valid"] is True
        assert result["checkpoint_ticks"] == [0]

    def test_gap_flagged(self) -> None:
        rows = [_row(0), _row(1), _row(3)]  # missing tick 2
        result = verify_chain(rows)
        assert result["valid"] is False
        kinds = {(a["kind"], a["tick"]) for a in result["anomalies"]}
        assert ("gap", 2) in kinds

    def test_duplicate_flagged(self) -> None:
        rows = [_row(0), _row(1), _row(1)]
        result = verify_chain(rows)
        assert result["valid"] is False
        assert any(a["kind"] == "duplicate" and a["tick"] == 1 for a in result["anomalies"])

    def test_bad_checkpoint_cadence_flagged(self) -> None:
        # tick 3 marked checkpoint (should not be); tick 52 NOT marked (should be)
        rows = [_row(t) for t in range(53)]
        rows[3]["is_checkpoint"] = True
        rows[52]["is_checkpoint"] = False
        result = verify_chain(rows)
        assert result["valid"] is False
        bad = {a["tick"] for a in result["anomalies"] if a["kind"] == "bad_checkpoint"}
        assert bad == {3, 52}

    def test_bad_hash_length_flagged(self) -> None:
        rows = [_row(0), _row(1, hash_len=10)]
        result = verify_chain(rows)
        assert result["valid"] is False
        assert any(a["kind"] == "bad_hash" and a["tick"] == 1 for a in result["anomalies"])

    def test_verification_scope_is_structural(self) -> None:
        """Every verdict names its own scope — machine-readable honesty."""
        assert verify_chain([])["verification_scope"] == "structural"
        assert verify_chain([_row(0)])["verification_scope"] == "structural"

    def test_content_tamper_is_not_flagged_by_format_only_check(self) -> None:
        """spec-099 fix #4 (pairs with the hash-chain honesty fix, #1/#2/#7).

        A same-LENGTH but different-CONTENT hash (a genuine tamper: one byte
        of a well-formed 64-hex-char digest flipped) is NOT flagged. This is
        not a bug to fix — it is the documented, ground-truthed scope limit:
        ``verify_chain`` checks hash FORMAT only, never CONTENT, because
        ``tick_commit.determinism_hash`` is a shallow identity hash
        (``sha256(session_id:tick:seed)``) whose seed is not reliably
        recoverable from persisted session metadata for headless-runner
        sessions (see the module docstring). This test locks in that the
        feature does not silently claim more than it checks: a content-only
        tamper stays ``valid`` (structurally) and produces zero anomalies.
        """
        genuine_hash = "b" * 64
        tampered_hash = "c" + "b" * 63  # same length, different content
        assert len(genuine_hash) == len(tampered_hash) == 64
        assert genuine_hash != tampered_hash

        rows = [_row(t) for t in range(3)]
        for row in rows:
            row["determinism_hash"] = genuine_hash
        rows[1]["determinism_hash"] = tampered_hash  # content-only tamper

        result = verify_chain(rows)
        assert result["valid"] is True  # format check alone can't see this
        assert result["anomalies"] == []
        assert result["verification_scope"] == "structural"
