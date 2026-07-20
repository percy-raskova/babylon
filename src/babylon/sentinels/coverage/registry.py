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

from typing import Literal

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


class GateEstate(BaseModel):
    """One claim that a gate's harness exercises a named service estate.

    A gate can be green and blind: ``qa:regression``'s byte-identical baselines
    passed for months while injecting no economics calculators at all, so the
    project's Definition of Done never executed a line of the estate it claimed
    to guard. This row makes the claim checkable — the estate is whatever a
    service factory returns, and the harness must inject all of it.

    Frozen and ``extra="forbid"`` so a malformed row is a loud import-time
    failure (Constitution III.11).

    :ivar gate_name: the mise task the claim is about (e.g. ``"qa:regression"``).
    :ivar harness_file: repo-relative ``.py`` path of the harness the gate runs.
    :ivar estate_name: human name for the estate (e.g.
        ``"financial_calculators"``).
    :ivar factory_file: repo-relative ``.py`` path defining ``factory_symbol``.
    :ivar factory_symbol: the factory function whose returned dict keys ARE the
        estate.
    :ivar exempt_keys: keys the gate deliberately does not inject.
    :ivar exempt_reason: why those keys are exempt; required when
        ``exempt_keys`` is non-empty — a narrowed claim must be argued.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    gate_name: str
    harness_file: str
    estate_name: str
    factory_file: str
    factory_symbol: str
    exempt_keys: tuple[str, ...] = ()
    exempt_reason: str = ""

    @model_validator(mode="after")
    def _validate_shape(self) -> GateEstate:
        """Reject non-``.py`` paths and silently-narrowed claims.

        :returns: ``self`` when valid.
        :raises ValueError: If ``harness_file``/``factory_file`` is not a ``.py``
            path, or ``exempt_keys`` is non-empty without an ``exempt_reason``.
        """
        for label, value in (
            ("harness_file", self.harness_file),
            ("factory_file", self.factory_file),
        ):
            if not value.endswith(".py"):
                raise ValueError(f"{self.gate_name!r}: {label} must be a .py path, got {value!r}")
        if self.exempt_keys and not self.exempt_reason.strip():
            raise ValueError(
                f"{self.gate_name!r}: exempt_keys requires an exempt_reason — "
                "narrowing a gate's claim silently is the failure this row exists "
                "to forbid"
            )
        return self


#: The gates whose executed-code set is compared against the estate they claim
#: to guard. ``qa:regression`` is the project's Definition of Done.
GATE_ESTATES: tuple[GateEstate, ...] = (
    GateEstate(
        gate_name="qa:regression",
        harness_file="tools/regression_test.py",
        estate_name="economics_calculators",
        factory_file=f"{_ECON}/factory.py",
        factory_symbol="create_economics_services",
        exempt_keys=(
            "melt_calculator",
            "basket_calculator",
            "gamma_calculator",
            "capital_calculator",
            "throughput_calculator",
            "transition_engine",
            "tensor_registry",
        ),
        exempt_reason=(
            "U1.3 wired the harness's calculator_overrides from "
            "create_financial_services only (the D4 committed FRED fixture covers "
            "the Vol III series alone). The Volumes I/II economics estate needs "
            "its own committed fixture before the harness can inject it; narrowed "
            "deliberately, not silently."
        ),
    ),
    GateEstate(
        gate_name="qa:regression",
        harness_file="tools/regression_test.py",
        estate_name="financial_calculators",
        factory_file=f"{_ECON}/factory.py",
        factory_symbol="create_financial_services",
    ),
)


class LatticeRungRequirement(BaseModel):
    """One declared Amendment U spatial-lattice-rung concordance (#39 T8).

    Amendment U's lattice (``hex ≺ county``, then three PARALLEL
    county-aggregations — CZ, MSA, state — with only ``state ≺ nation``
    nesting further) is grounded by a "backing concordance" per rung: a
    reference-DB table, a committed CSV artifact, or (where no external
    source exists) the derivation code/constant itself. The historical bug
    this row family guards against is the **CZ-silent-fallback class**: T7's
    web CZ framing used to fall back to county silently when the crosswalk
    was unavailable — a rung whose concordance goes missing or empty must
    fail LOUD, naming the rung, never degrade quietly (Constitution III.11).

    A SEPARATE, additive sibling of :class:`DataRequirement` (not an
    extension of it) — the two "reference_table" rows below (hex→county,
    county→MSA) *could* reuse ``DataRequirement``'s exact shape, but the
    county→CZ row's coverage assertion (parse the committed CSV, floor its
    key/value coverage) and the two derivation rows (no class at all) do not
    fit that model's "a source class must exist" contract, so a new sibling
    keeps :class:`DataRequirement` untouched rather than growing a
    conditionally-validated superset onto it (mirrors the vocabulary
    sentinel's own precedent of adding rule (d)'s edge-shape closure as a
    NEW, ADDITIVE family rather than mutating the node-shape rule (c)).

    Frozen and ``extra="forbid"`` so a malformed row is a loud failure at
    import time (Constitution III.11).

    :ivar rung: stable identity for the lattice rung (e.g. ``"hex_to_county"``).
    :ivar concordance_name: human name for the backing concordance (a table
        name, a CSV filename, or a description of the derivation).
    :ivar kind: ``"reference_table"`` (a reference-DB-backed SQLAlchemy model
        class; the static sensor proves the class exists, mirroring
        :func:`~babylon.sentinels.coverage.checks.check_source_classes_exist`
        — table EMPTINESS is governed by the existing ``data-catalog.yaml``
        KEEP law, :mod:`babylon.sentinels.coverage.db_probe`, not re-checked
        here), ``"committed_csv"`` (an in-repo CSV the fast gate parses
        directly and floors its key/value coverage — the CZ-silent-fallback
        guard), or ``"derivation"`` (no external source; a pure function or
        module-level constant IS the concordance, declared explicitly so the
        rung is never silently omitted from the coverage map).
    :ivar source_file: repo-relative path. A ``.py`` module for
        ``reference_table``/``derivation``; the committed ``.csv`` artifact
        itself for ``committed_csv``.
    :ivar material_relation: the material relation this rung grounds
        (Aleksandrov Test) — why the aggregation is meaningless without it.
    :ivar source_symbol: the class (``reference_table``) or function/constant
        name (``derivation``) whose continued existence the sensor proves.
        Unused (must stay blank) for ``committed_csv``.
    :ivar key_column: (``committed_csv`` only) the CSV column holding the
        finer-grained key (e.g. ``county_fips``).
    :ivar value_column: (``committed_csv`` only) the CSV column holding the
        coarser-grained value (e.g. ``cz_id``).
    :ivar min_keys: (``committed_csv`` only) floor on distinct ``key_column``
        values — below this, the artifact is truncated/corrupted.
    :ivar min_values: (``committed_csv`` only) floor on distinct
        ``value_column`` values.
    :ivar notes: free-text clarification.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    rung: str
    concordance_name: str
    kind: Literal["reference_table", "committed_csv", "derivation"]
    source_file: str
    material_relation: str
    source_symbol: str = ""
    key_column: str = ""
    value_column: str = ""
    min_keys: int = 0
    min_values: int = 0
    notes: str = ""

    @model_validator(mode="after")
    def _validate_shape(self) -> LatticeRungRequirement:
        """Reject empty/incoherent rows loudly at import (III.11).

        :returns: ``self`` when valid.
        :raises ValueError: if ``rung``/``concordance_name``/``source_file``
            is blank, or the per-``kind`` field contract is violated (a
            ``committed_csv`` row missing its column/floor declarations, or a
            ``reference_table``/``derivation`` row missing its
            ``source_symbol`` or pointing at a non-``.py`` file).
        """
        if not self.rung.strip():
            raise ValueError("LatticeRungRequirement.rung must be non-empty")
        if not self.concordance_name.strip():
            raise ValueError(f"{self.rung!r}: concordance_name must be non-empty")
        if not self.source_file.strip():
            raise ValueError(f"{self.rung!r}: source_file must be non-empty")
        if self.kind == "committed_csv":
            if not self.source_file.endswith(".csv"):
                raise ValueError(f"{self.rung!r}: committed_csv kind requires a .csv source_file")
            if not self.key_column.strip() or not self.value_column.strip():
                raise ValueError(
                    f"{self.rung!r}: committed_csv kind requires key_column and value_column"
                )
            if self.min_keys <= 0 or self.min_values <= 0:
                raise ValueError(
                    f"{self.rung!r}: committed_csv kind requires positive min_keys/min_values"
                )
        else:
            if not self.source_file.endswith(".py"):
                raise ValueError(f"{self.rung!r}: {self.kind} kind requires a .py source_file")
            if not self.source_symbol.strip():
                raise ValueError(f"{self.rung!r}: {self.kind} kind requires source_symbol")
        return self


