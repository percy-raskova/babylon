#!/usr/bin/env bash
# Own one disposable PostgreSQL runtime for the destructive PER-20 Rust proof.
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT
readonly IMAGE="babylon-per20-legacy-adopter:local"
# Internal handshake for the ignored Rust test. This runner forwards it only
# after it proves exact ownership of the random-canary container below.
readonly TEST_HARNESS_ACK="I_UNDERSTAND_PER20_DROPS_SCRATCH_DATABASES_ROLES_AND_CREATED_BABYLON_INTEL"
CANARY="$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')"
readonly CANARY
readonly CONTAINER="babylon-per20-adopter-${CANARY:0:12}"
VOLUME=""
OWNED=0

die() {
  printf 'run_rust_legacy_adopter_pg: %s\n' "$*" >&2
  exit 2
}

require_container_absent() {
  local context="$1"
  local inspect_status
  if timeout --signal=TERM --kill-after=2s 10s \
      docker container inspect "$CONTAINER" >/dev/null 2>&1; then
    die "task-owned container is present during $context"
  else
    inspect_status="$?"
  fi
  if [ "$inspect_status" -ne 1 ]; then
    die "task-owned container absence could not be verified during $context"
  fi
}

require_volume_absent() {
  local inspect_status
  if timeout --signal=TERM --kill-after=2s 10s \
      docker volume inspect "$VOLUME" >/dev/null 2>&1; then
    die "task-owned anonymous volume cleanup did not complete"
  else
    inspect_status="$?"
  fi
  if [ "$inspect_status" -ne 1 ]; then
    die "task-owned anonymous volume cleanup could not be verified"
  fi
}

claim_task_container() {
  local expected_container_id="$1"
  local identity
  local inspect_status=0
  identity="$(timeout --signal=TERM --kill-after=2s 10s \
    docker inspect --format '{{.Id}}|{{index .Config.Labels "babylon.per20_disposable"}}' \
      "$CONTAINER")" || inspect_status="$?"
  [ "$inspect_status" -eq 0 ] || return 1
  local actual_container_id="${identity%%|*}"
  local actual_canary="${identity#*|}"
  [ "$actual_canary" = "$CANARY" ] || return 1
  if [ -n "$expected_container_id" ] &&
      [ "$actual_container_id" != "$expected_container_id" ]; then
    return 1
  fi
  OWNED=1
}

# shellcheck disable=SC2329 # Invoked by the EXIT trap after ownership is proved.
cleanup_best_effort() {
  [ "$OWNED" -eq 1 ] || return 0
  timeout --signal=TERM --kill-after=5s 30s \
    docker rm --force --volumes "$CONTAINER" >/dev/null 2>&1 || true
}

cleanup_checked() {
  [ "$OWNED" -eq 1 ] || return 0
  timeout --signal=TERM --kill-after=5s 30s \
    docker rm --force --volumes "$CONTAINER" >/dev/null
  require_container_absent "cleanup"
  if [ -n "$VOLUME" ]; then
    require_volume_absent
  fi
  OWNED=0
}

wait_for_runtime() {
  local deadline=$((SECONDS + 90))
  local host_probe
  local remaining
  for _attempt in {1..90}; do
    remaining=$((deadline - SECONDS))
    if [ "$remaining" -le 0 ]; then
      break
    fi
    if [ "$(timeout --signal=TERM --kill-after=1s "${remaining}s" \
      docker exec "$CONTAINER" psql -qAt -U test -d template1 -c \
        "SELECT pg_catalog.current_setting('babylon.per20_disposable', true) = '$CANARY' \
           AND (SELECT extversion = '3.5.2' FROM pg_catalog.pg_extension WHERE extname = 'postgis') \
           AND (SELECT extversion = '0.8.5' FROM pg_catalog.pg_extension WHERE extname = 'vector')" \
        2>/dev/null || true)" = "t" ]; then
      host_probe="$(timeout --signal=TERM --kill-after=1s 1s \
        env -u PGHOSTADDR -u PGOPTIONS -u PGSERVICE -u PGSERVICEFILE \
          PGPASSWORD=test PGCONNECT_TIMEOUT=1 PGSSLMODE=disable \
        psql -X -w -qAt -F '|' -h 127.0.0.1 -p "$PORT" -U test -d postgres \
          -v ON_ERROR_STOP=1 \
          -c "SELECT 1, pg_catalog.current_setting('babylon.per20_disposable', true)" \
          2>/dev/null || true)"
      if [ "$host_probe" = "1|$CANARY" ]; then
        return 0
      fi
    fi
    if [ "$SECONDS" -lt "$deadline" ]; then
      sleep 1
    fi
  done
  return 1
}

