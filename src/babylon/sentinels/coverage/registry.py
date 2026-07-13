"""The declared source of truth for reference-data dependencies.

Every economic computation that reads the reference database (QCEW employment,
LODES commuter flows, BEA IMPORT_USE tables) depends on the corresponding rows
being present for the queried county/year. When they are absent the source
adapter returns a falsy :class:`~babylon.domain.economics.tensor.NoDataSentinel`
and the tick degrades to a placeholder *silently* — no crash, all tests green.
Constitution III.11 (Loud Failure) forbids exactly this silence.

Each row below is one :class:`DataRequirement`: a named reference-data
dependency, the adapter **class** that fulfils it, the module that class lives
in, the reference tables it reads, and the material relation the requirement
traces to (Aleksandrov Test). This literal is intentionally hand-written — it is
a dev-time contract, not player-moddable runtime config, so it carries no
regeneration machinery. The static coherence sensor in
:mod:`babylon.sentinels.coverage.checks` proves each named class still exists;
the row grows the coverage map so a moved/renamed/deleted source adapter reds
the fast-gate instead of silently orphaning a dependency.

The reference-table names are documented here for the *nightly* coverage probe
(out of scope for the fast-gate) and are NOT asserted statically — only the
source class's existence is.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class DataRequirement(BaseModel):
    """One declared reference-data dependency of the economic tick.

    Frozen and ``extra="forbid"`` so a malformed row is a loud failure at import
    time (Constitution III.11) rather than a quiet ``None`` at check time.

    :ivar name: stable identity for the dependency (e.g. ``"qcew_county_naics"``).
    :ivar source_class: the adapter class that fulfils the dependency; its
        continued existence is what the static sensor asserts.
    :ivar source_file: repo-relative path to the module defining ``source_class``.
    :ivar tables: the reference-DB table(s) the adapter reads — documentation for
        the *nightly* coverage probe, NOT asserted by the static sensor.
    :ivar material_relation: the material relation this data grounds (Aleksandrov
        Test): why the number the engine computes is meaningless without it.
    :ivar notes: free-text clarification.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    source_class: str
    source_file: str
    tables: tuple[str, ...]
    material_relation: str
    notes: str = ""

    @model_validator(mode="after")
    def _validate_shape(self) -> DataRequirement:
        """Reject empty identity/location fields loudly at import (III.11).

        :returns: ``self`` when valid.
        :raises ValueError: if ``name``, ``source_class``, or ``source_file`` is
            blank, or if ``source_file`` is not a ``.py`` path.
        """
        if not self.name.strip():
            raise ValueError("DataRequirement.name must be non-empty")
        if not self.source_class.strip():
            raise ValueError(f"{self.name!r}: source_class must be non-empty")
        if not self.source_file.endswith(".py"):
            raise ValueError(
                f"{self.name!r}: source_file must be a .py path, got {self.source_file!r}"
            )
        return self


#: Repo-relative root of the economics domain, factored out for readability.
_ECON = "src/babylon/domain/economics"

#: The known reference-data requirements of the economic tick. Each names the
#: adapter class the static sensor proves still exists; the ``tables`` are the
#: nightly probe's target and are documentation here.
DATA_REQUIREMENTS: tuple[DataRequirement, ...] = (
    DataRequirement(
        name="qcew_county_naics",
        source_class="SQLiteQCEWCountyNAICSSource",
        source_file=f"{_ECON}/throughput/adapters.py",
        tables=("fact_qcew_annual", "fact_qcew_county_rollup", "dim_industry"),
        material_relation=(
            "Per-county employment by NAICS sector — the v (variable capital) and "
            "living-labour base of every county's value product; without it the "
            "surplus-value and profit-rate tensors have no denominator."
        ),
        notes="Returns NoDataSentinel(fips, year) when a county/year QCEW row is absent.",
    ),
    DataRequirement(
        name="qcew_national_employment",
        source_class="SQLiteQCEWNationalEmploymentSource",
        source_file=f"{_ECON}/melt/adapters.py",
        tables=("fact_qcew_county_rollup", "dim_ownership", "dim_time"),
        material_relation=(
            "National total covered employment L_n — the denominator of the MELT "
            "(monetary expression of labour time) that converts price aggregates to "
            "socially-necessary labour hours."
        ),
        notes="get_national_employment(year); ~151M for 2022.",
    ),
    DataRequirement(
        name="lodes_commuter_flow",
        source_class="SQLiteLODESCommuterFlowSource",
        source_file=f"{_ECON}/throughput/adapters_lodes.py",
        tables=("fact_lodes_od",),
        material_relation=(
            "Origin-destination commuter flows — where labour is expended vs where "
            "it resides; the commuter adjustment that keeps value produced attributed "
            "to the workplace county, not the bedroom county."
        ),
        notes="Absent LODES rows degrade the commuter-adjusted throughput to residence-only.",
    ),
    DataRequirement(
        name="bea_import_use",
        source_class="DBImportShareSource",
        source_file=f"{_ECON}/tensor_hierarchy/production_chain_rent.py",
        tables=("fact_bea_import_use", "dim_industry"),
        material_relation=(
            "BEA import-use shares by industry — the unequal-exchange load carried in "
            "imported intermediates; the IMPORT_USE term of the Leontief imperial-rent "
            "(Phi) flow. Missing shares zero out the extraction the map is meant to show."
        ),
        notes="Feeds the per-county Leontief Phi flow (Program-17 item-1a).",
    ),
)
