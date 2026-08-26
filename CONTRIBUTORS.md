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
requests, reviews, and historical evidence. The team closed GitHub Project #7
and Project #8. They are historical inputs. The migration is complete. See
[`docs/agents/governance.md`](docs/agents/governance.md) for field ownership and
the accepted PER delivery convention.
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

Other lane names can also include their PER identity. Use `Part of PER-N` for
partial delivery and `Fixes PER-N` only for the final accepted delivery.
Every PR description must select exactly one of those two Linear delivery
dispositions and link the canonical issue.
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

<!-- Vale: these paragraphs preserve literal review and ceremony terms. -->
<!-- vale ste.UnapprovedWords = NO -->
Every PR needs a behavioral-contract disposition. For changed behavior, link
the durable, implementation-independent contract that proves the change. For
no behavior change, explain why the current contracts are enough.

If a governed baseline changes intentionally, use
`tools/generate_ceremony_message.py`. Include its ceremony record and the
required `Baselines: blessed(<slug>)` trailer. If you did not intend the drift,
stop and correct the fault.
<!-- vale ste.UnapprovedWords = YES -->

## Merge to `dev`

<!-- Vale: this procedure preserves literal GitHub review and branch terms. -->
<!-- vale ste.UnapprovedWords = NO -->
Before a merge, complete these steps:

1. Confirm the base branch and record the exact reviewed head SHA.
2. Confirm that all reported checks completed successfully for that exact
   reviewed head SHA and base branch.
3. Complete the Copilot review against that head. Fix each accepted finding or
   reply with the rationale for no change.
4. Confirm that every Copilot finding has a reply and that you resolved all
   Copilot review threads.
5. Confirm the behavioral-contract disposition and baseline disposition in the
   PR description.
6. Run the approved merge command.

```bash
mise run pr:merge -- N
```

Do not run `gh pr merge` directly in any form. The sanctioned command is the
only merge path.

Preserve the source branch by default. The standard command omits
`--delete-branch`. Delete a source branch only after an explicit owner decision
and a check that no open PR or other work depends on it.
<!-- vale ste.UnapprovedWords = YES -->

<!-- Vale: this paragraph preserves literal Git emergency-workflow terms. -->
<!-- vale Vale.Spelling = NO -->
<!-- vale ste.UnapprovedWords = NO -->
Only the Director merges to `main`. The two allowed sources are a release PR
from `dev`, or a critical hotfix from `fix/*` that branches from `main`. A
backport PR to `dev` is mandatory after a hotfix merge.
<!-- vale ste.UnapprovedWords = YES -->
<!-- vale Vale.Spelling = YES -->

<!-- Vale: this procedure preserves literal GitHub workflow and branch terms. -->
<!-- vale Vale.Spelling = NO -->
<!-- vale ste.UnapprovedWords = NO -->
<!-- vale ste.Articles = NO -->
## Merge to `main`

Before a release PR, prove the merged qualification workflow on the exact
`dev` head:

```bash
gh workflow run main.yml --ref dev
```

Open the release PR from `dev` to `main` only after that run produces the
complete combined manifest. The PR runs ordinary CI plus the uniquely named
release-only qualification checks. After the exact-head review and every
required check pass, the Director uses the sanctioned main mode:

```bash
mise run pr:merge -- N --director-main
```

A critical hotfix uses the same combined manifest and Director mode. Open its
mandatory backport PR to `dev` after the main merge.
<!-- vale ste.Articles = YES -->
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
