#!/bin/sh
# Babylon nix-bootstrap installer (ADR104; amends ADR094 D1/D2).
#
# What it does, in order:
#   1. If `nix` is absent, offers to install it via the Determinate Systems
#      installer (explicit consent prompt; `--yes` for non-interactive use).
#      Idempotent: entirely skipped when `nix` is already on PATH.
#   2. Refuses to go any further until the cache-signing public key
#      (CACHE_KEY below) has been minted by the owner-run keygen ceremony
#      (ADR104 / ai/_inbox/PROGRAM_v1_0_0_ceremony_runbook.md, Runbook C1) —
#      never installs unverified binaries.
#   3. Installs the `babylon` package from the signed R2 binary cache via
#      `nix profile install`.
#
# This script is plain POSIX `sh` — no bashisms, no `set -o pipefail` (undefined
# in POSIX sh per shellcheck SC3040, and unsupported by dash < 0.5.12, which
# ships on currently-supported Ubuntu/Debian LTS releases). The one pipe below
# (the Nix-installer download) does not need pipefail to fail loudly: if the
# curl half fails, the piped installer sees empty/partial stdin and the
# explicit `command -v nix` check right after still catches the missing
# binary and dies with a clear message.
#
# Paths this script writes to (host-harmlessness, ADR104 item 4):
#   - Nix's own territory: whatever the Determinate installer and
#     `nix profile install`/`remove` write (the /nix store, /etc/nix,
#     the nix-daemon systemd unit, shell-rc snippets, the user's nix
#     profile under $XDG_STATE_HOME/nix/profiles or ~/.local/state/nix) —
#     entirely the installer's/Nix's own management domain, invoked only
#     after explicit consent, never authored by this script directly.
#   - "$XDG_DATA_HOME/babylon" (default ~/.local/share/babylon) — never
#     created by this script; only ever `rm -rf`'d by --uninstall, in case
#     the game itself populated it on a prior run.
#   - "$XDG_CONFIG_HOME/babylon" (default ~/.config/babylon) — same.
# Nothing else on the host is touched: no other /etc writes, no crontab,
# no systemd units authored here, no dotfile edits. Any sudo prompt comes
# transitively from the Nix installer itself, never from this script.
#
# Usage:
#   sh install.sh                interactive install
#   sh install.sh --yes          non-interactive (auto-consent to installing Nix if absent)
#   sh install.sh --dry-run      print what would happen; touch nothing
#   sh install.sh --uninstall    remove the babylon profile entry + game dirs (Nix stays installed)
#   sh install.sh --help
#
# Cautious players: inspect before you trust. Rather than piping this
# script (or the Nix installer it runs) straight to a shell, download and
# read it first:
#   curl -o install.sh https://raw.githubusercontent.com/percy-raskova/babylon/main/install.sh
#   less install.sh
#   sh install.sh --yes
set -eu

# ── Configuration ──────────────────────────────────────────────────────────

# Public cache-signing key (ADR094 D1, carried by ADR104). The SECRET half
# lives ONLY in CI (nix copy --sign-key at release). This is the PUBLIC
# half, baked in so players can verify narinfo signatures. Replacing the
# placeholder below is a one-line diff — see the guard right after it.
CACHE_KEY="babylon-cache-1:REPLACE_WITH_PUBLIC_KEY"

SUBSTITUTER="https://cache.babylon.percypedia.biz"
FLAKE_REF="github:percy-raskova/babylon#babylon"

# Determinate Systems Nix installer, pinned to a released tag — never the
# unpinned rolling endpoint (ceremony runbook G1 + security posture note).
# Verified reachable (HTTP 200) 2026-07-21 against both
# https://api.github.com/repos/DeterminateSystems/nix-installer/releases/latest
# and https://install.determinate.systems/nix/tag/v3.21.8 directly. Bumping
# this is a deliberate, reviewed one-line diff, not automatic drift — same
# spirit as the nixpkgs pin-cadence discipline (ADR094 D5).
NIX_INSTALLER_TAG="v3.21.8"
NIX_INSTALLER_URL="https://install.determinate.systems/nix/tag/${NIX_INSTALLER_TAG}"

: "${HOME:?babylon-install: HOME must be set}"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/babylon"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/babylon"

ASSUME_YES=0
DRY_RUN=0
DO_UNINSTALL=0

# ── Helpers ────────────────────────────────────────────────────────────────

die() {
    printf 'babylon-install: %s\n' "$1" >&2
    exit 1
}

info() {
    printf 'babylon-install: %s\n' "$1" >&2
}

usage() {
    cat <<'EOF'
Usage: install.sh [--yes] [--dry-run] [--uninstall] [--help]

  (no flags)   Interactive install: installs Nix if absent (asks first),
               then installs the babylon package from the signed R2 cache.
  --yes        Non-interactive: auto-consent to any step that would
               otherwise prompt (installing Nix, or --uninstall's removal).
  --dry-run    Print what would happen; make no changes anywhere.
  --uninstall  Remove the babylon nix-profile entry and the game's data/
               config directories. Leaves Nix itself installed.
  --help       Show this message.
EOF
}

# Shared yes/no gate for anything that changes host state without --yes.
# Returns 0 on consent, 1 on decline. Hard-refuses (never blocks) when
# stdin is not a terminal and --yes was not given — e.g. `curl ... | sh`.
confirm() {
    if [ "$ASSUME_YES" -eq 1 ]; then
        return 0
    fi
    if [ ! -t 0 ]; then
        die "$1 needs confirmation but input is not a terminal (are you piping this script? e.g. curl ... | sh). Re-run with --yes to consent non-interactively, or download it first and inspect it — see the header of this script for the exact commands."
    fi
    printf 'babylon-install: %s [y/N] ' "$1" >&2
    if ! read -r reply; then
        reply="n"
    fi
    case "$reply" in
        y | Y | yes | YES | Yes) return 0 ;;
        *) return 1 ;;
    esac
}

