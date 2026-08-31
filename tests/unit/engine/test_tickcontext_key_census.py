"""Drift guard: no NEW undeclared TickContext keys during Phase 0 (P27 §6.5)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "tools"))
from tickcontext_key_census import stamped_keys  # noqa: E402

# The Phase-0 census. Adding a key here requires updating the census report
# AND the Rust TickContext contract — never add silently.
DECLARED_STAMPED_KEYS = frozenset(
    {
        "vol2_circulation_result",
    }
)


def test_no_undeclared_tickcontext_keys() -> None:
    found = frozenset(stamped_keys())
    new = found - DECLARED_STAMPED_KEYS
    gone = DECLARED_STAMPED_KEYS - found
    assert not new, f"NEW undeclared TickContext keys: {sorted(new)}"
    assert not gone, f"census stale — keys no longer stamped: {sorted(gone)}"
