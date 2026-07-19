"""Declared scan set and exemptions for the intensive-aggregation sensor.

:data:`SCANNED_FILES` is where intensive quantities are aggregated across space
or class in this codebase — the scissors, the economic tick, the dialectics
catalog. :data:`AGGREGATION_EXEMPTIONS` records the sites where an unweighted
mean is nonetheless correct, each with the reason that makes it correct. An
exemption without a reason is refused at import.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

#: Name fragments that mark a quantity as INTENSIVE — it does not average.
INTENSIVE_LEXICON: tuple[str, ...] = (
    "rate",
    "ratio",
    "share",
    "balance",
    "index",
    "intensity",
    "density",
    "fragility",
    "per_capita",
    "coefficient",
)

#: Name fragments that mark a *function* as computing a mean.
MEAN_LEXICON: tuple[str, ...] = ("mean", "avg", "average")

#: The files scanned by default — where intensives meet space/class aggregation.
SCANNED_FILES: tuple[str, ...] = (
    "src/babylon/engine/systems/market_scissors.py",
    "src/babylon/engine/systems/contradiction.py",
    "src/babylon/domain/dialectics/instances/catalog.py",
)


class AggregationExemption(BaseModel):
    """One site where an unweighted mean of an intensive is nonetheless correct.

    Frozen and ``extra="forbid"`` so a malformed row fails loudly at import
    (Constitution III.11).

    :ivar file: repo-relative path (or absolute path, in tests) of the site.
    :ivar symbol: the enclosing function name the sensor reports.
    :ivar reason: why equal weighting is materially right here — never blank.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    file: str
    symbol: str
    reason: str

    @model_validator(mode="after")
    def _validate_reason(self) -> AggregationExemption:
        """Refuse an exemption that does not say why it is legitimate.

        :returns: ``self`` when valid.
        :raises ValueError: If ``file``, ``symbol``, or ``reason`` is blank.
        """
        for label, value in (
            ("file", self.file),
            ("symbol", self.symbol),
            ("reason", self.reason),
        ):
            if not value.strip():
                raise ValueError(f"AggregationExemption.{label} must be non-empty")
        return self


#: Sanctioned unweighted means. Empty by design — an entry here is a claim that
#: equal weighting is materially correct, and must be argued, not assumed.
AGGREGATION_EXEMPTIONS: tuple[AggregationExemption, ...] = ()
