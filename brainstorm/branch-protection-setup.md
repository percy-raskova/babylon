# Branch Protection Setup Guide

Manual GitHub configuration for the Benevolent Dictator workflow.

**Location**: GitHub → Settings → Branches → Branch protection rules

---

## `dev` Branch Protection

Click "Add rule" and enter `dev` as the branch name pattern.

### Settings

| Setting | Value | Why |
|---------|-------|-----|
| Require a pull request before merging | ON | No direct pushes to dev |
| Require approvals | OFF | BD can self-merge feature branches |
| Require status checks to pass | ON | Quality gate |
| Status checks required | `ci` | Lint, types, tests must pass |
| Require branches to be up to date | OFF | Avoids rebase churn for contributors |
| Do not allow bypassing | ON | Rules apply to everyone |

### What this achieves

- Contributors must use PRs (no direct pushes)
- CI must pass before merge
- BD can merge their own PRs without waiting for reviews
- Contributors don't need to constantly rebase

---

## `main` Branch Protection

Click "Add rule" and enter `main` as the branch name pattern.

### Settings

| Setting | Value | Why |
|---------|-------|-----|
| Require a pull request before merging | ON | Even BD uses PRs |
| Require approvals | ON (1 approval) | Deliberate pause before release |
| Require review from Code Owners | ON | BD self-review as checkpoint |
| Require status checks to pass | ON | Release quality |
| Status checks required | `ci`, `docs` | Full validation |
| Require branches to be up to date | ON | No stale releases |
| Do not allow bypassing | ON | Release discipline |
| Do not allow deletions | ON | Protect release history |
| Do not allow force pushes | ON | Immutable releases |

### What this achieves

- Only BD can merge to main (via PR)
- All checks must pass
- BD must explicitly approve (forces reflection)
- Release history is protected

---

## CODEOWNERS File

Create `.github/CODEOWNERS` to enable "Require review from Code Owners":

```
# Default owner for everything
* @percy-raskova
```

This makes the BD the required reviewer for all PRs to main.

---

## Verification

After configuring, test by:

1. Creating a test branch
2. Opening a PR to dev
3. Verifying CI runs automatically
4. Checking that merge is blocked until CI passes

---

## Required vs Advisory Checks

The workflow defines three jobs:
- `ci` - Required (lint, types, tests)
- `docs` - Required for main, advisory for dev
- `style` - Always advisory (`continue-on-error: true`)

Branch protection enforces which jobs MUST pass. The workflow runs all jobs regardless.