#: Repo-relative home of the dialectics level-lattice module (the county→state
#: and state→nation derivations live here — factored out for readability).
_LEVELS = "src/babylon/domain/dialectics/instances/levels.py"

#: One row per Amendment U lattice rung (#39 T8), naming its backing
#: concordance. A rung whose concordance goes missing/empty fails LOUD,
#: naming the rung — the CZ-silent-fallback class this family guards against.
LATTICE_RUNG_REQUIREMENTS: tuple[LatticeRungRequirement, ...] = (
    LatticeRungRequirement(
        rung="hex_to_county",
        concordance_name="bridge_county_h3",
        kind="reference_table",
        source_file="src/babylon/reference/schema.py",
        source_symbol="BridgeCountyH3",
        material_relation=(
            "hex -> county spatial join — the immutable res-7 substrate's sole "
            "path into the county-grain economy (query_h3_to_county_fips/"
            "query_hex_claims read it); without it a hex-keyed seed cannot "
            "resolve to the real county the tick economy reads."
        ),
        notes=(
            "Table EMPTINESS is already governed nightly by data-catalog.yaml's "
            "KEEP-disposition law (db_probe.py) — bridge_county_h3 is disposition: "
            "keep there. This row proves the class the code depends on still "
            "exists at its declared module path (mirrors DataRequirement's own "
            "static contract)."
        ),
    ),
    LatticeRungRequirement(
        rung="county_to_cz",
        concordance_name="bridge_county_cz.csv",
        kind="committed_csv",
        source_file="src/babylon/data/reference/bridge_county_cz.csv",
        material_relation=(
            "county -> 1990 ERS commuting zone (Amendment U) — the daily "
            "reproduction-of-labor-power aggregation geography; T7's CZ web "
            "framing reads this crosswalk directly. If it goes missing or "
            "truncated the framing must fail loud, never silently fall back to "
            "county (the CZ-silent-fallback class this row exists to prevent)."
        ),
        key_column="county_fips",
        value_column="cz_id",
        min_keys=3000,
        min_values=741,
        notes=(
            "Floors mirror the artifact's OWN documented facts, not independently "
            "invented magic numbers: data-artifacts.yaml pins bridge_county_cz at "
            "rows=3141; cz_adjunction()'s docstring and "
            "tests/unit/dialectics/test_levels.py::TestCZAdjunction both "
            "independently pin 741 distinct CZs. >= (not ==) so a future, "
            "gap-closing re-derivation (more counties/CZs, never fewer) still "
            "passes."
        ),
    ),
    LatticeRungRequirement(
        rung="county_to_msa",
        concordance_name="bridge_county_metro",
        kind="reference_table",
        source_file="src/babylon/reference/schema.py",
        source_symbol="BridgeCountyMetro",
        material_relation=(
            "county -> OMB metropolitan statistical area (Amendment U) — the "
            "concentrated labor/housing-market geography; partial by design "
            "(non-metro counties carry no MSA), read by msa_adjunction() via "
            "dim_metro_area.area_type == 'msa'."
        ),
        notes=(
            "Table EMPTINESS is already governed nightly by data-catalog.yaml's "
            "KEEP-disposition law (db_probe.py) — bridge_county_metro is "
            "disposition: keep there."
        ),
    ),
    LatticeRungRequirement(
        rung="county_to_state",
        concordance_name="FIPS-prefix derivation",
        kind="derivation",
        source_file=_LEVELS,
        source_symbol="_state_parent_map",
        material_relation=(
            "county -> state (Amendment U, the juridical-repressive geography): "
            "a pure 2-digit FIPS-prefix derivation, no external table. Declared "
            "explicitly (rather than omitted) so the rung is not silently "
            "invisible from the coverage map merely because it needs no data "
            "file — the derivation function itself is the concordance."
        ),
    ),
    LatticeRungRequirement(
        rung="state_to_nation",
        concordance_name="constant nation id",
        kind="derivation",
        source_file=_LEVELS,
        source_symbol="_NATION_ID",
        material_relation=(
            "state -> nation (Amendment U): every state resolves to the "
            "constant nation id 'US'. Declared explicitly for the same reason "
            "as county_to_state — the constant itself is the concordance."
        ),
    ),
)
