# Contributor Rules

Babylon is an entertainment-first emergent political-economy game. Babylon is
not a forecast and not a scientific reproduction. Theory constrains the causal
model but does not predetermine results.

Determinism proves computational identity, not scientific truth. Historical
cases test causal signatures and counterfactual behavior. The Bevy client is an
administrative viewer with no player action.

The three executable gates are:

<!-- Vale: each protected item is a governed gate name. -->
<!-- vale Vale.Terms = NO -->
<!-- vale ste.UnapprovedWords = NO -->
1. **PostgreSQL/H3/Archive decision-loop slice**
<!-- vale Vale.Terms = YES -->
<!-- vale ste.UnapprovedWords = YES -->
<!-- vale ste.NounClusters = NO -->
2. **COVID E0 emergence proof**
<!-- vale ste.UnapprovedWords = YES -->
3. **Player agency**
<!-- vale ste.NounClusters = YES -->

Read [`CONSTITUTION.md`](CONSTITUTION.md) v4.0.0 for the law. Read
[`NORTH_STAR.md`](NORTH_STAR.md) for the game direction. Read
[`CLAUDE.md`](CLAUDE.md) for repository commands and live technical facts.

## Authority

The Director controls the reserved theory line and all merges to `main`. Agents
can merge a green PR to `dev` through the approved command.

A green gate grants a merge license. A red gate means stop and report the
fault.

Stop and ask the Director when a task needs one of these changes:

- a new mathematical primitive
- a weaker prohibition
- a change to the reserved theory line

Use the governed ceremony for new content vocabulary. Do not improvise a term
that changes the ontology.

## Development lane

Create a regular lane from `dev`. Open a PR against `dev`. Do not commit directly
to `dev` or `main`.

<!-- Vale: this paragraph preserves exact Linear fields and GitHub Project
     names from the control-surface contract. -->
<!-- vale ste.UnapprovedWords = NO -->
<!-- vale ste.NounClusters = NO -->
Linear is canonical for current work. GitHub owns source control, pull
requests, reviews, and historical evidence. Project #7 and Project #8 in GitHub
are transitional inputs. The migration is not complete. See
[`docs/agents/governance.md`](docs/agents/governance.md) for field ownership and
the manual identity link and full PER-15 archive condition.
<!-- vale ste.NounClusters = YES -->
<!-- vale ste.UnapprovedWords = YES -->

Use one of these lane prefixes:

- `feature/`
- `fix/`
- `docs/`
- `refactor/`
- `test/`
<!-- Vale: these lines preserve literal branch and issue identifiers. -->
<!-- vale ste.UnapprovedWords = NO -->
- `codex/PER-123-short-name`

Other lane names can also include their PER identity. This linkage remains a
manual convention until PER-2 verifies automation.
<!-- vale ste.UnapprovedWords = YES -->

Keep unrelated user changes unchanged. Report an unrelated fault unless the owner
adds it to the task.

## Changes and tests

Use TDD for behavior changes. Show a failing test before you change production
behavior. Then make the test pass. Change only the task area.

Use `type(scope): description` for a commit line. Put one logical unit in
each commit. End the message with the required co-author trailer.

Run this command for a commit:

```bash
mise run commit -- "type(scope): description"
```

Run the checks that `CLAUDE.md` assigns to the changed area. Do not bless a
baseline without its declared ceremony.

## Merge to `dev`

Before a merge, complete these steps:

1. Check that each CI task finished.
2. Check that the green task tested the PR head SHA.
3. Read each Copilot comment.
4. Correct the fault or reply with the rationale for no change.
5. Check that no Copilot comment remains without a response.
6. Run the approved merge command.

```bash
mise run pr:merge -- N
```

Do not use `gh pr merge --auto`. The approved command also checks CodeQL and
the merge target.

<!-- Vale: this paragraph preserves literal Git emergency-workflow terms. -->
<!-- vale Vale.Spelling = NO -->
<!-- vale ste.UnapprovedWords = NO -->
A critical hotfix alone can branch from and target `main`. Only the Director
can merge it. A backport PR to `dev` is mandatory after the merge.
<!-- vale ste.UnapprovedWords = YES -->
<!-- vale Vale.Spelling = YES -->

## Records

Keep old ADRs unchanged. They record the rationale that applied when the team
made a choice. Add a new ADR for a new architecture decision.

<!-- Vale: this paragraph preserves exact authority and repository path terms. -->
<!-- vale ste.UnapprovedWords = NO -->
Linear alone owns current status and work. `ai/state.yaml` is historical
implementation evidence, and `project/` is non-live context.
<!-- vale ste.UnapprovedWords = YES -->

Do not report a planned system as complete. Check the source behavior and an
executable test first.
