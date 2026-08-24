# Governance and Git

Babylon is an entertainment-first emergent political-economy game. Babylon is
not a forecast and not a scientific reproduction. Theory constrains the causal model but
does not predetermine results.

Determinism proves computational identity, not scientific truth. Historical
cases test causal signatures and counterfactual behavior. The Bevy client is an
administrative viewer with no player action.

The three executable gates are:

<!-- Vale: the next item is a governed gate name. -->
<!-- vale Vale.Terms = NO -->
<!-- vale ste.UnapprovedWords = NO -->
1. **PostgreSQL/H3/Archive decision-loop slice**
<!-- vale Vale.Terms = YES -->
<!-- vale ste.UnapprovedWords = YES -->
<!-- Vale: the next item is a governed gate name. -->
<!-- vale ste.NounClusters = NO -->
2. **COVID E0 emergence proof**
<!-- vale ste.UnapprovedWords = YES -->
<!-- Vale: the next item is a governed gate name. -->
3. **Player agency**
<!-- vale ste.NounClusters = YES -->

Read [`CONSTITUTION.md`](../../CONSTITUTION.md) v4.0.0 for the law. Read
[`NORTH_STAR.md`](../../NORTH_STAR.md) for the game direction. Read
[`CONTRIBUTORS.md`](../../CONTRIBUTORS.md) for the full merge rules.

## Control surfaces

<!-- Vale: the next paragraphs preserve exact Linear fields, work-item IDs,
     GitHub Project names, and pull-request field names from the contract. -->
<!-- vale ste.UnapprovedWords = NO -->
<!-- vale ste.NounClusters = NO -->
<!-- vale ste.Dictionary = NO -->
In Linear, use
**[Babylon v1 — Playable Political Economy](https://linear.app/percy-raskova/project/babylon-v1-playable-political-economy-299b037e7feb)**
and its charter as the current control surface. Start with
[PER-5](https://linear.app/percy-raskova/issue/PER-5/constitution-v4-and-linear-portfolio-cutover).
Use
[PER-15](https://linear.app/percy-raskova/issue/PER-15/migrate-canonical-issue-governance-from-github-to-linear)
for the migration status.

Linear alone is canonical for issue identity, scope, status, priority,
dependencies, horizon, milestones, schedule, and current work. GitHub supplies
source control, pull requests, reviews, and historical evidence.

The team closed GitHub Project #7 and Project #8. They are historical inputs.
The migration is complete, and PER-15 is complete. Both projects remain
recoverable evidence. Neither supplies current fields, views, estimates, or
status.

PER-2 records the accepted delivery automation. Link each pull request to its
PER identity in the branch name, title, or description. Use `Part of PER-N` as
a non-closing reference for a partial delivery. Use `Fixes PER-N` as a closing
reference only on the final delivery that satisfies the issue.

A multi-pull-request issue must remain open after every partial merge. Draft
and review activity keep the linked issue in progress. Only the merged closing
reference completes it. The automation does not require GitHub Project fields.
Imported historical issue sync cannot override canonical Linear project
scope, hierarchy, horizon, milestone, or priority.
<!-- vale ste.Dictionary = YES -->
<!-- vale ste.NounClusters = YES -->
<!-- vale ste.UnapprovedWords = YES -->

## Authority

Babylon uses Agentic Engineering. The human Director controls the reserved
theory line and merges releases to `main`. Gates grant agent autonomy.

A green gate grants a merge license. A red gate means stop. Report the fault
before you continue.

Stop and ask the Director when a task needs one of these changes:

- a new mathematical primitive
- a weaker prohibition
- a change to the reserved theory line

Use the content vocabulary ceremony for new governed terms.

## Git workflow

For a regular change, create each lane from `dev`. Open the PR against `dev`. Do not
commit directly to `dev` or `main`.

Use one of these prefixes for a lane:

- `feature/`
- `fix/`
- `docs/`
- `refactor/`
- `test/`

<!-- Vale: this paragraph preserves literal branch and issue identifiers. -->
<!-- vale ste.UnapprovedWords = NO -->
Codex-managed work can use `codex/`, with a PER identity such as
`codex/PER-123-short-name`. Other lanes can also include `PER-123` when that
makes the manual Linear link clear.
<!-- vale ste.UnapprovedWords = YES -->

Use `type(scope): description` for each commit line. Keep one logical unit in
each commit. Use `mise run commit` so the local hooks can check staged content.

<!-- Vale: this paragraph preserves literal Git emergency-workflow terms. -->
<!-- vale Vale.Spelling = NO -->
<!-- vale ste.UnapprovedWords = NO -->
Only the Director moves `dev` to `main` for a release. A critical hotfix is the
only bypass: branch from `main`, open directly to `main`, and use a
Director-only merge. Every merged hotfix needs a mandatory backport PR to
`dev`.
<!-- vale ste.UnapprovedWords = YES -->
<!-- vale Vale.Spelling = YES -->
Use the merge rules in `CONTRIBUTORS.md` for all other pull requests.

## Scope and records

Read `ai/decisions/index.yaml` for recorded architecture decisions.
<!-- Vale: this paragraph preserves exact authority and repository path terms. -->
<!-- vale ste.UnapprovedWords = NO -->
`ai/state.yaml` is historical implementation evidence, not current status.
The `project/` tree is non-live context. Linear alone owns current status and
work.
<!-- vale ste.UnapprovedWords = YES -->

Do not change an unrelated fault. Report it unless the task owner expands the
scope.

Add an ADR when the team makes an architecture decision. Keep old ADRs
unchanged because they record the rationale for an earlier choice.

Do not claim that planned behavior exists. Check the source and its executable
test before you change a live status claim.
