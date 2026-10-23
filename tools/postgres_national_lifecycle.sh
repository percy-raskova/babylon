#!/usr/bin/env bash
national_success_selection() {
  NATIONAL_SUCCESS_DISPOSITION="${BABYLON_NATIONAL_SUCCESS_DISPOSITION-cleanup}"
  case "$NATIONAL_SUCCESS_DISPOSITION" in
    cleanup) ;;
    retain-for-native)
      [ "${BABYLON_POSTGRES_LIVE_FOCUS:-runtime_smoke}" = national_storage ] &&
        [ "${BABYLON_NATIONAL_CAPTURE_MODE:-raw-economic}" = playable-aid ] ||
        die "native retention requires playable national scope"
      ;;
    *) die "unsupported national success disposition" ;;
  esac
}

# Sourced by run_rust_postgres.sh; only its national_storage branch owns this lease.
# Command-mode flock owns the descriptor; --close prevents inheritance by the
# runner, Cargo, compiler caches, collectors, and every other worker descendant.
national_storage_qualification_selection() {
  NATIONAL_STORAGE_QUALIFICATION="${BABYLON_NATIONAL_STORAGE_QUALIFICATION-report-only}"
  case "$NATIONAL_STORAGE_QUALIFICATION" in
    report-only | storage | save) ;;
    *) die "unsupported national storage qualification: $NATIONAL_STORAGE_QUALIFICATION" ;;
  esac
}

national_storage_qualification_flags() {
  case "$1" in
    report-only) ;;
    storage) printf '%s\n' --qualify ;;
    save) printf '%s\n' --qualify-save ;;
    *) die "unsupported national storage qualification: $1" ;;
  esac
}

national_capture_selection() {
  national_success_selection
  national_storage_qualification_selection
  case "${BABYLON_NATIONAL_CAPTURE_MODE-raw-economic}" in
    raw-economic | playable-aid)
      export BABYLON_NATIONAL_CAPTURE_MODE="${BABYLON_NATIONAL_CAPTURE_MODE-raw-economic}"
      ;;
    *) die "unsupported national capture mode: ${BABYLON_NATIONAL_CAPTURE_MODE}" ;;
  esac
}

# Every registered checkout uses one control inode and one private ownership lease.
national_control_directory() {
  local common
  common="$(git -C "$REPO_ROOT" rev-parse --path-format=absolute --git-common-dir)" || die "national Git common directory is unavailable"
  printf '%s/babylon-national-storage\n' "$common"
}

national_existing_game_guard() {
  local directory field checkout
  directory="$(national_control_directory)" || return 1
  if [ -e "$directory/active" ] || [ -L "$directory/active" ]; then
    die "retained national ownership record requires exact recovery; refusing another game"
  fi
  git -C "$REPO_ROOT" worktree list --porcelain -z >/dev/null || die "national worktree inventory is unavailable"
  while IFS= read -r -d '' field; do
    case "$field" in
      "worktree "*)
        checkout="${field#worktree }"
        if [ -e "$checkout/reports/test-results/national-storage-runner/active" ] ||
          [ -L "$checkout/reports/test-results/national-storage-runner/active" ]; then
          die "retained national legacy ownership record requires exact recovery; refusing another game"
        fi
        ;;
    esac
  done < <(git -C "$REPO_ROOT" worktree list --porcelain -z)
}

