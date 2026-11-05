#!/bin/sh
# Hermetic installer contract: no real home, systemd manager, or Cargo process.
set -eu

test_path="$(readlink -f -- "$0")"
host_dir="$(dirname -- "$(dirname -- "$test_path")")"
temporary_root="$(mktemp -d "${TMPDIR:-/tmp}/nnsims-host-install.XXXXXX")"
export HOST_CONTRACT_BUDGET_ROOT="$temporary_root/budget"
trap 'rm -rf -- "$temporary_root"' EXIT HUP INT TERM

fail() {
  echo "host installer contract: $*" >&2
  exit 1
}

fake_bin="$temporary_root/fake-bin"
mkdir -p "$fake_bin"

# Cargo sets CARGO_HOME for test binaries. Make that inherited value
# deliberately wrong so every fixture proves run_installer_from owns it.
inherited_cargo_home="$temporary_root/inherited-cargo-home"
mkdir -p "$inherited_cargo_home/bin"
printf '%s\n' '#!/bin/sh' 'exit 0' >"$inherited_cargo_home/bin/cargo"
chmod 755 "$inherited_cargo_home/bin/cargo"
export CARGO_HOME="$inherited_cargo_home"

printf '%s\n' \
  '#!/bin/sh' \
  'set -eu' \
  'if [ -n "${HOST_INSTALL_CONTRACT_READY:-}" ]; then' \
  '  : >"$HOST_INSTALL_CONTRACT_READY"' \
  '  attempts=0' \
  '  while [ ! -e "$HOST_INSTALL_CONTRACT_RELEASE" ] && [ "$attempts" -lt 500 ]; do' \
  '    attempts=$((attempts + 1))' \
  '    sleep 0.01' \
  '  done' \
  '  [ -e "$HOST_INSTALL_CONTRACT_RELEASE" ] || exit 5' \
  'fi' \
  'if [ -n "${HOST_INSTALL_CONTRACT_DELAY:-}" ]; then' \
  '  sleep "$HOST_INSTALL_CONTRACT_DELAY"' \
  'fi' \
  'exit 0' >"$fake_bin/systemd-analyze"
chmod 755 "$fake_bin/systemd-analyze"

printf '%s\n' \
  '#!/bin/sh' \
  'set -eu' \
  '[ "$1" = --user ] || exit 2' \
  'case "$2" in' \
  '  show-environment|daemon-reload) exit 0 ;;' \
  '  show)' \
  '    unit="$3"' \
  '    property="${4#--property=}"' \
  '    case "$unit:$property" in' \
  '      codex-rust.slice:CPUQuotaPerSecUSec) echo 8s ;;' \
  '      codex-rust.slice:MemoryHigh) echo 21474836480 ;;' \
  '      codex-rust.slice:MemoryMax) echo 25769803776 ;;' \
  '      codex-rust.slice:MemorySwapMax) echo 4294967296 ;;' \
  '      codex-rust.slice:IOWeight) echo 500 ;;' \
  '      codex-rust.slice:TasksMax) echo 1024 ;;' \
  '      codex-rust-nnsims.slice:CPUQuotaPerSecUSec|codex-rust-babylon.slice:CPUQuotaPerSecUSec) echo 4s ;;' \
  '      codex-rust-nnsims.slice:MemoryHigh|codex-rust-babylon.slice:MemoryHigh) echo 10737418240 ;;' \
  '      codex-rust-nnsims.slice:MemoryMax|codex-rust-babylon.slice:MemoryMax) echo 12884901888 ;;' \
  '      codex-rust-nnsims.slice:MemorySwapMax|codex-rust-babylon.slice:MemorySwapMax) echo 2147483648 ;;' \
  '      codex-rust-nnsims.slice:IOWeight|codex-rust-babylon.slice:IOWeight) echo 500 ;;' \
  '      codex-rust-nnsims.slice:TasksMax|codex-rust-babylon.slice:TasksMax) echo 512 ;;' \
  '      *) exit 3 ;;' \
  '    esac' \
  '    ;;' \
  '  *) exit 4 ;;' \
  'esac' >"$fake_bin/systemctl"
