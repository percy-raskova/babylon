# Implementation Brief — Phase 5.1 `feat/gamma-atus-adapter` (gamma_III leaves the hardcoded 0.33)

Scout date: 2026-07-08, repo at dev (`f08cd111`+). All line numbers verified against current working tree. Reference DB queried read-only at `/home/user/projects/game/babylon/data/sqlite/marxist-data-3NF.sqlite`.

## 1. Verified ground truth (what exists today)

### 1a. The wiring (commit cc4a5303 — confirmed)
`cc4a5303 feat(engine): wire gamma calculator into headless runner` (Jul 6, 2026; 2 files: runner.py +18, test_gamma_wiring.py +152).

- `src/babylon/engine/headless_runner/runner.py:869-917` — `_build_economics_overrides(session_factory=None)`. Lines 896-901 construct `MVPUnpaidCareHoursSource()` + `QCEWCareAdapter()` → `DefaultGammaIIICalculator` → `overrides["gamma_calculator"]`. Lines 905-915 wire `DefaultMELTCalculator` (SQLite BEA+QCEW national sources) when `session_factory` is provided.
- Call site: `runner.py:1031-1040` — `get_normalized_session_factory()` → `_build_economics_overrides(session_factory=...)` → `ServiceContainer.create(defines=defines, **economics_overrides)`. The comment block at `runner.py:1025-1030` claims TickDynamicsSystem "actually computes reproductive visibility instead of no-opping on the hardcoded 0.33 default" — **this comment is false for every canonical year except 2022** and must be rewritten in this branch.
- `ServiceContainer` fields: `src/babylon/engine/services.py:87-89` (`melt_calculator`, `basket_calculator`, `gamma_calculator`, all `Any = field(default=None)`), `create()` kwargs at `:157-159`, assignment `:241-243`. `event_bus: EventBus` field at `:67`; the runner overwrites it with the bridge-shared bus at `runner.py:1041`.

### 1b. Why gamma is frozen at 0.33 (the data starvation — confirmed with exact anchors)
- `src/babylon/economics/gamma/adapters.py:115-116` — `QCEWCareAdapter.get_paid_care_hours` returns non-None **only for `year == 2022`** when constructed parameterless (`elif year == 2022: sector_employment = MVP_CARE_EMPLOYMENT_2022`). Constructor at `:90-100` already accepts `employment_by_sector: dict[int, dict[str, int]] | None` (year → NAICS → employment) — reuse this.
- `adapters.py:141-151` — `_ATUS_UNPAID_CARE_HOURS` hardcoded dict covers **2015-2023 only** (2023 carried from 2022). `MVPUnpaidCareHoursSource` at `:154-184`.
- `adapters.py:39-43` `CARE_NAICS_CODES = {"61": 0.60, "62": 0.30, "814": 1.00}`; `:56` `HOURS_PER_YEAR: int = 2080`.
- `src/babylon/economics/gamma/gamma_iii.py:37-38` — `MIN_YEAR=2003, MAX_YEAR=2024` clamp; `:123-179` `DefaultGammaIIICalculator.compute()` (extends `CachedSource[float]`, `src/babylon/core/protocol_kit.py:58-118`); `:190-196` None→`NoDataSentinel("QCEW paid care hours unavailable for year …")`; `:208-214` None→`NoDataSentinel("ATUS unpaid care hours unavailable for year …")`.
- **The silent drop (C.8 target)**: `src/babylon/economics/tick/system/__init__.py:385-390`:
  ```python
        # Get gamma_III from GammaIIICalculator
        gamma_III_raw: float = 0.33
        if services.gamma_calculator is not None:
            g3_result = services.gamma_calculator.compute(year)
            if g3_result and not isinstance(g3_result, type(None)):
                gamma_III_raw = g3_result.gamma_iii
  ```
  `NoDataSentinel` is falsy → dropped with **zero logging**, sentinel `.reason` discarded. Contrast the MELT path at `:371-374` which logs a warning and aborts. `NoDataSentinel` is already imported at `:45`. Also: `gamma_basket` fallback 0.68 at `:378`; smoothing at `:392-403` (`CoefficientSmoother(alpha=0.3)`, `:106`); year-boundary gate `tick % WEEKS_PER_YEAR != 0` at `:132`; **melt gate** `services.melt_calculator is None → whole system skips` at `:136-138`; `_determine_year` at `:272-286` (`graph.get_graph_attr("base_year", 2010) + tick // 52`). A twin falsy-drop exists in `src/babylon/economics/tick/initializer.py:122-127` (legacy path — optional consistency fix, see §7).
