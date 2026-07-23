"""Declared invariants of the ``domain_sync`` sentinel: what the ledger DOMAINs are.

**The error class** (``ledger-contract-drift``): the constrained value types in
:mod:`babylon.models.types` (``Probability`` ``[0,1]``, ``Currency``
``[0,inf)``, ``Ratio`` ``(0,inf)``, ``LaborHours`` ``[0,inf)``) carry a
range contract that the PostgreSQL ledger ALSO enforces — historically as ~128
inline ``CHECK`` clauses hand-copied across the migration files, with the
5-digit county-FIPS regex ``~ '^\\d{5}$'`` duplicated across seven of them. Two
copies of one contract drift: someone widens ``Probability`` to ``le=2`` in
``types.py`` and the ledger still rejects ``1.5``; someone writes ``^[0-9]{5}$``
in a new migration and the "single" FIPS format silently forks. Migration
``0039_domain_contracts.sql`` lifts each contract into ONE PostgreSQL
``CREATE DOMAIN`` object; this sentinel is the guard that the migration's
committed bounds have not drifted from their single source.

**Two source-of-truth families, one registry.**

- **Numeric domains** (:data:`NUMERIC_DOMAINS`) draw their bounds from the
  ``annotated_types`` metadata on a named :mod:`babylon.models.types` type —
  ``types.py`` is the source of truth, the sentinel derives the expected
  ``CHECK`` from it live, and neither the migration nor a hand-edited generator
  can diverge without reddening the gate.
- **Format domains** (:data:`FORMAT_DOMAINS`) have no ``types.py`` source — a
  FIPS regex is a SQL-native format contract — so THIS registry is their single
  source of truth (the very thing the seven duplicated inline copies lacked).

**Scope discipline (read before extending — mirrors the ``defines_passthrough``
registry's own restraint):** a numeric domain is listed here ONLY when a real
ledger column already backs that ``types.py`` type with an inline ``CHECK`` of
the matching range (evidence in each row's ``evidence`` field). Several
``types.py`` types are DELIBERATELY absent — see :data:`DEFERRED_DOMAINS` — so
the estate never invents a DOMAIN for a type no column uses. Adding a domain is
a registry edit plus a regenerate (``tools/generate_domain_ddl.py``), never a
silent migration hand-edit.

Layer 0.5: imports nothing above :mod:`babylon.models`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, model_validator

__all__ = [
    "DEFERRED_DOMAINS",
    "FORMAT_DOMAINS",
    "MIGRATION_FILENAME",
    "MIGRATION_PATH",
    "NUMERIC_DOMAINS",
    "FormatDomainSpec",
    "NumericDomainSpec",
]

#: Repo root (this file is
#: ``<root>/src/babylon/sentinels/domain_sync/registry.py``).
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]

#: The one migration these domains are declared in. The sentinel parses this
#: file's committed text; the codegen tool writes it. Both resolve it here so
#: the path lives in exactly one place.
MIGRATION_FILENAME: Final[str] = "0039_domain_contracts.sql"
MIGRATION_PATH: Final[Path] = (
    _REPO_ROOT / "src" / "babylon" / "persistence" / "migrations" / MIGRATION_FILENAME
)


class NumericDomainSpec(BaseModel):
    """A range DOMAIN whose bounds are generated from a ``models.types`` type.

    :ivar name: The PostgreSQL domain name (lowercase SQL identifier).
    :ivar source_type: The attribute name on :mod:`babylon.models.types` whose
        ``annotated_types`` ``ge``/``le``/``gt`` metadata IS the range contract
        (e.g. ``"Probability"``). The bound is read from ``types.py`` live —
        never copied here — so this registry cannot itself drift from it.
    :ivar sql_base: The SQL base type the domain wraps (all backing columns are
        ``double precision``).
    :ivar evidence: Repo-relative ``file`` + column names of real ledger
        columns whose inline ``CHECK`` this domain's range matches — the
        "backs a real column" proof that keeps the estate from inventing a
        DOMAIN for an unused type.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    source_type: str
    sql_base: str
    evidence: tuple[str, ...]

    @model_validator(mode="after")
    def _validate_shape(self) -> NumericDomainSpec:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If ``name`` is not a lowercase identifier,
            ``source_type`` or ``sql_base`` is blank, or ``evidence`` is empty
            (a numeric domain with no backing column is exactly the invented
            domain this registry's scope discipline forbids).
        """
        if not self.name.isidentifier() or self.name != self.name.lower():
            raise ValueError(f"domain name must be a lowercase identifier, got {self.name!r}")
        if not self.source_type.strip():
            raise ValueError(f"{self.name!r}: source_type must be non-empty")
        if not self.sql_base.strip():
            raise ValueError(f"{self.name!r}: sql_base must be non-empty")
        if not self.evidence:
            raise ValueError(
                f"{self.name!r}: evidence must cite >=1 backing column "
                "(no invented domains — registry scope discipline)"
            )
        return self


class FormatDomainSpec(BaseModel):
    """A string-format DOMAIN whose pattern IS declared here (no ``types.py`` source).

    :ivar name: The PostgreSQL domain name (lowercase SQL identifier).
    :ivar sql_base: The SQL base type the domain wraps (``text``).
    :ivar kind: ``"regex"`` (checked with ``VALUE ~ '<pattern>'``) or
        ``"length"`` (checked with ``length(VALUE) = <pattern>``). Both are
        pure format predicates — no float arithmetic (``length`` is a builtin
        string function, ``=`` an integer comparison).
    :ivar pattern: The regex literal (for ``regex``) or the exact character
        count as a string (for ``length``) — this registry is the single
        source of truth these duplicated inline copies never had.
    :ivar evidence: Repo-relative migration files + columns that carry the
        duplicated inline copy this domain consolidates.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    sql_base: str
    kind: Literal["regex", "length"]
    pattern: str
    evidence: tuple[str, ...]

    @model_validator(mode="after")
    def _validate_shape(self) -> FormatDomainSpec:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If ``name`` is not a lowercase identifier,
            ``pattern`` is blank, ``evidence`` is empty, or a ``length`` row's
            ``pattern`` is not a positive integer literal.
        """
        if not self.name.isidentifier() or self.name != self.name.lower():
            raise ValueError(f"domain name must be a lowercase identifier, got {self.name!r}")
        if not self.pattern.strip():
            raise ValueError(f"{self.name!r}: pattern must be non-empty")
        if not self.evidence:
            raise ValueError(f"{self.name!r}: evidence must cite >=1 duplicated inline site")
        if self.kind == "length" and not (self.pattern.isdigit() and int(self.pattern) > 0):
            raise ValueError(
                f"{self.name!r}: a length domain's pattern must be a positive integer, "
                f"got {self.pattern!r}"
            )
        return self


#: The numeric range domains. Each is a ``models.types`` type that ALREADY
#: backs an inline-``CHECK`` ledger column of the matching range (evidence
#: cited per row). Bounds are read from ``types.py`` at generate/verify time —
#: never copied here — so these two definitions cannot drift apart.
NUMERIC_DOMAINS: Final[tuple[NumericDomainSpec, ...]] = (
    NumericDomainSpec(
        name="probability",
        source_type="Probability",
        sql_base="double precision",
        evidence=(
            "0020_dynamic_consciousness_state.sql: p_acquiescence, p_revolution "
            "(CHECK BETWEEN 0 AND 1; SocialClass.p_acquiescence is typed Probability)",
            "0024_dynamic_relationship_state.sql: tension, solidarity (BETWEEN 0 AND 1)",
            "0025_balkanization.sql: legitimacy, control_level, recognition_level, "
            "influence_level (BETWEEN 0 AND 1)",
            "0011_dynamic_hex_state.sql: internet_access_pct, surveillance_coupling "
            "(BETWEEN 0 AND 1)",
        ),
    ),
    NumericDomainSpec(
        name="currency",
        source_type="Currency",
        sql_base="double precision",
        evidence=(
            "0010_immutable_reference_tables.sql: rent, phi_year, bilateral_value "
            "(CHECK >= 0; imperial rent Phi is typed Currency)",
            "0012_dynamic_external_node_state.sql: phi_year_inflow, bilateral_trade_value "
            "(CHECK >= 0)",
        ),
    ),
    NumericDomainSpec(
        name="ratio",
        source_type="Ratio",
        sql_base="double precision",
        evidence=(
            "0010_immutable_reference_tables.sql: tau, erdi_ratio (CHECK > 0; exchange "
            "ratios are typed Ratio)",
            "0012_dynamic_external_node_state.sql: erdi_ratio (CHECK > 0)",
        ),
    ),
    NumericDomainSpec(
        name="labor_hours",
        source_type="LaborHours",
        sql_base="double precision",
        evidence=(
            "0011_dynamic_hex_state.sql: c, v, s (CHECK >= 0; the labor-time tensor "
            "cells are typed LaborHours — SNLT, distinct from Currency)",
        ),
    ),
)

#: The string-format domains. THIS registry is their single source of truth
#: (no ``types.py`` type carries a FIPS/H3 format). ``fips5`` consolidates the
#: 5-digit county/geoid regex duplicated across seven migrations; ``fips2`` the
#: 2-digit state regex across three; ``h3index`` the 15-char H3 length across
#: two.
FORMAT_DOMAINS: Final[tuple[FormatDomainSpec, ...]] = (
    FormatDomainSpec(
        name="fips5",
        sql_base="text",
        kind="regex",
        pattern=r"^\d{5}$",
        evidence=(
            "0010_immutable_reference_tables.sql: county_fips (x2)",
            "0011_dynamic_hex_state.sql: county_fips",
            "0018_tiger_county_geometry.sql: geoid",
            "0020_dynamic_consciousness_state.sql: county_fips",
            "0021_dynamic_demographics_state.sql: county_fips",
            "0022_dynamic_employment_state.sql: county_fips",
            "0027_hex_spatial_map.sql: county_fips",
        ),
    ),
    FormatDomainSpec(
        name="fips2",
        sql_base="text",
        kind="regex",
        pattern=r"^\d{2}$",
        evidence=(
            "0011_dynamic_hex_state.sql: state_fips",
            "0018_tiger_county_geometry.sql: state_fips",
            "0027_hex_spatial_map.sql: state_fips",
        ),
    ),
    FormatDomainSpec(
        name="h3index",
        sql_base="text",
        kind="length",
        pattern="15",
        evidence=(
            "0011_dynamic_hex_state.sql: h3_index (length = 15)",
            "0027_hex_spatial_map.sql: h3_index (length = 15)",
        ),
    ),
)

#: ``types.py`` constrained types DELIBERATELY NOT given a domain, each with the
#: reason (the "don't invent a domain for a type no column uses" discipline made
#: explicit and auditable). Not consumed by any check — a documentation anchor
#: the ADR and any future extender reads first.
DEFERRED_DOMAINS: Final[dict[str, str]] = {
    "Intensity": (
        "[0,1] — shares its range with Probability; no ledger column is persisted "
        "as a distinct contradiction-intensity CHECK (the 0024 comment notes tension "
        "IS the intensity measure, but that column is model-typed Probability). No "
        "distinct backing column -> not invented."
    ),
    "Coefficient": (
        "[0,1] — the basket gamma column (0010) is BETWEEN 0 AND 1 but is reference "
        "data with no confirmed Coefficient-typed model field; deferred to avoid "
        "mis-attribution. Candidate for a later coefficient domain + gamma retrofit."
    ),
    "Gini": (
        "[0,1] — the social_class.inequality field IS typed Gini, but its persisted "
        "column (postgres_schema.py) is an UNCONSTRAINED float (no CHECK to lift). A "
        "gini domain would ADD a new contract (retrofit territory, deliverable 4), "
        "deferred as byte-safety-unproven."
    ),
    "Ideology": (
        "[-1,1] — no ledger column persists an ideology-semantic value in [-1,1]; the "
        "ternary ideology_r/l/f columns (0020) are each [0,1], and the only [-1,1] "
        "column (metabolic_reduction, 0025) is a metabolic modifier, not ideology. "
        "Mapping it to an 'ideology' domain would be a semantic lie -> not invented."
    ),
    "SignedLaborHours": (
        "(-inf,+inf) — unbounded, so there is no CHECK to express; a DOMAIN with no "
        "CHECK is pointless. Never a domain."
    ),
}
