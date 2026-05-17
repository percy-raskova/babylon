# Contract: `BEAShareLookupService`

**Type**: Python Protocol (PEP 544 structural subtyping).
**Constitutional basis**: II.11 (Subsystem Table Ownership).
**Location**: `src/babylon/reference/bea/share_lookup_service.py`.

This is the **only** legitimate cross-subsystem read path for the BEA
fact tables. Code outside `src/babylon/reference/bea/` MUST NOT issue
SQL directly against `fact_bea_national_industry`,
`fact_bea_io_coefficient`, or `bridge_naics_bea`. Doing so is a
constitutional violation under II.11.

---

## Why this contract exists

The current `hex_hydrator.py` line ~107 holds a hardcoded magic constant:

```python
_INTERMEDIATE_INPUTS_FRACTION = 0.5  # Shaikh-tractable interim, replaced by spec-068
```

Replacing that constant with raw SQL against the BEA fact tables would
cross the subsystem boundary defined by Constitution II.11. The
`BEAShareLookupService` Protocol is the declared interface that crosses
the boundary cleanly:

- **BEA subsystem owns**: `fact_bea_*` schema, the loader pipeline,
  the lookup implementation, the share-computation math, the
  forward-fill logic, the vintage resolution.
- **Persistence subsystem (hex_hydrator) consumes**: only the Pydantic
  result records returned by the Protocol methods.

---

## Protocol definition

```python
from datetime import date
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict


class IndustryShareLookupResult(BaseModel):
    """Per-(BEA-industry, year) intermediate-inputs share lookup result.

    Returned by BEAShareLookupService.lookup_industry_share().
    """
    model_config = ConfigDict(frozen=True)

    intermediate_inputs_share: float        # [0.0, 1.0]
    value_added_share: float                # [0.0, 1.0]
    vintage_published_date: date | None
    used_fallback: bool
    fallback_reason: Literal["none", "forward_fill", "global_default"]


class CountyShareLookupResult(BaseModel):
    """Per-(county, year) intermediate-inputs share lookup result.

    Weighted by the county's QCEW industry employment mix.
    Returned by BEAShareLookupService.lookup_county_share().
    """
    model_config = ConfigDict(frozen=True)

    intermediate_inputs_share: float        # [0.0, 1.0]
    value_added_share: float                # [0.0, 1.0]
    fallback_employment_fraction: float     # [0.0, 1.0]
    per_industry_breakdown: dict[int, float]  # bea_industry_id -> weight


class BEAShareLookupService(Protocol):
    """Declared cross-subsystem interface for reading BEA shares.

    Constitution II.11: subsystem table ownership. The BEA subsystem
    OWNS fact_bea_national_industry, fact_bea_io_coefficient, and
    bridge_naics_bea. Cross-subsystem reads MUST go through this
    Protocol.
    """

    def lookup_industry_share(
        self,
        bea_industry_id: int,
        year: int,
    ) -> IndustryShareLookupResult:
        """Return the per-industry intermediate-inputs share.

        Forward-fills up to 5 years backward if the requested year is
        absent for this industry (Clarification Q3). If no data is
        available within 5 years, falls back to the global default
        share (typically 0.5, the spec-066/067 baseline) and sets
        used_fallback=True with fallback_reason="global_default".

        Args:
            bea_industry_id: BEA-summary industry id (FK to
                dim_bea_industry.bea_industry_id).
            year: Simulation year (2010-2024 in scope).

        Returns:
            IndustryShareLookupResult with shares always in [0, 1].

        Postconditions:
            - intermediate_inputs_share + value_added_share == 1.0
              within ±0.01 (the FR-002 accounting tolerance).
            - vintage_published_date is None iff
              fallback_reason == "global_default".
        """
        ...

    def lookup_county_share(
        self,
        county_fips: str,
        year: int,
    ) -> CountyShareLookupResult:
        """Return the per-county intermediate-inputs share.

        Computed as the QCEW-employment-weighted average of per-BEA-
        industry shares, mapped via bridge_naics_bea from the county's
        NAICS-6-digit employment distribution.

        Args:
            county_fips: 5-digit county FIPS code, zero-padded
                (e.g., "26163" for Wayne County, MI).
            year: Simulation year.

        Returns:
            CountyShareLookupResult with shares always in [0, 1] and
            fallback_employment_fraction giving the share of the
            county's employment that fell back (NAICS-2-digit or
            global default).

        Postconditions:
            - intermediate_inputs_share + value_added_share == 1.0
              within ±0.01.
            - sum(per_industry_breakdown.values()) == 1.0 within ±1e-9.
            - fallback_employment_fraction < 0.01 for the BEA tables to
              be considered "fully covering" this county-year per SC-008.
        """
        ...

    def lookup_io_coefficient(
        self,
        source_industry_id: int,
        target_industry_id: int,
        year: int,
        table_type: Literal["USE", "MAKE", "SUPPLY", "TOTAL_REQ"] = "USE",
    ) -> float | None:
        """Return the Leontief direct-requirements coefficient a_ij.

        Args:
            source_industry_id: BEA industry i (the input).
            target_industry_id: BEA industry j (the output).
            year: Simulation year.
            table_type: 'USE' (default — direct coefficients) or
                'TOTAL_REQ' (Leontief inverse — direct + indirect).

        Returns:
            Coefficient as a float, or None if no row exists
            (interpreted by callers as 0.0).

        Postconditions:
            - When table_type == "USE", returns a float in [0.0, 1.5].
            - Forward-fills up to 5 years per Clarification Q3.
        """
        ...
```