- Net effect at canonical start_year=2010: 2010-2014 → ATUS sentinel; 2015-2021, 2023-2024 → QCEW sentinel; **only 2022 computes (gamma = 0.3725)**. Matches HOLISTIC_REVIEW P1 (`project/HOLISTIC_REVIEW-2026-07-07.md:470-471`) exactly; its `adapters.py:113-119` citation is now `:113-116`.

### 1c. `fact_atus_reproductive_labor` inventory (queried live)
```sql
CREATE TABLE fact_atus_reproductive_labor (
  fact_id INTEGER PK, category_id → dim_atus_activity_category,
  time_id → dim_time, gender_id → dim_gender, source_id → dim_data_source,
  hours_per_week NUMERIC(6,2) NOT NULL, participation_rate NUMERIC(5,4),
  sample_size INTEGER, occupation_group VARCHAR(50), employment_status VARCHAR(50),
  UNIQUE(category_id, time_id, gender_id, occupation_group, employment_status))
-- indexes: category, time, gender (live DB LACKS the ORM's idx_atus_labor_occupation — harmless drift)
```
- **105 rows total. ALL year 2022** (single `time_id=26`). Structure: 5 `babylon_category` (childcare, cooking, eldercare, emotional_support, housework) × 3 genders × 7 slices (population row with `occupation_group IS NULL` + 6 class-proxy occupation slices). `employment_status` is NULL everywhere. Facts use gender_ids **4/5/6** (codes `'T'/'M'/'F'`); dim_gender also has duplicate rows 1/2/3 (`'total'/'male'/'female'`) — **filter by `DimGender.gender_label == "Total"`**, not by id.
- Semantics (ORM docstring `src/babylon/reference/schema.py:2120-2150`): **per-capita weekly hours** (BLS Table A-1 daily averages × 7, loaded from seed_data.yaml). NOT national billions. Population-average slice (gender Total, occupation NULL): childcare 2.8, cooking 4.69, eldercare 0.35, emotional_support 5.74, housework 5.11 h/wk.
- ORM: `FactATUSReproductiveLabor` (`schema.py:2120-2194`), `DimATUSActivityCategory` (`:2077`), `DimGender` (`:773-780`, cols `gender_code`/`gender_label`), `DimTime` (`:756-770`, `year`/`is_annual`).

### 1d. Readers today: **zero production readers — confirmed**
`rg fact_atus_reproductive_labor|FactATUSReproductiveLabor` across src/tests/tools/web hits only: the ORM definition + `__all__` (`schema.py:2120, 2152, 2716`) and `tests/unit/persistence/test_hex_hydrator_sources.py:10,29,100` — a **hex-hydrator-only blacklist** (`_FORBIDDEN_TABLE_PREFIXES = ("fact_atus_", …)`) that forbids the *hex hydrator's SQL* from touching ATUS tables. Economics adapters are out of its scope — do not "fix" it. The `ATUSDBLoader` named in the ORM docstring was deleted in spec-037 (see memory: reference-db-remediation).

### 1e. QCEW care-sector data (the real multi-year signal)
`fact_qcew_annual` (`schema.py:1271-1305`): 14,670,249 rows, **2010-2024**, **6-digit NAICS leaves ONLY** (post-spec-086; sector rows 61/62/814 exist in `dim_industry` but have 0 facts). Ownership codes present in facts: 1/2/3 (government) + 5 (private) — no total rows, so summing all ownerships is double-count-free. `fact_qcew_state_annual` is **EMPTY (0 rows)**. `dim_industry.sector_code` for 814-leaves is `'81'` (too coarse) — must prefix-match `naics_code`.

Measured national employment rollups (all ownerships), 57 care leaf industries:

| year | NAICS 61 | NAICS 62 | NAICS 814 | paid B-hrs (fractions applied) |
|---|---|---|---|---|
| 2010 | 10,496,223 | 18,063,296 | 629,965 | 25.68 |
| 2016 | 10,770,378 | 20,772,669 | 288,029 | 27.00 |
| 2022 | 11,934,379 | 22,177,638 | 218,853 | 29.19 |
| 2024 | 12,491,823 | 24,065,621 | 216,261 | 31.06 |

Private-only (own_code='5') 2022: 61=2,860,882, 62=20,269,842, 814=218,853 → 16.67 B-hrs (≈ the MVP-2022 19.6 B-hrs level).

