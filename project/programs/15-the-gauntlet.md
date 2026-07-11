# Program 15 — The Gauntlet

**Status: EXECUTED 2026-07-11** (promotion + records same day) · Ratified 2026-07-11
(plan-mode approval, 4 owner rulings) · ADR064 · no constitutional amendment (the program
*operationalizes* III.11 Loud Failure + III.12 behavioral contracts in CI; no primitive changed)

**One sentence:** push to dev runs a 4-minute fast lane (lint/types/unit/determinism/frontend/
secrets/IaC — all blocking), push to main runs the whole nine yards (integration, Playwright
against the real stack, the Postgres determinism bundle, reference-data suites, docs, infra
validation, image scanning), nightly and infra-live cover what pushes can't — and every gate
that can't be green yet says so out loud.

## Origin

Percy's directive: "A push to main does the whole god damn thing — a test build of the live
cloud server and infrastructure. A push to dev does reasonably sane CI checks. Audit all
pre-commit hooks for sanity and effectiveness. Dev = fast iteration, main = the real deal."
Plus explicit adds: Bandit-class SAST, secret scanning, Trivy, package caching, gh-act local
runs, maximum-verbosity agent-readable CI output, coverage + metrics artifacts.

Discovery found the inverse: a 9-job monolith firing identically on both branches, 100% red
since the Jul-10 resurrection, the full pytest suite silently run TWICE per push, **the
determinism gates running nowhere in CI**, main frozen since Apr 28 (dev 762 ahead), zero
branch protection, zero secret scanning despite the Jul-8 token leak, and three complexity
gates enforcing three contradictory thresholds.

## Owner rulings (2026-07-11)

1. **Infra depth = static + manual ephemeral:** secretless validation every main push;
   ephemeral Hetzner provision-and-destroy behind workflow_dispatch + weekly cron.
2. **Fix both stable reds in-program:** item 40 (CI reference-subset DB) AND item 41 (CVE wave).
3. **Promotion = direct ff-push + light protection:** no-force-push/no-deletion rulesets;
   `tools/promote.sh` is the gate GitHub can't express for direct pushes.
4. **Releases = tag-driven:** `mise run bump` on dev is the deliberate act; the tag fires
   release.yml. (Retired: push-to-main auto-bump — the 762-commit ff would have auto-published
   a surprise mega-release, the exact failure mode that stale-froze main last time.)
5. *(mid-program)* **Maximum verbosity + full metrics in CI:** logs are agent-read —
   `-vv -ra -l --tb=long --durations=0`, full-tree coverage.xml/json artifacts on both shards,
   junit everywhere, Playwright list reporter + retain-on-failure traces.

## The tier model

| Tier | Trigger | Jobs | Measured |
| --- | --- | --- | --- |
| **dev fast lane** (ci.yml) | push dev, PR to dev/main | fast-gate (hygiene/ruff incl. S/format/imports/mypy/lock) · test-unit (xdist -n4, full-tree cov, engine/systems ≥80 gate) · qa-regression (**the determinism gate, first time in CI ever**) · frontend (check+build+npm audit) · gitleaks (full history) · trivy-config (blocking) · security (pip-audit policy, blocking) | **4 min wall** (target was 8–10) |
| **main full pipeline** (main.yml) | push main, PR to main, dispatch | all of the above + test-rest · postgres-integration · playwright-e2e (real stack) · qa-e2e-regression + storage-budget · refdata-tests (ci-data-v1 subset) · ai-tests (advisory) · docs · trivy-image (advisory until base migration) · infra-validate (terraform/tflint/ansible/compose/hadolint) | maiden run at promotion |
| **nightly** (nightly.yml) | daily 06:00 UTC + Sunday | daily: test-rest, security, postgres-integration, refdata-tests vs dev HEAD; weekly: py3.13 forward-compat, sim trace/sweep artifacts, mutation-vs-baseline | inert until promotion (schedule reads default branch) |
| **infra-live** (infra-live.yml) | dispatch + Monday cron | apply → ansible → /health/ smoke → destroy under if:always(); fail-loud secret preflight; 2h orphan sweeper | awaits operator secrets |

## Execution record (branch `ci/two-tier-refactor`, PR #155)

