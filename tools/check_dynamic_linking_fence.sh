#!/bin/sh
# R1.4 fence, workflow-visible half (Director ruling 2026-08-18, BSL
# refactor program plan §14: "bevy/dynamic_linking — RULED: APPROVED WITH
# FENCE"). bevy's dynamic_linking feature is an OPT-IN, LOCAL-ITERATION-ONLY
# convenience for babylon-client (`mise run rust:client-dev-dylib`) — faster
# incremental Bevy rebuilds via libbevy_dylib.so. It must NEVER ride a CI,
# release, or pin-ceremony build: the .so is not meant to ship, and every
# gate build must prove the ordinary (statically-linked, default-features)
# path. This script is the static/textual half of the fence; rust/crates/
# babylon-client/tests/dynamic_linking_fence.rs is the compiled half
# (asserts the feature is off in whatever build ran the test suite).
#
# Matches ACTIVATION syntax only (`--features ... dynamic_linking` /
# `--all-features`), never the bare word — this file, ci.yml's own step
# name, and every task description below are free to keep SAYING
# "dynamic_linking" in prose without tripping the gate; only something that
# would actually turn the feature ON does.
#
# Checks, offline and in-repo:
#   1. No GitHub Actions workflow ever activates dynamic_linking (an
#      explicit `--features ... dynamic_linking` or a blanket
#      `--all-features`) — a workflow IS a CI/release/pin-ceremony build.
#   2. .mise.toml activates dynamic_linking ONLY inside the sanctioned
#      local-dev task's own `run` line (rust:client-dev-dylib) — any other
#      task's `run` doing so (rust:check included) is a leak into the gate.
#   3. No rust/**/Cargo.toml lists dynamic_linking inside a `default = [...]`
#      features array — default-on would silently activate it for every
#      plain `cargo build`/`test`, including CI's.
# Exit 0 clean / 1 violation found / 2 error.
set -eu

# POSIX ERE: a --features flag (possibly with other feature names first)
# whose feature list contains dynamic_linking, or a blanket --all-features.
ACTIVATION_RE='--features[^"'"'"']*dynamic_linking|--all-features'

FAIL=0

# --- 1. workflows: no step may actually turn the feature on ---
hits=$(grep -rnE -- "$ACTIVATION_RE" .github/workflows/ 2>/dev/null || true)
if [ -n "$hits" ]; then
    echo "check_dynamic_linking_fence: REFUSE — a GitHub Actions workflow activates dynamic_linking:" >&2
    printf '%s\n' "$hits" >&2
    FAIL=1
fi

# --- 2. .mise.toml: only the sanctioned task's run line may activate it ---
[ -f .mise.toml ] || { echo "check_dynamic_linking_fence: FATAL no .mise.toml" >&2; exit 2; }
SANCTIONED_HEADER='[tasks."rust:client-dev-dylib"]'
all_activations=$(grep -nE -- "$ACTIVATION_RE" .mise.toml || true)
if [ -n "$all_activations" ]; then
    sanctioned_line=$(awk -v start="$SANCTIONED_HEADER" '
        $0 == start { inblock=1; next }
        inblock && /^\[tasks\./ { exit }
        inblock && /^run[[:space:]]*=/ { print NR; exit }
    ' .mise.toml)
    leaked=$(printf '%s\n' "$all_activations" | awk -F: -v ok="${sanctioned_line:-0}" '$1 != ok')
    if [ -n "$leaked" ]; then
        echo "check_dynamic_linking_fence: REFUSE — .mise.toml activates dynamic_linking outside the sanctioned rust:client-dev-dylib task's run line:" >&2
        printf '%s\n' "$leaked" >&2
        FAIL=1
    fi
fi

# --- 3. no Cargo.toml makes dynamic_linking a DEFAULT feature ---
default_hits=$(grep -rn '^default[[:space:]]*=.*dynamic_linking' rust --include="Cargo.toml" 2>/dev/null || true)
if [ -n "$default_hits" ]; then
    echo "check_dynamic_linking_fence: REFUSE — dynamic_linking is a DEFAULT feature (activates on every plain cargo build/test):" >&2
    printf '%s\n' "$default_hits" >&2
    FAIL=1
fi

if [ "$FAIL" -ne 0 ]; then
    exit 1
fi

printf 'check_dynamic_linking_fence: OK — dynamic_linking activation confined to rust:client-dev-dylib, absent from every workflow, never a default feature.\n'
exit 0
