#!/bin/sh
# Babylon Player Channel installer (ADR094 D1/D2).
# Installs the `babylon` package from the R2-backed Nix binary cache. It does
# NOT install Nix itself — if Nix is absent it points at the official installer.
set -eu

# ── Public cache-signing key (ADR094 D1) ──────────────────────────────────
# The SECRET half lives ONLY in CI (nix copy --sign-key at release). This is
# the PUBLIC half, baked in so players can verify narinfo signatures. The owner
# replaces the placeholder after the owner-run keygen
# (babylon-infra cloudflare/scripts/generate-cache-key.sh). Until then this
# script refuses to run rather than install unverified binaries.
CACHE_KEY="babylon-cache-1:REPLACE_WITH_PUBLIC_KEY"

SUBSTITUTER="https://cache.babylon.percypedia.biz"
FLAKE_REF="github:percy-raskova/babylon#babylon"

die() {
    printf 'babylon-install: %s\n' "$1" >&2
    exit 1
}

# Refuse until the owner has replaced the placeholder public key (keygen pending).
case "$CACHE_KEY" in
    *REPLACE_WITH_PUBLIC_KEY*)
        die "CACHE_KEY is still the placeholder — the cache-signing keypair has not been minted (owner-run keygen pending, ADR094 D1). Refusing to install unverified binaries."
        ;;
esac

# Nix must already be present; we never install it for the user.
if ! command -v nix >/dev/null 2>&1; then
    die "Nix is not installed. Install it first (https://nixos.org/download or https://install.determinate.systems), then re-run this script."
fi

printf 'babylon-install: installing %s from %s\n' "$FLAKE_REF" "$SUBSTITUTER"
nix profile install "$FLAKE_REF" \
    --extra-substituters "$SUBSTITUTER" \
    --extra-trusted-public-keys "$CACHE_KEY"

printf 'babylon-install: done. Run "babylon doctor" to verify your setup.\n'