**Performance (measured on this machine)**: single full-scan aggregate with `LIKE`-prefix filters, grouped by year ≈ **19 s one-time**. IN-list of the 57 leaf `industry_id`s via `idx_qcew_industry_time` = **420 s** — do NOT use index probes; do ONE lazy full-scan, cache the per-year dict on the instance.

### 1f. Population for the unpaid conversion
Only DB-grounded universe: `fact_census_employment` (`FactCensusEmployment`, `schema.py:1006`) joined to `DimEmploymentStatus.status_code=='B23025_001'` (Total, ACS 16+) and `DimRace.race_code=='T'` → **266,885,578** — 2021-only vintage. Disclose the ~1% universe mismatch (ACS 16+ vs ATUS civilian noninstitutional 15+) and the 2021-pop × 2022-rates pairing.

### 1g. Precedents to copy
- **SQLite session-factory adapter pattern**: `src/babylon/economics/melt/gamma_hydration.py:132-227` (`SQLiteGammaHydrationSource`, spec-102 — including the "disclosed data-coverage gap, not a bug" docstring language) and `src/babylon/economics/melt/adapters.py:58-215`. `get_normalized_session_factory()` at `src/babylon/reference/database.py:155-162`.
- **Carry-forward policy + defines knob**: `LeontiefRentDefines.qcew_carry_forward_max_years` (`src/babylon/config/defines/economy_basic.py:496-500`, `Annotated[int, Field(ge=0, le=20)] = 5`).
- **Calibration event emission**: `src/babylon/economics/tensor_hierarchy/leontief_rent/industry_to_county_allocator.py:271-286` — publishes `Event(type=EventType.CALIBRATION_QCEW_CARRY_FORWARD.value, tick=0, payload=typed.model_dump())`. Engine systems also publish plain payload-dict `Event`s without a typed leaf (e.g. `engine/systems/decomposition.py:334-345`) — that is the acceptable minimal pattern here.
- **EventCapture auto-subscribe**: `src/babylon/engine/headless_runner/bridge.py:391-398` subscribes `event_capture.on_event` to **every `EventType` member** — a new enum member is captured with zero extra wiring. `bridge.refresh_event_log()` (`bridge.py:619-623`) drains into `_emit_artifacts(events=…)` (`runner.py:1146, 1176`).
- **Manifest optional top-level block**: `bridge_db_reads` (`manifest.py:229-231` param, `:317-318` emission; `runner.py:1177-1180` producer; test precedent `tests/unit/engine/headless_runner/test_bridge_db_reads_properties.py`).
- **Interpolation precedent** (if asked): spec-062 cross-scale does *within-year weekly* linear interpolation (`config/defines/cross_scale.py:23-26`) — there is NO cross-year interpolation precedent; the house pattern for missing years is **carry + calibration event**, so use carry, not interpolation.

### 1h. EventCapture wart (affects the counter — pre-existing)
`EventCapture._extract_event_type` (`event_capture.py:95-100`) looks for `.event_type`; the bus `Event` dataclass (`engine/event_bus.py:31-47`) has `.type`. Plain bus Events are therefore captured with `event_type == "Event"` and the real type lands in `details["type"]` (dict path via `__dict__`, `event_capture.py:127-144`). **Your manifest counter must match on `details["type"]` as well as `event_type`.** (`EventType` is a `StrEnum` — `models/enums/events.py:30` — so string equality works.) Flag this wart in the PR; fixing capture itself is out of scope.

## 2. Design

### 2a. Two new sources in `src/babylon/economics/gamma/sqlite_adapters.py` (new module)
Both implement the existing protocols in `gamma/data_sources.py` (`UnpaidCareHoursSource.get_unpaid_care_hours(year) -> float | None` at `:20-46`; `PaidCareHoursSource.get_paid_care_hours(year) -> float | None` at `:49-75`). Protocol + Default-impl DI, frozen inputs, mypy strict, RST docstrings — mirror `melt/gamma_hydration.py` file structure.

