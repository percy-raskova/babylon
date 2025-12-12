# Contributors

## Governance Model

Babylon follows the **Benevolent Dictator** governance model as described in [Producing Open Source Software](https://producingoss.com/en/benevolent-dictator.html).

Final decision-making authority rests with one person who, by virtue of personality and experience, is expected to use it wisely. In practice, this means:

- The BD serves as **arbitrator** when consensus cannot be reached
- Day-to-day development proceeds through normal collaborative discussion
- Area maintainers with greater expertise are deferred to in their domains
- The BD facilitates rather than dictates

## Benevolent Dictator

**Persephone Raskova** ([@percy-raskova](https://github.com/percy-raskova))

- Project founder and maintainer
- Final authority on architectural decisions
- Responsible for release management and version control

## Contributors

### Human Contributors

| Contributor | Commits | Role |
|-------------|---------|------|
| Persephone Raskova | 577 | Benevolent Dictator |

### AI Assistants

Development has been assisted by AI pair-programming tools:

| Assistant | Commits | Usage |
|-----------|---------|-------|
| Aider (with Claude/GPT) | 263 | Pair programming sessions |
| Devin AI | 20 | Autonomous development tasks |
| GitHub Copilot | 8 | Code completion |

AI-assisted commits are co-authored and reviewed by human contributors before merge.

## How to Contribute

1. **Open an Issue** - Discuss proposed changes before implementation
2. **Fork & Branch** - Create a feature branch from `dev`
3. **Follow Standards** - See [CLAUDE.md](CLAUDE.md) for coding standards
4. **Submit PR** - Open PR to `dev`, reference any related issues
5. **Review** - Wait for CI + approval, then squash merge

**New to contributing?** See [SETUP_GUIDE.md](SETUP_GUIDE.md) for step-by-step instructions.

---

## Git Workflow

### Branch Structure

```
main ─────────────────────────────────────────► stable releases
  │                                    ▲
  │                                    │ BD merges when ready
  ▼                                    │
dev ──────────────────────────────────────────► integration branch
  │         ▲         ▲         ▲
  │         │         │         │ PRs from contributors
  ▼         │         │         │
feature/*  fix/*   docs/*   refactor/*
```

### Quick Reference

| Action | Command |
|--------|---------|
| Start work | `git checkout dev && git pull upstream dev && git checkout -b feature/name` |
| Submit work | Push branch, open PR to `dev` |
| Commit format | `type(scope): description` (e.g., `feat(engine): add system`) |

### Branch Naming

| Prefix | Use For |
|--------|---------|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `docs/` | Documentation |
| `refactor/` | Code improvements |
| `test/` | Test changes |

### For Maintainers

- Only the BD merges `dev` → `main`
- Releases are tagged from `main` using Commitizen
- Hotfixes: `fix/*` → `main` (BD only), then backport to `dev`

---

## Questions?

- **GitHub Issues:** Bug reports and feature requests
- **GitHub Discussions:** General questions
- **PR Comments:** Code-specific questions
