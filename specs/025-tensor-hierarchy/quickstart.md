# Quickstart: Tensor Hierarchy

**Feature**: 025-tensor-hierarchy | **Date**: 2026-02-26

## Prerequisites

1. Poetry environment with NumPy and SciPy installed
2. SQLite database at `data/sqlite/marxist-data-3NF.sqlite`
3. BEA I-O XLSX files in `data/input-output/` (already downloaded)
4. BTS FAF data (needs download — see Data Acquisition below)

## Data Acquisition

### BEA I-O Tables (already present)

Files are at `data/input-output/make-use/` and `data/input-output/total-domestic-requirements/`. No action needed.

### BTS FAF Freight Flows (needs download)

1. Visit https://www.bts.gov/faf
2. Download FAF5 commodity flow data (CSV format)
3. Place in `data/bts/faf/`

### BEA-NAICS Concordance (already present)

File at `data/concordance/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx`. No action needed.

## Ingestion Order

Run loaders in this order (dependencies flow top-down):

```bash
# 1. Geographic dimensions (many loaders depend on these)
poetry run python -m babylon.data.geography.loader

# 2. BEA-NAICS bridge (needed for department mapping)
poetry run python -m babylon.data.bea.loader_concordance

# 3. BEA I-O coefficients (P1)
poetry run python -m babylon.data.bea.io_loader

# 4. ATUS reproductive labor (P2 — visibility metric)
poetry run python -m babylon.data.atus.loader

# 5. BTS FAF commodity flows (P3)
poetry run python -m babylon.data.bts.faf_loader
```

## Verification

```bash
# Run unit tests for tensor hierarchy
poetry run pytest tests/unit/economics/tensor_hierarchy/ -v

# Run integration tests
poetry run pytest tests/integration/economics/test_tensor_hierarchy.py -v

# Validate against BEA published benchmarks
poetry run pytest tests/unit/economics/tensor_hierarchy/test_inter_industry.py -k "benchmark" -v
```

## Implementation Priority

| Priority | Story | Dependencies | Status |
|----------|-------|--------------|--------|
| P1 | InterIndustryFlow + Leontief | BEA I-O XLSX (present), concordance (present) | Ready |
| P2 | VisibilityMetric (gamma wrapper) | Gamma module (Feature 015, complete) | Ready |
| P3 | GeographicFlow + ImperialRent | BTS FAF (needs download + loader) | Blocked on data |
| P4 | ReproductionRequirements | CEX data (no schema, no loader, no data) | Deferred |
| P5 | ClassTransitionMatrix | PSID data (no schema, no loader, no data) | Deferred |
