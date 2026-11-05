#!/bin/sh
# Operator-only inventory. Ordinary Cargo runs never scan checkout targets or sccache.
set -eu

checkout="$(dirname -- "$(dirname -- "$(readlink -f -- "$0")")")"
# shellcheck source=.codex/host/policy.sh disable=SC1091
. "$checkout/.codex/host/policy.sh"
if [ "$#" -eq 0 ]; then set -- status; fi
case "$#:$1:${2:-}" in
  1:status:|1:prune:|2:prune:--apply) ;;
  *) echo "usage: $0 [status|prune [--apply]]" >&2; exit 64 ;;
esac
binary="$(codex_rust_budget_bin "$(codex_rust_babylon_tools_root)")"
cache_dir="$(codex_rust_cache_dir babylon "$(codex_rust_babylon_cache_root)")"
codex_rust_babylon_validate_storage
if [ ! -x "$binary" ] || ! codex_rust_budget_digest_matches "$binary"; then
  echo "budget: missing or corrupt pinned $binary; run host setup" >&2; exit 69
fi
status="$("$binary" --root "$CODEX_RUST_BUDGET_ROOT" --owner "$checkout" \
  --target-dir "$checkout/rust/target" --mount "$CODEX_RUST_BABYLON_MOUNT" \
  --budget-bytes "$CODEX_RUST_BUDGET_BYTES" --reserve-bytes "$CODEX_RUST_RESERVE_BYTES" "$@")"
exec python3 "$checkout/tools/rust_build_budget.py" "$status" "$checkout" "$cache_dir"