national_lock_entry() {
  local directory descriptor identity
  national_existing_game_guard
  directory="$(national_control_directory)"
  umask 077
  mkdir -p "$directory"
  if [ "$#" -eq 0 ]; then
    exec flock --nonblock --close --verbose --conflict-exit-code 75 \
      "$directory/runner.lock" bash "$REPO_ROOT/tools/run_rust_postgres.sh" \
      --national-lock-held "$$"
  fi
  # No inherited environment variable can accidentally bypass acquisition.
  if [ "$#" -ne 2 ] || [ "$1" != --national-lock-held ] || [ "$2" != "$PPID" ]; then
    die "invalid internal national lock invocation"
  fi
  [ "$(cat "/proc/$PPID/comm")" = flock ] || die "national lock supervisor is not flock"
  identity="$(stat -Lc '%d:%i' "$directory/runner.lock")" || die "national lock inode is unavailable"
  for descriptor in /proc/"$PPID"/fd/*; do
    if [ "$(stat -Lc '%d:%i' "$descriptor" 2>/dev/null || true)" = "$identity" ]; then
      return 0
    fi
  done
  die "national lock supervisor does not own the exact lock inode"
}

national_begin() {
  # Bounded runtime phase records go to the existing --nocapture operator log.
  export BABYLON_TIMINGS=1
  local directory
  national_existing_game_guard
  directory="$(national_control_directory)"
  umask 077
  mkdir -p "$directory"
  NATIONAL_RECORD="$directory/active"
  [[ "${BABYLON_STORAGE_REPORT_DIRECTORY:-}" = /* ]] || die "national evidence directory must be absolute"
  local compatible="$REPO_ROOT/tools/devtools/national_storage_snapshot.py"
  export BABYLON_STORAGE_SNAPSHOT_SCRIPT="${BABYLON_STORAGE_SNAPSHOT_SCRIPT:-$compatible}"
  [ "$(realpath -e -- "$BABYLON_STORAGE_SNAPSHOT_SCRIPT")" = "$(realpath -e -- "$compatible")" ] || die "this focus requires the verified current encoded collector"
  if [[ "${BABYLON_STORAGE_SNAPSHOT_SCRIPT:-}" != /* ]] || [ ! -f "$BABYLON_STORAGE_SNAPSHOT_SCRIPT" ]; then
    die "an existing absolute snapshot collector is required"
  fi
  mkdir "$BABYLON_STORAGE_REPORT_DIRECTORY" || die "national evidence directory must be new"
  printf '%s\n' "$BABYLON_NATIONAL_CAPTURE_MODE" > "$BABYLON_STORAGE_REPORT_DIRECTORY/capture-mode"
  NATIONAL_DATABASE="national_${CANARY:0:12}"
  NATIONAL_WRITER="national_writer_${CANARY:0:12}"
  NATIONAL_DATABASE_OID=""
  national_record
  trap 'national_failure_summary "$?" || true' EXIT
  git -C "$REPO_ROOT" rev-parse HEAD > "$BABYLON_STORAGE_REPORT_DIRECTORY/source-head"
  cp -- "$BABYLON_STORAGE_SNAPSHOT_SCRIPT" "$BABYLON_STORAGE_REPORT_DIRECTORY/snapshot-source.py"
  cp -- "$(dirname -- "$BABYLON_STORAGE_SNAPSHOT_SCRIPT")/national_storage_relations.sql" "$BABYLON_STORAGE_REPORT_DIRECTORY/national_storage_relations.sql"
  cp -- "$REPO_ROOT/rust/crates/babylon-persistence/tests/national_storage_encoded_measurement.rs" "$BABYLON_STORAGE_REPORT_DIRECTORY/measurement-source.rs"
  cp -- "$REPO_ROOT/rust/crates/babylon-persistence/tests/fixtures/national_capture.rs" "$BABYLON_STORAGE_REPORT_DIRECTORY/national-input-source.rs"
  # Execute the frozen compatible collector with its adjacent SQL and explicit
  # output directory. Its stage convention is <stage>.json, matching the test.
  export BABYLON_STORAGE_SNAPSHOT_SCRIPT="$BABYLON_STORAGE_REPORT_DIRECTORY/snapshot-source.py"
  NATIONAL_POLICY_SOURCE="${BABYLON_STORAGE_POLICY_PATH:-$REPO_ROOT/contracts/national_storage_qualification_v6.json}"
  [[ "$NATIONAL_POLICY_SOURCE" = /* ]] || die "storage policy override must be an absolute path"
  NATIONAL_POLICY_SOURCE="$(realpath -e -- "$NATIONAL_POLICY_SOURCE")" || die "storage policy must exist"
  [ -f "$NATIONAL_POLICY_SOURCE" ] || die "storage policy must be a regular file"
  printf '%s\n' "$NATIONAL_POLICY_SOURCE" > "$BABYLON_STORAGE_REPORT_DIRECTORY/policy-source.path"
  sha256sum "$NATIONAL_POLICY_SOURCE" > "$BABYLON_STORAGE_REPORT_DIRECTORY/policy-source.sha256"
  cp -- "$NATIONAL_POLICY_SOURCE" "$BABYLON_STORAGE_REPORT_DIRECTORY/policy.json"
  national_policy_capture_agrees || die "benchmark policy changed during capture"
  export BABYLON_STORAGE_FROZEN_POLICY_PATH="$BABYLON_STORAGE_REPORT_DIRECTORY/policy.json"
  cp -- "$REPO_ROOT/tools/devtools/national_storage_qualification.py" "$BABYLON_STORAGE_REPORT_DIRECTORY/national_storage_qualification.py"
  mise exec -- uv run --frozen python "$BABYLON_STORAGE_REPORT_DIRECTORY/national_storage_qualification.py" \
    --validate-policy --policy "$BABYLON_STORAGE_REPORT_DIRECTORY/policy.json" \
    > "$BABYLON_STORAGE_REPORT_DIRECTORY/policy-validation.json" || die "captured benchmark policy refused before database setup"
  NATIONAL_QUALIFY_TIMING="${BABYLON_NATIONAL_QUALIFY_TIMING:-0}"
  case "$NATIONAL_QUALIFY_TIMING" in
    0|1) ;;
    *) die "BABYLON_NATIONAL_QUALIFY_TIMING must be 0 or 1" ;;
  esac
  printf '%s\n' "$NATIONAL_QUALIFY_TIMING" > "$BABYLON_STORAGE_REPORT_DIRECTORY/timing-qualification-mode"
  printf '%s\n' "$NATIONAL_STORAGE_QUALIFICATION" > "$BABYLON_STORAGE_REPORT_DIRECTORY/storage-qualification-mode"
  national_reproducibility
  cmp -- "$REPO_ROOT/rust/crates/babylon-persistence/tests/national_storage_encoded_measurement.rs" "$BABYLON_STORAGE_REPORT_DIRECTORY/measurement-source.rs" || die "measurement source changed during capture"
  cmp -- "$REPO_ROOT/rust/crates/babylon-persistence/tests/fixtures/national_capture.rs" "$BABYLON_STORAGE_REPORT_DIRECTORY/national-input-source.rs" || die "national input source changed during capture"
  cmp -- "$REPO_ROOT/tools/devtools/national_storage_qualification.py" "$BABYLON_STORAGE_REPORT_DIRECTORY/national_storage_qualification.py"
  (cd "$BABYLON_STORAGE_REPORT_DIRECTORY" && sha256sum measurement-source.rs national-input-source.rs snapshot-source.py national_storage_relations.sql national_storage_qualification.py policy.json policy-source.path policy-source.sha256 policy-validation.json timing-qualification-mode storage-qualification-mode capture-mode > operator.sha256)
}

national_policy_capture_agrees() {
  sha256sum --check "$BABYLON_STORAGE_REPORT_DIRECTORY/policy-source.sha256" || return 1
  cmp -- "$NATIONAL_POLICY_SOURCE" "$BABYLON_STORAGE_REPORT_DIRECTORY/policy.json" || return 1
}

national_record_contents() {
  printf '%s\n' 'national-storage-runner-v1' "$REPO_ROOT" "$CANARY" "$CONTAINER" \
    "$CONTAINER_ID" "$VOLUME" "${IMAGE_ID:-}" "$NATIONAL_DATABASE" \
    "$NATIONAL_WRITER" "$NATIONAL_DATABASE_OID" "$BABYLON_STORAGE_REPORT_DIRECTORY"
}

national_record() {
  umask 077
  local temporary="$NATIONAL_RECORD.tmp"
  national_record_contents > "$temporary"
  mv -- "$temporary" "$NATIONAL_RECORD"
  cp -- "$NATIONAL_RECORD" "$BABYLON_STORAGE_REPORT_DIRECTORY/ownership"
}

national_sql() {
  docker exec "$CONTAINER_ID" psql -X -qAt -U test -d postgres -v ON_ERROR_STOP=1 -c "$1"
}

national_create_game() {
  if [ "$BABYLON_NATIONAL_CAPTURE_MODE" = playable-aid ]; then
    # Production session admission grants the fixed view rosters as their
    # owner. Create the standard non-login principals through this exact
    # owned cluster admin so the writer never needs CREATEROLE.
    national_sql "CREATE ROLE babylon_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;"
    national_sql "CREATE ROLE babylon_observer NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;"
    local observer="national_observer_${CANARY:0:12}"
    national_sql "CREATE ROLE $observer LOGIN PASSWORD '$CANARY' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS IN ROLE babylon_observer;"
    national_sql "GRANT SET ON PARAMETER event_triggers TO $observer;"
    printf '%s\n' "$observer" > "$BABYLON_STORAGE_REPORT_DIRECTORY/observer-role"
    export BABYLON_NATIONAL_STORAGE_OBSERVER_DSN="postgresql://$observer:$CANARY@127.0.0.1:$PORT/$NATIONAL_DATABASE"
    local reader="national_reader_${CANARY:0:12}"
    national_sql "CREATE ROLE $reader LOGIN PASSWORD '$CANARY' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS IN ROLE babylon_reader;"
    national_sql "GRANT SET ON PARAMETER event_triggers TO $reader;"
    printf '%s\n' "$reader" > "$BABYLON_STORAGE_REPORT_DIRECTORY/reader-role"
    export BABYLON_NATIONAL_STORAGE_READER_DSN="postgresql://$reader:$CANARY@127.0.0.1:$PORT/$NATIONAL_DATABASE"
  fi
  national_sql "CREATE ROLE $NATIONAL_WRITER LOGIN PASSWORD '$CANARY' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;"
  national_sql "GRANT SET ON PARAMETER event_triggers TO $NATIONAL_WRITER;"
  national_sql "CREATE DATABASE $NATIONAL_DATABASE OWNER $NATIONAL_WRITER TEMPLATE template1;"
  NATIONAL_DATABASE_OID="$(national_sql "SELECT oid FROM pg_catalog.pg_database WHERE datname='$NATIONAL_DATABASE' AND datdba=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname='$NATIONAL_WRITER');")"
  [[ "$NATIONAL_DATABASE_OID" =~ ^[0-9]+$ ]] || die "national database identity was not proved"
  national_record
  export BABYLON_STORAGE_CANARY="$CANARY"
  export BABYLON_NATIONAL_STORAGE_WRITER_DSN="postgresql://$NATIONAL_WRITER:$CANARY@127.0.0.1:$PORT/$NATIONAL_DATABASE"
  export BABYLON_STORAGE_DSN="$BABYLON_NATIONAL_STORAGE_WRITER_DSN"
  # Authenticate startup permissions before capturing the expensive opening.
  # DSNs remain environment inputs; failures never emit driver exception text.
  mise exec -- uv run --frozen python - <<'PY_STARTUP' || die "national credential startup admission failed"
import os
import psycopg

names = ["BABYLON_NATIONAL_STORAGE_WRITER_DSN"]
if os.environ["BABYLON_NATIONAL_CAPTURE_MODE"] == "playable-aid":
    names.extend(["BABYLON_NATIONAL_STORAGE_OBSERVER_DSN", "BABYLON_NATIONAL_STORAGE_READER_DSN"])
for name in names:
    try:
        with psycopg.connect(os.environ[name], connect_timeout=10, options="-c event_triggers=off") as connection:
            flags = connection.execute(
                "SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls "
                "FROM pg_catalog.pg_roles WHERE rolname=current_user"
            ).fetchone()
            if flags is None or any(flags):
                raise ValueError("unconfined credential")
    except (psycopg.Error, ValueError):
        raise SystemExit("National startup admission refused: " + name) from None
PY_STARTUP
  export BABYLON_NATIONAL_STORAGE_CAMPAIGN
  BABYLON_NATIONAL_STORAGE_CAMPAIGN="$(cat /proc/sys/kernel/random/uuid)"
  printf '%s\n' "$BABYLON_NATIONAL_STORAGE_CAMPAIGN" > "$BABYLON_STORAGE_REPORT_DIRECTORY/campaign"
}

# Measurement horizon comes from the captured canonical policy, not campaign law.
national_period_count() {
  mise exec -- uv run --frozen python -c '
import json,re,sys
policy=json.load(open(sys.argv[1]))
maximum=policy["save_qualification_ticks"]
if type(maximum) is not int or not 0 < maximum <= 9223372036854775807:
    raise ValueError("invalid policy save qualification ticks")
value=sys.argv[2] or str(policy["routine_smoke_periods"])
if len(value)>len(str(maximum)) or re.fullmatch(r"[1-9][0-9]*",value) is None or int(value)>maximum:
    raise ValueError("period request outside captured save qualification horizon")
print(value)
' "$BABYLON_STORAGE_REPORT_DIRECTORY/policy.json" "${BABYLON_NATIONAL_STORAGE_PERIODS:-}"
}

# Shared nonmutating authority for live capture and terminal retention. A live
# game admits only its confined capabilities; terminal retention still requires
# every client to have exited. Neither path terminates a racing client.
national_verify_identity() {
  local identity inventory packet live=0 role_cte="" refused_sql=0
  case "$#" in
    0) ;;
    1) [ "$1" = --live ] || return 1; live=1 ;;
    *) return 1 ;;
  esac
  if [ "$live" -eq 1 ]; then
    [[ "${CANARY:-}" =~ ^[0-9a-f]{32}$ ]] &&
      [ "$NATIONAL_DATABASE" = "national_${CANARY:0:12}" ] &&
      [ "$NATIONAL_WRITER" = "national_writer_${CANARY:0:12}" ] &&
      [[ "${NATIONAL_DATABASE_OID:-}" =~ ^[1-9][0-9]*$ ]] || return 1
  fi
  [ -f "$NATIONAL_RECORD" ] && [ ! -L "$NATIONAL_RECORD" ] || return 1
  [ "$(stat -c '%a' "$NATIONAL_RECORD")" = 600 ] || return 1
  cmp -s -- "$NATIONAL_RECORD" <(national_record_contents) || return 1
  identity="$(docker inspect --format '{{.Id}}|{{.Image}}|{{index .Config.Labels "babylon.disposable_runtime"}}|{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' "$CONTAINER_ID")" || return 1
  [ "$identity" = "$CONTAINER_ID|$IMAGE_ID|$CANARY|$VOLUME" ] || return 1
  if [ "$live" -eq 1 ]; then
    role_cte="
WITH expected(name,login,parent) AS (VALUES
  ('$NATIONAL_WRITER',true,NULL::text),
  ('national_observer_${CANARY:0:12}',true,'babylon_observer'),
  ('national_reader_${CANARY:0:12}',true,'babylon_reader'),
  ('babylon_observer',false,NULL::text),
  ('babylon_reader',false,NULL::text)
), bad_roles AS (
  SELECT e.name FROM expected e LEFT JOIN pg_catalog.pg_roles r ON r.rolname=e.name
  WHERE r.oid IS NULL OR r.rolcanlogin IS DISTINCT FROM e.login
    OR r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls
    OR COALESCE((SELECT array_agg(p.rolname::text ORDER BY p.rolname COLLATE \"C\")
       FROM pg_catalog.pg_auth_members m JOIN pg_catalog.pg_roles p ON p.oid=m.roleid
       WHERE m.member=r.oid),ARRAY[]::text[])
       IS DISTINCT FROM CASE WHEN e.parent IS NULL THEN ARRAY[]::text[] ELSE ARRAY[e.parent] END
), bad_clients AS (
  SELECT pid FROM pg_catalog.pg_stat_activity
  WHERE backend_type='client backend' AND pid<>pg_backend_pid()
    AND (datname IS DISTINCT FROM '$NATIONAL_DATABASE'
      OR usename IS NULL OR usename NOT IN ('$NATIONAL_WRITER',
        'national_observer_${CANARY:0:12}','national_reader_${CANARY:0:12}'))
)
"
    refused_sql="(SELECT count(*) FROM bad_roles)+(SELECT count(*) FROM bad_clients)"
  fi
  # One fresh statement retains every database authority check. Live sampling
  # runs it before pause and after restoration, never while PostgreSQL is frozen.
  # Compare the entire packet: NULL, missing, extra or changed fields all refuse.
  packet="$(national_sql "$role_cte
SELECT pg_catalog.current_setting('babylon.disposable_runtime',true),
  (SELECT string_agg(datname,',' ORDER BY datname COLLATE \"C\") FROM pg_catalog.pg_database),
  CASE WHEN '$NATIONAL_DATABASE_OID'='' THEN '' ELSE
    (SELECT oid::text FROM pg_catalog.pg_database WHERE datname='$NATIONAL_DATABASE'
      AND datdba=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname='$NATIONAL_WRITER')) END,
  $refused_sql;")" || return 1
  [ "$packet" = "$CANARY|babylon_test,$NATIONAL_DATABASE,postgres,template0,template1|$NATIONAL_DATABASE_OID|0" ] || return 1
  if [ "$live" -eq 0 ]; then
    inventory="${packet#*|}"
    inventory="${inventory%%|*}"
    printf '%s\n' "$identity" "$inventory"
  fi
}

national_verify_live() {
  [ "$#" -eq 0 ] || return 1
  national_verify_identity --live
}

national_verify_success() {
  local identity sessions
  identity="$(national_verify_identity)" || return 1
  if [ -n "$NATIONAL_DATABASE_OID" ]; then
    sessions="$(national_sql "SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE pid<>pg_backend_pid() AND backend_type='client backend';")" || return 1
    [ "$sessions" = 0 ] || return 1
    (cd "$BABYLON_STORAGE_REPORT_DIRECTORY" && sha256sum --check operator.sha256) || return 1
    national_source_manifest > "$BABYLON_STORAGE_REPORT_DIRECTORY/source-after.sha256" || return 1
    cmp -- "$BABYLON_STORAGE_REPORT_DIRECTORY/source-before.sha256" "$BABYLON_STORAGE_REPORT_DIRECTORY/source-after.sha256" || return 1
    (cd "$REPO_ROOT" && sha256sum --check "$BABYLON_STORAGE_REPORT_DIRECTORY/inputs.sha256") || return 1
    sha256sum --check "$BABYLON_STORAGE_REPORT_DIRECTORY/source-archive.sha256" || return 1
    sha256sum --check "$BABYLON_STORAGE_REPORT_DIRECTORY/input-archive.sha256" || return 1
    # Evidence is small and immutable. The test is a fresh admitted
    # national fixture with generated qualification commands, never an imported
    # player save; no recurring dump copies.
    [ -s "$BABYLON_STORAGE_REPORT_DIRECTORY/schema-baseline.json" ] || return 1
    [ -s "$BABYLON_STORAGE_REPORT_DIRECTORY/opening-created.json" ] || return 1
    local periods stage
    periods="$(national_period_count)" || return 1
    printf -v stage 'tick-%02d-reopened.json' "$periods"
    [ -s "$BABYLON_STORAGE_REPORT_DIRECTORY/$stage" ] || return 1
    [ -s "$BABYLON_STORAGE_REPORT_DIRECTORY/qualification.json" ] || return 1
    [ -s "$BABYLON_STORAGE_REPORT_DIRECTORY/native-timings.json" ] || return 1
    (cd "$BABYLON_STORAGE_REPORT_DIRECTORY" && sha256sum --check evaluated-evidence.sha256) || return 1

  fi
  printf '%s\n' "$identity" > "$BABYLON_STORAGE_REPORT_DIRECTORY/success-proof"
}

national_verify_disposable() {
  national_verify_success || return 1
  if [ -n "$NATIONAL_DATABASE_OID" ]; then
    local sessions
    # Only after all nonmutating validation succeeds, freeze the disposable game.
    # A racing client causes refusal and restoration, never session termination.
    national_sql "ALTER DATABASE $NATIONAL_DATABASE ALLOW_CONNECTIONS false;" || return 1
    sessions="$(national_sql "SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE pid<>pg_backend_pid() AND backend_type='client backend';")" || {
      national_sql "ALTER DATABASE $NATIONAL_DATABASE ALLOW_CONNECTIONS true;"
      return 1
    }
    if [ "$sessions" != 0 ]; then
      national_sql "ALTER DATABASE $NATIONAL_DATABASE ALLOW_CONNECTIONS true;"
      return 1
    fi
  fi
  cp -- "$BABYLON_STORAGE_REPORT_DIRECTORY/success-proof" "$BABYLON_STORAGE_REPORT_DIRECTORY/cleanup-proof"
}

# Hash filesystem files, not Git's index: current untracked codecs participate.
national_source_paths() {
  local crate dependency
  for crate in babylon-client babylon-persistence babylon-tick babylon-material-circuit babylon-bsl babylon-graph babylon-kernel babylon-practice-contract; do
    # This is the measured target's complete current local dependency closure.
    # A new local dependency requires an explicit roster update, never omission.
    while IFS= read -r dependency; do
      case "$dependency" in
        babylon-client | babylon-persistence | babylon-tick | babylon-material-circuit | babylon-bsl | babylon-graph | babylon-kernel | babylon-practice-contract) ;;
        *) die "unrecorded local native dependency: $dependency" ;;
      esac
    done < <(sed -n 's/.*path = "\.\.\/\([^"/]*\)".*/\1/p' "rust/crates/$crate/Cargo.toml")
    find "rust/crates/$crate" -type f -print0
  done
  find rust -maxdepth 1 -type f -print0
  if [ -d rust/.cargo ]; then find rust/.cargo -type f -print0; fi
  # The image ID is recorded separately; pin its build, initialization and
  # mounted PostgreSQL configuration alongside the native source closure.
  find docker/postgres -type f -print0
  for configuration in .mise.toml mise.lock .python-version pyproject.toml uv.lock; do
    if [ -f "$configuration" ]; then printf '%s\0' "$configuration"; fi
  done
  find content -type f -print0
  national_input_paths
  printf '%s\0' tools/run_rust_postgres.sh tools/postgres_national_lifecycle.sh tools/run_observer_session.py tools/devtools/national_windowed_qualification.py tools/devtools/national_native_evidence.py tools/devtools/national_native_runner.py tools/devtools/national_game_memory.py tools/devtools/national_storage_qualification.py tools/devtools/national_storage_snapshot.py tools/devtools/national_storage_relations.sql
}

