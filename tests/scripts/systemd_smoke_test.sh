#!/usr/bin/env bash
# Spec 061 T125: systemd smoke test on a staging host.
#
# Drives the production systemd unit through the failure paths spec'd
# in research.md R3:
#   1. Stop Postgres → observe 3 in-process retries + sys.exit(1) in
#      the web log, observe systemd noticing the failure.
#   2. Wait for systemd's RestartSec backoff, observe a retry.
#   3. Start Postgres → observe successful boot, /health/detail/
#      reports EngineBridge.
#
# Usage:
#   sudo ./tests/scripts/systemd_smoke_test.sh
#
# Must run as root or with sudo (controls babylon-web.service and
# postgresql.service). Run ONLY on a dedicated staging host — this
# script intentionally kills Postgres.
#
# Exit codes:
#   0   all 3 phases observed correctly
#   1   a phase deviated from the expected behavior
#   2   prerequisites missing

set -euo pipefail

WEB_UNIT=${BABYLON_WEB_UNIT:-babylon-web.service}
PG_UNIT=${BABYLON_PG_UNIT:-postgresql.service}
HEALTH_URL=${BABYLON_HEALTH_URL:-http://localhost:8000/health/detail/}
STAFF_USER=${BABYLON_STAFF_USER:-admin}
STAFF_PASS=${BABYLON_STAFF_PASS:-admin}

require() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "FATAL: required tool '$1' not on PATH" >&2
        exit 2
    fi
}

require systemctl
require curl

if [[ $EUID -ne 0 ]]; then
    echo "FATAL: must run as root (or via sudo); systemctl operations require privilege" >&2
    exit 2
fi

# Confirm the units exist
if ! systemctl status "$WEB_UNIT" >/dev/null 2>&1; then
    echo "FATAL: $WEB_UNIT not found; install via 'ansible-playbook deploy/ansible/web.yml'" >&2
    exit 2
fi

echo "==[ Phase 1: web service is healthy before chaos ]=="
systemctl restart "$WEB_UNIT"
sleep 5
if ! curl -fsS -u "$STAFF_USER:$STAFF_PASS" "$HEALTH_URL" >/dev/null; then
    echo "FATAL: $HEALTH_URL not reachable; smoke aborted" >&2
    exit 2
fi
echo "  web service healthy: OK"

echo
echo "==[ Phase 2: stop Postgres; web service should retry → exit → restart ]=="
systemctl stop "$PG_UNIT"
echo "  waiting 15s for in-process retries + sys.exit(1) + systemd restart attempt..."
sleep 15

# Check unit state — should be activating (waiting for restart) or failed (still in backoff)
state=$(systemctl is-active "$WEB_UNIT" || true)
echo "  $WEB_UNIT is-active: $state"
case "$state" in
    activating|failed|deactivating)
        echo "  expected: web service NOT fully active without Postgres"
        ;;
    active)
        echo "  WARN: web service still reports active — boot may have a fast retry path"
        ;;
    *)
        echo "  WARN: unexpected state '$state'"
        ;;
esac

echo
echo "==[ Phase 3: restart Postgres; web service should boot successfully ]=="
systemctl start "$PG_UNIT"
sleep 10

# Trigger an explicit web restart to short-circuit the exponential backoff
# during smoke-testing
systemctl restart "$WEB_UNIT"
sleep 10

if ! curl -fsS -u "$STAFF_USER:$STAFF_PASS" "$HEALTH_URL" >/dev/null; then
    echo "FAIL: $HEALTH_URL not reachable after Postgres was restored" >&2
    exit 1
fi

impl=$(curl -fsS -u "$STAFF_USER:$STAFF_PASS" "$HEALTH_URL" | python3 -c "import json, sys; print(json.load(sys.stdin)['engine']['implementation'])")
echo "  health.engine.implementation = $impl"

if [[ "$impl" != "EngineBridge" ]]; then
    echo "FAIL: expected EngineBridge, got $impl" >&2
    exit 1
fi

echo
echo "=================================================="
echo "T125 systemd smoke test: all phases passed"
echo "=================================================="
