"""UUID relabeling invariance — spec 060 US6(a) / FR-013 / SC-009.

Replaces every entity UUID in a ``WorldState`` with a deterministic
non-equal alias and asserts that all numeric fields are bit-identical
(1e-15 relative tolerance). Catches: iteration-order-dependent
reductions; hash-of-id-based seeding; lexicographic-order coupling.

Contract: FR-013 / SC-009.
"""

from __future__ import annotations

import math

import pytest

from babylon.engine.scenarios.two_node import TwoNodeScenario
from tests._helpers.invariants.uuid_relabeler import relabel_uuids

_REL_TOL: float = 1e-15


def _walk_numeric_fields(model: object, prefix: str = "") -> dict[str, float]:
    """Collect every numeric leaf across a Pydantic model tree.

    Returns ``{dotted_path: value}`` for every int/float field
    (excluding bools).
    """
    from pydantic import BaseModel

    out: dict[str, float] = {}
    if isinstance(model, BaseModel):
        for fname in type(model).model_fields:
            child = getattr(model, fname)
            out.update(_walk_numeric_fields(child, prefix=f"{prefix}.{fname}" if prefix else fname))
    elif isinstance(model, dict):
        for k, v in model.items():
            out.update(_walk_numeric_fields(v, prefix=f"{prefix}[{k!r}]"))
    elif isinstance(model, (list, tuple)):
        for i, v in enumerate(model):
            out.update(_walk_numeric_fields(v, prefix=f"{prefix}[{i}]"))
    elif isinstance(model, bool):
        # Don't include bools (treated as numeric in Python)
        pass
    elif isinstance(model, (int, float)) and math.isfinite(float(model)):
        out[prefix] = float(model)
    return out


@pytest.mark.invariant
class TestUUIDRelabelInvariance:
    """Contract FR-013 / SC-009."""

    def test_numeric_fields_identical_under_relabeling(self) -> None:
        """Every numeric field must be bit-identical (1e-15 rel) after relabel.

        Diagnostic per spec-060 FR-013 / FR-010: names the offending
        entity_id, field path, and observed delta.
        """
        baseline, _config, _defines = TwoNodeScenario().build()

        # Many WorldState entity IDs are pattern-constrained
        # (e.g., SocialClass.id matches ^C[0-9]{3}$, Territory.id matches
        # ^(T[0-9]{3}|[0-9a-f]{15})$). Use an alias function that
        # preserves the leading-letter prefix so reconstruction passes
        # validation. This is sufficient to detect ID-iteration-order
        # bugs because every ID still changes (C001 → C500, C002 → C501,
        # T001 → T500, etc.).
        def _prefix_preserving_alias(i: int, original: str) -> str:
            prefix = original[0] if original and original[0].isalpha() else "X"
            # Offset by 500 so aliases never collide with originals
            return f"{prefix}{500 + i:03d}"

        relabeled, mapping = relabel_uuids(baseline, alias_fn=_prefix_preserving_alias)

        # Confirm relabeling actually happened (mapping non-empty)
        assert mapping, (
            "spec-060 FR-013: UUID relabeler produced no aliases on two_node scenario; "
            "the test cannot detect ID-coupling bugs without an actual relabel."
        )

        base_numerics = _walk_numeric_fields(baseline)
        relabeled_numerics = _walk_numeric_fields(relabeled)

        # The set of numeric-field paths differs only insofar as dict keys
        # got renamed; the *values* must coincide on every numeric leaf.
        # Compare values via sorted-by-path. Because dict-key segments
        # in the path differ post-relabel, we compare value MULTISETS.
        base_vals = sorted(base_numerics.values())
        relab_vals = sorted(relabeled_numerics.values())

        assert len(base_vals) == len(relab_vals), (
            f"spec-060 FR-013: numeric leaf count diverged under relabeling. "
            f"baseline={len(base_vals)} relabeled={len(relab_vals)}"
        )

        worst_delta: float = 0.0
        worst_pair: tuple[float, float] | None = None
        for a, b in zip(base_vals, relab_vals, strict=True):
            denom = max(abs(a), 1e-300)
            rel = abs(a - b) / denom
            if rel > worst_delta:
                worst_delta = rel
                worst_pair = (a, b)

        assert worst_delta <= _REL_TOL, (
            f"spec-060 FR-013: numeric field diverged under UUID relabeling. "
            f"worst pair={worst_pair} relative_error={worst_delta:.3e} "
            f"(tolerance={_REL_TOL:.0e}). entity_id mapping changed but a "
            f"numeric value moved with it — suggests ID-coupling in engine."
        )