chmod 755 "$fake_bin/systemctl"

# No network in these fixtures. Match the immutable release URL and copy bytes
# into curl's requested staging path. A second download is observable.
cat > "$fake_bin/curl" <<'CURL'
#!/bin/sh
set -eu
while [ "$1" != --output ]; do shift; done
[ "$3" = "https://github.com/goldenmonkeyrnd/cargo-worktree-budget/releases/download/v0.1.0/cargo-worktree-budget-x86_64-unknown-linux-gnu" ]
printf 'download\n' >> "$HOME/downloads"
cp -- "$HOST_CONTRACT_BUDGET_ASSET" "$2"
CURL
chmod +x "$fake_bin/curl"

prepare_home() {
  contract_home="$1"
  mkdir -p "$contract_home/.cargo/bin"
  printf '%s\n' '#!/bin/sh' 'exit 0' >"$contract_home/.cargo/bin/cargo"
  chmod 755 "$contract_home/.cargo/bin/cargo"
}

run_installer_from() {
  contract_source="$1"
  contract_home="$2"
  shift 2
  HOME="$contract_home" \
    CARGO_HOME="$contract_home/.cargo" \
    XDG_CONFIG_HOME="$contract_home/.config" \
    XDG_DATA_HOME="$contract_home/.local/share" \
    CODEX_RUST_TOOLS_ROOT="$contract_home/tools" \
    CODEX_RUST_CACHE_ROOT="$contract_home/cache" \
    HOST_INSTALL_CONTRACT_READY="${HOST_INSTALL_CONTRACT_READY:-}" \
    HOST_INSTALL_CONTRACT_RELEASE="${HOST_INSTALL_CONTRACT_RELEASE:-}" \
    HOST_INSTALL_CONTRACT_DELAY="${HOST_INSTALL_CONTRACT_DELAY:-}" \
    PATH="$contract_home/.local/bin:$fake_bin:/usr/bin:/bin" \
    "$contract_source/install.sh" "$@"
}

run_installer() {
  contract_home="$1"
  shift
  run_installer_from "$host_dir" "$contract_home" "$@"
}

# Pinned original v12 installer and installed files from commit 1d8ac15ec2ff.
upgrade_home="$temporary_root/upgrade-v12"
old_host="$temporary_root/old-v12"
prepare_home "$upgrade_home"
mkdir -p "$old_host"
[ "$(sha256sum < "$HOST_CONTRACT_V12" | cut -d' ' -f1)" = 2bd296cdc7e1e190bb8af922d059b659f912f2de2faffbeb51175cba0cd038c6 ] ||
  fail "v12 archive differs from the original release fixture"
tar -xzf "$HOST_CONTRACT_V12" -C "$old_host"
run_installer_from "$old_host" "$upgrade_home" >/dev/null
cp -a "$upgrade_home/.local/share/codex-rust-host/v12" "$temporary_root/snapshot-v12"
run_installer "$upgrade_home" >/dev/null || fail "original v12 could not upgrade"
diff -r "$temporary_root/snapshot-v12" "$upgrade_home/.local/share/codex-rust-host/v12" >/dev/null ||
  fail "upgrade modified installed v12"
[ "$(readlink -f -- "$upgrade_home/.local/bin/cargo")" = "$upgrade_home/.local/share/codex-rust-host/v13/cargo" ] ||
  fail "upgrade did not activate v13"
if run_installer_from "$old_host" "$upgrade_home" >/dev/null 2>&1; then
  fail "v12 repository downgraded the upgraded host"
fi

managed_home="$temporary_root/managed-home"
prepare_home "$managed_home"
run_installer "$managed_home" >/dev/null
run_installer "$managed_home" >/dev/null
run_installer "$managed_home" --check >/dev/null
[ "$(wc -l < "$managed_home/downloads")" -eq 1 ] || fail "healthy binary downloaded more than once"
bad_home="$temporary_root/bad-release"
prepare_home "$bad_home"
bad_asset="$temporary_root/invalid-release"
printf 'corrupt\n' > "$bad_asset"
if HOST_CONTRACT_BUDGET_ASSET="$bad_asset" run_installer "$bad_home" >/dev/null 2>&1; then
  fail "installer accepted corrupt release bytes"
