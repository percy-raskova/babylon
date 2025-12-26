# CI Best Practices Report: Benevolent Dictator Workflow

## Executive Summary

Your current CI is functional but designed for a single-branch model. With the Benevolent Dictator (BD) governance model and the `feature/* → dev → main` workflow, CI needs to create a **funnel of increasing strictness** where:

1. Feature branches get fast feedback
2. Dev integration catches issues early
3. Main remains pristine and release-ready

---

## 1. Current State Analysis

### What You Have

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

### The Gap

Contributors branch from `dev` and PR to `dev`, but CI only runs on PRs to `main`. This means:

- Contributors get no automated feedback on their PRs
- Issues aren't caught until BD attempts the dev→main merge
- The BD becomes the de facto testing bottleneck

---

## 2. Recommended CI Trigger Strategy

### The Funnel Model

| Event | Checks | Rationale |
|-------|--------|-----------|
| PR to `dev` | Fast checks (lint, types, unit tests) | Contributor feedback loop |
| Push to `dev` | Full suite (all tests, docs build) | Post-merge validation |
| PR to `main` | Full suite + strict mode | BD's pre-release gate |
| Push to `main` | Full suite + release artifacts | Release automation |

### Key Insight

PRs to `dev` should be **permissive but informative**. The goal is helping contributors, not blocking them. PRs to `main` should be **strict**—this is the BD's final quality gate.

---

## 3. Required vs Advisory Checks by Merge Target

### PRs to `dev` (Contributor Workflow)

| Check | Status | Rationale |
|-------|--------|-----------|
| Ruff (lint) | Required | Catches obvious bugs fast |
| MyPy (types) | Required | Type errors are correctness issues |
| Fast tests (`-m "not ai"`) | Required | Core functionality must work |
| Docs build | Advisory | Shouldn't block contributors |
| Style (formatting) | Advisory | Pre-commit handles this locally |
| AI evals | Skip | Too slow for PR feedback |

### PRs to `main` (BD Release Gate)

| Check | Status | Rationale |
|-------|--------|-----------|
| All above | Required | Release quality |
| Docs build | Required | Docs are part of the release |
| Full test suite | Required | Everything must pass |
| Doctest | Required | Examples in docs must work |

### Philosophy

> "Block on correctness, advise on style"

This matches your existing philosophy from the CI comments. The difference is applying it asymmetrically based on merge target.

---

## 4. Branch Protection Configuration

### For `dev` Branch

| Setting | Value | Rationale |
|---------|-------|-----------|
| Require PR | Yes | No direct pushes |
| Require CI pass | Yes | Basic quality gate |
| Require up-to-date | No | Would create rebase churn |
| Require review | No | BD can self-merge from feature branches |
| Allow force push | No | Protects shared history |
| Allow deletions | No | Prevents accidents |

### For `main` Branch

| Setting | Value | Rationale |
|---------|-------|-----------|
| Require PR | Yes | Even BD uses PRs |
| Require CI pass | Yes | Release quality |
| Require up-to-date | Yes | No stale releases |
| Require review | Optional | Forces BD to pause and reflect |
| Allow force push | No | Release history is sacred |
| Allow deletions | No | Never |

### BD Self-Review Consideration

Some BD projects require the BD to approve their own PRs. This seems redundant but serves a purpose: it creates a deliberate pause point. The act of clicking "Approve" forces conscious reflection before merging to main.

---

## 5. Merge Strategy Recommendations

### Feature → Dev: Squash Merge

**Rationale:**
- Each PR becomes one atomic commit in dev
- Easy to revert a problematic contribution
- Cleans up messy feature branch history
- Contributor attribution preserved in commit message

**Commit message format:**
```
feat(topology): add solidarity edge decay (#42)

Co-authored-by: contributor <email>
```

### Dev → Main: Regular Merge (No Squash)

**Rationale:**
- Preserves the individual commits that went into this release
- Creates explicit "merge boundary" commits
- Git history tells the story: "Release 0.3.0 includes these 12 changes"
- Easy to identify what changed between releases

**The merge commit becomes a release marker:**
```
Merge branch 'dev' into main

Release 0.3.0 - Imperial Rent Balancing
```

---

## 6. Handling Stale Branches

### The Problem

In active projects, `dev` moves forward while feature branches stagnate. This creates:
- Merge conflicts
- Integration surprises
- Testing against outdated assumptions

### Recommendations

**Don't require up-to-date for PRs to dev.** This creates "rebase hell" where every contributor is constantly rebasing as others merge. It punishes slow, careful work.

**Do notify contributors when their branch is stale.** A bot comment like:

> "This PR is 15 commits behind dev. Consider rebasing before final review."

**Do require up-to-date for PRs to main.** Since only the BD merges to main, and these are deliberate release events, requiring freshness is reasonable.

### Sync Workflow (Optional)

A manual workflow contributors can trigger:

```
Workflow: Sync with dev
Trigger: workflow_dispatch or comment "/sync"
Action: Rebase feature branch onto dev
```

This helps contributors without forcing them.

---

## 7. Release Workflow (Dev → Main)

