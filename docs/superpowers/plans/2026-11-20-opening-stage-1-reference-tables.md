# The Opening, Stage 1: The Two Reference Tables Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Commit the jobs and pay of the twelve trades by place, and the accounts of the twelve trades, as pinned,
tested reference tables, with every version 1 file left byte for byte as it is.

**Architecture:** A second trade mapping cuts consumer goods and leisure out of today's ten trades. A second jobs basis
keeps the county cells of that cut, plus the parent rows above withheld cells and the state and national rows. A second
cohort table, in version 1's columns, is what stage 2's Rust reader parses. A pay table places withheld jobs and names
each group's wage (rule O2). An accounts table folds the 2024 summary supply and use tables into the twelve trades,
with the rent that home owners are counted as paying themselves split out from the 2017 detail tables. Builders read
raw sources only when run by hand; tests read committed tables and small fixtures.

**Tech Stack:** Python 3.12 tools under `tools/`, pyarrow 25.0.0, openpyxl 3.1.5, gzip, JSON contracts under
`contracts/`, `data-artifacts.yaml`, `data-catalog.yaml`, pytest.

**Spec:** `docs/superpowers/specs/2026-11-20-the-opening-of-the-national-economy-design.md` (sections 4, 9 and 10;
rules O1, O2, O3). Decision record: `ai/decisions/ADR313_the_national_economy_opens_in_balance.yaml`. The lead commits
both, and this plan, before Task 1. This plan is stage 1 of the spec's build order. No Rust changes.

**Build order:** Tasks 1 to 6 in order. Task 3 needs Task 2's parquet; Task 4 needs Tasks 2 and 3; Task 6 needs Tasks
2 and 5. A first cut of the accounts exists outside the repository (the "spike"); it is scratch and is not copied.

Checked once against the code and the data by a second reader on 20 November 2026; its eight findings are in the tasks.

## Global Constraints

- Work only in `/media/user/dev-ssd/worktrees/households-homes/babylon`, branch `codex/households-and-homes`. Start
  every shell command with `cd` to it. Never push. No secrets, no `.env`. Nothing from `/media/user/data/babylon-data`
  is copied into the worktree except the built tables this plan commits.
- One cargo or pytest process at a time, on the whole machine. Never pass `-j`. Python tests run with
  `mise run test:q -- <paths>`. A builder run reads 520 MB; run it alone, never beside a test run.
- Tests and CI never read the data drive. A test uses a small fixture it carries or builds in `tmp_path`. A builder
  reads raw sources only when run by hand, from `--source-root` given on the command line, and refuses a file whose
  size or SHA-256 differs from its pinned manifest, before parsing anything.
- Only public, redistributable sources (ADR098). QCEW (BLS) and the supply and use tables (BEA) are United States
  government works.
- Deterministic output. Fixed row order. Parquet: zstd level 19, format 2.6, one row group, dictionary columns named,
  statistics on. CSV: `\n` line ends, ASCII, gzip level 9 with `mtime=0` and an empty file name. Each table has a
  `.metadata.json` beside it (`indent=2, sort_keys=True`, trailing newline) with contract, issue `PER-371`, rows,
  bytes, SHA-256, columns, ordering, writer versions, sources with their digests, semantics and coverage.
- Version 1 does not change by one byte: `contracts/national_qcew_function_mapping_v1.json`,
  `tools/make_national_qcew_function_basis.py`, `tools/make_national_cohort_reference.py`, their two tables, their
  metadata and their tests. New modules import from them; they never edit them.
