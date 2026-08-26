# Copilot Rules

Read [`CLAUDE.md`](../CLAUDE.md) before each check. It links to the Constitution
and the test rules.

[`CONSTITUTION.md`](../CONSTITUTION.md) v4.0.0 is the authority.
[`NORTH_STAR.md`](../NORTH_STAR.md) explains the game direction and the first
three gates. Do not say that a planned system is complete.

<!-- Vale: this paragraph preserves exact Linear fields and GitHub Project
     names from the control-surface contract. -->
<!-- vale ste.UnapprovedWords = NO -->
<!-- vale ste.NounClusters = NO -->
Linear is canonical for current work. GitHub owns source control, pull
requests, reviews, and historical evidence. The team closed GitHub Project #7
and Project #8. They are historical inputs. The migration is complete. See
[`docs/agents/governance.md`](../docs/agents/governance.md) for scope or status
disputes.
<!-- vale ste.NounClusters = YES -->
<!-- vale ste.UnapprovedWords = YES -->

## Report these defects

### Tick identity

Each tick must have the same hash for the same input. Report each observable
iteration with an order that is not stable. Report values such as `NaN`, `inf`,
and `-0.0`. Report each game rule that reads the wall clock.

### Causal forms

ADR172 forbids a fixed sigmoid, logistic, `tanh`, or `softmax` curve in a game
rule. The engine must derive an S-curve from its population data. Report each
new fixed curve in Python, Rust, or coefficient data.

### Frozen models

`model_copy(update=...)` skips validation. Report each use that writes a
constrained value. Examples include `Probability`, `Currency`, `Intensity`,
and `Coefficient`.

### Native hyperedges

The public `graph` model uses first-class hyperedges. Incidence data can be an
internal storage method. Report each public pairwise expansion of a member list.

### Rust ports

Rust ports must keep the frozen Python behavior. `babylon.kernel` and
`docs/reference/bsl-language.rst` give the contracts. Report changed
semantics, unlicensed currency operations, or silent error defaults.

### Honest vocabulary

Fixtures must use node types, edge types, and fields that production creates.
Report invented type strings and fixture-only fields.

### Frozen Python engine

The Python engine is a behavioral reference at `p27-python-freeze`. New engine
features belong in Rust. Python changes can repair the reference or strengthen
a language-neutral contract.

### Workflow safety

Report `gh pr merge --auto`. Report `restore-keys` on Python
virtual-environment caches. A fallback for a non-venv cache can be correct.
Report a scheduled workflow that is not on the default `branch`.

## Skip these comments

Do not report format, import order, line length, or name preferences.
The project tools own those checks. Do not propose unrelated flexibility.

## Repository facts

Python `graph code` uses `rustworkx` through `BabylonGraph`. Rust uses the
`GraphSubstrate` trait. The Archive uses `pgvector` with Postgres.

Game coefficients belong in `GameDefines` and `defines.yaml`. Report each new
coefficient that game logic hard-codes.

The Director holds the reserved theory line. Agents follow the merge protocol
in `CLAUDE.md`. Write one actionable defect for each comment. Include its effect
and its path.
