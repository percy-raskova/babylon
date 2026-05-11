"""MetamorphicPair — optional convenience wrapper (spec 060).

Holds a (baseline, perturbed) pair of world states plus the
perturbation label and params, for diagnostic readability. Concrete
use is up to the test author — tests may build pairs inline if that's
clearer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


@dataclass(frozen=True)
class MetamorphicPair:
    """A (baseline, perturbed) pair labelled with the perturbation."""

    baseline: BaseModel
    perturbed: BaseModel
    perturbation_name: str
    perturbation_params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Best-effort tick parity check — only enforced when both
        # operands carry a ``tick`` attribute.
        b_tick = getattr(self.baseline, "tick", None)
        p_tick = getattr(self.perturbed, "tick", None)
        if b_tick is not None and p_tick is not None and b_tick != p_tick:
            raise ValueError(
                f"MetamorphicPair tick mismatch: baseline={b_tick}, "
                f"perturbed={p_tick}; paired runs must start at the same tick"
            )


__all__ = ["MetamorphicPair"]