fi
[ ! -e "$bad_home/.local/share/codex-rust-host/highest-policy-version" ] ||
  fail "bad asset activated the new policy"
[ -L "$managed_home/.local/bin/cargo" ] ||
  fail "the first install did not create the PATH shim"
[ -L "$managed_home/.local/share/codex-rust-host/bin/cargo" ] ||
  fail "the first install did not create the dedicated Cargo-only shim"
[ "$(find "$managed_home/.local/share/codex-rust-host/bin" -mindepth 1 -maxdepth 1 -printf '%f\n')" = cargo ] ||
  fail "the dedicated managed shim directory contains more than Cargo"
[ "$(sed -n '1p' "$managed_home/.local/share/codex-rust-host/highest-policy-version")" = 13 ] ||
  fail "the first install did not persist policy v13 as the high-water mark"
[ -d "$managed_home/cache/sccache/nnsims/0.17.0-p2" ] ||
  fail "the NNSims compiler cache was not provisioned"
[ -d "$managed_home/cache/sccache/babylon/0.17.0-p2" ] ||
  fail "the Babylon compiler cache was not provisioned"
printf '%s\n' '# same-version drift' >> \
  "$managed_home/.local/share/codex-rust-host/v13/policy.sh"
if run_installer "$managed_home" >/dev/null 2>&1; then
  fail "the installer overwrote a divergent copy of its own policy version"
fi

unit_drift_home="$temporary_root/unit-drift-home"
prepare_home "$unit_drift_home"
run_installer "$unit_drift_home" >/dev/null
printf '%s\n' '# same-version drift' >> \
  "$unit_drift_home/.config/systemd/user/codex-rust-nnsims.slice"
if run_installer "$unit_drift_home" >/dev/null 2>&1; then
  fail "the installer overwrote a divergent unit from its own policy version"
fi

collision_home="$temporary_root/concurrent-collision-home"
alternate_host="$temporary_root/alternate-host"
prepare_home "$collision_home"
mkdir -p "$alternate_host"
cp -R "$host_dir/." "$alternate_host/"
printf '%s\n' '# divergent same-version repository bundle' >>"$alternate_host/policy.sh"
first_ready="$temporary_root/first-installer-ready"
first_release="$temporary_root/release-first-installer"
HOST_INSTALL_CONTRACT_READY="$first_ready" \
  HOST_INSTALL_CONTRACT_RELEASE="$first_release" \
  run_installer "$collision_home" >/dev/null 2>&1 &
first_installer_pid="$!"
attempts=0
while [ ! -e "$first_ready" ] && [ "$attempts" -lt 500 ]; do
  attempts=$((attempts + 1))
  sleep 0.01
done
[ -e "$first_ready" ] || fail "the first concurrent installer never reached its held validation"
HOST_INSTALL_CONTRACT_DELAY=1 \
  run_installer_from "$alternate_host" "$collision_home" >/dev/null 2>&1 &
second_installer_pid="$!"
sleep 0.1
kill -0 "$second_installer_pid" 2>/dev/null ||
  fail "the concurrent installer did not wait for the host-wide lock"
: >"$first_release"
set +e
wait "$first_installer_pid"
first_installer_status="$?"
wait "$second_installer_pid"
second_installer_status="$?"
set -e
[ "$first_installer_status" -eq 0 ] ||
  fail "the lock-owning installer exited $first_installer_status"
[ "$second_installer_status" -ne 0 ] ||
  fail "two divergent same-version installers both committed host policy"
cmp -s "$host_dir/policy.sh" \
  "$collision_home/.local/share/codex-rust-host/v13/policy.sh" ||
  fail "the refused concurrent installer mixed its policy into the installed bundle"

partial_home="$temporary_root/partial-bundle-home"
prepare_home "$partial_home"
partial_root="$partial_home/.local/share/codex-rust-host/v13"
mkdir -p "$partial_root/real" "$partial_root/systemd"
install -m 755 "$host_dir/cargo" \
  "$partial_root/cargo"