- A builder's run command is `UV_PROJECT_ENVIRONMENT=.venv mise exec -- uv run --frozen python tools/<builder>.py
  --source-root /media/user/data/babylon-data` (the last flag only for builders that read raw sources). Record it in
  the metadata's `regeneration` field.
- Each build task proves determinism once: build a second time into a scratch directory made with
  `mktemp -d -p /media/user/dev-ssd`; `cmp` the table with the committed one; compare the two metadata files as JSON
  after dropping `artifact.path` (`provenance_path` writes the real output path there); then remove the directory.
- A new committed table gets a hand-written register entry in `data-artifacts.yaml` (fields `name`, `format`,
  `source_table: null`, `generator`, `mode: register`, `rows`, `sha256`, `home`, `material_relation`, placed after
  `national_cohort_reference_2024`), and `tests/unit/reference/test_data_artifacts.py`'s `assert checked == 37` goes up
  by one with a clause added to its comment. `uv run --frozen python tools/make_data_artifacts.py --check` must pass.
- **The size rule.** A committed file over 1,024 KB is named, in the same commit, in four places: the `^...$`
  exclude of the 1 MiB `check-added-large-files` hook and the `files:` of the 2 MiB named-artifact hook in
  `.pre-commit-config.yaml`; `RUNTIME_ASSET_BLOB_LIMITS` in `tools/check_repo_hygiene.py` at 2,097,152 (with a
  two-line comment like version 1's); and the path list of `test_named_runtime_assets_have_an_exact_two_mib_budget`
  in `tests/unit/tools/test_repo_hygiene.py`. That task's gate adds `mise run check:hygiene` and the hygiene test file.
  A file over 2,048 KB stops the task: tell the lead.
- **Gate, run by every task before its last commit,** one leg at a time:
  `mise exec -- uv run --frozen ruff check <changed .py files>`;
  `mise exec -- uv run --frozen ruff format --check <changed .py files>`;
  `mise exec -- uv run --frozen mypy --strict --follow-imports=silent <new tools/*.py files>` (new code is clean;
  errors inside imported version 1 modules are not this plan's);
  then one `mise run test:q -- <paths>` whose paths are the two version 1 test files
  (`tests/unit/tools/test_national_qcew_function_basis.py`, `tests/unit/tools/test_national_cohort_reference.py`),
  the task's own test files and `tests/unit/reference/test_data_artifacts.py`.
- Commit one unit of work at a time: `git add <files>`, message in a file, `PYTHONPATH=src mise exec -- git commit -q
  -F <file>`, then check that `git log --oneline -1` moved. The body ends with `Part of PER-371` and a
  `Co-Authored-By` line naming the model that wrote the commit. Never commit `uv.lock`.
- Integers only in the tables. Money from QCEW is whole USD; from BEA, whole USD thousands. Splits use exact
  `fractions.Fraction` and largest-remainder rounding, so a split cell's parts add up to the cell exactly.
- Every refusal is a `ReferenceBuildError` (from `tools/make_national_county_reference.py`) whose message starts with
  a fixed code, as the version 1 builders do. No silent clamp except the one O2 names (Task 4, decision 3).
- Markdown is wrapped at 120 columns, headings at 80. Refer to the player as "they".

## Review Focus

1. **A published parent smaller than its published children** (annual averages are rounded). Expected: the withheld
   children get zero, never a negative job. Test: Task 4, `a_parent_below_its_children_places_zero`.
2. **A national ownership row that is itself withheld** (state-owned restaurants, local-government vehicle plants
   are `N` at US000). Expected: the wage falls to the nation's figure over all ownerships, never to nothing. Test:
   Task 4, `a_withheld_national_row_falls_to_all_ownerships`.
3. **A BEA cell that is neither a whole number nor `...`** (a later release could print `(D)` or a decimal).
   Expected: the builder refuses, naming sheet, row and column. Test: Task 5, `only_integers_and_the_dots_are_read`.
4. **The split of housing.** Expected: owner-occupied housing plus the housing left in construction and housing
   equals the source's housing cell, in every cell, exactly. Test: Task 6, `owner_and_tenant_housing_add_up`.
5. **Version 1 drifting by accident** (a shared helper edited, a default output path reused). Expected: the three
   version 1 files keep their pinned digests, and no version 2 builder's default output is a version 1 path. Test:
   Task 1, `version_1_files_keep_their_digests`.

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `contracts/national_qcew_function_mapping_v2.json` | The twelve-trade NAICS cut | 1 |
| `tools/make_national_qcew_function_basis_v2.py` | Mapping v2 validation; the v2 jobs basis | 1, 2 |
| `src/babylon/data/reference/economy/national_qcew_function_basis_v2_2024.parquet` (+ `.metadata.json`) | County leaves, county parents, state and national leaves | 2 |
| `tools/make_national_cohort_reference_v2.py` | The v2 cohort table, version 1 columns | 3 |
| `src/babylon/data/reference/economy/national_cohort_reference_v2_2024.csv.gz` (+ metadata) | What stage 2's Rust reader parses | 3 |
| `tools/make_national_trade_pay.py` | O2: placed withheld jobs and each group's wage | 4 |
| `src/babylon/data/reference/economy/national_trade_pay_2024.csv.gz` (+ metadata) | Jobs, payroll and wage source of each admitted group | 4 |
| `contracts/national_accounts_trade_mapping_v1.json` | 71 summary industries to twelve trades; owner-occupied shares | 5 |
| `tools/national_trade_accounts_2024_sources.json` | Pinned BEA workbooks | 5 |
| `tools/make_national_trade_accounts.py` | BEA sheet reader, folding, checks, writer | 5, 6 |
| `src/babylon/data/reference/economy/national_trade_accounts_2024.csv.gz` (+ metadata) | The accounts of the twelve trades | 6 |
| `tests/unit/tools/test_national_qcew_function_basis_v2.py` | Tasks 1 and 2 | 1, 2 |
| `tests/unit/tools/test_national_cohort_reference_v2.py` | Task 3 | 3 |
| `tests/unit/tools/test_national_trade_pay.py` | Task 4 | 4 |
| `tests/unit/tools/test_national_trade_accounts.py` | Tasks 5 and 6 | 5, 6 |
| `data-artifacts.yaml`, `tests/unit/reference/test_data_artifacts.py`, `.pre-commit-config.yaml`, `data-catalog.yaml` | Registry, size rules, catalogue | 2, 3, 4, 5, 6 |

---

### Task 1: The twelve-trade mapping

**Files:**
- Create: `contracts/national_qcew_function_mapping_v2.json`; `tools/make_national_qcew_function_basis_v2.py`
  (mapping part only); `tests/unit/tools/test_national_qcew_function_basis_v2.py`

**Interfaces:**
- Consumes: `make_national_qcew_function_basis` as `basis`: `FunctionMapping`, `aggregation_level`, `parent_sector`,
  `OWNERSHIP_CODES`, `SECTORS`; `make_national_county_reference`: `ROOT`, `ReferenceBuildError`, `_unique_object`.
- Produces:

```python
MAPPING_V2_PATH: Final = ROOT / "contracts/national_qcew_function_mapping_v2.json"
FUNCTION_IDS_V2: Final = ("food", "extraction", "energy_utilities", "manufacturing", "consumer_goods",
    "capital_goods", "construction_housing", "distribution_transport", "household_services",
    "leisure_hospitality", "business_services", "public_provisioning")
def validate_mapping_v2(document: dict[str, Any]) -> basis.FunctionMapping: ...
def load_mapping_v2(path: Path = MAPPING_V2_PATH) -> basis.FunctionMapping: ...
```

**Decisions:**
1. The contract has version 1's keys and wording, with `contract: "NationalQcewFunctionMappingV2"`, `issue: "PER-371"`,
   `supersedes: "contracts/national_qcew_function_mapping_v1.json"`, and the functions in `FUNCTION_IDS_V2` order. Each
   function's `naics_codes` are in this order:
   - `food`: 111, 112, 114, 1151, 1152, 311, 3121 · `extraction`: 113, 1153, 21 · `energy_utilities`: 22, 324
   - `manufacturing`: 3122, 313, 321, 322, 323, 325, 326, 327, 331, 332
   - `consumer_goods`: 314, 315, 316, 337, 339, 3361, 3362, 3363, 3343, 3352
   - `capital_goods`: 333, 3341, 3342, 3344, 3345, 3346, 3351, 3353, 3359, 3364, 3365, 3366, 3369
   - `construction_housing`: 23, 531 · `distribution_transport`: 42, 44-45, 48-49
   - `household_services`: 61, 62, 81 · `leisure_hospitality`: 71, 72
   - `business_services`: 51, 52, 532, 533, 54, 55, 56 · `public_provisioning`: 92
2. Labels: "Consumer goods", "Leisure and hospitality"; the others keep version 1's. New qualifications, one sentence
   each: consumer goods is "Apparel, footwear, textile products, furniture, miscellaneous goods, motor vehicles with
   bodies and parts, audio and video equipment and household appliances; QCEW does not observe product end-use.";
   leisure and hospitality is "Arts, entertainment, recreation, accommodation and food services; a luxury service
   proxy, not measured household consumption."; manufacturing, capital goods and household services drop the
   industries that left them from their wording.
3. `validate_mapping_v2` repeats version 1's checks (identity, ownership, function ids, qualification, levels,
   duplicates, residual `["99"]`, overlap) with the version 2 contract name and ids, and the same error codes.
   It returns version 1's `FunctionMapping` type, so version 1's cohort helpers accept it.

- [ ] **Step 1: Write the failing tests.**
  - `test_v2_mapping_has_twelve_trades`: ids `== FUNCTION_IDS_V2`; `len(mapping.code_to_function) == 63`;
    `len(mapping.source_codes) == 64`; `mapping.document["contract"] == "NationalQcewFunctionMappingV2"`; the file is
    under 16,384 bytes (the Rust reader's bound).
  - `test_v2_mapping_moves_the_cut_industries`: `function_for` gives `consumer_goods` for 3361, 3343, 3352, 314, 339;
    `capital_goods` for 3364, 3353, 3341; `manufacturing` for 332, 3122; `leisure_hospitality` for 71, 72;
    `household_services` for 62; `None` for 99. `function_for("334")`, `("335")`, `("336")` raise
    `ReferenceBuildError` matching `unsupported_naics`.
  - `test_v2_mapping_refuses_overlap_duplicates_and_identity`: appending 336 to `capital_goods` raises
    `overlapping_naics`; appending 333 to `food` raises `duplicate_naics`; contract `"NationalQcewFunctionMappingV1"`
    raises `function_mapping_identity`; removing `leisure_hospitality` raises `function_mapping_functions`.
  - `version_1_files_keep_their_digests`: SHA-256 of the v1 mapping is
    `7185d0bedb1bf4a830ff5199d4af9fbd53aa88b66ca4e34c167404422c22c07d` (the digest `mapping.rs` pins), of the v1
    basis parquet `df7b6937540a0e6afab334de146c8229fac4865829347f8fca37c86c9a056d7c`, of the v1 cohort table
    `1c963f6b709c31f798253e41662619a32ad31d4532022931392cf2fbd78eb497`; and `MAPPING_V2_PATH` differs from
    `basis.MAPPING_PATH`. Tasks 2 to 6 each add their default outputs to this inequality (their Files list this
    test file).
- [ ] **Step 2: Run** `mise run test:q -- tests/unit/tools/test_national_qcew_function_basis_v2.py`. Expected: import
  error, no module.
- [ ] **Step 3: Write the contract and implement** `validate_mapping_v2` and `load_mapping_v2`.
- [ ] **Step 4: Run the tests and the gate.** Expected: PASS.
- [ ] **Step 5: Commit** `feat(reference): cut consumer goods and leisure out of the trade mapping`.

### Task 2: The version 2 jobs basis

**Files:**
- Modify: `tools/make_national_qcew_function_basis_v2.py`; the Task 1 test file; `data-artifacts.yaml`;
  `tests/unit/reference/test_data_artifacts.py`; the four files of the size rule (the parquet passes 1,024 KB)
- Create: `src/babylon/data/reference/economy/national_qcew_function_basis_v2_2024.parquet` and `.metadata.json`

**Interfaces:**
- Consumes: Task 1; `basis.selected_sources(source_root)` (the pinned `tiger` and `qcew` entries of
  `tools/national_county_reference_2024_sources.json`; no new QCEW pin), `basis.parse_observation`'s rules,
  `read_counties`, `STATE_COUNTS`, `ensure_output_paths`, `provenance_path`, `sha256`.
- Produces:

```python
ARTIFACT_OUT: Final = ROOT / "src/babylon/data/reference/economy/national_qcew_function_basis_v2_2024.parquet"
METADATA_OUT: Final = ARTIFACT_OUT.with_suffix(".metadata.json")
ROLES: Final = ("county_leaf", "county_parent", "nation_leaf", "state_leaf")   # lexical, the sort order
PARENT_CODES: Final = ("10", "11", "115", "31-33", "312", "334", "335", "336", "53")
SCHEMA_V2: Final[pa.Schema]  # row_role, area_fips, ownership_code, naics_code: string; agglvl_code: uint8;
    # disclosure_code: string; annual_avg_establishments: int64; annual_avg_jobs, annual_payroll_usd,
    # mean_weekly_wage_usd: int64 nullable. All but the last three not nullable.
@dataclass(frozen=True)
class SourceRow:
    row_role: str; area_fips: str; ownership_code: str; naics_code: str; agglvl_code: int
    disclosure_code: str; annual_avg_establishments: int
    annual_avg_jobs: int | None; annual_payroll_usd: int | None; mean_weekly_wage_usd: int | None
def role_level(code: str, role: str) -> int: ...
def parse_source_row(row: Mapping[str, str], role: str) -> SourceRow: ...
@dataclass(frozen=True)
class CaptureV2:
    rows: tuple[SourceRow, ...]; diagnostics: dict[str, Any]
def capture_basis_v2(rows: Iterable[Mapping[str, str]], county_ids: set[str],
                     mapping: basis.FunctionMapping) -> CaptureV2: ...
def read_basis_v2(path: Path = ARTIFACT_OUT) -> tuple[SourceRow, ...]: ...   # checks SCHEMA_V2 and metadata digest
def build(*, source_root: Path, artifact_out: Path = ARTIFACT_OUT,
          metadata_out: Path = METADATA_OUT) -> dict[str, Any]: ...
```

**Decisions:**
1. Roles and levels. `county_leaf`: a mapped or residual code, area in the TIGER county roster, level as
   `basis.aggregation_level`. `county_parent`: a code in `PARENT_CODES`, county area, level 71 for `"10"` (the county
   total by ownership), 74 for `11`, `31-33`, `53`, 75 for the others. `state_leaf`: a mapped or residual code at area
   `<state>000` for the 51 keys of `STATE_COUNTS`, level `aggregation_level(code) - 20`. `nation_leaf`: the same at
   `US000`, level `aggregation_level(code) - 60`. Ownership 1, 2, 3, 5 only.
2. Refuse or skip. The level sets are county {71, 74, 75, 76}, state {54, 55, 56}, nation {14, 15, 16}. An area's role
   takes the mapped and residual codes, and a county also takes `PARENT_CODES`. A row whose code its area's role
   takes, with ownership 1, 2, 3 or 5, and whose level lies in any of the three sets but is not that role's level for
   that code, is refused, `aggregation_identity: <code>`. A row with a level in none of the sets, or a code its role
   does not take, is skipped silently. `diagnostics["outside_rows"]` counts rows with a mapped, residual or parent
   code, ownership 1, 2, 3 or 5 and a level in some set, whose area is not taken: `domestic_unallocated`
   (`<state>999`) or `outside_50_states_dc` (any other, territories included). Period, disclosure and
   suppressed-zero checks are version 1's (`period_identity`, `source_disclosure`, `suppressed_nonzero`). A second
   row with the same `(row_role, area_fips, ownership_code, naics_code)` is `duplicate_source_cell`.
3. All parent rows are kept, published or not, for every county and ownership (the placement needs to see a withheld
   parent to move up). The ownership totals at level 70 (own 0, code 10) still feed `diagnostics["national_jobs"]`
   exactly as version 1 computes it.
4. Rows sorted by `(row_role, area_fips, ownership_code, naics_code)`; dictionary columns `row_role`, `area_fips`,
   `ownership_code`, `naics_code`, `agglvl_code`, `disclosure_code`. Metadata contract
   `NationalQcewFunctionBasis2024V2`, `function_mapping` with the v2 path and digest, `source_manifest` as version 1,
   `coverage` with rows and withheld rows by role, and per-function diagnostics over `county_leaf` rows with version
   1's fields, re-implemented over `FUNCTION_IDS_V2` (version 1's loop names its ten ids).

- [ ] **Step 1: Write the failing tests** (rows built by a `source(area, level, ...)` helper like version 1's).
  - `each_area_takes_its_role`: county `01017` own 5 code 3361 level 76, the same code at `01000` level 56 and at
    `US000` level 16, and code 336 at `01017` level 75 give rows with roles `county_leaf`, `state_leaf`,
    `nation_leaf`, `county_parent` and levels 76, 56, 16, 75; `capture.rows` is sorted by the four-part key.
  - `only_the_placement_parents_are_kept`: at `01017` own 5, codes 31-33 (74), 115 (75), 10 (71) become
    `county_parent`; 21 (74) becomes `county_leaf`; 3331 (76) and 3361 at level 77 are skipped; own 0 code 10 level 70
    adds to `national_jobs["county_jobs"]` and makes no row.
  - `a_wrong_level_for_the_role_is_refused`: code 3361 at `01000` with level 76 raises `aggregation_identity: 3361`.
  - `unallocated_and_territories_make_no_rows`: `01999` level 76 and `72000` level 56 are skipped and counted under
    `domestic_unallocated` and `outside_50_states_dc`.
  - `changed_source_bytes_are_refused_before_parsing`: a `tmp_path` source root holding a one-byte
    `tiger/county/tl_2024_us_county.dbf` raises `source_digest: tiger`.
  - `the_committed_v2_basis_holds_every_role` (reads the committed parquet): rows by role `county_leaf` 151,199,
    `county_parent` 32,482, `state_leaf` 5,119, `nation_leaf` 166 (188,966 in all); withheld by role 64,131, 9,400,
    624, 26; no `county_leaf` code is 334, 335 or 336; keys strictly sorted; schema `== SCHEMA_V2`; metadata digest
    equals the file's; the registry entry `national_qcew_function_basis_v2_2024` has that digest and 188,966 rows;
    bytes under 2,097,152. (The four counts were taken during planning from the pinned singlefile with this filter;
    version 1's 144,881 came out of the same filter. A different count is a defect to report, not a number to copy.)
- [ ] **Step 2: Run them and see them fail** (`capture_basis_v2` missing).
- [ ] **Step 3: Implement** `role_level`, `parse_source_row`, `capture_basis_v2`, `read_basis_v2`, `build` and `main`
  (flags `--source-root`, `--artifact-out`, `--metadata-out`).
- [ ] **Step 4: Run the unit tests.** Expected: all but the committed-table test pass.
- [ ] **Step 5: Build by hand, prove determinism, register.** Add the entry, raise `checked` to 38, apply the size rule.
- [ ] **Step 6: Run the tests and the gate.** Expected: PASS.
- [ ] **Step 7: Commit** `feat(reference): capture the twelve-trade jobs basis with parents, states and nation`.

### Task 3: The version 2 cohort table

**Files:**
- Create: `tools/make_national_cohort_reference_v2.py`; `tests/unit/tools/test_national_cohort_reference_v2.py`;
  `src/babylon/data/reference/economy/national_cohort_reference_v2_2024.csv.gz` and
  `national_cohort_reference_v2_2024.metadata.json`
- Modify: `data-artifacts.yaml`; `tests/unit/reference/test_data_artifacts.py`; the Task 1 test file; the four files of
  the size rule (the table is about 1,848,908 bytes)

**Interfaces:**
- Consumes: Task 2's `read_basis_v2`, `ARTIFACT_OUT`, `METADATA_OUT`; Task 1's `load_mapping_v2`, `MAPPING_V2_PATH`;
  `make_national_cohort_reference` as `cohort`: `COLUMNS`, `Cohort`, `observation`, `subtotal`, `fields`,
  `pinned_input`; the county roster path and metadata.
- Produces:

```python
ARTIFACT_OUT: Final = ROOT / "src/babylon/data/reference/economy/national_cohort_reference_v2_2024.csv.gz"
METADATA_OUT: Final = ARTIFACT_OUT.with_name("national_cohort_reference_v2_2024.metadata.json")
def county_observations(rows: Iterable[SourceRow]) -> Iterator[dict[str, Any]]: ...  # county_leaf only, v1 field names
def capture_cohorts_v2(rows: Iterable[Mapping[str, Any]], counties: set[str],
                       mapping: basis.FunctionMapping) -> tuple[cohort.Cohort, ...]: ...
def build(*, artifact_out: Path = ARTIFACT_OUT, metadata_out: Path = METADATA_OUT) -> dict[str, Any]: ...
```

**Decisions:**
1. Columns are version 1's twelve, in order, with the same header line. New value sets: `function_id` adds
   `consumer_goods` and `leisure_hospitality`; member NAICS codes add 3341, 3342, 3343, 3344, 3345, 3346, 3351, 3352,
   3353, 3359, 3361, 3362, 3363, 3364, 3365, 3366, 3369 and lose 334, 335, 336; 71 and 72 move groups. The largest
   group has 13 members (capital goods), under the reader's bound of 15.
2. `capture_cohorts_v2` is version 1's `capture` with the mapping passed in (version 1 loads its own and stays
   untouched). `county_observations` renames `area_fips` to `county_geoid` and drops `row_role`, so version 1's
   `observation` checks every row.
3. Metadata as version 1's, contract `NationalCohortReference2024V2`, `leaf_basis` pinned to the v2 parquet,
   `function_mapping` to the v2 contract, `native_readers: []` (stage 2 adds the reader).

- [ ] **Step 1: Write the failing tests.**
  - `the_car_plants_and_the_machines_are_separate_groups`: rows 3361 (P, 4 establishments, 10 jobs, 1,000 USD) and
    333 (P, 2, 5, 700) at `26163` own 5 give two admitted groups, `capital_goods` then `consumer_goods` (version 1's
    lexical order), with complete job totals 5 and 10.
  - `only_county_leaves_become_members`: a `county_parent` 336 row and a `state_leaf` 3361 row passed through
    `county_observations` yield nothing.
  - `restaurants_join_leisure`: rows 72 and 71 make one `leisure_hospitality` group with members `71~P...;72~P...`.
  - `the_committed_v2_cohorts` (reads the committed table): header equal to version 1's; the set of non-empty
    `function_id`s equals `FUNCTION_IDS_V2`; members total 151,199; no `member_count` above 13; every member code is a
    v2 source code; the group `26163,consumer_goods,5` has `53_000 <= jobs_known < 54_000` (the spec's Wayne car
    plants); bytes under 2,097,152 and decoded bytes under 8,388,608; metadata and registry digests agree; groups,
    mapped groups and admitted groups equal the metadata's coverage, which the build prints.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement** the three functions and `main`.
- [ ] **Step 4: Build, prove determinism, register** (`checked` 39), apply the size rule.
- [ ] **Step 5: Run the tests and the gate.** Then commit `feat(reference): group the twelve-trade cohorts for the
  native reader`.

### Task 4: The pay of each trade by place (rule O2)

**Files:**
- Create: `tools/make_national_trade_pay.py`; `tests/unit/tools/test_national_trade_pay.py`;
  `src/babylon/data/reference/economy/national_trade_pay_2024.csv.gz` and `national_trade_pay_2024.metadata.json`
- Modify: `data-artifacts.yaml`; `tests/unit/reference/test_data_artifacts.py`; the Task 1 test file; the four files
  of the size rule if the table passes 1,024 KB (about 65,065 rows; it may)

**Interfaces:**
- Consumes: Task 2's `SourceRow`, `read_basis_v2`, `PARENT_CODES`; Task 1's `load_mapping_v2`; Task 3's table (keys
  only, to check coverage).
- Produces:

```python
COLUMNS: Final = ("county_geoid", "function_id", "ownership_code", "jobs", "payroll_usd", "jobs_rule",
    "wage_rule", "wage_jobs", "wage_payroll_usd")
JOBS_RULES: Final = ("published", "placed", "partial")
WAGE_RULES: Final = ("county", "state", "nation", "nation_all_ownerships")
def subtree(parent: str, leaves: Iterable[str]) -> tuple[str, ...]: ...
def apportion(total: int, weights: Sequence[tuple[str, int]]) -> dict[str, int]: ...
def place_withheld(leaves: Sequence[SourceRow], parents: Mapping[str, SourceRow]) -> dict[str, tuple[int, int]]: ...
@dataclass(frozen=True)
class TradePay:
    county_geoid: str; function_id: str; ownership_code: str; jobs: int; payroll_usd: int
    jobs_rule: str; wage_rule: str; wage_jobs: int; wage_payroll_usd: int
def pay_rows(rows: Sequence[SourceRow], mapping: basis.FunctionMapping) -> tuple[TradePay, ...]: ...
def build(*, artifact_out: Path = ARTIFACT_OUT, metadata_out: Path = METADATA_OUT) -> dict[str, Any]: ...
```

**Decisions:**
1. Why a third table: stage 2's reader parses version 1's columns, which cannot carry state rows, national rows or
   parent rows. So the rule runs here, in Python, and Rust reads its result. One row for each admitted group of the
   v2 cohort table, in the same order; a test checks the keys match.
2. `subtree(parent, leaves)`: `"10"` holds every leaf, 99 included; a sector holds the leaves whose
   `basis.parent_sector` is that sector; a three-digit code holds the four-digit leaves that start with it.
3. Placement, for one county and ownership. Visit the parents in the order 115, 312, 334, 335, 336, 11, 31-33, 53,
   10. At a parent that is present and published, let W be its subtree's withheld leaves not yet placed. If W is not
   empty: `left = max(0, parent - (published + already placed leaves of its subtree))`, for jobs and for payroll each;
   share `left` over W by establishments with `apportion`. The `max(0, ...)` is O2's one clamp (rounded averages).
   A withheld parent is skipped, so its leaves move up to the next parent. Leaves still withheld after `10` stay
   unplaced; stage 2 applies today's rule to them.
4. `apportion(total, weights)`: each share is `floor(total x w / sum(w))`; the units left go one each to the largest
   remainders, ties by code in lexical order. Weights all zero share equally by the same rule.
5. A group's `jobs` and `payroll_usd` are its published members plus its placed members. `jobs_rule` is `published`
   when no member was withheld, `placed` when every withheld member was placed, else `partial`. The `jobs` of a
   `partial` group leave out its unplaced members; stage 2 adds today's rule's jobs for them on top.
6. Wage. `county` when `jobs_rule` is not `partial` and `jobs > 0`: the pair is `(jobs, payroll_usd)`. Else `state`:
   the published `state_leaf` rows of the county's state for the same trade and ownership, summed, if their jobs are
   above 0. Else `nation`: the same over `nation_leaf` rows. Else `nation_all_ownerships`: published `nation_leaf`
   rows of the trade over the four ownerships. Else `no_wage: <county>/<function>/<ownership>`. The hourly wage is
   `wage_payroll_usd / (wage_jobs x 2080)`, computed by the reader, not stored.
7. Metadata contract `NationalTradePay2024V1`, evidence `Derived` for placed values and `Observed` for published,
   counts by `jobs_rule` and `wage_rule`, and jobs placed in all.

- [ ] **Step 1: Write the failing tests** (county `26163`, own 5, unless named).
  - `withheld_plants_share_the_published_parent`: parent 336 P (100 establishments, 60,000 jobs, 6,000,000,000 USD);
    3361 N (10), 3362 N (30), 3363 P (60; 20,000 jobs; 1,800,000,000 USD). Placed: 3361 10,000 jobs and
    1,050,000,000 USD; 3362 30,000 and 3,150,000,000. The `consumer_goods` row: 60,000 jobs, 6,000,000,000 USD,
    `placed`, `county`, pair (60,000, 6,000,000,000).
  - `a_withheld_parent_passes_to_the_sector`: 336 N; 31-33 P with 1,000 jobs and 100,000 USD; published leaves 333
    with 300 jobs and 30,000 USD, 3363 with 200 and 20,000; 3361 N (1), 3362 N (3). Placed 3361 125 jobs and 12,500
    USD, 3362 375 and 37,500.
  - `a_parent_below_its_children_places_zero`: 336 P with 100 jobs and 10,000 USD; 3363 P with 101 and 10,100; 3361 N.
    3361 is placed at 0 jobs and 0 USD; the `consumer_goods` row has 101 jobs, `placed`, `county`.
  - `apportion_breaks_ties_by_code`: `apportion(7, [("3361", 0), ("3362", 0), ("3363", 0)])` is
    `{"3361": 3, "3362": 2, "3363": 2}`; `apportion(10, [("a", 1), ("b", 2)])` is `{"a": 3, "b": 7}`.
  - `the_county_total_places_a_withheld_sector`: own 1, code 10 P with 500 jobs and 50,000,000 USD; 92 P with 400 and
    40,000,000; 61 N (2). 61 placed at 100 jobs and 10,000,000 USD.
  - `a_withheld_county_takes_the_state_wage`: nothing above 3361 published; `26000` own 5 rows 3361 P (48,138 jobs,
    4,997,065,672 USD) and 3362 N. Row: `partial`, `state`, pair (48,138, 4,997,065,672).
  - `a_withheld_national_row_falls_to_all_ownerships`: own 2, code 72 N in county, state and `US000`; `US000` rows 72
    own 5 P (14,092,895; 420,499,947,209) and own 3 P (105,403; 5,330,928,520), and 71 none. The leisure row's wage
    is `nation_all_ownerships` with pair (14,198,298, 425,830,875,729).
  - `no_wage_anywhere_is_refused`: a group with no published row at any level raises `no_wage: 26163/`.
  - `the_committed_pay_table` (reads the committed tables): keys equal the admitted keys of the v2 cohort table; every
    `jobs_rule` and `wage_rule` is in its set; `wage_jobs > 0` on every row; counts by rule equal the metadata; the
    Wayne `consumer_goods` own 5 row has `jobs >= 53_000` and `wage_rule == "county"`; registry digest agrees.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement** the functions above and `main`.
- [ ] **Step 4: Build, prove determinism, register** (`checked` 40), and apply the size rule if it passes 1,024 KB.
- [ ] **Step 5: Run the tests and the gate.** Then commit `feat(reference): place withheld jobs and name each trade's
  wage by place`.

### Task 5: The accounts' sources and mapping

**Files:**
- Create: `tools/national_trade_accounts_2024_sources.json`; `contracts/national_accounts_trade_mapping_v1.json`;
  `tools/make_national_trade_accounts.py` (sources, reader, mapping, owner shares);
  `tests/unit/tools/test_national_trade_accounts.py`
- Modify: `data-catalog.yaml` (the existing `BEA_IO_NATIONAL_SUPPLY` source); the Task 1 test file

**Interfaces:**
- Consumes: Task 1's `load_mapping_v2`; `sha256`, `_unique_object`, `ReferenceBuildError`.
- Produces:

```python
SOURCES: Final = ROOT / "tools/national_trade_accounts_2024_sources.json"
ACCOUNTS_MAPPING: Final = ROOT / "contracts/national_accounts_trade_mapping_v1.json"
TRADES: Final = FUNCTION_IDS_V2
OWNER: Final = "owner_occupied_housing"
@dataclass(frozen=True)
class BeaSheet:
    rows: tuple[str, ...]; columns: tuple[str, ...]; cells: dict[tuple[str, str], int]   # USD millions
    def get(self, row: str, column: str) -> int: ...     # absent cell reads 0
def verify_accounts_sources(source_root: Path, manifest: Path = SOURCES) -> dict[str, Path]: ...
def read_sheet(path: Path, sheet: str, *, code_row: int, first_row: int) -> BeaSheet: ...
@dataclass(frozen=True)
class AccountsMapping:
    document: dict[str, Any]; whole: dict[str, str]; splits: dict[str, dict[str, tuple[str, ...]]]
    owner_shares: dict[str, Fraction]
def load_accounts_mapping(path: Path, functions: basis.FunctionMapping) -> AccountsMapping: ...
def owner_occupied_shares(use_detail: BeaSheet, supply_detail: BeaSheet) -> dict[str, Fraction]: ...
```

**Decisions:**
1. Sources (contract `NationalTradeAccounts2024SourcesV1`), each with `id`, `path`, `url`, `bytes`, `sha256`, `note`:

| id | path | bytes | sha256 |
|---|---|---|---|
| `use_summary` | `input-output/supply-use/Use_Summary.xlsx` | 1161293 | `98dd61d7c2a8df7c9678b1ebff9015372ac5ed082df33f9b15e8d7bf9408f341` |
| `supply_summary` | `input-output/supply-use/Supply_Summary.xlsx` | 822838 | `286c42547ff83b7756aae893829d8cb54825ec4ed9bdae60fda23ec7bdc634d9` |
| `use_detail` | `input-output/supply-use/Use_SUT_Detail.xlsx` | 2121639 | `07aa2a21151e78ec1462c8f48142d274c153d90aff07bd797e07c6bc8486911e` |
| `supply_detail` | `input-output/supply-use/Supply_Detail.xlsx` | 1610518 | `7a3a403f7a7e8335e61776c1da6c423409d54090acaee597bbae738fa9a6703e` |

   The four are members of `bea/SUPPLY-USE.zip` on the data drive, same bytes; the note says so. The `url` is the
   BEA input-output accounts download that `bea/SUPPLY-USE.zip` came from; confirm it from the zip's provenance before
   writing it, and write `null` with the reason in `note` if it cannot be confirmed offline.
2. Sheets: summaries `2024` (and `2017` of the use summary, for one check); details `2017`. Column codes are on row
   index 5 (0-based) in all four, from column index 2 (columns 0 and 1 hold the row code and name; in the summaries
   row 5 starts `None, "Commodities/Industries"`). Data rows start at index 7 in the summaries and 6 in the details.
   Reading the header stops at the first empty cell (the details end with two: indices 425 and 426 in the use
   detail, 416 and 417 in the supply detail). Reading rows stops at the first row whose code is empty (the details
   end with blank rows and a "Note.  Detail may not add to total due to rounding." row). Codes are read with `str()`
   and stripped (detail headers hold integers and `"TRADE "`). A cell is an `int`, `None` or `"..."` (both read 0);
   anything else is `bea_cell: <sheet>/<row>/<column>`. A repeated row or column code is `bea_duplicate_code`.
3. The mapping contract `NationalAccountsTradeMappingV1` (`issue` PER-371, `evidence_class` Designed,
   `source_vintage` 2024) lists the 71 industry codes of the 2024 use summary, in its column order, each once. Whole
   codes: `111CA` food; 211, 212, 213 extraction; 22, 324 energy_utilities; 23, `ORE` construction_housing; 321, 327,
   331, 332, 322, 323, 325, 326 manufacturing; 333, `3364OT` capital_goods; `3361MV`, 337, 339, `315AL`
   consumer_goods; 42, 441, 445, 452, `4A0`, 481, 482, 483, 484, 485, 486, `487OS`, 493, `GFE` distribution_transport;
   511, 512, 513, 514, `521CI`, 523, 524, 525, `532RL`, 5411, 5415, `5412OP`, 55, 561, 562 business_services; 61, 621,
   622, 623, 624, 81 household_services; `711AS`, 713, 721, 722 leisure_hospitality; `GFGD`, `GFGN`, `GSLG`, `GSLE`
   public_provisioning; `HS` construction_housing with `"owner_occupied": true`. Splits, by national jobs: `113FF`
   extraction (113, 1153) / food (114, 1151, 1152); `311FT` food (311, 3121) / manufacturing (3122); `313TT`
   manufacturing (313) / consumer_goods (314); `334` consumer_goods (3343) / capital_goods (3341, 3342, 3344, 3345,
   3346); `335` consumer_goods (3352) / capital_goods (3351, 3353, 3359). Residual product rows: `Used` is
   `scrap_used`, `Other` is `noncomparable`.
4. A split's NAICS codes must be leaves of the named trade in mapping v2 and lie under its BEA code: `113FF` under
   113, 114, 115; `311FT` under 311, 312; `313TT` under 313, 314; `334` under 334; `335` under 335. Its lists must
   cover exactly the v2 leaves under those prefixes. Any breach is `accounts_split_naics: <code>/<naics>` (a missing
   leaf names that leaf). The 71 codes must equal the sheet's (`accounts_mapping_coverage`).
5. The owner-occupied shares are documented figures of the contract, as `[owner, total]` in USD millions from 2017:
   from the use detail, industry `531HSO` of `531HSO` + `531HST`: `intermediate_inputs` (`T005`) [212560, 238323],
   `compensation` (`V00100`) [0, 18920], `production_taxes` (`T00OTOP`) [178599, 254103], `gross_operating_surplus`
   (`V00300`) [1164524, 1541039]; from the use detail, product row `531HSO`, `households` (`F01000`)
   [1553178, 2020853]; from the supply detail, product row `531HSO`, `product_subsidies` (`SUB`) [-2441, -38219].
   `owner_occupied_shares` recomputes them from the sheets; a difference is `owner_occupied_share: <name>`. The build
   also checks that the 2017 use summary's `HS` column (`T005`, `V001`, `T00OTOP`, `V003`) and `HS` row (`F010`)
   equal the detail's two rows within 2 million each.
6. The catalogue reuses `BEA_IO_NATIONAL_SUPPLY` ("Supply-Use Tables"): add `local_path`
   `/media/user/data/babylon-data/input-output/supply-use/` and an `added_by` naming PER-371, the four workbooks
   (summary 2024, detail 2017) and the committed table. No new id, no version bump.

- [ ] **Step 1: Write the failing tests** (workbooks are built in `tmp_path` with openpyxl).
  - `only_integers_and_the_dots_are_read`: cells 5, `None`, `"..."` read 5, 0, 0; `"(D)"` raises
    `bea_cell: 2024/111CA/F010`; `1.5` raises `bea_cell`; a repeated row code raises `bea_duplicate_code`.
  - `every_summary_industry_is_placed_once`: the contract loads with 66 whole codes, 5 splits and `HS` marked owner;
    removing `GSLE` raises `accounts_mapping_coverage`; adding 3361 to `334`'s consumer list raises
    `accounts_split_naics: 334/3361` (not under 334); removing 1151 from `113FF`'s food list raises
    `accounts_split_naics: 113FF/1151` (a leaf left out); adding 3121 to `313TT`'s list raises
    `accounts_split_naics: 313TT/3121`.
  - `owner_shares_are_the_2017_figures`: the loaded shares are `Fraction(212560, 238323)`, `Fraction(0, 18920)`,
    `Fraction(178599, 254103)`, `Fraction(1164524, 1541039)`, `Fraction(1553178, 2020853)`, `Fraction(2441, 38219)`;
    a fixture detail pair with those cells reproduces them; one cell changed raises `owner_occupied_share: households`.
  - `changed_accounts_sources_are_refused`: a `tmp_path` root with a short `Use_Summary.xlsx` raises
    `source_digest: use_summary`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Write the manifest, the contract and the catalogue entry; implement the reader and loaders.**
- [ ] **Step 4: Run the tests and the gate.** Then commit `feat(reference): pin the supply and use tables and map
  their industries to twelve trades`.

### Task 6: The accounts of the twelve trades

**Files:**
- Modify: `tools/make_national_trade_accounts.py`; its test; `data-artifacts.yaml`;
  `tests/unit/reference/test_data_artifacts.py`; the Task 1 test file
- Create: `src/babylon/data/reference/economy/national_trade_accounts_2024.csv.gz` and
  `national_trade_accounts_2024.metadata.json`

**Interfaces:**
- Consumes: Task 5; Task 2's `read_basis_v2` (`nation_leaf` rows).
- Produces:

```python
ARTIFACT_OUT: Final = ROOT / "src/babylon/data/reference/economy/national_trade_accounts_2024.csv.gz"
COLUMNS: Final = ("block", "row_key", "column_key", "unit", "value")
PRODUCTS: Final = (*TRADES, OWNER, "scrap_used", "noncomparable")
INDUSTRIES: Final = (*TRADES, OWNER)
FINAL_USES: Final = {"households": ("F010",), "investment_structures": ("F02S",), "investment_equipment": ("F02E",),
    "investment_intellectual_property": ("F02N",), "investment_residential": ("F02R",), "inventories": ("F030",),
    "exports": ("F040",), "federal_consumption": ("F06C", "F07C"),
    "federal_investment": ("F06S", "F06E", "F06N", "F07S", "F07E", "F07N"),
    "state_local_consumption": ("F10C",), "state_local_investment": ("F10S", "F10E", "F10N")}
SUPPLY: Final = {"commodity_output": ("T007",), "imports": ("MCIF", "MADJ"), "trade_margins": ("Trade",),
    "transport_margins": ("Trans",), "import_duties": ("MDTY",), "product_taxes": ("TOP",),
    "product_subsidies": ("SUB",), "total_supply": ("T016",)}
INDUSTRY: Final = ("gross_output", "intermediate_inputs", "compensation", "production_taxes_less_subsidies",
    "gross_operating_surplus", "value_added_basic")
JOBS: Final = ("jobs", "annual_payroll_usd", "jobs_public", "annual_payroll_public_usd")
@dataclass(frozen=True)
class AccountCell:
    block: str; row_key: str; column_key: str; unit: str; value: int
def split_shares(nation: Sequence[SourceRow], mapping: AccountsMapping) -> dict[str, dict[str, Fraction]]: ...
def split_cell(value_thousands: int, shares: Sequence[tuple[str, Fraction]]) -> dict[str, int]: ...
def fold(use: BeaSheet, supply: BeaSheet, mapping: AccountsMapping,
         shares: Mapping[str, Mapping[str, Fraction]]) -> tuple[AccountCell, ...]: ...
def jobs_cells(nation: Sequence[SourceRow], functions: basis.FunctionMapping) -> tuple[AccountCell, ...]: ...
def check(cells: Sequence[AccountCell], use: BeaSheet, supply: BeaSheet) -> dict[str, Any]: ...
def build(*, source_root: Path, artifact_out: Path = ARTIFACT_OUT,
          metadata_out: Path = METADATA_OUT) -> dict[str, Any]: ...
```

**Decisions:**
1. Blocks, all dense, in this order: `use` (rows `PRODUCTS`; columns `INDUSTRIES` then `FINAL_USES`; 15 x 23 = 345
   cells), `supply` (rows `PRODUCTS`, columns `SUPPLY`; 120), `make` (rows `INDUSTRIES`, columns `PRODUCTS`: what
   each industry makes of each product, from the supply table's industry columns; 13 x 15 = 195), `industry` (rows
   `INDUSTRIES`, columns `INDUSTRY`; 78), `jobs` (rows `TRADES`, columns `JOBS`; 48), `split` (rows the five split
   codes, columns their two trades; 10). 796 rows. Units: `usd_thousands` for `use`, `supply`, `make`, `industry`;
   `jobs` or `usd` in `jobs`; `jobs` in `split`. Values keep the source's sign (distribution margins and subsidies
   are negative). Government final uses stay apart by level, federal (F06, F07) and state and local (F10).
2. Basis: product rows at purchasers' prices (margins and product taxes sit in the goods rows); industry figures at
   basic prices. Imports are a positive supply column, `MCIF + MADJ`. Nothing else is redefined.
3. A whole code's cell goes to its trade. A split code's cell is shared by `split_cell` with its jobs shares, the same
   shares for its product row and its industry column, in `use` and in `make` alike: the row split first, then each
   part by the column split. The caller turns millions into thousands first; `split_cell` apportions by largest
   remainder on the absolute value (ties by key order) and restores the sign.
4. Housing. The owner's `intermediate_inputs` is `HS`'s `T005` split directly by `intermediate_inputs`; each of the
   `HS` column's intermediate cells is split by the same share (their sum may differ from it by up to a thousand a
   cell; metadata records the difference). `V001`, `T00OTOP` and `V003` split by their own shares. `T00OSUB` for
   `HS` is checked to be 0 (`owner_occupied_share: other_subsidies` otherwise). The owner's `value_added_basic` and
   `gross_output` are sums of its parts; construction and housing keeps `HS` less the owner, cell by cell. The `HS`
   product row holds households only: `F010` splits by `households`, `SUB` by `product_subsidies`; the owner's
   `total_supply` is its households cell and its `commodity_output` that less its subsidies. In `make`, the owner
   makes only its own product, equal to its `commodity_output`; the `HS` column's `HS` cell less that, and its other
   cells (23, 5415, 5412OP), stay with construction and housing.
5. `production_taxes_less_subsidies` is `T00OTOP - T00OSUB` (the source prints `T00OSUB` positive).
6. `split_shares` uses published `nation_leaf` jobs over the four ownerships. `jobs` sums them by trade;
   `jobs_public` sums ownerships 1, 2 and 3 (it shows the public schools and hospitals that the spec keeps in household
   services while the accounts count their output under government).
7. `check` tests the source's own identities per source code, before folding (folding is exact, so the trades
   inherit them), and refuses a gap above 10 million USD as `accounts_identity: <check>/<code>`. Checks and the
   largest gap measured in the 2024 tables: `use_total` (`T019 - T001 -` final uses) 2; `use_row` (buyer cells `-
   T001`) 6; `use_column` (product cells `- T005`) 8; `supply_parts` (`T016 -` its parts) 2; `use_supply` (`T016 -
   T019`) 1; `industry_output` (`T018 - T005 - VABAS`) 1; `value_added` (`V001 + T00OTOP - T00OSUB + V003 - VABAS`)
   1; `make_row` (industry cells `- T007`) 4; `make_column` (product cells `-` supply `T017`) 4; `make_use_output`
   (supply `T017 -` use `T018`) 0. Then `gdp`: final uses less imports against the sum of `VAPRO`, within 0.01%.
   Metadata `checks` keeps the largest gap of each; `source_controls` keeps the sums of `T018`, `T005`, `VABAS`,
   `T019`. (A check of trade sums against a fixed bound refuses the real data: business services' use gap is 12.)
8. Metadata contract `NationalTradeAccounts2024V1`: sources and mapping digests, the v2 basis digest, openpyxl
   version, semantics (units, the price basis, margins, housing, government industries, residual rows, inventory),
   and the carried judgments: `GFE` (mostly the postal service) is distribution; `GSLE` and the general governments
   are public provisioning; public schools and hospitals are counted twice in kind (jobs in household services,
   output in government) and stage 5 settles it; 2,080 hours a year for all trades.

- [ ] **Step 1: Write the failing tests.**
  - `split_cell_parts_add_up`: `split_cell(7000, [("a", Fraction(1, 3)), ("b", Fraction(2, 3))])` is
    `{"a": 2333, "b": 4667}`; `split_cell(-5000, ...)` with the same shares is `{"a": -1667, "b": -3333}`.
  - `owner_and_tenant_housing_add_up`: a fixture use sheet whose `HS` column has `T005` 238,323 spread over two
    rows, `V001` 18,920, `T00OTOP` 254,103, `V003` 1,541,039, and whose `HS` row has `F010` 2,020,853: the owner's
    cells are 212,560,000, 0, 178,599,000, 1,164,524,000 and households 1,553,178,000 USD thousands; owner plus
    construction and housing equals 1,000 times the `HS` cell in every cell.
  - `split_codes_follow_national_jobs`: with fixture `nation_leaf` rows giving 113 74,846 jobs and 114 375,931, a
    `113FF` output of 450,777 million splits into extraction 74,846,000 and food 375,931,000 USD thousands.
  - `a_gap_beyond_its_bound_is_refused`: a fixture code `111CA` whose `T018` exceeds `T005 + VABAS` by 11 million
    raises `accounts_identity: industry_output/111CA`; by 10 million it passes.
  - `the_owner_makes_only_housing`: a fixture supply `HS` column with `HS` 3,162,745 and `23` 29,504 gives the owner
    one `make` cell, its `commodity_output`, and construction and housing the rest of both cells.
  - `the_committed_accounts` (reads the committed table): 796 rows in the block counts above; metadata `checks` holds
    the largest gaps of decision 7 exactly (2, 6, 8, 2, 1, 1, 1, 4, 4, 0); the `split` block is
    113FF extraction 74,846 / food 375,931; 311FT food 2,090,409 / manufacturing 10,634; 313TT manufacturing 84,975 /
    consumer_goods 96,972; 334 consumer_goods 18,851 / capital_goods 1,001,166; 335 consumer_goods 60,010 /
    capital_goods 360,166. The `jobs` block's `jobs` and `annual_payroll_usd`: food 3,276,552 / 182,524,887,785;
    extraction 661,997 / 81,101,049,742; energy_utilities 966,571 / 120,557,836,752; manufacturing 5,061,467 /
    408,360,829,124; consumer_goods 2,239,990 / 168,955,584,595; capital_goods 3,282,239 / 372,473,890,208;
    construction_housing 10,164,182 / 815,427,986,577; distribution_transport 29,169,333 / 1,789,433,399,662;
    household_services 42,212,557 / 2,712,539,847,517; leisure_hospitality 17,159,014 / 572,592,943,503;
    business_services 32,695,640 / 3,809,815,227,073; public_provisioning 7,846,751 / 662,040,421,314 (154,736,293
    jobs in all). The `households` cells of `owner_occupied_housing` and `construction_housing` sum to 3,151,785,000
    (`HS` 3,143,691 plus `ORE` 8,094 million; `23` has none). The sum of `gross_output` over
    `INDUSTRIES` is 1,000 times `source_controls["T018"]`. Metadata and registry digests agree.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement** `split_shares`, `split_cell`, `fold`, `jobs_cells`, `check`, `build` and `main`.
- [ ] **Step 4: Build, prove determinism, register** (`checked` 41); the size rule applies if it passes 1,024 KB.
- [ ] **Step 5: Run the tests and the gate,** then `uv run --frozen python tools/make_data_artifacts.py --check`.
  Commit `feat(reference): fold the 2024 supply and use tables into the twelve trades`.

## What Stage 2's Reader Checks Today

For the stage 2 plan; nothing here changes in stage 1. `rust/crates/babylon-persistence/src/national_cohorts/`:

- `mapping.rs` includes `contracts/national_qcew_function_mapping_v1.json` and pins its digest (`MAPPING_SHA256`);
  refuses a document over 16,384 bytes; requires contract `NationalQcewFunctionMappingV1`, `Designed`, vintage 2024,
  exactly 10 functions, residual `["99"]`, every id known to `EconomicFunction::from_source_key`, no repeated function
  or code, and exactly 50 member codes with 99. Version 2: 12 functions, 64 codes, two new `EconomicFunction` keys.
- `parse.rs`: ASCII, ends in `\n`, no `\r`; the exact header; 12 fields a line; county in the roster; function key or
  empty; ownership 1, 2, 3, 5; `admitted` 0 or 1 and equal to "mapped and some known subtotal above 0"; 1 to 15
  members, strictly sorted by code, each admitted by the mapping for that function; `P` members with three values,
  `N` with none; each subtotal and published count re-added; groups strictly sorted; totals equal `GROUP_COUNT`,
  `MEMBER_COUNT` (144,881) and `ADMITTED_COUNT`. Version 2: members 151,199, groups and admitted from Task 3.
- `artifact.rs`: includes the table, at most 2,097,152 bytes compressed and 8,388,608 decoded, pins
  `ARTIFACT_SHA256` and `LEAF_BASIS_SHA256` (the basis parquet's digest). Version 2's compressed size is near the
  first bound; Task 3's test fails if it passes it.
- Group order is the derived `Ord` of `CohortKey`, so of `EconomicFunction`, whose variants are declared in
  alphabetical order (`babylon-kernel/src/economic_identity.rs`). The Python builders sort ids lexically, so
  `ConsumerGoods` must be declared after `ConstructionHousing`, and `LeisureHospitality` after `HouseholdServices`.
- Integers are canonical (no sign, no leading zero, at most `i64::MAX`); each member has exactly 6 `~` fields;
  `member_count` is above 0; every count field is bounded at 15; groups join the 3,144-county reference.
- `national_cohorts/tests.rs:153` asserts ten functions and that `label()` and `source_key()` equal the contract's
  label and id (version 2's labels: Task 1, decision 2).
- Other readers of the version 1 table: `economic_catalog/preset.rs:40`, `tests/national_cohorts.rs`,
  `tests/captured_source_dependencies.rs`.
- `LEAF_BASIS_SHA256` means "the leaf basis" today; the v2 basis also holds parent, state and nation rows, so the pin
  needs a new meaning or a new name. `function_mapping_sha256()` (`artifact.rs:131`) exposes one mapping pin.
- The pay table (Task 4) has no reader yet; stage 2 writes one.