```python
"""SQLite adapters hydrating gamma_III care-hours from the reference DB.

Feature: remediation Phase 5.1 (feat/gamma-atus-adapter)

Kills the data starvation in :mod:`babylon.economics.gamma.adapters`
(``QCEWCareAdapter`` parameterless = 2022-only; ``_ATUS_UNPAID_CARE_HOURS``
= 2015-2023 hardcode) by reading ``fact_qcew_annual`` (2010-2024) and
``fact_atus_reproductive_labor`` (2022 seed, carried) following the same
session-factory SQLAlchemy adapter pattern as
:mod:`babylon.economics.melt.gamma_hydration`.

Disclosed data-coverage gaps (not bugs):
  - ``fact_atus_reproductive_labor`` holds a single 2022 BLS Table A-1
    seed (per-capita weekly hours); other years are nearest-year carried
    within ``carry_max_years`` and logged.
  - Universe population is the ACS 2021 B23025_001 total (266,885,578)
    from ``fact_census_employment`` — single vintage, ~1% universe
    mismatch vs the ATUS civilian noninstitutional 15+ population.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from sqlalchemy import func, or_

from babylon.economics.gamma.adapters import CARE_NAICS_CODES, HOURS_PER_YEAR
from babylon.reference.schema import (
    DimATUSActivityCategory, DimEmploymentStatus, DimGender, DimIndustry,
    DimOwnership, DimRace, DimTime, FactATUSReproductiveLabor,
    FactCensusEmployment, FactQcewAnnual,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

WEEKS_PER_YEAR: int = 52
BILLION: float = 1_000_000_000.0


class SQLiteQCEWCarePaidHoursSource:
    """PaidCareHoursSource over fact_qcew_annual 6-digit leaves (2010-2024).

    One lazy full-scan aggregate (~20 s against the 14.7M-row table,
    measured; index probes measured 20x slower) cached for instance life.
    """

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        ownership_scope: Literal["all", "private"] = "all",
    ) -> None:
        self._session_factory = session_factory
        self._ownership_scope = ownership_scope
        self._by_year: dict[int, dict[str, int]] | None = None

    def _load(self) -> dict[int, dict[str, int]]:
        if self._by_year is not None:
            return self._by_year
        naics2 = func.substr(DimIndustry.naics_code, 1, 2)
        naics3 = func.substr(DimIndustry.naics_code, 1, 3)
        with self._session_factory() as session:
            query = (
                session.query(
                    DimTime.year, naics2, naics3,
                    func.sum(FactQcewAnnual.employment),
                )
                .join(DimIndustry, DimIndustry.industry_id == FactQcewAnnual.industry_id)
                .join(DimTime, DimTime.time_id == FactQcewAnnual.time_id)
                .filter(or_(naics2.in_(("61", "62")), naics3 == "814"))
                .filter(DimTime.is_annual == 1)
            )
            if self._ownership_scope == "private":
                query = query.join(
                    DimOwnership, DimOwnership.ownership_id == FactQcewAnnual.ownership_id
                ).filter(DimOwnership.own_code == "5")
            rows = query.group_by(DimTime.year, naics2, naics3).all()
        by_year: dict[int, dict[str, int]] = {}
        for year, n2, n3, employment in rows:
            code = "814" if n3 == "814" else str(n2)
            bucket = by_year.setdefault(int(year), dict.fromkeys(CARE_NAICS_CODES, 0))
            bucket[code] = bucket.get(code, 0) + int(employment or 0)
        self._by_year = by_year
        return by_year

    def get_paid_care_hours(self, year: int) -> float | None:
        sector_employment = self._load().get(year)
        if sector_employment is None:
            return None
        total = sum(
            sector_employment.get(code, 0) * HOURS_PER_YEAR * fraction
            for code, fraction in CARE_NAICS_CODES.items()
        )
        return total / BILLION
```
(Note: `naics3 == "814"` first — 814x leaves would otherwise land in a `"81"` bucket. `dict.fromkeys(CARE_NAICS_CODES, 0)` pre-seeds so absent sectors read 0, matching `QCEWCareAdapter`'s continue-on-missing at `adapters.py:123-126`. Expected 2022 output: 29.19 (all) / 16.67 (private).)

```python
class SQLiteATUSUnpaidCareHoursSource:
    """UnpaidCareHoursSource over fact_atus_reproductive_labor.

    national_billions(year) =
        SUM(hours_per_week over configured babylon_categories,
            gender_label='Total', occupation_group IS NULL,
            employment_status IS NULL)
        * 52 * universe_population / 1e9

    Nearest-year carry (both directions, look-back wins ties) within
    ``carry_max_years``; each carry logs + invokes ``on_carry(year, used)``.
    """

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        categories: tuple[str, ...] = ("childcare", "eldercare"),
        carry_max_years: int = 12,
        on_carry: Callable[[int, int], None] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._categories = categories
        self._carry_max_years = carry_max_years
        self._on_carry = on_carry
        self._by_year: dict[int, float] | None = None
        self.carry_count: int = 0  # public: read by the runner for the manifest

    def _universe_population(self, session: Session) -> float | None:
        total = (
            session.query(func.sum(FactCensusEmployment.person_count))
            .join(DimEmploymentStatus,
                  DimEmploymentStatus.status_id == FactCensusEmployment.status_id)
            .join(DimRace, DimRace.race_id == FactCensusEmployment.race_id)
            .filter(DimEmploymentStatus.status_code == "B23025_001",
                    DimRace.race_code == "T")
            .scalar()
        )
        return float(total) if total else None

    def _load(self) -> dict[int, float]:
        if self._by_year is not None:
            return self._by_year
        with self._session_factory() as session:
            population = self._universe_population(session)
            if population is None:
                logger.warning("ATUS unpaid source: no census universe population row")
                self._by_year = {}
                return self._by_year
            rows = (
                session.query(DimTime.year,
                              func.sum(FactATUSReproductiveLabor.hours_per_week))
                .join(DimTime, DimTime.time_id == FactATUSReproductiveLabor.time_id)
                .join(DimATUSActivityCategory,
                      DimATUSActivityCategory.category_id
                      == FactATUSReproductiveLabor.category_id)
                .join(DimGender,
                      DimGender.gender_id == FactATUSReproductiveLabor.gender_id)
                .filter(
                    DimGender.gender_label == "Total",
                    FactATUSReproductiveLabor.occupation_group.is_(None),
                    FactATUSReproductiveLabor.employment_status.is_(None),
                    DimATUSActivityCategory.babylon_category.in_(self._categories),
                )
                .group_by(DimTime.year)
                .all()
            )
        self._by_year = {
            int(year): float(hours) * WEEKS_PER_YEAR * population / BILLION
            for year, hours in rows
        }
        return self._by_year

    def has_data(self) -> bool:
        return bool(self._load())

    def get_unpaid_care_hours(self, year: int) -> float | None:
        data = self._load()
        if year in data:
            return data[year]
        if not data:
            return None
        nearest = min(data, key=lambda y: (abs(y - year), y))  # look-back wins ties
        if abs(nearest - year) > self._carry_max_years:
            return None
        self.carry_count += 1
        logger.info(
            "ATUS unpaid care hours: year %d carried from %d (distance %d)",
            year, nearest, abs(nearest - year),
        )
        if self._on_carry is not None:
            self._on_carry(year, nearest)
        return data[nearest]
```
CRITICAL filters (each prevents a real double-count in the 105-row table): `occupation_group IS NULL` (else 7x), `gender_label == 'Total'` (else 3x + wrong universe), `employment_status IS NULL` (future-proof). Expected 2022 value with default categories: `(2.8 + 0.35) × 52 × 266,885,578 / 1e9 = 43.72 B-hrs`.

### 2b. Calibration outcomes — OWNER DECISIONS D1/D2 (present to Percy before merge)
`validate_gamma_iii` bands (`gamma/validation.py:21-26`): expected [0.20, 0.40], warning [0.10, 0.50]. Current empirical 2022-only value: 0.3725. Measured combos:

| D1 ownership | D2 unpaid categories | unpaid 2022 (B) | gamma 2010 | gamma 2016 | gamma 2022 | band |
|---|---|---|---|---|---|---|
| **all (recommended)** | **childcare+eldercare (recommended)** | 43.72 | **0.370** | **0.382** | **0.400** | expected (2022 at boundary) |
| private-only | childcare+eldercare | 43.72 | ~0.24 | ~0.26 | 0.276 | expected |
| all | +housework+cooking (4-cat) | 179.7 | 0.125 | 0.131 | 0.140 | warning |
| all | all 5 (incl. emotional_support) | 259.4 | 0.090 | 0.094 | 0.101 | warning-floor |
| all | MVP dict 33.0 (rejected: level break) | 33.0 | 0.438 | 0.450 | 0.469 | warning |

Recommended default rationale: (a) ownership="all" — TVT I.5 visibility is waged-vs-unwaged; public-school teachers and public-hospital staff are waged care labor regardless of employer; (b) categories=("childcare","eldercare") matches the "care" construct the MVP values calibrated against and keeps the decade inside the expected band with minimal drift from today's 0.33/0.3725. If Percy picks a warning-band combo, widen `GAMMA_III_EXPECTED_*` in the same commit with provenance (spec-027/028 constants pattern). **Do not silently pick — this is an ask-first item** (it re-levels `NationalTickParameters.gamma_III` consumed at `tick/system/__init__.py:413-414, 560, 568` and `tick/initializer.py:81`).

### 2c. GameDefines knobs
Add a frozen model in `src/babylon/config/defines/economy_basic.py` beside the `qcew_carry_forward_max_years` precedent (`:496-500`), mounted wherever `LeontiefRentDefines` is mounted (engineer: locate the mount and mirror it):
```python
class GammaSourceDefines(BaseModel):
    """Gamma_III data-source knobs (remediation 5.1). Provenance: proof.md."""
    model_config = ConfigDict(frozen=True)

    paid_ownership_scope: Literal["all", "private"] = "all"
    unpaid_categories: tuple[str, ...] = ("childcare", "eldercare")
    unpaid_carry_max_years: Annotated[int, Field(ge=0, le=20)] = 12
    """12 (not the QCEW-precedent 5) because the ATUS seed is 2022-only and
    the canonical 2010-start decade must be reachable by carry. Revisit when
    a multi-year ATUS load lands (ATUSDBLoader recovery, spec-005/086 family)."""
```

### 2d. Wiring — `_build_economics_overrides` (runner.py:869-917)
Extend the signature backward-compatibly: `def _build_economics_overrides(session_factory: Any = None, *, defines: Any = None, event_bus: Any = None) -> dict[str, Any]:`
- `session_factory is None` → unchanged MVP path (keeps 2 existing wiring tests green).
- `session_factory` provided → build `SQLiteQCEWCarePaidHoursSource(session_factory, ownership_scope=…)` + `SQLiteATUSUnpaidCareHoursSource(session_factory, categories=…, carry_max_years=…, on_carry=<publish carry event if event_bus>)`; **run-consistent source selection**: `unpaid = db_unpaid if db_unpaid.has_data() else MVPUnpaidCareHoursSource()` (never mix levels across years mid-run). Note `has_data()` triggers the ATUS query (fast, 105 rows) but NOT the QCEW scan (that stays lazy until the first year-boundary tick).
- Call site `runner.py:1034-1036`: pass `defines=defines, event_bus=event_bus` (both in scope: `defines` at `:956`, `event_bus` at `:988`). Rewrite the false comment block `:1025-1030` and the stale helper docstring `:872-895`.
- Keep a runner-local reference to the unpaid source (e.g. return it via the overrides under a private key you pop before `ServiceContainer.create`, or hold the variable) so `_emit_artifacts` can read `carry_count`.

### 2e. C.8 hooks (REMEDIATION_PLAN.md:91; Phase-5 exit at :179 = "manifest shows gamma fallback count ~0 for covered years")
1. **New EventType members** — `src/babylon/models/enums/events.py`, calibration cluster (`:138-142`):
   ```python
   CALIBRATION_GAMMA_III_FALLBACK = "calibration_warning.gamma_iii_fallback"
   CALIBRATION_ATUS_CARRY_FORWARD = "calibration_warning.atus_carry_forward"
   ```
   **Two tests assert `len(EventType) == 79`** — update to 81 in `tests/unit/models/test_enums.py:335` and `tests/unit/topology/test_phase_transition.py:45`. Do NOT add typed `TickEvent` leaves (`models/events/_legacy.py:1180-1201` union stays at 19) — these are bus-only calibration events; the plain-payload precedent is `decomposition.py:334-345`. EventCapture picks them up automatically via `bridge.py:391-398`.
2. **Loud sentinel path** — replace `tick/system/__init__.py:385-390`:
   ```python
        # Get gamma_III from GammaIIICalculator
        gamma_III_raw: float = 0.33
        if services.gamma_calculator is not None:
            g3_result = services.gamma_calculator.compute(year)
            if isinstance(g3_result, NoDataSentinel):
                logger.warning(
                    "TickDynamics Step 2: gamma_III unavailable for year %d "
                    "(falling back to %.2f): %s",
                    year, gamma_III_raw, g3_result.reason,
                )
                self._publish_gamma_fallback(services, year, g3_result.reason, gamma_III_raw)
            elif g3_result:
                gamma_III_raw = g3_result.gamma_iii
   ```
   Helper on `TickDynamicsSystem` (lazy engine imports — tick.system↔engine circular import is a known landmine, see `--doctest-modules` breakage in MEMORY.md):
   ```python
    def _publish_gamma_fallback(
        self, services: ServiceContainer, year: int, reason: str, fallback_value: float
    ) -> None:
        """Publish the C.8 calibration event for a dropped gamma sentinel."""
        bus = getattr(services, "event_bus", None)
        if bus is None:
            return
        from babylon.engine.event_bus import Event
        from babylon.models.enums.events import EventType

        bus.publish(Event(
            type=EventType.CALIBRATION_GAMMA_III_FALLBACK,
            tick=0,  # allocator precedent; EventCapture stamps the runner tick anyway
            payload={"year": year, "reason": reason, "fallback_value": fallback_value},
        ))
   ```
3. **Manifest block** — `manifest.py`: add `economics_fallbacks: dict[str, Any] | None = None` param to `build_manifest` (beside `bridge_db_reads`, `:229-231`) and emit top-level (`:317-318` pattern). **Never put it in `deterministic_inputs`** — it is a run output; `input_hash` (`:324-332`) must stay input-only. In `_emit_artifacts` (`runner.py:1409-1505`), count from the `events` tuple (works for both call sites `:1176` and `:1226`):
   ```python
   _GAMMA_FALLBACK = "calibration_warning.gamma_iii_fallback"
   fallbacks = [
       e for e in events
       if getattr(e, "event_type", None) == _GAMMA_FALLBACK
       or str((getattr(e, "details", None) or {}).get("type", "")) == _GAMMA_FALLBACK
   ]  # details["type"] path required — see EventCapture wart §1h
   economics_fallbacks = {
       "gamma_iii_fallback_count": len(fallbacks),
       "gamma_iii_fallback_years": sorted({e.details.get("payload", {}).get("year") for e in fallbacks} - {None}),
       "gamma_unpaid_carry_count": unpaid_carry_count,  # threaded from the source
   }
   ```
4. **Wired-vs-None startup table** — after `ServiceContainer.create` (`runner.py:1037-1040`): `ServiceContainer` is a dataclass, so `for f in dataclasses.fields(services): if f.name.endswith("_calculator") or f.name in (...): logger.info("service %-24s -> %s", f.name, type(getattr(services, f.name)).__name__ if getattr(services, f.name) is not None else "None")`. Phase 2.R (`proof/baseline-regen-2026-07`, still pending in the ledger) also claims C.8 — coordinate: land the minimal version here, let 2.R extend, don't implement twice.

## 3. TDD plan (RED first; one commit per unit via `mise run commit -- "…"`)

Existing coverage (do not duplicate): `tests/unit/economics/gamma/` — 6 files, 1,577 lines, 64/64 green (test_gamma_iii.py alone covers formula, sentinel propagation, distinct ATUS/QCEW reasons, year bounds, Fortunati, mutation killers). Mocks in `tests/unit/economics/gamma/conftest.py:23-85` (`MockUnpaidCareHoursSource`, `MockPaidCareHoursSource` + `_check_protocol_compliance:180`). Wiring: `tests/unit/engine/headless_runner/test_gamma_wiring.py` (3 tests incl. the monkeypatched `run()` capture at `:53-152` — keep its stubs working; new kwargs must default). Tick step-2: `tests/unit/economics/tick/test_system.py:73` (MockGammaIIICalculator), `:256` `test_gamma_III_matches_gamma_calculator`.

**New RED tests:**
1. `tests/unit/economics/gamma/test_sqlite_adapters.py` — use root fixture `reference_sqlite_session_factory` (`tests/conftest.py:147`; fresh in-memory `NormalizedBase` schema, test seeds its own rows). Seeding pattern to copy: `tests/unit/economics/melt/test_gamma_hydration.py:32-188`.
   - Paid: seed `DimTime(2018, is_annual=1)` + `DimIndustry` 6-digit leaves (`611110`, `621111`, `814110`, and a decoy `812112`) + `DimOwnership(own_code='5'/'3')` + `FactQcewAnnual` rows → expected billions by hand (`E×2080×fraction/1e9`); missing year → None; `ownership_scope="private"` excludes government rows; decoy NAICS excluded; two-leaf same-sector rows sum.
   - Unpaid: seed `DimATUSActivityCategory` (childcare/eldercare/housework), `DimGender` ('T'/'M' with labels), `DimDataSource`, `FactATUSReproductiveLabor` population rows PLUS occupation-slice and Male rows → assert slices/gender excluded (no double count); category subset honored; carry: year+3 returns anchor value, `carry_count` increments, `on_carry` called with `(year, anchor)`; beyond window → None; empty table → `has_data() is False` and None; no census population row → None.
   - Protocol compliance checks mirroring `conftest._check_protocol_compliance`.
2. `tests/unit/economics/tick/test_system.py` additions — gamma calculator returning `NoDataSentinel(reason=…)`: assert `gamma_III_raw == 0.33` retained AND `caplog` records the reason AND a `calibration_warning.gamma_iii_fallback` event arrives on `services.event_bus` (subscribe a list-appending handler before `step`); returning a real `GammaIII` → no event.
3. `tests/unit/engine/headless_runner/test_gamma_wiring.py` additions — `_build_economics_overrides(session_factory=…)` (real-SQLite-guarded like `:40-42`) wires `SQLiteQCEWCarePaidHoursSource` as the paid source and a DB-backed unpaid source when the table has rows; parameterless call still returns MVP-wired calculator.
4. Manifest: `build_manifest(..., economics_fallbacks={...})` emits the top-level key; omitted when None (mirror `test_bridge_db_reads_properties.py`).
5. Enum: update the two `len(EventType) == 79` assertions → 81 (same commit as the enum change).

## 4. Verification commands
```bash
poetry run pytest tests/unit/economics/gamma/ -v
poetry run pytest tests/unit/economics/tick/test_system.py -v
poetry run pytest tests/unit/engine/headless_runner/test_gamma_wiring.py -v
poetry run pytest tests/unit/models/test_enums.py tests/unit/topology/test_phase_transition.py -k EventType -v
mise run test:q -- tests/unit/economics/gamma tests/unit/economics/tick tests/unit/engine/headless_runner
mise run check          # ruff + format + mypy strict + test:unit
poetry run mypy src/babylon/economics/gamma/ --strict
```
Empirical real-DB probe (expect the §2b table; ~20 s first call):
```bash
poetry run python -c "
from babylon.reference.database import get_normalized_session_factory
from babylon.economics.gamma.sqlite_adapters import (
    SQLiteATUSUnpaidCareHoursSource, SQLiteQCEWCarePaidHoursSource)
from babylon.economics.gamma.gamma_iii import DefaultGammaIIICalculator
sf = get_normalized_session_factory()
calc = DefaultGammaIIICalculator(
    SQLiteATUSUnpaidCareHoursSource(sf), SQLiteQCEWCarePaidHoursSource(sf))
for y in range(2010, 2025):
    r = calc.compute(y)
    print(y, f'{r.gamma_iii:.3f}' if r else r.reason)"
```

## 5. R-PROOF (baseline-affecting — mandatory)
This branch changes `gamma_III_raw` from a constant 0.33 to ~0.37-0.40 varying by year for every covered year → `NationalTickParameters` → smoothing → county states → trace.csv bytes. Per the plan, `2.R proof/baseline-regen-2026-07` (REMEDIATION_PLAN.md:125) is the ONE coordinated regen that also closes the original cc4a5303 R-PROOF violation and is **still pending** in the ledger. Sequence: land 5.1 code → rebase on/behind 2.R → ONE fresh 520-tick canonical (`mise run sim:e2e-bg`, watch `mise run sim:status`) → diff vs old baseline → commit baseline + `specs/…/proof.md` documenting: manifest `economics_fallbacks` before (fallback every year-boundary) vs after (`gamma_iii_fallback_count ≈ 0` for 2010-2020; carries disclosed), the gamma trajectory table, and the three disclosed approximations (2022 ATUS anchor + carry, 2021 population vintage, D1/D2 choices). Style reference: `specs/102-gamma-shocks/proof.md`. If 2.R has already regenerated by the time this lands, run 5.1's own regen ON TOP — never two concurrent regens.

## 6. Collateral (CI hygiene)
- `gamma/__init__.py` — add new classes to imports + `__all__` (`:76-105`).
- Fix the stale line-number references in `_build_economics_overrides`' docstring and the `:1025-1030` comment.
- `ai-docs/state.yaml` note + MEMORY.md "gamma wired but data-starved" line becomes stale after merge (record-repair territory, Phase 7 — just flag in the PR).
- Import order per CLAUDE.md (`from __future__ import annotations` first); tuple `zip` strictness N/A; keep every function under 100 lines.

## 7. Explicitly out of scope (do not drift)
- `basket_calculator` (0.68 fallback at `tick/system/__init__.py:378`) and the other ~13 dormant service slots — Phase 5.2.
- Fixing `EventCapture._extract_event_type` for plain bus Events — pre-existing wart; flag only.
- `tick/initializer.py:122-127` twin falsy-drop — optional one-line logging parity if trivially safe (legacy `Simulation` path is live per Jul-7 verification), otherwise note it.
- Loading multi-year ATUS microdata into the reference DB (a future 086-style loader spec is the real fix for the 2022-only seed; say so in proof.md).
- MELT 2023+ coverage (system-level gate at `:136-138`; canonical 2010-start decade is fully covered).