for partial_unit in codex-rust.slice codex-rust-nnsims.slice codex-rust-babylon.slice; do
  install -m 644 "$host_dir/systemd/$partial_unit" "$partial_root/systemd/$partial_unit"
done
ln -s "$partial_home/.cargo/bin/cargo" "$partial_root/real/cargo"
if run_installer "$partial_home" >/dev/null 2>&1; then
  fail "the installer completed a partial same-version policy bundle"
fi
[ ! -e "$partial_home/.local/share/codex-rust-host/highest-policy-version" ] ||
  fail "a partial policy bundle advanced the high-water mark"

downgrade_home="$temporary_root/missing-units-downgrade-home"
prepare_home "$downgrade_home"
run_installer "$downgrade_home" >/dev/null
rm -f -- \
  "$downgrade_home/.config/systemd/user/codex-rust.slice" \
  "$downgrade_home/.config/systemd/user/codex-rust-nnsims.slice" \
  "$downgrade_home/.config/systemd/user/codex-rust-babylon.slice"
if run_installer_from "$old_host" "$downgrade_home" >/dev/null 2>&1; then
  fail "a missing unit set let policy v12 replace the persisted v13 high-water mark"
fi
[ "$(readlink -f -- "$downgrade_home/.local/bin/cargo")" = \
  "$downgrade_home/.local/share/codex-rust-host/v13/cargo" ] ||
  fail "the refused downgrade changed the active Cargo shim"

dedicated_shim_home="$temporary_root/unrelated-dedicated-shim-home"
prepare_home "$dedicated_shim_home"
mkdir -p "$dedicated_shim_home/.local/share/codex-rust-host/bin"
printf '%s\n' '#!/bin/sh' 'exit 0' \
  >"$dedicated_shim_home/.local/share/codex-rust-host/bin/rustc"
chmod 755 "$dedicated_shim_home/.local/share/codex-rust-host/bin/rustc"
if run_installer "$dedicated_shim_home" >/dev/null 2>&1; then
  fail "the installer admitted a non-Cargo binary into the dedicated shim directory"
fi

shim_home="$temporary_root/unrelated-shim-home"
prepare_home "$shim_home"
mkdir -p "$shim_home/.local/bin"
printf '%s\n' '#!/bin/sh' 'exit 0' >"$shim_home/.local/bin/cargo"
chmod 755 "$shim_home/.local/bin/cargo"
if run_installer "$shim_home" >/dev/null 2>&1; then
  fail "the installer overwrote an unrelated Cargo shim"
fi

unit_home="$temporary_root/unrelated-unit-home"
prepare_home "$unit_home"
mkdir -p "$unit_home/.config/systemd/user"
printf '%s\n' '[Slice]' 'MemoryMax=1G' >"$unit_home/.config/systemd/user/codex-rust.slice"
if run_installer "$unit_home" >/dev/null 2>&1; then
  fail "the installer overwrote an unrelated user unit"
fi

# Run the actual Codex setup in a disposable checkout. Only external commands
# (network installers, the system manager, compiler and mise gates) are doubled.
source_root="$PWD"
setup_home="$temporary_root/setup-home"
checkout="$temporary_root/checkout"
prepare_home "$setup_home"
mkdir -p "$checkout/.codex" "$checkout/rust" "$checkout/.codex/environments"
cp -R "$host_dir" "$checkout/.codex/host"
cp "$source_root/.codex/environments/environment.toml" "$checkout/.codex/environments/"
cp "$source_root/.python-version" "$source_root/.env.example" "$checkout/"
cp "$source_root/rust/rust-toolchain.toml" "$checkout/rust/"
git init -q "$checkout"
git -C "$checkout" remote add origin https://github.com/percy-raskova/babylon.git
printf '0::/codex-rust.slice/codex-rust-babylon.slice/fixture.scope\n' > "$temporary_root/cgroup"
sed -i "s|cgroup_membership_file=/proc/self/cgroup|cgroup_membership_file=$temporary_root/cgroup|" "$checkout/.codex/host/cargo"
cat > "$setup_home/.cargo/bin/cargo" <<'CARGO'
#!/bin/sh
set -eu
[ -n "$CARGO_TARGET_DIR" ] && [ -n "$CARGO_BUILD_BUILD_DIR" ] || exit 2
printf '{"target_directory":"%s","build_directory":"%s"}\n' "$CARGO_TARGET_DIR" "$CARGO_BUILD_BUILD_DIR"
CARGO
cat >"$fake_bin/df" <<'DF'
#!/bin/sh
printf 'Filesystem 1024-blocks Used Available Capacity Mounted\nfixture 100000000 0 100000000 0%% /\n'
DF
for tool in rustup mise; do
  printf '%s\n' '#!/bin/sh' 'echo "$0 $*" >> "$HOME/setup-tools"' > "$fake_bin/$tool"
