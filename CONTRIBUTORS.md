# Contributing to Babylon

Thanks for your interest in Babylon. This file covers **governance and the git
workflow**. For getting set up and your first contribution, see
[SETUP_GUIDE.md](SETUP_GUIDE.md); for coding standards and architecture, see
[CLAUDE.md](CLAUDE.md).

## Governance: Benevolent Dictator

This project uses the
[Benevolent Dictator](https://producingoss.com/en/benevolent-dictator.html)
model. Persephone Raskova ([@percy-raskova](https://github.com/percy-raskova))
has final authority on all merges to `main`.

## Branch model

```
main ────► stable releases        (BD merges only)
  ▲
dev ─────► integration             (open your PRs here)
  ▲
feature/*, fix/*, docs/*, refactor/*, test/*
```

- **Contributors** branch from `dev` and open PRs **to `dev`**.
- **Only the BD** merges `dev` → `main` for releases.
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

The step-by-step fork → branch → PR walkthrough lives in
[SETUP_GUIDE.md](SETUP_GUIDE.md#part-2--your-first-contribution).