national_source_manifest() {
  (cd "$REPO_ROOT" && national_source_paths | LC_ALL=C sort -zu | xargs -0 sha256sum)
}

national_input_paths() {
  local preset="$REPO_ROOT/rust/crates/babylon-persistence/src/economic_catalog/preset.rs" relative absolute count=0
  while IFS= read -r relative; do
    absolute="$(realpath -e -- "$(dirname -- "$preset")/$relative")" || return 1
    [[ "$absolute" = "$REPO_ROOT/"* ]] || return 1
    printf '%s\0' "${absolute#"$REPO_ROOT/"}"
    count=$((count + 1))
  done < <(sed -n '/^    let rows: .* = &\[/,/^    \];/ { s/.*include_bytes!("\([^"]*\)").*/\1/p; }' "$preset")
  [ "$count" -eq 15 ] || return 1
}

national_reproducibility() {
  local cache="$REPO_ROOT/reports/test-results/national-storage-runner/reproducibility" digest temporary destination
  mkdir -p "$cache"
  national_source_manifest > "$BABYLON_STORAGE_REPORT_DIRECTORY/source-before.sha256"
  national_input_paths > "$BABYLON_STORAGE_REPORT_DIRECTORY/input-paths.nul"
  (cd "$REPO_ROOT" && xargs -0 sha256sum < "$BABYLON_STORAGE_REPORT_DIRECTORY/input-paths.nul") > "$BABYLON_STORAGE_REPORT_DIRECTORY/inputs.sha256"
  # Immutable, content-addressed inputs are retained once; no database backups.
  digest="$(sha256sum "$BABYLON_STORAGE_REPORT_DIRECTORY/inputs.sha256")"; digest="${digest%% *}"
  destination="$cache/inputs-$digest.tar.gz"
  if [ ! -e "$destination" ]; then
    temporary="$destination.$CANARY.partial"
    tar -C "$REPO_ROOT" -czf "$temporary" --null -T "$BABYLON_STORAGE_REPORT_DIRECTORY/input-paths.nul"
    mv -- "$temporary" "$destination"
    sha256sum "$destination" > "$destination.sha256"
  fi
  [ -f "$destination.sha256" ] || die "existing reproducibility capsule lacks an ownership checksum"
  sha256sum --check "$destination.sha256"
  sha256sum "$destination" > "$BABYLON_STORAGE_REPORT_DIRECTORY/input-archive.sha256"
  stat -c '%s' "$destination" > "$BABYLON_STORAGE_REPORT_DIRECTORY/input-archive-bytes"
  # The full current Rust source capsule also covers untracked implementation.
  digest="$(sha256sum "$BABYLON_STORAGE_REPORT_DIRECTORY/source-before.sha256")"; digest="${digest%% *}"
  destination="$cache/source-$digest.tar.gz"
  if [ ! -e "$destination" ]; then
    temporary="$destination.$CANARY.partial"
    (cd "$REPO_ROOT" && national_source_paths | LC_ALL=C sort -zu |
      LC_ALL=C comm -z -23 - <(LC_ALL=C sort -zu "$BABYLON_STORAGE_REPORT_DIRECTORY/input-paths.nul") |
      tar -czf "$temporary" --null -T -)
    mv -- "$temporary" "$destination"
    sha256sum "$destination" > "$destination.sha256"
  fi
  [ -f "$destination.sha256" ] || die "existing reproducibility capsule lacks an ownership checksum"
  sha256sum --check "$destination.sha256"
  sha256sum "$destination" > "$BABYLON_STORAGE_REPORT_DIRECTORY/source-archive.sha256"
  stat -c '%s' "$destination" > "$BABYLON_STORAGE_REPORT_DIRECTORY/source-archive-bytes"
  # Detect edits racing the capsule read; refuse before any service starts.
  national_source_manifest > "$BABYLON_STORAGE_REPORT_DIRECTORY/source-captured.sha256"
  cmp -- "$BABYLON_STORAGE_REPORT_DIRECTORY/source-before.sha256" "$BABYLON_STORAGE_REPORT_DIRECTORY/source-captured.sha256"
}

