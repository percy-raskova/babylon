# Governance & Workflow

## Model: Agentic Engineering

Babylon is built by **Agentic Engineering** (Constitution §IX.5, Amendment AD; ADR151). A human **Director** — Persephone Raskova ([@percy-raskova](https://github.com/percy-raskova)) — steers direction and holds **sole authority over the ideological/theoretical line** (the MLM-TW commitments, the doctrine trees, political framing, the five canonical outcomes) plus **final merge authority** to `main` (the Benevolent-Dictator role, subsumed and renamed). Autonomous AI agents are the engineering workforce: they execute across **parallel isolated worktree lanes** under the interleaving rule (one engine train on the tick pipeline at a time), and their autonomy is **licensed by the gates**, not by trust —

- **green gate = self-merge license; red gate = STOP;**
- determinism (III.7), the sentinel family, behavioral contracts (III.12), the TDD red phase, Loud Failure (III.11), baseline ceremonies (§6.5);
- a task that would add a primitive, relax a prohibition, or **touch the ideological line** stops and escalates — to an amendment or **to the Director** (the escalation ladder is Constitution §IX.3), never resolved by improvisation.

Full model + git workflow: [CONTRIBUTORS.md](../../CONTRIBUTORS.md).

## Git Workflow

**Branch Structure**:

```
main ────► stable releases (Director merges only)
  │              ▲
  ▼              │
dev ─────► integration (PRs welcome here)
  │    ▲
  ▼    │
feature/*, fix/*, docs/*, refactor/*
```

- Contributors branch from `dev`, PR to `dev` (one branch per lane / worktree)
- The Director only merges `dev` → `main` for releases
- Hotfixes go `fix/*` → `main` (Director only), then backport to `dev`
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
