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
MEASUREMENT_DEPENDENCIES: tuple[MeasurementDependency, ...] = (
    MeasurementDependency(
        opposition_key="price_value",
        inputs_fields=("market_balance",),
        producer_file=_CONTRADICTION,
        produces_symbols=("market_balance", "price_log", "price_velocity"),
    ),
    # U5.7 derives financialization_index in ContradictionSystem from the
    # scissors' fictitious_log; market_scissors.py is the upstream axis
    # owner, contradiction.py is the field producer.
    MeasurementDependency(
        opposition_key="financial",
        inputs_fields=("financialization_index",),
        producer_file=_CONTRADICTION,
        produces_symbols=("financialization_index", "fictitious_log"),
    ),
    MeasurementDependency(
        opposition_key="surplus_distribution",
        inputs_fields=("rentier_share",),
        producer_file=_CONTRADICTION,
        produces_symbols=("surplus_distribution", "rentier_share"),
    ),
    MeasurementDependency(
        opposition_key="debt_spiral",
        inputs_fields=("debt_ratio",),
        producer_file=_CONTRADICTION,
        produces_symbols=("debt_accumulation", "debt_ratio"),
    ),
    MeasurementDependency(
        opposition_key="credit",
        inputs_fields=("credit_fragility",),
        producer_file=_CONTRADICTION,
        produces_symbols=("credit_fragility", "credit_state"),
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
