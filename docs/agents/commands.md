# Commands Reference

`.mise.toml` and its included task files own executable commands. Use
`mise tasks` for the complete current list.

```bash
mise install --locked
mise run install
mise run hooks
mise run dev:doctor
```

Use the checkout's own pinned environment. Create a sibling worktree from
`origin/dev` with Git or Codex. First update the remote reference:

```bash
git fetch origin
GIT_LFS_SKIP_SMUDGE=1 git worktree add -b codex/PER-123-short-name /media/user/data/worktrees/PER-123/babylon origin/dev
cd /media/user/data/worktrees/PER-123/babylon
CODEX_WORKTREE_PATH="$PWD" python3 - <<'PYTHON'
import subprocess
import tomllib

with open(".codex/environments/environment.toml", "rb") as stream:
    setup = tomllib.load(stream)["setup"]["linux"]["script"]
subprocess.run(["bash", "-c", setup], check=True)
PYTHON
```

The Codex setup installs pinned tools, the locked editable `.venv`,
and shared hooks that resolve the current checkout's `.venv` at execution,
then checks local imports and the worktree's Rust target. It does
not copy reference data or start Postgres. Data tasks check their own
inputs. Nested worktrees must exclude the parent checkout's Mise configuration.
`mise config ls` shows the files loaded.

Managed Babylon builds keep executables in each checkout's `rust/target`.
One checkout at a time uses the media mount's intermediate directory. Switching
checkouts rebuilds from the repository's compiler cache. The lease covers test
execution and all coverage reports. The local dynamic client runs under its own
profile. For full workspace debugger symbols, run `cargo build --profile
full-debug` from `rust/`.

`mise run rust:build-budget` shows whether the directory is busy, the last recorded idle owner,
intermediate bytes, checkout target bytes, and compiler cache bytes.

The `pinned_files` inventory checks launch manifests and later operator build receipts
in run directories directly under this checkout's `reports/test-results`.
It checks the native runtime and client separately. The launcher checks both
digests against one receipt and checks the source and campaign before launch.

`referenced_bytes` counts allocated bytes at those paths, including digest mismatches.
`matching_bytes` counts the subset that matches at least one recorded digest.
Both totals count hard links once. An incomplete check shows `null`.
These bytes are part of the checkout target total.

To preview cleanup, run
`mise run rust:build-budget -- prune`. Add `--apply` to remove idle managed
intermediates. The manager requires 40 GiB free and retains up to 64 GiB of
intermediates between commands.

```bash
mise run check:static                 # Retained static contracts, lint, types, lock
mise run check                        # Static checks, governance, and Python unit tests
mise run test:q -- tests/unit/PATH.py # One Python test file
mise run rust:test:q -- -p CRATE       # Scoped native tests with reports
mise run rust:check-no-docs            # Complete local native gate
mise run rust:test:summary             # Compact latest native report
mise run rust:test:failed              # Repeat the exact failing native tests
```

Run heavy gates serially. Documentation generation requires an explicit user
request; hosted release qualification owns the full documentation build.

```bash
mise run play                         # Durable Bevy observer session
mise run sim:report                    # 15 periods / 60 weeks; includes annual rollover
mise run sim:report 130                # 10 modeled years; each period is four weeks
mise run data:doctor                   # Local reference input checks
mise run data:artifacts                # Rebuild declared data artifacts
mise run data:verify-build             # Verify deterministic reference build
mise run test:rust-postgres   # Isolated pinned PostgreSQL contracts
```

For a release, the fast gate runs ordinary unit tests once. The release
remainder runs non-unit tests and any slow units; the reference-data job owns
``requires_reference_db`` tests, including unit tests. An empty slow-unit shard
is allowed, but a failed collection or test remains a failure.

The frozen Python simulation, formula gates, vault regressions, scenario
runners, and optimization campaigns are retired. Their source and evidence
remain recoverable from Git history.

Stage the exact intended files, commit with `mise run commit -- "type(scope):
description"`, and use `mise run pr:merge -- N` only after merge authorization
and exact-head qualification. See [governance](governance.md) for releases.
