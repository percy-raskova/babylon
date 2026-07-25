#!/bin/sh
# Releases pin their environment (docs/versioning.md): since the
# environment-sovereignty ruling (2026-07-21, ADR102) the toolchain is the
# vendored flake — flake.nix + flake.lock live in THIS repo, so any tag pins
# the environment by construction. What can still drift is the LOCKSTEP, so
# this check asserts, offline and in-repo:
#   1. flake.lock exists and its nixpkgs-data node matches the rev declared
#      in flake.nix's URL (the lock never silently drifted the sqlite pin);
#   2. tools/build_reference_db.py::PINNED_SQLITE_VERSION matches the
#      data-artifacts.yaml product block's sqlite_version (builder and
#      registry agree on the byte-identity contract).
# Exit 0 consistent / 1 drifted / 2 error.
set -eu

[ -f flake.lock ] || { echo "check_release_pins: FATAL no flake.lock" >&2; exit 2; }
[ -f flake.nix ] || { echo "check_release_pins: FATAL no flake.nix" >&2; exit 2; }

declared=$(sed -n 's|.*nixpkgs-data\.url = "github:NixOS/nixpkgs/\([0-9a-f]\{40\}\)".*|\1|p' flake.nix)
[ -n "$declared" ] || { echo "check_release_pins: FATAL flake.nix has no rev-pinned nixpkgs-data.url" >&2; exit 2; }

locked=$(python3 -c "
import json
lock = json.load(open('flake.lock'))
print(lock['nodes']['nixpkgs-data']['locked']['rev'])
" 2>/dev/null) || { echo "check_release_pins: FATAL flake.lock has no nixpkgs-data node" >&2; exit 2; }

if [ "$declared" != "$locked" ]; then
    printf 'check_release_pins: REFUSE — nixpkgs-data declared %s but locked %s.\n' "$declared" "$locked" >&2
    exit 1
fi

pinned=$(sed -n 's/^PINNED_SQLITE_VERSION = "\([0-9.]*\)".*/\1/p' tools/build_reference_db.py)
[ -n "$pinned" ] || { echo "check_release_pins: FATAL no PINNED_SQLITE_VERSION in tools/build_reference_db.py" >&2; exit 2; }

# sed, not a YAML parser: the step runs before any Python env setup in
# release.yml, so only stdlib is assumed (json above is stdlib; yaml is not).
registry=$(sed -n 's/^  sqlite_version: "\([0-9.]*\)".*/\1/p' data-artifacts.yaml | head -1)
[ -n "$registry" ] || { echo "check_release_pins: FATAL no product.sqlite_version in data-artifacts.yaml" >&2; exit 2; }

if [ "$pinned" != "$registry" ]; then
    printf 'check_release_pins: REFUSE — PINNED_SQLITE_VERSION %s != registry product sqlite_version %s.\n' "$pinned" "$registry" >&2
    exit 1
fi

printf 'check_release_pins: OK — nixpkgs-data %s locked; sqlite lockstep %s.\n' "$locked" "$pinned"
exit 0
