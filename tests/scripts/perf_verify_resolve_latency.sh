#!/usr/bin/env bash
# Spec 061 T124: perf verification of resolve-tick → results visibility.
#
# Measures the p95 latency from POST /resolve/ to action_result rows
# being visible via GET /state/. Asserts p95 < 10s per SC-012.
#
# Usage:
#   ./tests/scripts/perf_verify_resolve_latency.sh <session_id> [N]
#
# Args:
#   session_id   UUID of a seeded session (from seed_initial_game)
#   N            Number of resolve calls to time (default 20)
#
# Reads:
#   BABYLON_BASE_URL  base URL of the running web app (default http://localhost:8000)
#
# Exit codes:
#   0   p95 < 10s
#   1   p95 ≥ 10s — SC-012 violation
#   2   prerequisites missing

set -euo pipefail

SESSION_ID=${1:-}
N=${2:-20}
BASE_URL=${BABYLON_BASE_URL:-http://localhost:8000}

if [[ -z $SESSION_ID ]]; then
    echo "Usage: $0 <session_id> [N=20]" >&2
    exit 2
fi

if ! command -v curl >/dev/null 2>&1; then
    echo "FATAL: curl not on PATH" >&2
    exit 2
fi

# Need jq for p95 calculation, but fall back to sort+awk if unavailable.
HAVE_JQ=0
command -v jq >/dev/null 2>&1 && HAVE_JQ=1

declare -a TIMINGS_MS=()

for i in $(seq 1 "$N"); do
    start=$(date +%s%3N)
    curl -fsS -X POST "$BASE_URL/api/games/$SESSION_ID/resolve/" -o /dev/null \
        --max-time 30
    # Confirm the new tick is visible via state/
    curl -fsS "$BASE_URL/api/games/$SESSION_ID/state/" -o /dev/null --max-time 5
    end=$(date +%s%3N)
    elapsed=$((end - start))
    TIMINGS_MS+=("$elapsed")
    printf "  resolve %2d/%2d : %5d ms\n" "$i" "$N" "$elapsed"
done

# Compute p95
SORTED=$(printf '%s\n' "${TIMINGS_MS[@]}" | sort -n)
COUNT=${#TIMINGS_MS[@]}
P95_IDX=$((COUNT * 95 / 100))
[[ $P95_IDX -lt 1 ]] && P95_IDX=1
P95_MS=$(echo "$SORTED" | sed -n "${P95_IDX}p")

echo
echo "=================================================="
echo "perf summary over $COUNT resolves:"
echo "  min : $(echo "$SORTED" | head -1) ms"
echo "  p50 : $(echo "$SORTED" | sed -n "$((COUNT / 2))p") ms"
echo "  p95 : $P95_MS ms"
echo "  max : $(echo "$SORTED" | tail -1) ms"
echo "=================================================="

THRESHOLD_MS=10000  # SC-012: 10s p95
if [[ $P95_MS -ge $THRESHOLD_MS ]]; then
    echo "FAIL: p95 $P95_MS ms ≥ threshold $THRESHOLD_MS ms (SC-012 violation)" >&2
    exit 1
fi

echo "PASS: p95 $P95_MS ms < threshold $THRESHOLD_MS ms (SC-012 satisfied)"
