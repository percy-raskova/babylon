# The `p27-python-freeze` tag — the frozen Python engine's executable pin

**Authority:** Amendment AE (Constitution v3.0.0, ADR172) — "the Python engine
freezes at the `p27-python-freeze` executable pin, reference-only after."
Chartered as Program 27 Phase 0 Task 17
(`docs/superpowers/plans/2026-07-29-program-27-phase-0-contracts-and-evidence.md`);
Phase 0 is complete at this document's merge plus the first green
`frozen-engine` run.

## What the tag pins

An annotated tag on `dev` at the last commit of the frozen reference era —
after the Director-merged phi_hour boundary clamp (PR #370, the final
authorized Python-engine fix) and the Phase 1 exit checklist (PR #435). The
tag message records the exact pin set:

| Pin | Value at the tag | Where it lives |
|---|---|---|
| Source tree | the tagged commit | git |
| Nix toolchain | `flake.lock` blob `94ed2d750efa` | in-tree, flake-owned sqlite 3.53.1 |
| Python deps | `uv.lock` blob `d35423513fb1` | in-tree, frozen-sync only |
| Reference DB | product sha256 `5e1e60fc8097…` | `data-artifacts.yaml` (the registry is canonical — ADR098; `mise run data:build-db` reproduces it sha-identically on the pinned toolchain) |
| Migration head | `0044_hash_rename_adr179_t2.sql` | `src/babylon/persistence/migrations/` |

## What "frozen" means (spec §4)

The Python engine is **reference-only** past this tag:

- New capability lands Rust-side (Amendment AE; the Rust-first inversion).
- Python engine changes after the tag are **repairs to the reference or
  contract authoring only**, require Director sign-off, and trigger contract
  re-extraction for any family whose vectors they touch.
- The frozen reference keeps its known honest divergences BY DESIGN — e.g.
  the imposed survival logistic (ADR173: the Rust/BSL engine derives the
  S-curve emergently; survival conformance vectors encode the EMERGENT
  formulation, not Python replay) and the phi_hour clamp as a
  frozen-reference noise floor (ADR175 ruling 13: signed Φ with attribution
  is the Rust-side law).

## How to run the frozen engine

```bash
git clone https://github.com/percy-raskova/babylon.git babylon
cd babylon
git checkout p27-python-freeze
cd ..
git clone https://github.com/percy-raskova/hypergraph-rs.git hypergraph-rs
cd hypergraph-rs
git checkout dc1c06abbbc7a3f8633d1561451e61e101ad2090
cd ../babylon
UV_FROZEN=1 uv sync --frozen
UV_FROZEN=1 mise run qa:regression           # canon scenarios, byte-identical
UV_FROZEN=1 mise run qa:vault-regression     # golden-vault byte-gate
```

## The `frozen-engine` CI job

`.github/workflows/frozen-engine.yml` runs weekly (Monday 06:00 UTC) and on
dispatch (`gh workflow run frozen-engine`). It checks out the tag and runs
the same byte-gates as `ci.yml`'s qa-regression job, step-for-step.

**A red `frozen-engine` run is a red gate** (spec §4): the frozen reference
has rotted — a runner-image drift, a dependency yank, or an accidental
force-move of the tag — and every cutover comparison is unsound until it is
repaired. STOP and diagnose; repairing the frozen engine requires Director
sign-off, and the tag is never silently re-cut.
