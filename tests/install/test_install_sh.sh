#!/bin/sh
# Dry-run harness for install.sh: shellcheck lint + placeholder-guard + stubbed nix call.
# No network, no real nix. Exits non-zero on the first failed assertion.
set -eu

here=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
script="$here/install.sh"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# 1. Lint clean (POSIX sh dialect).
shellcheck -s sh "$script" || fail "shellcheck reported issues"

# 2. Unmodified script must REFUSE (placeholder public key still present).
if sh "$script" >/dev/null 2>&1; then
  fail "install.sh ran with the placeholder CACHE_KEY still in place"
fi
sh "$script" 2>&1 | grep -q "placeholder" || fail "guard did not mention the placeholder"

# 3. With the key replaced and a stubbed nix, it must call 'nix profile install'
#    carrying the substituter + trusted key flags. Work on a scratch copy.
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
sed 's/babylon-cache-1:REPLACE_WITH_PUBLIC_KEY/babylon-cache-1:AAAATESTKEY000/' \
  "$script" > "$tmp/install.sh"

mkdir -p "$tmp/bin"
cat > "$tmp/bin/nix" <<'STUB'
#!/bin/sh
printf '%s\n' "nix $*" >> "$NIX_CALL_LOG"
STUB
chmod +x "$tmp/bin/nix"

NIX_CALL_LOG="$tmp/calls.log"
export NIX_CALL_LOG
: > "$NIX_CALL_LOG"

PATH="$tmp/bin:$PATH" sh "$tmp/install.sh" >/dev/null 2>&1 || fail "install.sh errored with stub nix"

grep -q "nix profile install github:bogdanscarwash/babylon#babylon" "$NIX_CALL_LOG" \
  || fail "did not invoke 'nix profile install' with the flake ref"
grep -q -- "--extra-substituters https://cache.babylon.percypedia.biz" "$NIX_CALL_LOG" \
  || fail "missing --extra-substituters flag"
grep -q -- "--extra-trusted-public-keys babylon-cache-1:AAAATESTKEY000" "$NIX_CALL_LOG" \
  || fail "missing --extra-trusted-public-keys flag"

echo "PASS: install.sh dry-run"
