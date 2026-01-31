# Quickstart: QCEW Data Ingestion Pipeline

**Feature**: 004-qcew-data-ingestion
**Date**: 2026-01-30

## Overview

This guide shows how to download and load QCEW employment data from BLS into the Babylon database.

## Prerequisites

- Network access to BLS servers (data.bls.gov)
- ~5GB disk space for full 2010-2024 dataset
- Census dimensions loaded (`mise run data:census`)

## Quick Start (One Command)

Download and load Detroit metro data for all years:

```bash
# Download bulk files
mise run data:qcew-download -- --years 2010-2024

# Load into database
mise run data:qcew -- --years 2010-2024 --force-files
```

Or use the combined wrapper:

```bash
./scripts/download_qcew.sh 2010 2024
mise run data:qcew -- --years 2010-2024 --force-files
```

## Step-by-Step Usage

### 1. Download QCEW Data

```bash
# Download specific years
mise run data:qcew-download -- --years 2015-2020

# Download single year
mise run data:qcew-download -- --years 2023

# Force re-download (skip existing disabled)
mise run data:qcew-download -- --years 2023 --no-skip-existing
```

### 2. Check Downloaded Files

```bash
ls -la data/qcew/
# Should show:
# 2015.annual singlefile.csv
# 2016.annual singlefile.csv
# ...
```

### 3. Load Into Database

```bash
# Load from downloaded files
mise run data:qcew -- --years 2015-2020 --force-files

# Verify loaded data
sqlite3 data/sqlite/marxist-data-3NF.sqlite \
  "SELECT year, COUNT(*) FROM fact_qcew_annual GROUP BY year"
```

## Python API Usage

### Download Programmatically

```python
from babylon.data.qcew.downloader import QcewDownloader, DownloadConfig

# Configure download
config = DownloadConfig(
    years=list(range(2010, 2025)),
    output_dir=Path("data/qcew"),
    skip_existing=True,
    rate_limit_seconds=1.0
)

# Run download
downloader = QcewDownloader()
report = downloader.download_all(config)

# Check results
print(f"Downloaded: {report.years_downloaded}")
print(f"Skipped: {report.years_skipped}")
print(f"Failed: {report.years_failed}")
print(f"Total size: {report.total_bytes / 1e9:.1f} GB")
```

### Load Programmatically

```python
from babylon.data.qcew import QcewLoader
from babylon.data.loader_base import LoaderConfig
from babylon.data.reference.database import get_normalized_session

# Configure loader
config = LoaderConfig(qcew_years=list(range(2010, 2025)))
loader = QcewLoader(config)

# Load data
with get_normalized_session() as session:
    stats = loader.load(session, force_files=True)
    print(f"Loaded {stats.facts_loaded['qcew_county']:,} county records")
```

## Detroit Metro Filter

To load only Detroit metro counties (smaller, faster):

```python
# The loader filters during processing
# Just ensure these counties exist in dim_county:
# - 26163 (Wayne County)
# - 26125 (Oakland County)
# - 26099 (Macomb County)
```

After loading, verify:

```sql
SELECT fips_code, c.county_name, COUNT(*) as records
FROM fact_qcew_annual f
JOIN dim_county c ON f.county_id = c.county_id
WHERE c.fips IN ('26163', '26125', '26099')
GROUP BY fips_code, c.county_name;
```

## Verify Data Integrity

### Check Year Coverage

```sql
SELECT DISTINCT t.year
FROM fact_qcew_annual f
JOIN dim_time t ON f.time_id = t.time_id
JOIN dim_county c ON f.county_id = c.county_id
WHERE c.fips = '26163'
ORDER BY t.year;
```

Expected: All years from 2010 to 2024.

### Check Industry Coverage

```sql
SELECT i.naics_code, i.industry_title, COUNT(*) as records
FROM fact_qcew_annual f
JOIN dim_industry i ON f.industry_id = i.industry_id
JOIN dim_county c ON f.county_id = c.county_id
WHERE c.fips = '26163' AND t.year = 2022
GROUP BY i.naics_code, i.industry_title
ORDER BY records DESC
LIMIT 10;
```

## Troubleshooting

### Download Fails for a Year

```bash
# Check if file exists on BLS
curl -I https://data.bls.gov/cew/data/files/2024/csv/2024_annual_singlefile.zip

# If 404, year may not be published yet
# If 200, retry download
mise run data:qcew-download -- --years 2024 --no-skip-existing
```

### Disk Space Issues

```bash
# Check space needed
du -sh data/qcew/

# Clean up ZIP files after extraction
mise run data:qcew-download -- --cleanup-zips
```

### Resume After Interruption

The download automatically skips existing files:

```bash
# Just re-run - it will continue where it left off
mise run data:qcew-download -- --years 2010-2024
```

## Performance Notes

| Operation                  | Time (approximate) |
| -------------------------- | ------------------ |
| Download 1 year            | 1-2 minutes        |
| Extract 1 year             | 10-30 seconds      |
| Load 1 year (nationwide)   | 3-5 minutes        |
| Load 1 year (Detroit only) | 30 seconds         |

**Full 2010-2024 ingestion**: ~45 minutes (nationwide) or ~10 minutes (Detroit metro)
