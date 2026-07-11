# Governance & Workflow

## Git Workflow

**Benevolent Dictator** model. Persephone Raskova ([@percy-raskova](https://github.com/percy-raskova)) has final merge authority.

**Branch Structure**:

```
main ────► stable releases (BD merges only)
  │              ▲
  ▼              │
dev ─────► integration (PRs welcome here)
  │    ▲
  ▼    │
feature/*, fix/*, docs/*, refactor/*
```

- Contributors branch from `dev`, PR to `dev`
- BD only merges `dev` → `main` for releases
- Hotfixes go `fix/*` → `main` (BD only), then backport to `dev`
- **Never** commit directly to `main` or `dev`

**Branch Naming**:

| Prefix      | Purpose           |
| ----------- | ----------------- |
| `feature/`  | New functionality |
| `fix/`      | Bug fixes         |
| `docs/`     | Documentation     |
| `refactor/` | Code improvements |
| `test/`     | Test changes      |

**Commits**: Use conventional commit format: `type(scope): description`

**Commit Early, Commit Often**: Each logical unit of work should be its own commit. Pre-commit hooks test only staged files. If you accumulate multiple units and Bug B's tests depend on Bug A's code, you cannot commit them separately — hooks will fail.

## CI Hygiene

**Fix Unrelated Issues When Encountered**: If CI reveals lint/type errors in files you didn't modify, fix them. Don't leave broken windows.

## Session Continuity

**Before Re-investigating**:

- Check `ai/decisions.yaml` for relevant ADRs
- Review `ai/state.yaml` for current project status

**After Completing Significant Work**:

1. Update `ai/state.yaml` with new status/test counts
1. Create ADR in `ai/decisions.yaml` for architectural patterns
1. Update `ai/roadmap.md` if milestones changed

**ADR Format** (in `decisions.yaml`):

```yaml
ADR0XX_descriptive_name:
  status: "accepted"
  date: "YYYY-MM-DD"
  title: "Short descriptive title"
  context: |
    What problem were we solving?
  decision: |
    What did we decide?
  rationale:
    key_point: "Why this approach?"
  consequences:
    positive:
      - "Benefit 1"
    negative:
      - "Tradeoff 1"
```

## AI-Docs Maintenance

**Files to Consider**:

| File                  | Update When...                                                         |
| --------------------- | ---------------------------------------------------------------------- |
| `state.yaml`          | Test counts change, sprint status changes, new components added        |
| `roadmap.md`          | Phase/sprint milestones reached, new planned work identified           |
| `tooling.yaml`        | New tools added, configuration changes, testing infrastructure updates |
| `observer-layer.yaml` | Observer system changes, event types added                             |
| `architecture.yaml`   | System architecture changes, new Systems added                         |
| `decisions.yaml`      | Architectural decisions made (ADRs)                                    |

**Anti-Pattern**: Do NOT mark features as implemented without verifying the code exists.
