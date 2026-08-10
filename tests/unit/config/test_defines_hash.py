"""Contract tests for the single canonical defines-hash (Program 27 spec §7)."""

import hashlib
import json
import sys
from pathlib import Path

from babylon.config.defines import GameDefines, canonical_defines_hash


def test_canonical_hash_is_full_sha256_hex() -> None:
    h = canonical_defines_hash(GameDefines())
    assert len(h) == 64
    assert h == h.lower()
    int(h, 16)  # raises if not hex


def test_canonical_hash_matches_specified_byte_layout() -> None:
    """The byte layout is the spec, not the implementation (III.12(a))."""
    defines = GameDefines()
    payload = defines.model_dump(mode="json")
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()
    assert canonical_defines_hash(defines) == expected


def test_canonical_hash_is_stable_across_calls() -> None:
    d1, d2 = GameDefines(), GameDefines()
    assert canonical_defines_hash(d1) == canonical_defines_hash(d2)


def test_all_production_call_sites_delegate_to_canonical() -> None:
    """runner.py and regression_test.py must both produce the canonical
    value — the drift this task retires (spec §7). play.py's own leg of
    this check retired with the module (Amendment AF / ADR186 deletion
    ceremony — the Ratatui client's composition root)."""
    from babylon.engine.headless_runner.runner import _defines_hash as runner_hash

    sys.path.insert(0, str(Path(__file__).parents[3] / "tools"))
    from regression_test import hash_defines as regression_hash

    defines = GameDefines()
    canonical = canonical_defines_hash(defines)
    assert runner_hash(defines) == canonical
    assert regression_hash(defines) == canonical
