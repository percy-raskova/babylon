"""Unit tests for hash-chain structural verification (spec-099, US2, no DB)."""

from __future__ import annotations

import pytest

from observatory.deep_queries import verify_chain

pytestmark = pytest.mark.unit


def _row(tick: int, *, checkpoint: bool | None = None, hash_len: int = 64) -> dict:
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
