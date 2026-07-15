"""Declared per-tick accounting identities the engine guarantees on a trace.

This is instance #3 of the ``babylon.sentinels`` family — the
**Economic-Conservation** sentinel. It declares the accounting/conservation
identities that must hold across *every* row of a deterministic dense trace
(``tools/regression_test.DenseTrace``), and the float tolerance each is judged
within (Constitution Amendment Q / III.12 — *no bare* ``==``).

Only **declared data** lives here (Constitution layer-0.5 boundary): the identity
name, the dense-trace column it constrains, the tolerance, and which clauses of
the accounting law apply. The *checking* logic — which walks a live trace and
applies these clauses — lives in the test layer
(``tests/unit/sentinels/test_conservation.py``), which may import the engine to
build the trace. Keeping the predicate as pure data means a malformed identity is
a **loud import-time failure** (III.11), not a silent mis-check at runtime.

The two declared identities, both verified to hold on the ``imperial_circuit``
scenario across all 53 rows (ticks 0–52):

1. **Finiteness** — no ``NaN``/``inf`` in any numeric economic cell. A collapsed
   float is the canonical "silent corruption" this family exists to catch.
2. **Imperial-rent reserve depletion** — ``economy_imperial_rent_pool`` is a
   finite reserve that is non-negative, never exceeds its initial value, and is
   non-increasing tick-over-tick. Material relation (Aleksandrov Test): the pool
   is the core's accumulated super-profit reserve; within a closed imperial
   circuit with no fresh accumulation it can only be drawn down to fund
   super-wages / repression — it cannot spontaneously refill, and value that does
   not exist cannot be extracted, so it cannot go negative.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

#: The dense-trace header column carrying the accumulated imperial-rent reserve
#: (``tools/regression_test._dense_header`` position 1).
IMPERIAL_RENT_POOL_COLUMN: str = "economy_imperial_rent_pool"

#: Wildcard :attr:`ConservationIdentity.column` meaning *every numeric cell*.
ALL_NUMERIC_COLUMNS: str = "*"


class ConservationIdentity(BaseModel):
    """One declared per-tick accounting identity, judged within a tolerance.

    Frozen and ``extra="forbid"`` so a malformed identity is a loud failure at
    import time (Constitution III.11) rather than a quiet mis-check at runtime.

    The ordered/bounded clauses (:attr:`non_negative`, :attr:`non_increasing`,
    :attr:`bounded_by_initial`) constrain a single time-series and so require a
    concrete :attr:`column`; the :attr:`ALL_NUMERIC_COLUMNS` wildcard may carry
    only :attr:`require_finite`, enforced by :meth:`_validate`.

    :ivar name: Stable identity tag (e.g. ``"imperial_rent_pool_depletion"``).
    :ivar column: The dense-trace header column constrained, or
        :attr:`ALL_NUMERIC_COLUMNS` (``"*"``) for a whole-row finiteness check.
    :ivar abs_tolerance: The declared absolute float tolerance (Amendment Q).
        Applies to the ordered/bounded clause comparisons; ``0.0`` for a
        finiteness-only identity, where no tolerance is meaningful.
    :ivar require_finite: Every constrained cell must be a finite float.
    :ivar non_negative: Every value must satisfy ``v >= -abs_tolerance``.
    :ivar non_increasing: Consecutive values must satisfy
        ``v[t+1] - v[t] <= abs_tolerance`` (a reserve that only depletes).
    :ivar bounded_by_initial: Every value must satisfy
        ``v <= v[0] + abs_tolerance`` (never exceeds the seeded reserve).
    :ivar rationale: Why this identity holds — the material relation it traces to
        and, for tolerances, the one-line derivation of the chosen value.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    column: str
    abs_tolerance: float
    require_finite: bool = True
    non_negative: bool = False
    non_increasing: bool = False
    bounded_by_initial: bool = False
    rationale: str = ""

    @model_validator(mode="after")
    def _validate(self) -> ConservationIdentity:
        """Reject a malformed identity loudly at import (III.11).

        :returns: ``self`` when the identity is well-formed.
        :raises ValueError: on an empty ``name``; a negative ``abs_tolerance``;
            or a wildcard-column identity carrying an ordered/bounded clause
            (which needs a single concrete series to be meaningful).
        """
        if not self.name:
            raise ValueError("ConservationIdentity.name must be non-empty")
        if self.abs_tolerance < 0.0:
            raise ValueError(f"{self.name!r}: abs_tolerance must be >= 0, got {self.abs_tolerance}")
        ordered = self.non_negative or self.non_increasing or self.bounded_by_initial
        if self.column == ALL_NUMERIC_COLUMNS and ordered:
            raise ValueError(
                f"{self.name!r}: the {ALL_NUMERIC_COLUMNS!r} wildcard column supports only "
                "require_finite; ordered/bounded clauses need a single concrete column"
            )
        return self


#: Absolute tolerance for the imperial-rent depletion clauses.
#:
#: Rationale (Amendment Q): dense-trace cells are Python ``repr()`` — the shortest
#: round-trippable IEEE-754 decimal — so parsing a cell back to ``float`` is
#: lossless; this tolerance therefore absorbs only sub-ULP arithmetic noise on a
#: genuinely-flat pool. The smallest real per-tick drawdown observed on
#: ``imperial_circuit`` is ``0.093`` — ~8 orders of magnitude above ``1e-9`` — so
#: a real refill can never hide beneath the tolerance.
_POOL_ABS_TOLERANCE: float = 1e-9


#: The declared conservation identities. Every row is verified to hold on the
#: ``imperial_circuit`` dense trace (ticks 0–52) before being committed here.
CONSERVATION_REGISTRY: tuple[ConservationIdentity, ...] = (
    ConservationIdentity(
        name="economic_columns_finite",
        column=ALL_NUMERIC_COLUMNS,
        abs_tolerance=0.0,
        require_finite=True,
        rationale=(
            "No economic quantity may collapse to NaN/inf. A non-finite cell is the "
            "canonical silent-corruption failure (a divide-by-zero or overflow that "
            "type-checks and serializes) this sentinel family exists to make loud (III.11)."
        ),
    ),
    ConservationIdentity(
        name="imperial_rent_pool_depletion",
        column=IMPERIAL_RENT_POOL_COLUMN,
        abs_tolerance=_POOL_ABS_TOLERANCE,
        require_finite=True,
        non_negative=True,
        non_increasing=True,
        bounded_by_initial=True,
        rationale=(
            "The imperial-rent pool is the core's accumulated super-profit reserve. In a "
            "closed imperial circuit with no fresh accumulation it can only be drawn down to "
            "fund super-wages/repression: it is non-negative (value that does not exist "
            "cannot be extracted), bounded above by the seeded reserve (nothing refills it), "
            "and non-increasing tick-over-tick. Tolerance derivation: see _POOL_ABS_TOLERANCE."
        ),
    ),
)
