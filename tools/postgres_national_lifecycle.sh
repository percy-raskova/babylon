#!/usr/bin/env bash
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
  NATIONAL_POLICY_SOURCE="${BABYLON_STORAGE_POLICY_PATH:-$REPO_ROOT/contracts/national_storage_qualification_v2.json}"
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

national_verify_disposable() {
  local identity inventory sessions
  [ -f "$NATIONAL_RECORD" ] && [ ! -L "$NATIONAL_RECORD" ] || return 1
  [ "$(stat -c '%a' "$NATIONAL_RECORD")" = 600 ] || return 1
  cmp -s -- "$NATIONAL_RECORD" <(national_record_contents) || return 1
  identity="$(docker inspect --format '{{.Id}}|{{.Image}}|{{index .Config.Labels "babylon.disposable_runtime"}}|{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' "$CONTAINER_ID")" || return 1
  [ "$identity" = "$CONTAINER_ID|$IMAGE_ID|$CANARY|$VOLUME" ] || return 1
  [ "$(national_sql "SELECT current_setting('babylon.disposable_runtime',true);")" = "$CANARY" ] || return 1
  inventory="$(national_sql "SELECT string_agg(datname,',' ORDER BY datname COLLATE \"C\") FROM pg_catalog.pg_database;")" || return 1
  [ "$inventory" = "babylon_test,$NATIONAL_DATABASE,postgres,template0,template1" ] || return 1
  if [ -n "$NATIONAL_DATABASE_OID" ]; then
    [ "$(national_sql "SELECT oid FROM pg_catalog.pg_database WHERE datname='$NATIONAL_DATABASE' AND datdba=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname='$NATIONAL_WRITER');")" = "$NATIONAL_DATABASE_OID" ] || return 1
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
  printf '%s\n' "$identity" "$inventory" > "$BABYLON_STORAGE_REPORT_DIRECTORY/cleanup-proof"
}

# Hash filesystem files, not Git's index: current untracked codecs participate.
national_source_paths() {
  local crate dependency
  for crate in babylon-persistence babylon-tick babylon-material-circuit babylon-bsl babylon-graph babylon-kernel babylon-practice-contract; do
    # This is the measured target's complete current local dependency closure.
    # A new local dependency requires an explicit roster update, never omission.
    while IFS= read -r dependency; do
      case "$dependency" in
        babylon-persistence | babylon-tick | babylon-material-circuit | babylon-bsl | babylon-graph | babylon-kernel | babylon-practice-contract) ;;
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
  printf '%s\0' tools/run_rust_postgres.sh tools/postgres_national_lifecycle.sh tools/devtools/national_storage_qualification.py tools/devtools/national_storage_snapshot.py tools/devtools/national_storage_relations.sql
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
    playable_flags+=(--playable-report "$BABYLON_STORAGE_REPORT_DIRECTORY/national-playable-qualification.json" --qualify-playable)
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
  local evidence_manifest="$BABYLON_STORAGE_REPORT_DIRECTORY/evaluated-evidence.sha256"
  [ ! -e "$evidence_manifest" ] && [ ! -e "$evidence_manifest.partial" ] || return 1
  # Authenticate the exact inputs before evaluation, then prove they did not
  # change while the evaluator read them. No source-policy re-read occurs.
  sha256sum "$BABYLON_STORAGE_REPORT_DIRECTORY/schema-baseline.json" \
    "$BABYLON_STORAGE_REPORT_DIRECTORY/opening-created.json" \
    "${ticks[@]}" "${reopens[@]}" \
    "$BABYLON_STORAGE_REPORT_DIRECTORY/native-timings.json" "${gameplay[@]}" "${progress[@]}" \
    > "$evidence_manifest.partial" || return 1
  # Matching routine runs enforce the separate smoke contract; explicit full
  # timing qualification remains independent. Explicit storage/save modes also
  # enforce their horizons; report-only runs do not claim acceptance. Refusal
  # retains the game.
  mise exec -- uv run --frozen python "$BABYLON_STORAGE_REPORT_DIRECTORY/national_storage_qualification.py" \
    --policy "$BABYLON_STORAGE_REPORT_DIRECTORY/policy.json" \
    --baseline "$BABYLON_STORAGE_REPORT_DIRECTORY/schema-baseline.json" \
    --opening "$BABYLON_STORAGE_REPORT_DIRECTORY/opening-created.json" \
    --ticks "${ticks[@]}" --reopens "${reopens[@]}" \
    --timings "$BABYLON_STORAGE_REPORT_DIRECTORY/native-timings.json" "${timing_flags[@]}" "${storage_flags[@]}" "${playable_flags[@]}" \
    > "$BABYLON_STORAGE_REPORT_DIRECTORY/qualification.json.partial" || return 1
  sha256sum --check "$evidence_manifest.partial" || return 1
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
            or re.fullmatch(r"(?:tick-[0-9]+(?:-reopened)?|schema-baseline|opening-created|native-timings|national-playable-qualification|qualification)\.json(?:\.partial)?",path.name)):
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
