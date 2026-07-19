"""Declared measurement dependencies, one row per opposition.

Each row answers three questions about one opposition key: which
``GraphInputs`` fields its measure READS, which file PRODUCES those fields, and
which symbols that file PUBLISHES for others to read. From those three facts the
sensor derives the real dependency graph and diffs it against the declared
``_DEFAULT_COUPLINGS`` map in both directions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class MeasurementDependency(BaseModel):
    """One opposition's measured inputs and the file that produces them.

    Frozen and ``extra="forbid"`` so a malformed row fails loudly at import
    (Constitution III.11).

    :ivar opposition_key: the registry key (e.g. ``"debt_spiral"``).
    :ivar inputs_fields: the ``GraphInputs`` fields this opposition's measure
        reads — the material the gap reading is made of.
    :ivar producer_file: repo-relative ``.py`` path computing those fields.
    :ivar produces_symbols: the names ``producer_file`` publishes for others;
        a downstream producer mentioning one of these IS a real dependency.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    opposition_key: str
    inputs_fields: tuple[str, ...]
    producer_file: str
    produces_symbols: tuple[str, ...]

    @model_validator(mode="after")
    def _validate_shape(self) -> MeasurementDependency:
        """Reject blank keys, empty field sets, and non-``.py`` producer paths.

        :returns: ``self`` when valid.
        :raises ValueError: If ``opposition_key`` is blank, ``inputs_fields`` or
            ``produces_symbols`` is empty, or ``producer_file`` is not ``.py``.
        """
        if not self.opposition_key.strip():
            raise ValueError("MeasurementDependency.opposition_key must be non-empty")
        if not self.inputs_fields:
            raise ValueError(
                f"{self.opposition_key!r}: inputs_fields must name at least one "
                "GraphInputs field — an opposition measuring nothing is not a "
                "measurement dependency"
            )
        if not self.produces_symbols:
            raise ValueError(f"{self.opposition_key!r}: produces_symbols must be non-empty")
        if not self.producer_file.endswith(".py"):
            raise ValueError(
                f"{self.opposition_key!r}: producer_file must be a .py path, "
                f"got {self.producer_file!r}"
            )
        return self


#: Repo-relative producer roots, factored out for readability.
_CONTRADICTION = "src/babylon/engine/systems/contradiction.py"
_SCISSORS = "src/babylon/engine/systems/market_scissors.py"

#: The declared measurement dependencies of the money/value oppositions.
#:
#: DECLARED LIMITATION: every row below names ``_CONTRADICTION`` as its producer
#: file, and ``check_real_dependencies_are_declared`` (direction B) skips any
#: pair of rows sharing a producer file — a same-file pair mentions its
#: sibling's symbols trivially, so a mention there proves nothing. Direction B
#: is therefore INERT on this registry as seeded, and its invariant test passes
#: vacuously. It is kept as a guard for future rows: the first opposition whose
#: inputs are produced outside ``contradiction.py`` (the U6 monetary anchor, a
#: ``market_scissors.py``-produced field, any new System computing a
#: ``GraphInputs`` field) makes the check live with no code change. Its efficacy
#: is proven meanwhile by the injected-fixture mutation tests in
#: ``tests/unit/sentinels/test_coupling_sentinel.py``, which supply rows with two
#: distinct producer files. Declared here rather than discovered later: this is
#: the correct-but-inert class inside the program that ships its sensor.
#:
#: ``produces_symbols`` is restricted, per row, to the symbols ``_CONTRADICTION``
#: itself computes and returns on its ``GraphInputs`` — i.e. it always equals
#: that row's own ``inputs_fields`` today, because ``_CONTRADICTION`` is the
#: sole producer of all five ``GraphInputs`` fields here. Earlier drafts also
#: listed symbols ``_CONTRADICTION`` merely *reads* off another file's output
#: (``price_log``/``price_velocity``/``fictitious_log`` from
#: ``market_scissors.py`` via ``_SCISSORS``, ``surplus_distribution`` from
#: ``distribution/calculator.py``, ``debt_accumulation`` and ``credit_state``
#: from ``tick/system/__init__.py``/``tick/graph_bridge.py``) — that violated
#: the ``:ivar produces_symbols:`` contract above (only the *producer* of a
#: symbol may claim to publish it) and, for ``price_velocity`` specifically, was
#: outright false: that name never appears in ``contradiction.py`` at all. Those
#: real cross-file relationships are true, but they belong to a row keyed by
#: their actual producer file, not to a row whose registered opposition_key
#: comes from U5 and whose producer_file is ``_CONTRADICTION`` — none of the
#: five keys here name that file's opposition, so no such row is added yet.
MEASUREMENT_DEPENDENCIES: tuple[MeasurementDependency, ...] = (
    MeasurementDependency(
        opposition_key="price_value",
        inputs_fields=("market_balance",),
        producer_file=_CONTRADICTION,
        produces_symbols=("market_balance",),
    ),
    # U5.7 derives financialization_index in ContradictionSystem from the
    # scissors' fictitious_log; market_scissors.py is the upstream axis
    # owner and the real producer of fictitious_log, contradiction.py only
    # reads it — so fictitious_log is not in this row's produces_symbols.
    MeasurementDependency(
        opposition_key="financial",
        inputs_fields=("financialization_index",),
        producer_file=_CONTRADICTION,
        produces_symbols=("financialization_index",),
    ),
    MeasurementDependency(
        opposition_key="surplus_distribution",
        inputs_fields=("rentier_share",),
        producer_file=_CONTRADICTION,
        produces_symbols=("rentier_share",),
    ),
    MeasurementDependency(
        opposition_key="debt_spiral",
        inputs_fields=("debt_ratio",),
        producer_file=_CONTRADICTION,
        produces_symbols=("debt_ratio",),
    ),
    MeasurementDependency(
        opposition_key="credit",
        inputs_fields=("credit_fragility",),
        producer_file=_CONTRADICTION,
        produces_symbols=("credit_fragility",),
    ),
)


def dependency_for(opposition_key: str) -> MeasurementDependency | None:
    """Look up one opposition's declared measurement dependency.

    :param opposition_key: The registry key to look up.
    :returns: The declared row, or ``None`` when the key is not registered (the
        sensors skip unregistered endpoints rather than inventing a claim).
    """
    for row in MEASUREMENT_DEPENDENCIES:
        if row.opposition_key == opposition_key:
            return row
    return None
