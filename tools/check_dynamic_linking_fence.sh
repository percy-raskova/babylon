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
# would actually turn the feature ON does. Verified quote-blind forms fixed
# 2026-08-18 (reviewer-verified gap, task-fix1-report.md): the ACTIVATION_RE
# character class now covers every form below, not just the bare-unquoted
# one —
#   --features dynamic_linking
#   --features "dynamic_linking"          (double-quoted)
#   --features 'dynamic_linking'          (single-quoted)
#   --features "foo,dynamic_linking"      (quoted comma-list, feature not first)
#   --features 'foo,dynamic_linking'
#   --features=dynamic_linking            (= form, no space)
#   --features="dynamic_linking"          (= form, quoted)
#   --features foo --features dynamic_linking   (repeated flag; grep finds
#       a match starting at the SECOND --features even when the first
#       flag's argument doesn't contain dynamic_linking)
#   --all-features                        (any quoting; takes no argument)
# still never the bare word alone with neither --features nor
# --all-features anywhere on the line.
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

# POSIX ERE: a --features flag (possibly with other feature names first,
# `=`-joined or space-joined, quoted with " or ' or not quoted at all, or
# TOML-double-escaped as \" inside a .mise.toml basic string — this repo's
# own .mise.toml already has that convention live, e.g. its
# soundtrack/db:sql tasks' `run = "... \"...\" ..."` lines) whose feature
# list contains dynamic_linking, or a blanket --all-features. The character
# class is an ALLOWLIST of characters a Cargo feature-list argument (plus
# its surrounding shell/TOML quoting) actually uses — letters/digits/
# underscore/comma/period/quotes/equals/whitespace/backslash — it
# deliberately excludes `-`, so the wildcard can't leap across an unrelated
# `--flag` boundary into a later, disconnected mention of the word (keeping
# the bare-word non-match property this file's header describes) while
# still matching within one flag's own argument, including a REPEATED
# --features flag later on the same line (grep finds a match starting at
# that occurrence even when an earlier --features doesn't itself contain
# dynamic_linking). The POSIX [:space:] class must come before the literal
# `\` in the bracket expression — GNU grep parses a leading bare `\[` as
# the start of a (malformed) nested class instead of two literal chars;
# ordering it last avoids that parse trap (verified directly against
# /usr/bin/grep, not the interactive shell's grep-as-ugrep wrapper).
ACTIVATION_RE='--features[A-Za-z0-9_,."'"'"'=[:space:]\]*dynamic_linking|--all-features'

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
# A crate's [features] `default = [...]` array can span multiple lines
# (this workspace already has multi-line-array precedent: rust/Cargo.toml's
# own [workspace] `members = [` list) — a same-line-only regex would miss
# a `default = [` / `"dynamic_linking",` / `]` split across three lines.
# One awk invocation scans every rust/**/Cargo.toml (find -exec ... {} +
# batches all matches into that single call, no shell loop over find
# output needed): FNR==1 resets state per file; infeatures tracks the
# [features] table specifically (default arrays elsewhere are out of
# scope by design); capturing spans from the `default =` line to the line
# holding its closing `]`, same-line or not; only the captured span is
# checked for dynamic_linking — never the bare word anywhere else in the
# file (a crate's own `dynamic_linking = [...]` feature *definition* line
# must never trip this).
default_hits=$(find rust -name 'Cargo.toml' -exec awk '
    FNR == 1 { infeatures = 0; capturing = 0 }
    /^\[features\]/ { infeatures = 1; next }
    /^\[/            { infeatures = 0; capturing = 0 }
    infeatures && !capturing && /^default[[:space:]]*=/ {
        start = FNR
        buf = $0
        if ($0 ~ /\]/) { if (buf ~ /dynamic_linking/) print FILENAME ":" start ": " buf; next }
        capturing = 1
        next
    }
    capturing {
        buf = buf "\n" $0
        if ($0 ~ /\]/) {
            if (buf ~ /dynamic_linking/) print FILENAME ":" start "-" FNR ":\n" buf
            capturing = 0
        }
    }
' {} + 2>/dev/null || true)
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
