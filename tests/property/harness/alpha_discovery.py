"""Discovery walker for spec-054 US4 (alpha-smoothing bound invariant).

Walks ``babylon.config.defines`` recursively through nested Pydantic models;
matches field names against the regex
``r"(?:.*_alpha|alpha_smoothing_rate|.*_decay_alpha)$"`` per spec FR-005;
excludes documented false-positive fields per ``research.md §4``.

Each entry in ``_NOT_EMA_ALPHAS`` MUST carry a one-line comment explaining
why the field is not an EMA rate (per spec-054 FR-005).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Final

from pydantic import BaseModel

from babylon.config.defines import GameDefines

# Documented exclusions: fields whose name matches the EMA regex but which
# are NOT exponential moving average rates. Each entry MUST have a one-line
# comment per spec-054 FR-005.
_NOT_EMA_ALPHAS: Final[frozenset[str]] = frozenset(
    {
        "pareto_alpha",  # power-law distribution exponent, not EMA rate
        "curvature_alpha",  # geometric curvature scale, not EMA rate
    }
)

_ALPHA_FIELD_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:.*_alpha|alpha_smoothing_rate|.*_decay_alpha)$"
)


@dataclass(frozen=True)
class AlphaCoefficient:
    """An EMA-smoothed coefficient discovered in ``defines.py``.

    Attributes:
        containing_class: Pydantic class on ``defines.py`` where the field lives.
        field_name: Field's attribute name (e.g., ``"alpha_smoothing_rate"``).
        default_alpha: Default value declared in ``defines.py``. Validated to
            lie in ``(0.0, 1.0]``.
    """

    containing_class: type[BaseModel]
    field_name: str
    default_alpha: float

    def __post_init__(self) -> None:
        if not (0.0 < self.default_alpha <= 1.0):
            msg = (
                f"AlphaCoefficient {self.containing_class.__name__}."
                f"{self.field_name} default_alpha={self.default_alpha} "
                f"is not a valid EMA rate (must be in (0.0, 1.0])"
            )
            raise ValueError(msg)


@lru_cache(maxsize=1)
def discover_alpha_coefficients() -> tuple[AlphaCoefficient, ...]:
    """Walk ``GameDefines`` recursively; yield every EMA-smoothed coefficient.

    Field-name regex is ``r"(?:.*_alpha|alpha_smoothing_rate|.*_decay_alpha)$"``.
    Excludes ``_NOT_EMA_ALPHAS`` (documented false positives).

    Returns:
        Immutable tuple of ``AlphaCoefficient`` records, sorted by
        (containing_class.__qualname__, field_name) for deterministic
        parametrize-id ordering.
    """
    defines = GameDefines()
    found: list[AlphaCoefficient] = []
    for cls, instance in _iter_nested_pydantic(defines):
        for name in cls.model_fields:
            if not _ALPHA_FIELD_RE.match(name):
                continue
            if name in _NOT_EMA_ALPHAS:
                continue
            value = getattr(instance, name, None)
            if value is None or not isinstance(value, (int, float)):
                continue
            # Out-of-range defaults raise ValueError from __post_init__ —
            # let the exception propagate so test collection halts with a
            # clear diagnostic rather than silently dropping the field.
            found.append(
                AlphaCoefficient(
                    containing_class=cls,
                    field_name=name,
                    default_alpha=float(value),
                )
            )
    return tuple(sorted(found, key=lambda a: (a.containing_class.__qualname__, a.field_name)))


# --------------------------------------------------------------------------- #
# Internal helpers                                                            #
# --------------------------------------------------------------------------- #


def _iter_nested_pydantic(
    root: BaseModel,
) -> list[tuple[type[BaseModel], BaseModel]]:
    """Walk a Pydantic model recursively; yield (cls, instance) for every node."""
    seen_ids: set[int] = set()
    out: list[tuple[type[BaseModel], BaseModel]] = []

    def _walk(obj: BaseModel) -> None:
        if id(obj) in seen_ids:
            return
        seen_ids.add(id(obj))
        out.append((type(obj), obj))
        for name in type(obj).model_fields:
            value = getattr(obj, name, None)
            if isinstance(value, BaseModel):
                _walk(value)

    _walk(root)
    return out


# Surface the not-EMA exclusion list for inspection (e.g., quickstart docs).
NOT_EMA_ALPHAS: Final[frozenset[str]] = _NOT_EMA_ALPHAS

__all__ = ["AlphaCoefficient", "NOT_EMA_ALPHAS", "discover_alpha_coefficients"]