---

## Concrete implementation: `DefaultBEAShareLookupService`

Ships in `src/babylon/reference/bea/share_lookup_service.py` alongside
the Protocol. Constructor signature:

```python
class DefaultBEAShareLookupService:
    GLOBAL_FALLBACK_SHARE: ClassVar[float] = 0.5  # spec-066/067 baseline

    def __init__(
        self,
        session: Session,
        max_forward_fill_years: int = 5,
    ) -> None: ...
```

`session` is a read-only SQLAlchemy `Session` against the reference DB
(typically obtained via `get_reference_session()`). The service
caches per-(industry, year) lookups in-process to amortize the
SQL cost for the canonical 520-tick run (~166K reads collapse to ~840).

---

## Consumer contract: hex_hydrator change

Before spec-068 (current):

```python
_INTERMEDIATE_INPUTS_FRACTION = 0.5  # spec-066 interim

def _compute_county_c(county_qcew_row, ...):
    ii_share = _INTERMEDIATE_INPUTS_FRACTION  # same for every county
    ...
```

After spec-068 (target):

```python
from babylon.reference.bea import BEAShareLookupService

class HexHydrator:
    def __init__(
        self,
        ...,
        bea_share_service: BEAShareLookupService,  # injected
    ) -> None:
        self._bea_share_service = bea_share_service

    def _compute_county_c(self, county_fips: str, year: int, ...):
        result = self._bea_share_service.lookup_county_share(
            county_fips=county_fips,
            year=year,
        )
        ii_share = result.intermediate_inputs_share  # per-county
        ...
```

The hex_hydrator MUST NOT import:

- `babylon.reference.schema.FactBEANationalIndustry`
- `babylon.reference.schema.FactBEAIOCoefficient`
- `babylon.reference.schema.BridgeNAICSBEA`
- Any direct SQL referencing those tables.

It MAY import:

- `babylon.reference.bea.BEAShareLookupService` (the Protocol)
- `babylon.reference.bea.IndustryShareLookupResult`
- `babylon.reference.bea.CountyShareLookupResult`

A `tools/check_subsystem_boundary.py` linter (out of scope for
spec-068 but recommended for spec-068 follow-up) can grep for the
forbidden imports to enforce this at CI time.

---

## Testing the contract

**Unit tests** (`tests/unit/reference/bea/test_share_lookup_service.py`):

- `test_lookup_industry_share_present_year` — happy path, no fallback.
- `test_lookup_industry_share_forward_fill_within_5_years` — gap-1,
  gap-2, ..., gap-5 all forward-fill correctly.
- `test_lookup_industry_share_global_default_beyond_5_years` —
  walks back >5 years, falls back to GLOBAL_FALLBACK_SHARE = 0.5.
- `test_lookup_county_share_accounting_identity` — `ii + va == 1.0 ± 0.01`.
- `test_lookup_county_share_per_industry_breakdown_sums_to_one`.
- `test_lookup_county_share_employs_qcew_post_067_canonical_leaves` —
  verifies the service does NOT sum over QCEW rollup rows (the ones
  spec-067 just deleted).
- `test_lookup_io_coefficient_returns_none_for_missing_row`.
- `test_lookup_io_coefficient_total_req_table_type`.

**Integration tests** (`tests/integration/reference/bea/test_hex_hydrator_wired.py`):

- `test_county_c_v_stddev_post_wiring` — full Michigan-83 run after
  spec-068 wiring; stddev(c/v) ≥ 0.2 (SC-005).
- `test_imperial_rent_per_county_heterogeneous` — Φ per county now
  varies across the 83 counties (where pre-068 it was uniform).

**Contract tests** (`tests/contract/reference/bea/test_protocol_compliance.py`):

- `DefaultBEAShareLookupService` is a structural subtype of
  `BEAShareLookupService`.
- All three Protocol methods return the documented Pydantic types.
- No method ever returns negative shares or shares > 1.0.

---

## Versioning

This is contract version `1.0`. Backwards-incompatible changes (method
signature changes, return-type changes, removal of methods) require:

1. Bumping the contract version to `2.0`.
2. An ADR documenting the migration path for hex_hydrator and any
   future consumers.
3. A grace-period release where both `1.0` and `2.0` implementations
   are exported from `babylon.reference.bea`.

Forward-compatible additions (new methods, new optional kwargs, new
fields on result types) bump to `1.1` and do NOT require an ADR.