When the BD merges dev to main, this should trigger:

### Automated Steps

1. **Validate** - Full CI suite passes
2. **Tag** - Create git tag from version in pyproject.toml
3. **Changelog** - Generate from conventional commits since last tag
4. **Artifacts** - Build PDF docs, any distributable assets
5. **Release** - Create GitHub Release with notes and artifacts

### Manual Trigger Option

Some BDs prefer explicit control:

```
BD merges dev → main
BD manually triggers "Release" workflow
Workflow prompts for version number
Artifacts generated and published
```

This prevents accidental releases from routine merges.

---

## 8. Hotfix Handling

Hotfixes bypass dev. This needs special handling.

### The Flow

```
main (broken)
  │
  └─► fix/critical-bug (branch from main)
        │
        └─► PR to main (BD only)
              │
              ├─► CI runs, BD merges
              │
              └─► Automatic backport PR to dev
```

### Backport Automation

After a hotfix merges to main:

1. Bot creates PR: "Backport fix/critical-bug to dev"
2. If clean merge: auto-merge or notify BD
3. If conflicts: assign to BD for manual resolution

### Why Not Skip the Backport?

If you don't backport to dev, the next dev→main merge will either:
- Re-introduce the bug (if dev had the buggy code)
- Create merge conflicts (if dev diverged)

Always backport.

---

## 9. Job Optimization

### Current Issue

Your CI runs everything sequentially in one job. This means:
- Lint failure at minute 1 still waits for 3-minute test setup
- Contributors wait longer than necessary for feedback

### Recommended Structure

```
┌─────────────────────────────────────────────────┐
│                   PR to dev                      │
├─────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Lint    │  │  Types   │  │  Unit Tests  │  │
│  │  (30s)   │  │  (45s)   │  │  (90s)       │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
│       │              │              │           │
│       └──────────────┼──────────────┘           │
│                      ▼                          │
│              ┌──────────────┐                   │
│              │   Required   │                   │
│              │   (all must  │                   │
│              │    pass)     │                   │
│              └──────────────┘                   │
├─────────────────────────────────────────────────┤
│       ┌──────────────┐    ┌──────────────┐     │
│       │  Docs Build  │    │    Style     │     │
│       │  (advisory)  │    │  (advisory)  │     │
│       └──────────────┘    └──────────────┘     │
└─────────────────────────────────────────────────┘
```

### Fast Fail

Lint and type checks should fail fast. If `ruff check` fails in 30 seconds, don't make contributors wait for the full test suite.

---

## 10. Security Considerations

### Fork PRs

External contributors fork the repo and submit PRs. These PRs should NOT have access to secrets. Your current setup is safe because you don't use secrets in CI.

If you add deployment or publishing workflows:
- Use `pull_request_target` carefully
- Never run untrusted code with secrets
- Review fork PRs manually before running privileged workflows

### Dependency Auditing

Consider adding:
- Dependabot for automated dependency updates
- `pip-audit` or similar for vulnerability scanning

Not urgent for a simulation engine, but good hygiene.

---

## 11. Developer Experience

### What Contributors Need

1. **Clear feedback**: Why did the check fail?
2. **Fast feedback**: Lint results in <1 minute
3. **Actionable feedback**: Link to fix instructions
4. **Visible status**: Can I merge yet?

### Status Badges

Add to README:

```markdown
[![CI](https://github.com/repo/actions/workflows/ci.yml/badge.svg?branch=dev)](...)
[![Docs](https://github.com/repo/actions/workflows/ci.yml/badge.svg?branch=dev&event=push)](...)
```

Use `branch=dev` since that's where active development happens.

### Failure Notifications

- PR authors: GitHub already notifies on check failure
- BD: Consider Slack/Discord webhook on main branch failures
- Public: Workflow status visible in GitHub UI

---

## 12. BD-Specific Considerations

### The Trust Asymmetry

In BD model, the BD is trusted but external contributors are not. However:

> CI should apply equally to all code.

The BD's code goes through the same checks. This:
- Catches BD mistakes (everyone makes them)
- Sets the example for contributors
- Provides objective quality evidence

### The Bottleneck Risk

