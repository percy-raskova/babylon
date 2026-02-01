# Research: Data Preflight & Loader Unification

**Branch**: `009-data-preflight` | **Date**: 2026-01-31

## Research Questions

### 1. Existing Preflight Pattern Analysis {#1-existing-preflight-pattern-analysis}

**Question**: How does the current `run_preflight()` function dispatch checks to different loaders?

**Findings**:
- `run_preflight()` accepts a `loaders: list[str]` parameter
- Dispatches to private `_check_*` functions based on loader names in a conditional chain
- Uses `AddCheckFn` callback pattern to accumulate `PreflightCheck` objects
- Returns `PreflightResult` aggregating all checks

**Code Reference**: `src/babylon/data/preflight.py:409-477`

```python
def run_preflight(
    config: LoaderConfig,
    loaders: list[str],
    base_dir: Path | None = None,
    online: bool = False,
) -> PreflightResult:
    # Dispatches to _check_census, _check_fred, _check_lodes, etc.
```

**Decision**: Extend this pattern by adding `VerificationProtocol` support without removing existing `_check_*` functions for backward compatibility.

---

### 2. DataLoader ABC Extension Point {#2-dataloader-abc-extension-point}

**Question**: Where should `VerificationProtocol` be defined and how should it relate to `DataLoader`?

**Findings**:
- `DataLoader` ABC in `loader_base.py` defines: `load()`, `get_dimension_tables()`, `get_fact_tables()`
- Loaders already receive `LoaderConfig` in `__init__()`
- Some loaders (TIGER, LODES) have custom `__init__` parameters for data paths

**Alternatives Considered**:
1. Add `check_source_files()` as abstract method to `DataLoader` - **Rejected**: Would break all existing loaders
2. Define separate `VerificationProtocol` - **Selected**: Non-breaking, opt-in pattern
3. Use mixin class `VerifiableLoader` - **Rejected**: Protocol is simpler and more Pythonic

**Decision**: Define `VerificationProtocol` as a `typing.Protocol` in `loader_base.py`. Loaders that want preflight integration implement it. Preflight checks for protocol compliance at runtime.

---

### 3. Detroit Scenario Data Requirements {#3-detroit-scenario-data-requirements}

**Question**: What specific files are required for Wayne, Oakland, and Macomb counties (2010-2025)?

**Findings**:

| Data Source | Required Files | Year Coverage | Notes |
|-------------|----------------|---------------|-------|
| QCEW | `data/qcew/*.csv` | 2010-2023 | API for 2021+, files for earlier |
| LODES | `data/lodes/us_xwalk.csv[.gz]` | N/A (crosswalk) | Static geographic crosswalk |
| ACS (Census) | API-based | 2010-2023 | 5-year estimates, ~1 year lag |
| TIGER | `data/tiger/county/tl_2024_us_county.shp` | 2024 | County boundaries shapefile |

**County FIPS Codes**:
- Wayne County (Detroit): `26163`
- Oakland County: `26125`
- Macomb County: `26099`

**Decision**: LODES crosswalk is national (all counties); filtering happens at load time. TIGER shapefile contains all counties. QCEW and Census checks already exist but need year range validation for Detroit.

---

### 4. Git LFS Pointer Detection {#4-git-lfs-pointer-detection}

**Question**: How is Git LFS pointer detection currently implemented?

**Findings**:
- Existing function `_is_lfs_pointer()` in `census/cbsa_parser.py`
- Checks if file starts with `version https://git-lfs.github.com/spec/v1`
- Returns `True` if file is LFS pointer (not actual content)

**Code Reference**: `src/babylon/data/census/cbsa_parser.py`

```python
def _is_lfs_pointer(path: Path) -> bool:
    """Check if a file is a Git LFS pointer instead of actual content."""
    with open(path, "rb") as f:
        header = f.read(100)
    return header.startswith(b"version https://git-lfs.github.com/spec/v1")
```

**Decision**: Extract this to `preflight.py` as a shared utility for all loaders to reuse.

---

### 5. Empty File Detection {#5-empty-file-detection}

**Question**: How should empty/corrupt files be detected per clarification?

**Findings**:
- Clarification specifies: "Treat as failures (same as missing - block simulation start)"
- Python `Path.stat().st_size` provides file size efficiently
- Files under ~100 bytes are likely invalid for data files

**Decision**: Add `_check_file_not_empty()` helper that:
1. Checks file exists
2. Checks file size > 0
3. Checks not LFS pointer
Returns appropriate `PreflightCheck` for each failure mode.

---

## Summary of Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Protocol Location | `loader_base.py` | Near `DataLoader` ABC, same import path |
| Protocol Type | `typing.Protocol` | Non-breaking, opt-in, Pythonic |
| Loader Registration | Explicit whitelist in `preflight.py` | Per clarification, simpler than discovery |
| LFS Detection | Extract to `preflight.py` | Shared utility for all loaders |
| Empty File Handling | Treat as failure | Per clarification |
| Backward Compatibility | Keep existing `_check_*` functions | Non-breaking change |