# Revalidate the original capture. Never regenerate the frozen run inputs while
# admitting results: source edits must refuse instead of replacing the baseline.
national_verify_source_capture() {
  [ -s "$BABYLON_STORAGE_REPORT_DIRECTORY/source-before.sha256" ] || return 1
  cmp -s -- "$BABYLON_STORAGE_REPORT_DIRECTORY/source-before.sha256" \
    <(national_source_manifest) || return 1
  (cd "$REPO_ROOT" && sha256sum --check --status "$BABYLON_STORAGE_REPORT_DIRECTORY/inputs.sha256") || return 1
  sha256sum --check --status "$BABYLON_STORAGE_REPORT_DIRECTORY/source-archive.sha256" || return 1
  sha256sum --check --status "$BABYLON_STORAGE_REPORT_DIRECTORY/input-archive.sha256" || return 1
}


national_measure() {
  (cd "$BABYLON_STORAGE_REPORT_DIRECTORY" && sha256sum --check operator.sha256) || return 1
  local periods tick stage routine_periods
  periods="$(national_period_count)" || return 1
  routine_periods="$(mise exec -- uv run --frozen python -c '
import json,sys
with open(sys.argv[1]) as stream:
    policy=json.load(stream)
value=policy["routine_smoke_periods"]
if type(value) is not int or not 0 < value <= 9223372036854775807:
    raise ValueError("invalid captured routine smoke periods")
print(value)
' "$BABYLON_STORAGE_REPORT_DIRECTORY/policy.json")" || return 1
  local -a ticks=() reopens=() timing_flags=() gameplay=() playable_flags=() progress=() storage_flags=()
  local storage_mode storage_flag
  storage_mode="$(cat "$BABYLON_STORAGE_REPORT_DIRECTORY/storage-qualification-mode")" || return 1
  [ "$storage_mode" = "$NATIONAL_STORAGE_QUALIFICATION" ] || return 1
  storage_flag="$(national_storage_qualification_flags "$storage_mode")" || return 1
  if [ -n "$storage_flag" ]; then
    storage_flags+=("$storage_flag")
  fi
  if [ "$BABYLON_NATIONAL_CAPTURE_MODE" = playable-aid ]; then
    for stage in national-capture-mode.json national-playable-qualification.json reader-role observer-role; do
      [ -s "$BABYLON_STORAGE_REPORT_DIRECTORY/$stage" ] || return 1
      gameplay+=("$BABYLON_STORAGE_REPORT_DIRECTORY/$stage")
    done
    playable_flags+=(--playable-report "$BABYLON_STORAGE_REPORT_DIRECTORY/national-playable-qualification.json")
    # The two-period smoke retains every finite accounting proof. Both positive
    # practices need separate periods under the actual shared commitment, and
    # remain required by the longer material-playable admission.
    if [ "$periods" -gt "$routine_periods" ]; then
      playable_flags+=(--qualify-playable)
    fi
    while IFS= read -r -d '' stage; do
      progress+=("$stage")
    done < <(find "$BABYLON_STORAGE_REPORT_DIRECTORY" -maxdepth 1 -type f -name 'progress-[0-9][0-9][0-9]-*.json' -print0 | LC_ALL=C sort -z)
    [ -s "$BABYLON_STORAGE_REPORT_DIRECTORY/progress-000-starting.json" ] || return 1
    local boundary
    for ((tick=1; tick<=periods; tick++)); do
      for boundary in committed archive accounting production reopened; do
        printf -v stage 'progress-%03d-%s.json' "$tick" "$boundary"
        [ -s "$BABYLON_STORAGE_REPORT_DIRECTORY/$stage" ] || return 1
      done
    done
  fi
  # Derive enforcement only from the already authenticated frozen policy and
  # exact native period request. Other horizons remain independent evidence.
  if [ "$periods" = "$routine_periods" ]; then
    timing_flags+=(--qualify-smoke)
  fi
  [ "$(cat "$BABYLON_STORAGE_REPORT_DIRECTORY/timing-qualification-mode")" = "$NATIONAL_QUALIFY_TIMING" ] || return 1
  if [ "$NATIONAL_QUALIFY_TIMING" = 1 ]; then
    timing_flags+=(--qualify-timing)
  fi
  for ((tick=1; tick<=periods; tick++)); do
    printf -v stage 'tick-%02d' "$tick"
    ticks+=("$BABYLON_STORAGE_REPORT_DIRECTORY/$stage.json")
    reopens+=("$BABYLON_STORAGE_REPORT_DIRECTORY/$stage-reopened.json")
  done
  local -a memory_flags=() memory_files=()
  if [ -e "$BABYLON_STORAGE_REPORT_DIRECTORY/combined-memory.json" ]; then
    local artifact
    for artifact in combined-memory.json combined-memory-source.sha256 combined-memory-executables.json combined-memory-sampler-source.py combined-memory-tooling.json ownership; do
      [ -s "$BABYLON_STORAGE_REPORT_DIRECTORY/$artifact" ] &&
        [ ! -L "$BABYLON_STORAGE_REPORT_DIRECTORY/$artifact" ] || return 1
      memory_files+=("$BABYLON_STORAGE_REPORT_DIRECTORY/$artifact")
    done
    memory_flags+=(--combined-memory-report "$BABYLON_STORAGE_REPORT_DIRECTORY/combined-memory.json")
  fi
  local -a native_flags=() native_files=() evaluator_command=()
  local native_report="$BABYLON_STORAGE_REPORT_DIRECTORY/native-window-evidence.json"
  evaluator_command=(python "$BABYLON_STORAGE_REPORT_DIRECTORY/national_storage_qualification.py")
  if [ -e "$native_report" ] || [ -L "$native_report" ]; then
    [ "$BABYLON_NATIONAL_CAPTURE_MODE" = playable-aid ] &&
      [ "${#memory_files[@]}" -gt 0 ] || return 1
    # The native evidence models import the canonical typed reader contracts.
    # Execute that same frozen evaluator in the project module context; verify
    # both its captured bytes and complete source closure before/after reads.
    cmp -- "$REPO_ROOT/tools/devtools/national_storage_qualification.py" \
      "$BABYLON_STORAGE_REPORT_DIRECTORY/national_storage_qualification.py" || return 1
    national_verify_source_capture || return 1
    local native_names artifact
    native_names="$(cd "$REPO_ROOT" && mise exec -- uv run --frozen python - "$native_report" <<'PY_NATIVE_ROSTER'
import sys
from pathlib import Path
from tools.devtools.national_native_evidence import MANIFEST_BYTES,NativeRunEvidence,private_bytes
from tools.devtools.national_storage_qualification import strict_json_bytes
evidence=NativeRunEvidence.model_validate(strict_json_bytes(private_bytes(Path(sys.argv[1]),MANIFEST_BYTES)))
for artifact in (evidence.controls,evidence.opening,*evidence.boundaries,*evidence.advances,*evidence.archives,*evidence.recoveries,*evidence.aid_originals):
    print(artifact.name)
PY_NATIVE_ROSTER
    )" || return 1
    native_files+=("$native_report")
    while IFS= read -r artifact; do
      [ -n "$artifact" ] && [ -s "$BABYLON_STORAGE_REPORT_DIRECTORY/$artifact" ] &&
        [ ! -L "$BABYLON_STORAGE_REPORT_DIRECTORY/$artifact" ] || return 1
      native_files+=("$BABYLON_STORAGE_REPORT_DIRECTORY/$artifact")
    done <<< "$native_names"
    native_flags+=(--native-report "$native_report" --qualify-native)
    evaluator_command=(python -c 'from tools.devtools.national_storage_qualification import main; raise SystemExit(main())')
  fi
  local evidence_manifest="$BABYLON_STORAGE_REPORT_DIRECTORY/evaluated-evidence.sha256"
  [ ! -e "$evidence_manifest" ] && [ ! -e "$evidence_manifest.partial" ] || return 1
  # Authenticate the exact inputs before evaluation, then prove they did not
  # change while the evaluator read them. No source-policy re-read occurs.
  sha256sum "$BABYLON_STORAGE_REPORT_DIRECTORY/schema-baseline.json" \
    "$BABYLON_STORAGE_REPORT_DIRECTORY/opening-created.json" \
    "${ticks[@]}" "${reopens[@]}" \
    "$BABYLON_STORAGE_REPORT_DIRECTORY/native-timings.json" "${gameplay[@]}" "${progress[@]}" "${memory_files[@]}" "${native_files[@]}" \
    > "$evidence_manifest.partial" || return 1
  # Matching routine runs enforce the separate smoke contract; explicit full
  # timing qualification remains independent. Explicit storage/save modes also
  # enforce their horizons; report-only runs do not claim acceptance. Refusal
  # retains the game.
  mise exec -- uv run --frozen "${evaluator_command[@]}" \
    --policy "$BABYLON_STORAGE_REPORT_DIRECTORY/policy.json" \
    --baseline "$BABYLON_STORAGE_REPORT_DIRECTORY/schema-baseline.json" \
    --opening "$BABYLON_STORAGE_REPORT_DIRECTORY/opening-created.json" \
    --ticks "${ticks[@]}" --reopens "${reopens[@]}" \
    --timings "$BABYLON_STORAGE_REPORT_DIRECTORY/native-timings.json" "${timing_flags[@]}" "${storage_flags[@]}" "${playable_flags[@]}" "${memory_flags[@]}" "${native_flags[@]}" \
    > "$BABYLON_STORAGE_REPORT_DIRECTORY/qualification.json.partial" || return 1
  sha256sum --check "$evidence_manifest.partial" || return 1
  if [ "${#native_flags[@]}" -gt 0 ]; then national_verify_source_capture || return 1; fi
  (cd "$BABYLON_STORAGE_REPORT_DIRECTORY" && sha256sum --check operator.sha256) || return 1
  mv -- "$BABYLON_STORAGE_REPORT_DIRECTORY/qualification.json.partial" "$BABYLON_STORAGE_REPORT_DIRECTORY/qualification.json"
  mise exec -- uv run --frozen python -c \
    'import json,sys; print("National storage measurement status=" + json.load(open(sys.argv[1]))["status"] + "; native test success alone is not storage acceptance")' \
    "$BABYLON_STORAGE_REPORT_DIRECTORY/qualification.json" || return 1
  sha256sum "$BABYLON_STORAGE_REPORT_DIRECTORY/qualification.json" >> "$evidence_manifest.partial" || return 1
  mv -- "$evidence_manifest.partial" "$evidence_manifest" || return 1
  sha256sum --check "$evidence_manifest" || return 1
}