# ── Argument parsing ───────────────────────────────────────────────────────

while [ $# -gt 0 ]; do
    case "$1" in
        --yes) ASSUME_YES=1 ;;
        --dry-run) DRY_RUN=1 ;;
        --uninstall) DO_UNINSTALL=1 ;;
        --help | -h)
            usage
            exit 0
            ;;
        *)
            usage >&2
            die "unknown argument: $1"
            ;;
    esac
    shift
done

# ── Uninstall ──────────────────────────────────────────────────────────────

uninstall() {
    info "uninstall will remove:"
    info "  - the 'babylon' entry from your nix profile"
    info "  - $DATA_DIR"
    info "  - $CONFIG_DIR"
    info "Nix itself is left installed (not removed)."

    case "$DATA_DIR" in
        "" | /) die "refusing: DATA_DIR resolved to a suspicious path ('$DATA_DIR')" ;;
    esac
    case "$CONFIG_DIR" in
        "" | /) die "refusing: CONFIG_DIR resolved to a suspicious path ('$CONFIG_DIR')" ;;
    esac

    if [ "$DRY_RUN" -eq 1 ]; then
        info "[dry-run] would run: nix profile remove --regex '.*babylon.*'"
        info "[dry-run] would run: rm -rf $DATA_DIR"
        info "[dry-run] would run: rm -rf $CONFIG_DIR"
        info "[dry-run] Nix itself would be left installed."
        return 0
    fi

    if ! confirm "Proceed with uninstall?"; then
        info "declined — nothing removed."
        exit 1
    fi

    if command -v nix >/dev/null 2>&1; then
        if nix profile remove --regex '.*babylon.*'; then
            info "removed the babylon nix-profile entry."
        else
            info "WARNING: no matching nix-profile entry found (already removed, or never installed via 'nix profile'). Check manually: nix profile list"
        fi
    else
        info "nix is not on PATH — skipping profile-entry removal."
    fi

    rm -rf "$DATA_DIR"
    rm -rf "$CONFIG_DIR"
    info "removed $DATA_DIR and $CONFIG_DIR."
    info "Nix itself was left installed. To remove Nix too, run the Determinate uninstaller (/nix/nix-installer uninstall) — see https://install.determinate.systems."
}

if [ "$DO_UNINSTALL" -eq 1 ]; then
    uninstall
    exit 0
fi

# ── Install: cache-key guard (ADR104; owner-run keygen, Runbook C1) ────────
# Refuse until the owner has replaced the placeholder public key. This
# check is unconditional — it fires in --dry-run too, because a real run
# would refuse here and this script never pretends otherwise.
case "$CACHE_KEY" in
    *REPLACE_WITH_PUBLIC_KEY*)
        die "CACHE_KEY is still the placeholder — the cache-signing keypair has not been minted yet (owner-run keygen ceremony; see ai/_inbox/PROGRAM_v1_0_0_ceremony_runbook.md Runbook C1, and ADR104). Refusing to install unverified binaries."
        ;;
esac

# ── Install: bootstrap Nix if absent (idempotent) ──────────────────────────

if command -v nix >/dev/null 2>&1; then
    info "Nix already present — skipping Nix install."
else
    if [ "$DRY_RUN" -eq 1 ]; then
        info "[dry-run] Nix is not installed."
        info "[dry-run] would run: curl --proto '=https' --tlsv1.2 -sSf -L $NIX_INSTALLER_URL | sh -s -- install --no-confirm"
    else
        if ! confirm "Nix is not installed. This will download and run the Determinate Systems Nix installer ($NIX_INSTALLER_URL), which requires sudo. Proceed?"; then
            info "declined — Nix was not installed. Nothing was changed."
            exit 1
        fi

        info "installing Nix ($NIX_INSTALLER_TAG)..."
        curl --proto '=https' --tlsv1.2 -sSf -L "$NIX_INSTALLER_URL" | sh -s -- install --no-confirm

        # Make `nix` available in *this* running script without a new shell.
        if [ -f /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh ]; then
            # shellcheck disable=SC1091
            . /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
        fi

        if ! command -v nix >/dev/null 2>&1; then
            die "Nix installer finished but 'nix' is still not on PATH in this shell. Close and reopen your terminal (or run: . /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh), then re-run this script."
        fi
        info "Nix installed."
    fi
fi

# ── Install: babylon package from the signed cache ─────────────────────────

if [ "$DRY_RUN" -eq 1 ]; then
    info "[dry-run] would run: nix profile install $FLAKE_REF --extra-substituters $SUBSTITUTER --extra-trusted-public-keys $CACHE_KEY"
    exit 0
fi

info "installing $FLAKE_REF from $SUBSTITUTER"
nix profile install "$FLAKE_REF" \
    --extra-substituters "$SUBSTITUTER" \
    --extra-trusted-public-keys "$CACHE_KEY"

info 'done. Run "babylon doctor" to verify your setup.'
