# Versioning — the save-compatibility contract

Owner-ratified 2026-07-20 (spec: docs/superpowers/specs/2026-07-20-versioning-rigor-design.md).
Commitizen enforces commit form; this doc defines what versions MEAN and how releases happen.

## The axis: player saves

- **MAJOR** — an existing save/campaign cannot load without migration. Examples: Ledger
  schema breaks, Archive embedding-column (`vector(N)`) binding changes, defines-format
  breaks that invalidate campaign state.
- **MINOR** — new features; old saves load clean.
- **PATCH** — fixes; no behavior-contract change.
- **Pre-1.0:** the strict reading applies anyway — a 0.x MINOR may not break saves.
  `1.0.0` is a promise-keeping event, not a semantics change.

## Commit scopes (controlled vocabulary)

`cli`, `intelligence`, `engine`, `persistence`, `render`, `web`, `data`, `deps`, `ci`,
`nix`, `flake`, `docs`, `plans`, `ai`, `specs`, `tooling`, `hygiene`, `packaging`.
babylon-infra additionally: `tf`, `ansible`, `cloudflare`, `secrets`, `tasks`.
New scopes are added here first, then used.

## The release ceremony (owner-run)

1. `mise run release:bump` — refuses on a dirty tree or off-`dev`; runs the
   releases-pin-released-infra check (below); shows `cz bump --dry-run`.
2. `mise run release:bump -- --yes` — the real bump commit + `vX.Y.Z` tag (local).
3. Owner pushes `dev`, then the tag. **Pushing the tag IS the release**: it fires
   `release.yml` (GitHub release) and `nix-release.yml` (signed closure → player cache).

## Releases pin released infra

A release may only ship an `infra/` gitlink pointing at a commit that carries an infra
`v*` tag (`tools/check_release_pins.sh`, run by the ceremony and re-checked in
`release.yml`). Day-to-day dev may pin any sha. When the infra contract surface (flake
devshells, deploy workflows, terraform interface) changed since the last infra tag, tag
infra first (`mise run release:bump` in babylon-infra), bump the gitlink, then release.

## Tag namespace

`v*` is for releases, only. Historical/narrative tags live under `archive/`.
Owner-run cleanup 2026-07-20: `v1.0.0` (abandoned 2025-12 bump) deleted;
`v0.2.3-rent-trinity` and `v0.3.7.1-george-jackson-validated` moved to `archive/`.