All merges to main flow through the BD. CI helps by:
- Pre-validating dev branch (BD can trust it's stable)
- Automating release mechanics (less manual work)
- Providing clear merge/no-merge signals

### Scaling

BD model works for small projects. If you grow to 10+ regular contributors:
- Consider adding maintainers with dev merge rights
- Keep main merge rights with BD only
- BD becomes curator rather than gatekeeper

---

## Summary of Recommendations

| Area | Recommendation |
|------|----------------|
| Triggers | Add `pull_request: [dev]` and `push: [dev]` |
| PR to dev | Required: lint, types, fast tests. Advisory: docs, style |
| PR to main | All checks required, strict mode |
| Merge strategy | Squash to dev, regular merge to main |
| Branch protection | Stricter on main than dev |
| Staleness | Don't require up-to-date for dev PRs |
| Releases | Automate tag/changelog on main merge |
| Hotfixes | Automate backport PRs to dev |
| Job structure | Parallel fast checks, fail fast |

---

## Decisions Made

1. **Self-review for main**: Yes - require BD to approve own PRs as deliberate pause
2. **Release automation**: Automatic on dev→main merge
3. **Backport automation**: Manual - bot creates PR, BD merges manually
4. **Advisory checks**: Yellow warning with clear "this is just a suggestion" messaging
5. **Stale branch notifications**: Bot comments

---

## 13. Beginner-Friendly CI Philosophy

### The Context

Contributors are new to coding, getting their feet wet. Not professionals. The goal is a mix of rigor and approachability—enough structure to teach good habits, not so much that it scares people off from a hobby project.

### The Welcoming Failure

When CI fails, beginners often feel:
- "I broke something"
- "I'm not good enough"
- "This is too complicated"

Counter this with **friendly, educational failure messages**.

### Failure Message Strategy

**Bad** (intimidating):
```
Error: MyPy found 3 type errors. Build failed.
```

**Good** (welcoming):
```
🔍 Type Check Results

Found 3 type hints that need attention. Don't worry - this is
one of the trickier parts of Python!

What to do:
1. Look at the file:line numbers below
2. Check if you're missing a type hint (e.g., `def foo(x):` → `def foo(x: int):`)
3. Ask for help in discussions if you're stuck!

Errors:
  src/systems/custom.py:42 - Missing return type annotation
  ...

📚 Learn more: docs/how-to/fix-type-errors.md
```

### The "It's Okay" Signals

For advisory checks, make it crystal clear these aren't failures:

```
💡 Style Suggestion (not required)

The formatter found some spacing tweaks. These won't block your PR!

If you want to fix them locally:
  poetry run ruff format .

Or just ignore this - the maintainer can clean it up when merging.
```

### Progressive Disclosure

Don't dump all information at once. Structure feedback as:

1. **Summary**: Pass/Fail + one sentence
2. **What to do**: Concrete next step
3. **Details**: Expandable/collapsible error log
4. **Help**: Link to docs or discussion

### The Three Audiences

| Audience | What they need |
|----------|----------------|
| Complete beginner | "What does this mean? What do I do?" |
| Learning developer | "Where exactly is the problem?" |
| Experienced dev | "Just show me the error" |

Good CI serves all three by layering information.

### Avoid These Beginner Traps

| Trap | Why it hurts | Alternative |
|------|--------------|-------------|
| Jargon in errors | "What's a type stub?" | Plain English + link to explanation |
| Wall of red text | Overwhelming, feels catastrophic | Summarize first, details on demand |
| Silent failures | "Did it work? I can't tell" | Always explicit pass/fail |
| Too many checks | "I'll never get this right" | Start minimal, add checks gradually |
| No path forward | "Now what?" | Every failure includes next step |

### The "First PR" Experience

A contributor's first PR sets the tone. Consider:

1. **Greet them**: Bot comment welcoming first-time contributors
2. **Guide them**: Link to contributing guide in PR template
3. **Patience with CI**: First PRs often fail CI - that's learning
4. **Celebrate success**: When they fix it, acknowledge the effort

### Sample Bot Comment for First PR

```markdown
👋 Welcome to Babylon!

Thanks for your first contribution! Here's what happens next:

1. **CI checks are running** - These automated tests help catch bugs.
   Don't worry if something fails - it happens to everyone!

2. **A maintainer will review** - We'll give feedback and help you
   get this merged.

3. **Questions?** - Drop a comment here or open a Discussion.

We're excited to have you contributing! 🎉
```

### Rigor Without Intimidation

The balance:

| Rigorous | But Approachable |
|----------|------------------|
| Type hints required | Clear error messages explaining why |
| Tests must pass | Link to "how to run tests locally" |
| Lint checks run | Auto-fix available, or maintainer fixes |
| Conventional commits | Template provided in PR description |

### The Maintainer Safety Net

For a hobby project with beginners, the BD often fixes small issues rather than sending PRs back. This is fine!

**Acceptable workflow:**
1. Contributor submits PR with minor style issues
2. CI shows yellow warning (advisory)
3. BD merges and fixes style in the merge commit
4. Contributor learns from the diff

This keeps momentum while teaching by example.

### What NOT to Require from Beginners

- Perfect commit messages (fix them yourself)
- 100% test coverage (celebrate any tests)
- Documentation updates (add them yourself)
- Changelog entries (generate automatically)

Focus requirements on **correctness** (does it work?) not **polish** (is it perfect?).

---

## Implementation Priority

Given the beginner-friendly context, implement in this order:

### Phase 1: Foundation (Do Now)
- Add dev branch to CI triggers
- Split required vs advisory checks
- Add friendly PR template

### Phase 2: Welcoming (Next)
- First-time contributor bot greeting
- Friendly failure message formatting
- "How to fix" documentation links

### Phase 3: Automation (Later)
- Release automation on main merge
- Backport PR creation for hotfixes
- Stale branch notifications

### Phase 4: Polish (Eventually)
- Status badges in README
- Changelog generation
- Dependency auditing