# Failure evidence contains only stage names and hashes, never lease/DSN contents.
# Publish once atomically; an earlier proof or failure record is never replaced.
national_failure_summary() {
  [ -d "${BABYLON_STORAGE_REPORT_DIRECTORY:-/nonexistent}" ] || return 0
  local summary="$BABYLON_STORAGE_REPORT_DIRECTORY/failure-summary.json"
  [ ! -e "$summary" ] || return 0
  python3 - "$BABYLON_STORAGE_REPORT_DIRECTORY" "${1:-1}" <<'PY_FAILURE'
import hashlib,json,os,re,sys,tempfile
from pathlib import Path
root=Path(sys.argv[1])
try:
    status=int(sys.argv[2])
    records=[]
    for path in sorted(root.iterdir()):
        if path.is_file() and (re.fullmatch(r"progress-[0-9]{3}-[a-z-]+\.json",path.name)
            or re.fullmatch(r"(?:tick-[0-9]+(?:-reopened)?|schema-baseline|opening-created|native-timings|national-playable-qualification|qualification|native-window-evidence|native-controls|material-[0-9]+|advance-[0-9]+|recovery-[0-9]+-[0-9]+|aid-[0-9a-f]{64}|combined-memory(?:-progress)?)\.json(?:\.partial)?",path.name)):
            records.append({"file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"bytes":path.stat().st_size})
    progress=[record["file"] for record in records if record["file"].startswith("progress-")]
    # Modification time orders stages within the same tick without reading payloads.
    latest=max(progress,key=lambda name:(root/name).stat().st_mtime_ns) if progress else None
    result={"status":"failure-retained","exit_code":status,"latest_progress":latest,"files":records}
    fd,temporary=tempfile.mkstemp(prefix=".failure-summary-",dir=root)
    try:
        with os.fdopen(fd,"w") as stream:
            json.dump(result,stream,sort_keys=True);stream.write("\n")
        os.link(temporary,root/"failure-summary.json")
    finally:
        os.unlink(temporary)
except (OSError,ValueError):
    raise SystemExit("National failure summary could not be published") from None
PY_FAILURE
}


# Success retention authenticates every cleanup prerequisite without freezing or
# deleting the game. The persistent active record still refuses any second game.
national_retain_success() {
  [[ "${NATIONAL_DATABASE_OID:-}" =~ ^[1-9][0-9]*$ ]] || return 1
  national_verify_success || return 1
  local receipt="$BABYLON_STORAGE_REPORT_DIRECTORY/native-handoff.json"
  [ ! -e "$receipt" ] && [ ! -L "$receipt" ] || return 1
  mise exec -- uv run --frozen python - "$BABYLON_STORAGE_REPORT_DIRECTORY" <<'PY_RECEIPT'
import hashlib,json,os,sys
from pathlib import Path
from datetime import datetime,timezone
root=Path(sys.argv[1])
qualification=json.loads((root/'qualification.json').read_bytes())
policy=json.loads((root/'policy.json').read_bytes())
timing=json.loads((root/'native-timings.json').read_bytes())
periods=timing['run']['periods']
if type(periods) is not int or periods <= 0 or qualification['status'] not in {'qualified','incomplete'}:
    raise SystemExit('native retention refuses failed evidence')
scope=('routine-smoke' if periods == policy['routine_smoke_periods'] else
       'qualification-horizon' if periods >= policy['qualification_ticks'] else 'bounded-measurement')
terminal=f'tick-{periods:02d}-reopened.json'
files=['qualification.json','native-timings.json','evaluated-evidence.sha256','policy.json','campaign',terminal]
reopened=json.loads((root/terminal).read_bytes())
receipt={'version':1,'status':'success-retained-for-native','scope':scope,
 'qualification_status':qualification['status'],'periods':periods,
 'terminal_markers':reopened['acknowledged_markers'],
 'campaign':(root/'campaign').read_text().strip(),
 'recorded_at':datetime.now(timezone.utc).isoformat(),
 'evidence_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files}}
partial=root/'native-handoff.json.partial'
with partial.open('x') as output:
    json.dump(receipt,output,sort_keys=True); output.write('\n')
os.replace(partial,root/'native-handoff.json')
PY_RECEIPT
}

# An explicit existing-campaign Open acquires the same supervisor-owned lock.
# No caller command is accepted; this dispatch invokes only the native launcher.
national_native_open() {
  local directory descriptor identity campaign
  if [ "$#" = 2 ] && [ "$1" = --national-native-open ]; then
    campaign="$2"
    [[ "$campaign" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] ||
      die "canonical existing campaign required"
    directory="$(national_control_directory)" || return 1
    [ -f "$directory/active" ] && [ ! -L "$directory/active" ] || die "retained existing campaign required"
    exec flock --nonblock --close --conflict-exit-code 75 "$directory/runner.lock"       bash "$REPO_ROOT/tools/run_rust_postgres.sh" --national-native-lock-held "$$" "$campaign"
  fi
  [ "$#" = 3 ] && [ "$1" = --national-native-lock-held ] && [ "$2" = "$PPID" ] || die "invalid native lock invocation"
  [ "$(cat "/proc/$PPID/comm")" = flock ] || die "native lock supervisor is not flock"
  campaign="$3"
  directory="$(national_control_directory)" || return 1
  identity="$(stat -Lc '%d:%i' "$directory/runner.lock")" || return 1
  local locked=0
  for descriptor in /proc/"$PPID"/fd/*; do
    [ "$(stat -Lc '%d:%i' "$descriptor" 2>/dev/null || true)" != "$identity" ] || locked=1
  done
  [ "$locked" = 1 ] || die "native supervisor lacks exact lock inode"
  NATIONAL_RECORD="$directory/active"
  [ -f "$NATIONAL_RECORD" ] && [ ! -L "$NATIONAL_RECORD" ] &&
    [ "$(stat -c '%a' "$NATIONAL_RECORD")" = 600 ] || die "private retained ownership required"
  local -a record
  mapfile -t record < "$NATIONAL_RECORD"
  [ "${#record[@]}" = 11 ] && [ "${record[0]}" = national-storage-runner-v1 ] &&
    [ "${record[1]}" = "$REPO_ROOT" ] || die "retained ownership scope mismatch"
  CANARY="${record[2]}"; CONTAINER="${record[3]}"; CONTAINER_ID="${record[4]}"
  VOLUME="${record[5]}"; IMAGE_ID="${record[6]}"; NATIONAL_DATABASE="${record[7]}"
  NATIONAL_WRITER="${record[8]}"; NATIONAL_DATABASE_OID="${record[9]}"
  BABYLON_STORAGE_REPORT_DIRECTORY="${record[10]}"
  [[ "$CANARY" =~ ^[0-9a-f]{32}$ ]] && [[ "$CONTAINER_ID" =~ ^[0-9a-f]{64}$ ]] &&
    [[ "$IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ ]] &&
    [ "$CONTAINER" = "babylon-runtime-pg-${CANARY:0:12}" ] &&
    [ "$NATIONAL_DATABASE" = "national_${CANARY:0:12}" ] &&
    [ "$NATIONAL_WRITER" = "national_writer_${CANARY:0:12}" ] &&
    [[ "$NATIONAL_DATABASE_OID" =~ ^[1-9][0-9]*$ ]] &&
    [[ "$BABYLON_STORAGE_REPORT_DIRECTORY" = /* ]] || die "retained identity malformed"
  [ "$(cat "$BABYLON_STORAGE_REPORT_DIRECTORY/campaign")" = "$campaign" ] || die "existing campaign differs from retained evidence"
  [ "$(cat "$BABYLON_STORAGE_REPORT_DIRECTORY/capture-mode")" = playable-aid ] || die "retained campaign is not playable"
  [ -f "$BABYLON_STORAGE_REPORT_DIRECTORY/native-handoff.json" ] &&
    [ ! -L "$BABYLON_STORAGE_REPORT_DIRECTORY/native-handoff.json" ] || die "successful retention receipt required"
  export BABYLON_STORAGE_REPORT_DIRECTORY
  # Reuse captured policy for the same explicit period request, never a new default.
  BABYLON_NATIONAL_STORAGE_PERIODS="$(mise exec -- uv run --frozen python - "$BABYLON_STORAGE_REPORT_DIRECTORY/native-timings.json" <<'PY_PERIODS'
import json,sys
periods=json.load(open(sys.argv[1]))['run']['periods']
if type(periods) is not int or periods <= 0:
    raise SystemExit('retained period count refused')
print(periods)
PY_PERIODS
  )" || return 1
  export BABYLON_NATIONAL_STORAGE_PERIODS
  national_verify_success || die "retained ownership/evidence refused; game preserved"
  local endpoint
  endpoint="$(docker port "$CONTAINER_ID" 5432/tcp)" || return 1
  [[ "$endpoint" =~ ^127\.0\.0\.1:([0-9]+)$ ]] || die "retained port must be exact loopback"
  PORT="${BASH_REMATCH[1]}"
  export BABYLON_RUNTIME_DSN="postgresql://$NATIONAL_WRITER:$CANARY@127.0.0.1:$PORT/$NATIONAL_DATABASE"
  export BABYLON_OBSERVER_DSN="postgresql://national_observer_${CANARY:0:12}:$CANARY@127.0.0.1:$PORT/$NATIONAL_DATABASE"
  export BABYLON_READER_DSN="postgresql://national_reader_${CANARY:0:12}:$CANARY@127.0.0.1:$PORT/$NATIONAL_DATABASE"
  mise exec -- uv run --frozen python - "$BABYLON_STORAGE_REPORT_DIRECTORY" "$campaign" <<'PY_VERIFY' || return 1
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]); receipt=json.loads((root/'native-handoff.json').read_bytes())
periods=json.loads((root/'native-timings.json').read_bytes())['run']['periods']
expected={'qualification.json','native-timings.json','evaluated-evidence.sha256','policy.json','campaign',f'tick-{periods:02d}-reopened.json'}
if receipt['version'] != 1 or receipt['periods'] != periods or receipt['status'] != 'success-retained-for-native' or receipt['campaign'] != sys.argv[2]:
    raise SystemExit('retained receipt scope mismatch')
for name,digest in receipt['evidence_sha256'].items():
    if name not in expected or hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
        raise SystemExit('retained receipt evidence mismatch')
if set(receipt['evidence_sha256']) != expected:
    raise SystemExit('retained receipt evidence incomplete')
PY_VERIFY
  # Root supplies the exact combined-source admission before any live handoff.
  local manifest
  for manifest in native-combined-source.sha256 native-executables.sha256; do
    [ -s "$BABYLON_STORAGE_REPORT_DIRECTORY/$manifest" ] &&
      [ ! -L "$BABYLON_STORAGE_REPORT_DIRECTORY/$manifest" ] || die "native build admission manifest required"
  done
  (cd "$REPO_ROOT" && sha256sum --check --status "$BABYLON_STORAGE_REPORT_DIRECTORY/native-combined-source.sha256") ||
    die "native combined source admission refused"
  # Record stays active after native exit; another Open rechecks zero sessions.
  mise exec -- uv run --frozen python - "$REPO_ROOT" "$campaign" <<'PY_OPEN'
import hashlib,importlib.util,os,re,sys
from pathlib import Path
from uuid import UUID
root=Path(sys.argv[1])
spec=importlib.util.spec_from_file_location('national_native_launcher',root/'tools/run_observer_session.py')
launcher=importlib.util.module_from_spec(spec); sys.modules[spec.name]=launcher; spec.loader.exec_module(launcher)
environment=dict(os.environ)
target=Path(environment.get('CARGO_TARGET_DIR','target'))
if not target.is_absolute(): target=root/'rust'/target
runtime=target/'debug/babylon-runtime'; client=target/'debug/babylon-client'
if not runtime.is_file() or not client.is_file():
    raise SystemExit('existing native binaries required; build separately')
expected={str(runtime.resolve()),str(client.resolve())}
rows={}
for line in (Path(environment['BABYLON_STORAGE_REPORT_DIRECTORY'])/'native-executables.sha256').read_text().splitlines():
    match=re.fullmatch(r'([0-9a-f]{64})  (/.+)',line)
    if match is None or match[2] in rows: raise SystemExit('native executable manifest refused')
    rows[match[2]]=match[1]
if set(rows) != expected: raise SystemExit('native executable manifest scope refused')
for name,digest in rows.items():
    if hashlib.file_digest(open(name,'rb'),'sha256').hexdigest()!=digest:
        raise SystemExit('native executable admission refused')
credentials=launcher.ReaderCredentials(environment['BABYLON_OBSERVER_DSN'],environment['BABYLON_READER_DSN'])
writer,reader=launcher.child_environments(environment,credentials)
raise SystemExit(launcher.run_pair(runtime,client,root,writer,reader,
    defines_path=launcher.DEFAULT_DEFINES,initial_target=launcher.OpenCampaignTarget(UUID(sys.argv[2]))))
PY_OPEN
}
