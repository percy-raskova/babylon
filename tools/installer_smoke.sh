#!/usr/bin/env bash
# Installer smoke harness (T7 UNIT I4) — static + dry-run verification of
# install.sh, runnable by a human, by CI (once wired at the T7 merge — not
# yet, see below), and as the fast leg the future fresh-VM test can shell
# out to before paying for a real VM. Everything here is local, network-free,
# and host-harmless: no real Nix install, no real `nix profile install`, no
# docker/VM spun up (that's the outlined-only leg at the bottom of this file).
#
# What this checks, in order:
#   1. bash -n            — install.sh parses as valid shell.
#   2. shellcheck         — install.sh lints clean under the POSIX sh dialect
#                            (resolves shellcheck from PATH, else fetches it
#                            via `nix run nixpkgs#shellcheck` per CLAUDE.md's
#                            documented fallback — no full closure build).
#   3. tests/install/test_install_sh.sh — reused, not reimplemented (DRY):
#                            already covers the placeholder-refusal guard,
#                            --dry-run action lines for the "nix present"
#                            branch, and --uninstall --dry-run. Run as a
#                            subprocess rather than duplicated inline.
#   4. --dry-run, Nix-ABSENT branch — the one dry-run action line
#      tests/install/test_install_sh.sh does NOT exercise (it always stubs
#      nix onto PATH first): with a keyed scratch copy and a PATH that
#      genuinely has no `nix` on it, assert the script prints "Nix is not
#      installed" + the planned curl|sh install line, and does not fail.
#   5. --uninstall --yes consent path — proves `confirm()` auto-consents
#      without a terminal when --yes is given, by actually removing
#      tmp-scoped fake XDG_DATA_HOME/XDG_CONFIG_HOME dirs (not just
#      printing a plan). Deliberately uses --uninstall, not the Nix-bootstrap
#      curl-pipe branch: install.sh's Nix-bootstrap re-exec sources
#      /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh by a
#      hardcoded ABSOLUTE host path (not PATH-based), so it cannot be
#      stubbed without touching real host state or depending on whether
#      this exact box happens to have real Nix at that exact path already
#      — exactly the host-harmlessness this lane must never risk. The
#      --uninstall path exercises the identical confirm()/ASSUME_YES gate
#      with zero host-path coupling.
#   6. --uninstall (no --yes), stdin non-tty — the safety-net companion to
#      #5: proves the SAME gate refuses non-interactively (never silently
#      proceeds when piped, e.g. `curl ... | sh`) and that nothing was
#      touched when it refuses.
#
# Wiring status: NOT yet called from CI or pre-commit — that lands with the
# T7 merge PR. Run it by hand until then:
#   bash tools/installer_smoke.sh
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_SH="$REPO_ROOT/install.sh"
UNIT_TEST="$REPO_ROOT/tests/install/test_install_sh.sh"

FAIL=0
note() { printf 'installer-smoke: %s\n' "$*"; }
bad() {
    printf 'installer-smoke: FAIL: %s\n' "$*" >&2
    FAIL=1
}
ok() { printf 'installer-smoke: OK: %s\n' "$*"; }

[ -f "$INSTALL_SH" ] || {
    printf 'installer-smoke: FATAL: %s not found\n' "$INSTALL_SH" >&2
    exit 2
}

# Resolve shellcheck: PATH first, else fetch it via nix (mirrors
# tests/install/test_install_sh.sh's own fallback — same reasoning, kept in
# sync deliberately rather than imported, since this file must stay
# self-contained per its brief).
if command -v shellcheck >/dev/null 2>&1; then
    run_shellcheck() { shellcheck "$@"; }
