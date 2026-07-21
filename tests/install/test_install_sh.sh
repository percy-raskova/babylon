#!/bin/sh
# Dry-run harness for install.sh: shellcheck lint + placeholder-guard + stubbed nix call.
# No network, no real nix, no real Nix-installer invocation. Exits non-zero on
# the first failed assertion. (ADR104: install.sh now nix-bootstraps; every
# scratch copy below stubs `nix` on PATH so `command -v nix` finds it and the
# nix-install branch is never actually exercised here.)
set -eu

here=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
script="$here/install.sh"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# Resolve shellcheck: PATH first, else fetch it via nix (the repo's
# canonical toolchain, CLAUDE.md "Environment") rather than hard-failing
# in a shell that just lacks the binary directly on PATH.
if command -v shellcheck >/dev/null 2>&1; then
  run_shellcheck() { shellcheck "$@"; }
elif command -v nix >/dev/null 2>&1; then
  run_shellcheck() { nix run nixpkgs#shellcheck -- "$@"; }
else
  fail "shellcheck is not on PATH and nix is not available to fetch it"
fi

stub_nix_on_path() {
  # $1 = scratch dir to prepend a stubbed `nix` binary onto PATH for.
  mkdir -p "$1/bin"
  cat > "$1/bin/nix" <<'STUB'
#!/bin/sh
printf '%s\n' "nix $*" >> "$NIX_CALL_LOG"
STUB
  chmod +x "$1/bin/nix"
}

# 1. Lint clean (bash dialect — install.sh's shebang is #!/usr/bin/env bash).
run_shellcheck -s bash "$script" || fail "shellcheck reported issues"

# 2. Syntax clean.
bash -n "$script" || fail "bash -n reported a syntax error"

# 3. Unmodified script must REFUSE (placeholder public key still present),
#    even with a stubbed nix already on PATH (the cache-key guard fires
#    before the Nix-presence check).
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
stub_nix_on_path "$tmp"
NIX_CALL_LOG="$tmp/calls.log"
export NIX_CALL_LOG
: > "$NIX_CALL_LOG"

if PATH="$tmp/bin:$PATH" sh "$script" >/dev/null 2>&1; then
  fail "install.sh ran with the placeholder CACHE_KEY still in place"
fi
PATH="$tmp/bin:$PATH" sh "$script" 2>&1 | grep -q "placeholder" \
  || fail "guard did not mention the placeholder"

# 4. Same refusal must hold under --dry-run (the guard is unconditional).
if PATH="$tmp/bin:$PATH" sh "$script" --dry-run >/dev/null 2>&1; then
  fail "install.sh --dry-run ran with the placeholder CACHE_KEY still in place"
fi

# 5. With the key replaced and a stubbed nix already on PATH (Nix-bootstrap
#    branch is idempotent-skipped), it must call 'nix profile install'
#    carrying the correct flake ref, substituter and trusted key flags.
#    Work on a scratch copy.
tmp2=$(mktemp -d)
trap 'rm -rf "$tmp" "$tmp2"' EXIT
sed 's/babylon-cache-1:REPLACE_WITH_PUBLIC_KEY/babylon-cache-1:AAAATESTKEY000/' \
  "$script" > "$tmp2/install.sh"
stub_nix_on_path "$tmp2"

NIX_CALL_LOG="$tmp2/calls.log"
export NIX_CALL_LOG
: > "$NIX_CALL_LOG"

PATH="$tmp2/bin:$PATH" sh "$tmp2/install.sh" --yes >/dev/null 2>&1 \
  || fail "install.sh errored with stub nix"

grep -q "nix profile install github:percy-raskova/babylon#babylon" "$NIX_CALL_LOG" \
  || fail "did not invoke 'nix profile install' with the corrected flake ref"
grep -q -- "--extra-substituters https://cache.babylon.percypedia.biz" "$NIX_CALL_LOG" \
  || fail "missing --extra-substituters flag"
grep -q -- "--extra-trusted-public-keys babylon-cache-1:AAAATESTKEY000" "$NIX_CALL_LOG" \
  || fail "missing --extra-trusted-public-keys flag"

# 6. --dry-run against the same keyed copy must print the plan and invoke
#    'nix' zero times.
: > "$NIX_CALL_LOG"
out=$(PATH="$tmp2/bin:$PATH" sh "$tmp2/install.sh" --dry-run 2>&1) \
  || fail "install.sh --dry-run exited non-zero on a keyed copy"
printf '%s\n' "$out" | grep -q -- "--extra-trusted-public-keys babylon-cache-1:AAAATESTKEY000" \
  || fail "--dry-run did not print the planned nix profile install command"
[ -s "$NIX_CALL_LOG" ] && fail "--dry-run actually invoked nix (calls.log is non-empty)"

# 7. --uninstall --dry-run must print a removal plan and touch nothing.
out=$(PATH="$tmp2/bin:$PATH" sh "$tmp2/install.sh" --uninstall --dry-run 2>&1) \
  || fail "install.sh --uninstall --dry-run exited non-zero"
printf '%s\n' "$out" | grep -q "nix profile remove" \
  || fail "--uninstall --dry-run did not print the planned profile removal"
printf '%s\n' "$out" | grep -q "Nix itself would be left installed" \
  || fail "--uninstall --dry-run did not say Nix stays installed"

echo "PASS: install.sh dry-run"
