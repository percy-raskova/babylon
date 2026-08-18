"""Conformance vector proving `metabolism/biocapacity-update`'s `new-max`
floor clamp (`max(0.0, max_cap - damage)`) is REACHABLE and
mutation-catchable (F4 fix round, adversarial review of PR #501).

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/metabolism_extreme_damage_conformance.rs``.

See ``metabolism-extreme-damage-conformance.bscn`` for the full derivation
of why ``damage > max_biocapacity`` is legal and reachable (no field this
system reads has an upper bound that would forbid it), and why the
mutation signal for this specific clamp lives in ``max_biocapacity``, not
``biocapacity`` (which floors to ``0.0`` regardless, for an independent
reason -- the ecological cost alone).

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/metabolism_extreme_damage_conformance.py
"""

from __future__ import annotations

from _conformance_support import run_tick_and_print

from babylon.engine.systems.metabolism import MetabolismSystem

SUBJECT_ID = "extreme-county"
SEED = {
    "biocapacity": 100000.0,
    "max_biocapacity": 100.0,
    "extraction_intensity": 1.0,
    "regeneration_rate": 0.02,
}


def main() -> None:
    """Run one tick of the frozen MetabolismSystem with an extreme biocapacity seed."""
    run_tick_and_print(
        MetabolismSystem,
        [(SUBJECT_ID, SEED)],
        ["biocapacity", "max_biocapacity"],
    )


if __name__ == "__main__":
    main()