elif command -v nix >/dev/null 2>&1; then
    run_shellcheck() { nix run nixpkgs#shellcheck -- "$@"; }
else
    bad "shellcheck is not on PATH and nix is not available to fetch it"
    run_shellcheck() { return 1; }
fi

# ── 1. bash -n ───────────────────────────────────────────────────────────
bashn_err="$(mktemp)"
if bash -n "$INSTALL_SH" 2>"$bashn_err"; then
    ok "bash -n install.sh"
else
    bad "bash -n install.sh: $(cat "$bashn_err")"
fi
rm -f "$bashn_err"

# ── 2. shellcheck (POSIX sh dialect — install.sh's own shebang + docs) ────
if run_shellcheck -s sh "$INSTALL_SH"; then
    ok "shellcheck -s sh install.sh"
else
    bad "shellcheck reported issues against install.sh"
fi

# ── 3. Reuse the existing TDD harness (DRY) ───────────────────────────────
if [ -f "$UNIT_TEST" ]; then
    if sh "$UNIT_TEST"; then
        ok "tests/install/test_install_sh.sh (placeholder guard, dry-run action lines, uninstall --dry-run)"
    else
        bad "tests/install/test_install_sh.sh reported a failure"
    fi
else
    bad "$UNIT_TEST not found — cannot reuse its assertions"
fi

# ── 4. --dry-run, Nix-ABSENT branch action lines ──────────────────────────
# Needs a keyed scratch copy: the CACHE_KEY placeholder guard fires
# unconditionally, dry-run or not, before the Nix-bootstrap section is ever
# reached — so we cannot observe this branch's dry-run text without a real
# (fake-but-non-placeholder) key first.
tmp4="$(mktemp -d)"
sed 's/babylon-cache-1:REPLACE_WITH_PUBLIC_KEY/babylon-cache-1:AAAATESTKEY000/' \
    "$INSTALL_SH" >"$tmp4/install.sh"

# A minimal PATH that genuinely has no `nix` on it (this dev box has a real
# one at /nix/var/nix/profiles/default/bin — must be excluded, not just
# shadowed, or `command -v nix` would find the real binary and this check
# would silently test the wrong branch).
noNixPath="/usr/local/bin:/usr/bin:/bin"
if PATH="$noNixPath" command -v nix >/dev/null 2>&1; then
    bad "check 4 setup: nix is still resolvable on the restricted PATH ($noNixPath) — cannot simulate Nix-absent"
else
    out4="$(PATH="$noNixPath" HOME="$HOME" sh "$tmp4/install.sh" --dry-run 2>&1)" && rc4=0 || rc4=$?
    check4_ok=1
    if [ "$rc4" -ne 0 ]; then
        bad "install.sh --dry-run (Nix absent) exited $rc4, expected 0. Output: $out4"
        check4_ok=0
    fi
    if ! printf '%s\n' "$out4" | grep -q "Nix is not installed"; then
        bad "--dry-run (Nix absent) did not report 'Nix is not installed'. Output: $out4"
        check4_ok=0
    fi
    if ! printf '%s\n' "$out4" | grep -q "would run: curl"; then
        bad "--dry-run (Nix absent) did not print the planned curl|sh install line. Output: $out4"
        check4_ok=0
    fi
    [ "$check4_ok" -eq 1 ] && ok "--dry-run prints the Nix-bootstrap action lines when Nix is absent"
fi
rm -rf "$tmp4"

# ── 5. --uninstall --yes: consent path, actually acts, no terminal needed ─
# Uses the UNMODIFIED install.sh (placeholder CACHE_KEY is fine — the
# uninstall dispatch runs before the cache-key guard). Fake XDG dirs are
# tmp-scoped so a real destructive rm -rf never touches anything but them.
tmp5="$(mktemp -d)"
fakeData5="$tmp5/xdg-data/babylon"
fakeConfig5="$tmp5/xdg-config/babylon"
mkdir -p "$fakeData5" "$fakeConfig5" "$tmp5/bin"
: >"$fakeData5/sentinel"
: >"$fakeConfig5/sentinel"
cat >"$tmp5/bin/nix" <<'STUB'
#!/bin/sh
printf '%s\n' "nix $*" >>"$NIX_CALL_LOG"
exit 0
STUB
chmod +x "$tmp5/bin/nix"
NIX_CALL_LOG="$tmp5/calls.log"
: >"$NIX_CALL_LOG"

if PATH="$tmp5/bin:$PATH" XDG_DATA_HOME="$tmp5/xdg-data" XDG_CONFIG_HOME="$tmp5/xdg-config" \
    NIX_CALL_LOG="$NIX_CALL_LOG" \
    sh "$INSTALL_SH" --uninstall --yes </dev/null >"$tmp5/stdout.log" 2>&1; then
    if [ -e "$fakeData5/sentinel" ] || [ -e "$fakeConfig5/sentinel" ]; then
        bad "--uninstall --yes exited 0 but left fake XDG dirs behind (nothing was actually removed)"
    elif ! grep -q "profile remove" "$NIX_CALL_LOG"; then
        bad "--uninstall --yes did not invoke 'nix profile remove'"
    else
        ok "--uninstall --yes auto-consents without a terminal and actually removes state"
    fi
else
    bad "--uninstall --yes (non-tty stdin) exited non-zero: $(cat "$tmp5/stdout.log")"
fi
rm -rf "$tmp5"

# ── 6. --uninstall (no --yes), stdin non-tty: refuses, touches nothing ───
tmp6="$(mktemp -d)"
fakeData6="$tmp6/xdg-data/babylon"
fakeConfig6="$tmp6/xdg-config/babylon"
mkdir -p "$fakeData6" "$fakeConfig6" "$tmp6/bin"
: >"$fakeData6/sentinel"
: >"$fakeConfig6/sentinel"
# Stub nix here too, prepended ahead of the real one on PATH: this is a
# safety net, not the thing under test — if the refusal below ever
# regressed, we want any stray 'nix profile remove' to hit this harmless
# stub, never the real nix profile on this dev box.
cat >"$tmp6/bin/nix" <<'STUB'
#!/bin/sh
printf '%s\n' "nix $*" >>"$NIX_CALL_LOG"
exit 0
STUB
chmod +x "$tmp6/bin/nix"

if PATH="$tmp6/bin:$PATH" XDG_DATA_HOME="$tmp6/xdg-data" XDG_CONFIG_HOME="$tmp6/xdg-config" \
    sh "$INSTALL_SH" --uninstall </dev/null >"$tmp6/stdout.log" 2>&1; then
    bad "--uninstall with no --yes and non-tty stdin exited 0 — should have refused"
else
    if ! grep -qi "not a terminal" "$tmp6/stdout.log"; then
        bad "--uninstall refusal did not mention the non-terminal reason. Output: $(cat "$tmp6/stdout.log")"
    elif [ ! -e "$fakeData6/sentinel" ] || [ ! -e "$fakeConfig6/sentinel" ]; then
        bad "--uninstall refused but still removed fake XDG dirs — refusal must touch nothing"
    else
        ok "--uninstall with no --yes refuses non-interactively and touches nothing"
    fi
fi
rm -rf "$tmp6"

# ── Summary ────────────────────────────────────────────────────────────────
if [ "$FAIL" -eq 0 ]; then
    note "ALL CHECKS PASSED"
else
    note "ONE OR MORE CHECKS FAILED — see FAIL lines above"
fi
exit "$FAIL"

# ═══════════════════════════════════════════════════════════════════════════
# OUTLINE ONLY — the full fresh-VM leg (T8 DoD battery). NOT executed by
# this script. No docker/VM is pulled or spun up above this line. This block
# documents the end-to-end leg per PROGRAM_v1_0_0_playable_archive.md's
# v1.0.0 Definition of Done ("fresh-VM nix-bootstrap install harmless to
# host, doctor green") and PROGRAM_v1_0_0_ceremony_runbook.md §2(d)
# ("End-to-end smoke"), for T8 (or a future controller-scheduled job) to
# implement as its own heavy, single-flight gate — never fanned out, per
# CLAUDE.md's machine-safety rule, and never run from a developer's own box
# against production without deliberately choosing to.
#
# Preconditions (hard blockers, per ADR104 / the ceremony runbook):
#   - C1 keygen has run: install.sh's CACHE_KEY placeholder has been
#     replaced with the real public half. Until then this leg CANNOT pass —
#     by design (Constitution III.11 Loud Failure); that is not a bug in
#     the leg, it is the leg proving the refusal guard still works too.
#   - C4 has landed: NIX_CACHE_SIGNING_KEY / R2_ACCESS_KEY_ID /
#     R2_SECRET_ACCESS_KEY / CF_ACCOUNT_ID are wired in CI and at least one
#     `vX.Y.Z` tag has been pushed, so nix-release.yml has populated
#     cache.babylon.percypedia.biz with a signed closure to substitute from.
#
# Recipe (illustrative — not run here):
#
#   1. Provision a disposable, network-connected clean box with NO Nix and
#      NO prior babylon state. Either:
#        docker run --rm -it -v "$PWD/install.sh:/install.sh:ro" \
#          ubuntu:24.04 bash
#      or a throwaway VM (Vagrant/cloud instance) — must be genuinely
#      pristine, since the whole point is proving install.sh is safe to run
#      on a box that has never seen Nix or babylon before.
#
#   2. Inside the clean box, run the real (non-dry-run, consenting) install:
#        sh /install.sh --yes
#      Expect: Determinate Nix installer runs (pinned tag from
#      NIX_INSTALLER_TAG), then `nix profile install` pulls the babylon
#      closure — verify via the ceremony runbook's exact grep:
#        nix build github:percy-raskova/babylon#babylon \
#          --extra-substituters https://cache.babylon.percypedia.biz \
#          --extra-trusted-public-keys "babylon-cache-1:<REAL_PUBLIC_KEY>" \
#          -L 2>&1 | grep -Ei 'copying|building'
#      Pass: only "copying … from 'https://cache.babylon.percypedia.biz'"
#      lines appear — 'building' anywhere means the cache did NOT serve a
#      pre-built closure and the box compiled it locally (still correct,
#      but not what this leg is proving).
#
#   3. Verify host-harmlessness (install.sh's own contract, see its header):
#        - only Nix's own territory (/nix, /etc/nix, the nix-daemon unit,
#          shell-rc snippets, the user's nix profile) plus
#          $XDG_DATA_HOME/babylon and $XDG_CONFIG_HOME/babylon should have
#          changed. A snapshot diff (e.g. `find / -newer /tmp/marker -xdev`
#          taken before/after, restricted to non-ephemeral paths) is one way
#          to assert this on a real VM; trivially true in a throwaway
#          container.
#
#   4. Verify the game itself is usable:
#        babylon doctor        # must exit 0 / print green
#
#   5. Verify uninstall symmetry:
#        sh /install.sh --uninstall --yes
#      Expect: the babylon nix-profile entry and both XDG dirs are gone;
#      `nix` itself remains on the box (install.sh never removes Nix).
#
#   6. Tear down the disposable box. Nothing above this recipe should ever
#      run against a developer's real machine or in ordinary CI — it is the
#      single-flight, controller-scheduled gate named in
#      PROGRAM_v1_0_0_playable_archive.md's execution-kickoff order ("ALL
#      heavy gates … fresh-VM install test … single-flight controller-
#      scheduled"), run once before tagging v1.0.0 (T8), not on every push.
# ═══════════════════════════════════════════════════════════════════════════