done
chmod +x "$fake_bin/df" "$fake_bin/rustup" "$fake_bin/mise"
setup_tools="$setup_home/tools"
mkdir -p "$setup_tools/sccache/0.17.0/bin"
printf '%s\n' '#!/bin/sh' 'echo sccache 0.17.0' > "$setup_tools/sccache/0.17.0/bin/sccache"
chmod +x "$setup_tools/sccache/0.17.0/bin/sccache"
run_setup() (
  cd "$checkout"
  export HOME="$setup_home" CARGO_HOME="$setup_home/.cargo"
  export XDG_DATA_HOME="$setup_home/.local/share" XDG_CONFIG_HOME="$setup_home/.config"
  export CODEX_WORKTREE_PATH="$checkout" CODEX_RUST_TOOLS_ROOT="$setup_tools"
  export CODEX_RUST_SCOPE_ACTIVE=1 CODEX_RUST_CACHE_ROOT="$setup_home/cache"
  export PATH="$fake_bin:/usr/bin:/bin"
  unset CARGO_TARGET_DIR CARGO_BUILD_TARGET_DIR CARGO_BUILD_BUILD_DIR
  python3 -c 'import tomllib; print(tomllib.load(open(".codex/environments/environment.toml","rb"))["setup"]["linux"]["script"])' |
    bash
)
# A mount nested below an otherwise valid cache root must fail before writing.
# Kernel and CI environments that permit user namespaces run both mount cases.
if unshare --user --map-root-user --mount true 2>/dev/null; then
  mkdir -p "$setup_home/cache/sccache" "$temporary_root/other-cache"
  for kind in bind tmpfs; do
    unshare --user --map-root-user --mount sh -eu -c '
      if [ "$1" = bind ]; then
        mount --bind "$2" "$3/sccache"
      else
        mount -t tmpfs tmpfs "$3/sccache"
      fi
      export CODEX_RUST_CACHE_ROOT="$3" CODEX_RUST_TOOLS_ROOT="$4"
      if "$5/install.sh" --check 2>"$6"; then exit 2; fi
      grep -Fq "requires the mounted" "$6"
      [ ! -e "$3/sccache/babylon" ]
    ' sh "$kind" "$temporary_root/other-cache" "$setup_home/cache" "$setup_tools" "$host_dir" "$temporary_root/mount-error" ||
      fail "installer admitted a $kind submount of its cache root"
  done
fi
run_setup >/dev/null
grep -q 'mise run check:worktree-contract' "$setup_home/setup-tools" || fail "setup skipped the worktree contract"
[ -f "$checkout/.env" ] && [ "$(cat "$setup_home/.local/share/codex-rust-host/highest-policy-version")" = 13 ] ||
  fail "setup did not install v13"
mkdir "$temporary_root/unmounted"
sed -i "s|^CODEX_RUST_BABYLON_MOUNT=.*|CODEX_RUST_BABYLON_MOUNT=$temporary_root/unmounted|" "$checkout/.codex/host/policy.sh"
if run_setup >/dev/null 2>"$temporary_root/setup-error"; then
  fail "setup fell back to the home filesystem without a mounted volume"
fi
grep -Fq "requires the mounted $temporary_root/unmounted volume" "$temporary_root/setup-error" ||
  fail "setup failed to identify the missing mount"

echo "host installer contract: PASS"