# shellcheck disable=SC2329 # Invoked by the INT, TERM, and HUP traps below.
on_signal() {
  local -r status="$1"
  trap - EXIT INT TERM HUP
  if [ "$OWNED" -eq 0 ]; then
    claim_task_container "" || true
  fi
  cleanup_best_effort
  exit "$status"
}

trap cleanup_best_effort EXIT
trap 'on_signal 130' INT
trap 'on_signal 143' TERM
trap 'on_signal 129' HUP

[ "${#CANARY}" -eq 32 ] || die "canary generation failed"
command -v psql >/dev/null 2>&1 || die "psql client is required for host readiness proof"
require_container_absent "startup"

printf 'PER-20 runtime target: image=%s container=%s volume=anonymous port=dynamic-loopback\n' \
  "$IMAGE" "$CONTAINER"
env DOCKER_BUILDKIT=1 \
  timeout --signal=TERM --kill-after=10s 180s \
  docker build --tag "$IMAGE" "$REPO_ROOT/docker/postgres"

run_status=0
created_container_id="$(timeout --signal=TERM --kill-after=5s 30s docker run --detach \
  --name "$CONTAINER" \
  --label "babylon.per20_disposable=$CANARY" \
  --publish 127.0.0.1::5432 \
  --mount type=volume,target=/var/lib/postgresql/data \
  --mount "type=bind,source=$REPO_ROOT/docker/postgres/postgresql.ci.conf,target=/etc/postgresql/postgresql.conf,readonly" \
  --mount "type=bind,source=$REPO_ROOT/docker/postgres/initdb,target=/docker-entrypoint-initdb.d,readonly" \
  --shm-size=1g \
  --env POSTGRES_USER=test \
  --env POSTGRES_PASSWORD=test \
  --env POSTGRES_DB=babylon_test \
  "$IMAGE" postgres \
  -c config_file=/etc/postgresql/postgresql.conf \
  -c "babylon.per20_disposable=$CANARY")" || run_status="$?"
if [ "$run_status" -eq 0 ]; then
  claim_task_container "$created_container_id" || die "created container identity was not proved"
else
  claim_task_container "" || true
  die "task-owned container did not start"
fi

VOLUME="$(timeout --signal=TERM --kill-after=2s 10s \
  docker inspect --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' "$CONTAINER")"
[ -n "$VOLUME" ] || die "anonymous data volume identity was not resolved"
published="$(timeout --signal=TERM --kill-after=2s 10s \
  docker port "$CONTAINER" 5432/tcp)"
readonly PORT="${published##*:}"
case "$PORT" in
  ''|*[!0-9]*) die "dynamic loopback port was not numeric" ;;
esac

wait_for_runtime || die "pinned PostgreSQL runtime was not ready within 90 seconds"

printf 'PER-20 runtime ready: container=%s volume=%s port=%s\n' \
  "$CONTAINER" "$VOLUME" "$PORT"
cd "$REPO_ROOT/rust"
status=0
timeout --signal=TERM --kill-after=10s 600s \
  env \
    BABYLON_LEGACY_ADOPTER_TEST_DSN="postgresql://test:test@127.0.0.1:$PORT/postgres" \
    BABYLON_LEGACY_ADOPTER_DISPOSABLE_ACK="$TEST_HARNESS_ACK" \
    BABYLON_LEGACY_ADOPTER_DISPOSABLE_CANARY="$CANARY" \
    CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$REPO_ROOT/rust/target}" \
  cargo test -p babylon-persistence --test legacy_adopter_postgres --locked -- --nocapture \
    --ignored --test-threads=1 || status=$?

cleanup_checked
trap - EXIT INT TERM HUP
printf 'PER-20 runtime cleanup verified: container=%s volume=%s\n' "$CONTAINER" "$VOLUME"
exit "$status"
