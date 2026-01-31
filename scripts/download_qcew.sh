#!/usr/bin/env bash
# Download QCEW bulk data files from BLS
#
# Usage:
#   ./scripts/download_qcew.sh              # Download 2010-2024 (default)
#   ./scripts/download_qcew.sh 2015 2020    # Download 2015-2020
#   ./scripts/download_qcew.sh 2023 2023    # Download single year
#
# This script wraps the mise task for convenience.

set -euo pipefail

START_YEAR="${1:-2010}"
END_YEAR="${2:-2024}"

echo "=============================================="
echo "QCEW Bulk Data Download"
echo "=============================================="
echo "Year range: ${START_YEAR}-${END_YEAR}"
echo "Output directory: data/qcew/"
echo ""

# Run the mise task with year range
mise run data:qcew-download -- --years "${START_YEAR}-${END_YEAR}"

echo ""
echo "=============================================="
echo "Download complete!"
echo ""
echo "Next steps:"
echo "  1. Load into database: mise run data:qcew -- --years ${START_YEAR}-${END_YEAR} --force-files"
echo "  2. Or view files: ls -la data/qcew/*.csv"
echo "=============================================="
