# Contributing to Babylon

Thanks for your interest in Babylon. This file covers **governance and the git
workflow**. For getting set up and your first contribution, see
[SETUP_GUIDE.md](SETUP_GUIDE.md); for coding standards and architecture, see
[CLAUDE.md](CLAUDE.md). The model here is ratified in the Constitution
([CONSTITUTION.md](CONSTITUTION.md) §IX.5, Amendment AD; ADR151).

## Governance: Agentic Engineering

Babylon is built by **Agentic Engineering** — a human **Director** sets
direction and holds the ideological line; autonomous AI agents perform the bulk
of the engineering under a discipline regime that makes their autonomy
trustworthy without line-by-line human review.

### The Director

Persephone Raskova ([@percy-raskova](https://github.com/percy-raskova)) is the
Director. She holds two powers:

1. **Final merge authority** — nothing reaches `main` without her. (This is the
   [Benevolent Dictator](https://producingoss.com/en/benevolent-dictator.html)
   role, **subsumed** here and renamed for the function it serves in an
   agent-executed project — not replaced.)
2. **Ideological authority** — she holds **sole authority over the ideological
   and theoretical line the simulation encodes**: the MLM-TW theoretical
   commitments (Constitution Article I), the doctrine trees, political framing,
   and the canonical outcomes (the five terminal endgames).

This second power is a **reserved power**. Agents engineer *within* the line —
they implement, refactor, test, and propose — but they do **not** author or
alter political content without a Director ruling. A question about the
political line is not an ambiguity to resolve; it is an **escalation to the
Director**.

### Agents are the engineering workforce

Autonomous agents execute across **parallel isolated lanes** — each lane a git
worktree on its own branch — under the **interleaving rule**: at most one engine
train touches the tick pipeline at a time, so determinism baselines never race.
Lane ownership is declared (a lane marker) so concurrent sessions do not collide
on the same files.

### The discipline is what licenses the autonomy

Agent output is trusted because the **gates**, not a reviewer, certify it:

- **Determinism** — every tick produces a hash; non-determinism is a bug
  (Constitution III.7).
- **The sentinel family** — built-but-dead, wrong-shape, and dead-write
  detectors that fail a green-looking test sitting over dead code.
- **Behavioral contracts** — the rewrite test (III.12): golden baselines,
  property laws, and byte-identity ceremonies that pin what the system *does*.
- **The TDD red phase** and **Loud Failure** (III.11) — a missing input fails
  loudly, never silently no-ops.

**A green gate is a self-merge license; a red gate is a STOP.** Ceremony
discipline (baseline blessings, §6.5) is deferred to merge — never taxed on the
inner loop. When a task would add a new primitive, relax a prohibition, or touch
the ideological line, it **stops and escalates** — to a constitutional amendment
or to the Director (the escalation ladder is Constitution §IX.3).

## Branch model

```
main ────► stable releases        (Director merges only)
  ▲
dev ─────► integration             (open your PRs here)
  ▲
feature/*, fix/*, docs/*, refactor/*, test/*   (one per lane)
```

- Branch from `dev` and open PRs **to `dev`** — one branch per lane / worktree.
- **Only the Director** merges `dev` → `main` for releases.
- **Never** commit directly to `main` or `dev`.

| Prefix | Purpose |
| ----------- | --------------------------------------------- |
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `docs/` | Documentation |
| `refactor/` | Code improvements (no behavior change) |
| `test/` | Test changes |

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):
`type(scope): description` (e.g. `feat(engine): add faction influence system`).
Commitizen validates this on commit. Commit after each logical unit of work —
see [CLAUDE.md](CLAUDE.md) for the rationale.

## Before you open a PR

```bash
mise run check   # lint + format + typecheck + unit tests (the fast gate)
```

For any engine / economics / defines change, the byte-identity gate must be
green too (`mise run qa:regression`), and any `tests/baselines/**` movement is a
declared ceremony — see [CLAUDE.md](CLAUDE.md) §"Definition of done". These
gates are what let a PR self-merge on green; a red gate is a STOP, not a
negotiation.

The step-by-step fork → branch → PR walkthrough lives in
[SETUP_GUIDE.md](SETUP_GUIDE.md#part-2--your-first-contribution).