| Phase | Substance |
| --- | --- |
| 0 measure | Determinism probe **3× GO** — `qa:regression` byte-identical on hosted runners across CPU/glibc/Python/poetry (the go/no-go for the dev-tier gate). 150 stable CI reds enumerated; unit tree 9,207/0 locally → all env-class. Complexity-theater exposed (xenon B was never actually enforced anywhere real); ruff C90-15 becomes the single gate. S-findings, trivy, gitleaks sized. PEP-621 migration + poetry 2.2.1 fleet pin. Rest-shard local timing abandoned (agent-fleet contention made it an upper bound only; CI measures natively). |
| 1 two tiers | Composite actions (bootstrap-python via mise-action — one toolchain source; bootstrap-node; postgres-up w/ GHA layer cache; fetch-reference-db w/ verify-before-first-open). ci.yml rewritten (509 lines deleted); main.yml + nightly.yml authored; extended-analysis + probe retired. 148 reds → `requires_reference_db` (collection-verified per file); 17-test rot tail fixed (stale `calculator_overrides` mocks, missing PG skip-guards, stale SimulationConfig test deleted, 3 spec-064-retired contracts xfail-pending-owner). pytest-cov addopts bug root-caused (`-o addopts=""` is load-bearing — every prior CI run silently wrote htmlcov/). |
| 2 caching | venv key v3, mypy incremental (SHA-suffixed + restore-keys), Playwright browsers, buildx GHA layer cache, trivy built-in DB cache; release.yml timeout + commitizen pinned 4.15.1. Cold-vs-warm runs: identical verdicts (caches are speed, never correctness). |
| 3 security | ruff S repo-wide (54 findings → 0: 13 load-bearing asserts → raises with qa:regression 5/5 byte-identical; 25 audited S608 noqas; 2 real fixes — CREATE VIEW identifier escaping in archival+observatory, S112 logging; per-file-ignores with justifications). gitleaks: config + full-4,209-commit history CLEAN (8 historical findings inspected unredacted, all non-live, rule+path-scoped allowlist) + CI jobs + pre-commit hook. pip-audit policy wrapper (TDD, 24 tests): ignores need reason+expiry, expired = hard fail. trivy-config blocking both tiers (caught DS-0002 on its first run). dependabot: +npm/+docker/+deploy-pip. postgis 16-3.4→16-3.5 + build-time security upgrades (HIGH/CRIT 184→139; the bullseye no-fix residue is upstream's — base migration owner-queued). |
| 4 hooks | `default_stages: [pre-commit]` kills the years-old double-run (every hook ran at pre-commit AND commit-msg). mypy → local system = exact CI parity. Deleted: xenon, complexity-check, radon-metrics, mdformat. Added: gitleaks v8.30.1, actionlint, shellcheck (caught SC2001 in promote.sh on its first commit), hadolint (threshold aligned with CI), poetry-check --lock, no-commit-to-branch [main,dev], LFS pointer fsck at pre-push. `mise run setup` installs all 3 hook types (the fresh-clone footgun). |
| 5 infra | 1,574 lines of rg-verified dead scaffolding deleted (8 roles, Vagrant, dead playbooks/inventories/group_vars). requirements.yml populated from actual module usage. Live bugs fixed: bare `ufw:` ×4 → FQCN, broken `terraform output -raw server_ips_v4` (live-tested fix), playbook.yml ghost, variables.tf drift → cx32/debian-13. Terraform CI-gated: `manage_cloudflare` (11 resources; prod zone untouchable by CI) + `server_name_prefix` (incl. firewall/lb — Hetzner name-uniqueness collisions found by the agent); default expansion proven identical against live state read-only. infra-validate job + infra-live.yml + .tflint.hcl. |
| 6 item 40 | `tools/make_reference_subset.py` (TDD 63 tests; policy-as-data; loud-fail on unclassified tables; deterministic — regeneration reproduces the hash; journal_mode=DELETE + the WAL checkpoint-settling footgun documented). ci-data-v1 release: 391 MiB (93% smaller). FIPS-01011 carve-out preserves the spec-098 regression guard. Proven: 3 national blockers by SQL, adapter suites via env override, the 2 hardcoded-path files via isolated worktree (44 pass + 1 intentional xfail). fetch composite verifies sha on download AND cache-restore. CI_REFDB_READY=true — the four gated jobs un-gate. |
| 7 item 41 | Six serial batches, each railed by qa:regression byte-identity: patch-class ×7 → pillow → aiohttp → starlette (own lane, 0.x→1.x major, zero first-party imports) → django 5.2.16 (manage.py check + observatory + mypy/django-stubs) → cryptography 49.0.0 (own lane, full ansible gate re-run). **73 CVEs → 5** no-fix/parent-pinned ignores with expiry 2026-10-01. Security job BLOCKING on all tiers — green in CI same day. npm audit --omit=dev in frontend jobs (0 findings). numpy/scipy/rustworkx never touched. |
| 8 promotion | release.yml → tags v*; `mise run bump` (dev-guarded); tools/promote.sh (ff-ancestry + all-checks-green via API + operator confirm); rulesets; dev→main ff. |

## Numbers

- Dev lane wall: **4 min** (fast-gate 2.5, unit 3.9 w/ 9,099 tests + coverage, determinism 1.2,
  frontend 1.4, gitleaks 0.2, trivy 0.2). Old monolith: ~15 min when green, 100% red in practice.
- Unit shard: 836s serial local → **139s** on hosted xdist -n4.
- pip-audit: 73 → 5 (all evidenced, all expiring). npm audit: 0. gitleaks full history: clean.
- Reference DB for CI: 5.7 GB → 391 MiB, deterministic, sha-pinned.
- qa:regression: byte-identical at every phase boundary AND on hosted runners (3× probe + every
  PR run since).

## Standing owner items spawned

See owner-queue entries dated 2026-07-11: base-image migration (alpine/PG17), sentence-
transformers pin (2 transformers CVEs), spec-064 retired-contract tests (3 xfails), Oakland
LODES hypothesis (3 xfails), sshd_config.j2 authoring, stale deploy docs, complexity ratchet
(mccabe 15→10 wants 39 fixes), infra-live secrets (console task), local venv py3.13 vs pinned
3.12 drift.
