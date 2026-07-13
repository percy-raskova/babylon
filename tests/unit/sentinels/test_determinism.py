"""The Determinism sentinel — Constitution III.7's dynamic guard.

The static-source sentinels prove non-determinism *sources* (unseeded RNG,
wall-clock reads, set/dict iteration order) are absent from the code. This is
their dynamic partner: it runs the shared scenario twice with an identical seed
and asserts the two dense traces are **byte-identical**. If any latent
non-determinism slips past the static guard, two seed-identical runs diverge and
their canonical-CSV SHA-256 hashes stop matching — this sentinel reds loudly
(III.11).

The invariant traces to a material relation (Aleksandrov Test): "history is the
deterministic output of material conditions" — the same initial conditions and
the same seed must yield the same history, or the engine is not a lawful model.

The efficacy proof (:func:`test_hash_distinguishes_divergent_traces`) shows the
check is non-vacuous: a single mutated cell in an otherwise-identical trace
flips the hash, so a real per-tick divergence would be caught.
"""

from __future__ import annotations

import hashlib

import pytest
from tools.regression_test import DenseTrace, dense_trace_to_csv_bytes

from babylon.sentinels.dynamic import DynamicArtifact

pytestmark = pytest.mark.unit


def _hash_trace(trace: DenseTrace) -> str:
    """Return the SHA-256 hex digest of a dense trace's canonical CSV bytes.

    :param trace: The dense trace to serialize and hash.
    :returns: Full 64-char SHA-256 hex digest of the canonical CSV byte stream.
    """
    return hashlib.sha256(dense_trace_to_csv_bytes(trace)).hexdigest()


def test_shared_run_is_deterministic(shared_tick: DynamicArtifact) -> None:
    """Two seed-identical runs of the shared scenario hash byte-identically.

    This is the canonical Determinism assertion (Constitution III.7): the
    ``shared_tick`` fixture executes the ``imperial_circuit`` scenario twice with
    the same seed and records both canonical dense-trace hashes. Equality is the
    invariant; any inequality is a non-determinism bug in the engine.

    :param shared_tick: Session-scoped read-only tick artifact.
    """
    assert shared_tick.hash_a == shared_tick.hash_b, (
        "Non-determinism detected: two seed-identical runs of "
        f"{shared_tick.scenario!r} produced diverging dense traces "
        f"({shared_tick.hash_a} != {shared_tick.hash_b}). A latent "
        "unseeded-RNG / wall-clock / iteration-order source has slipped past "
        "the static guard (Constitution III.7)."
    )


def test_hash_distinguishes_divergent_traces(shared_tick: DynamicArtifact) -> None:
    """Efficacy: a one-cell divergence flips the canonical-trace hash.

    Proves the equality check is not vacuous. We take the real dense trace,
    hash it, then build a structurally-identical copy with a single mutated
    cell in one tick row and hash that. The hashes MUST differ — which means a
    genuine per-tick divergence between run A and run B would be caught by
    :func:`test_shared_run_is_deterministic`, not silently absorbed.

    :param shared_tick: Session-scoped read-only tick artifact.
    """
    real = shared_tick.trace
    assert real.rows, "shared trace must have at least one row to mutate"

    baseline_hash = _hash_trace(real)

    # Structurally-identical copy: same scenario, same header, deep-copied rows.
    mutated_rows = [list(row) for row in real.rows]
    # Perturb a single cell — a divergence a real non-determinism bug produces.
    original_cell = mutated_rows[0][-1]
    mutated_rows[0][-1] = original_cell + "_DIVERGED"
    mutated = DenseTrace(
        scenario=real.scenario,
        header=list(real.header),
        rows=mutated_rows,
    )

    mutated_hash = _hash_trace(mutated)

    assert baseline_hash != mutated_hash, (
        "Determinism sentinel is vacuous: a mutated trace cell did not change "
        "the canonical hash, so a real run-A/run-B divergence would go "
        "undetected."
    )
    # And an untouched re-hash of the same trace is stable (self-consistency).
    assert _hash_trace(real) == baseline_hash
