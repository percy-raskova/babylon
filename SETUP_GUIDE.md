# Setup Guide for Contributors

Welcome! This guide will walk you through everything you need to contribute to Babylon. No prior open source experience required.

______________________________________________________________________

## Prerequisites

Before you start, make sure you have these installed:

| Tool   | Version        | Check with         |
| ------ | -------------- | ------------------ |
| Python | 3.12 or higher | `python --version` |
| Poetry | Any recent     | `poetry --version` |
| Git    | Any recent     | `git --version`    |

**Don't have these?**

- Python: [python.org/downloads](https://python.org/downloads)
- Poetry: `curl -sSL https://install.python-poetry.org | python3 -`
- Git: [git-scm.com/downloads](https://git-scm.com/downloads)

______________________________________________________________________

## Step 1: Get the Code

### Option A: Fork (Recommended for First-Time Contributors)

1. Go to [github.com/percy-raskova/babylon](https://github.com/percy-raskova/babylon)
1. Click the **Fork** button (top right)
1. Clone YOUR fork:

```bash
git clone https://github.com/YOUR-USERNAME/babylon.git
cd babylon
```

4. Add the original repo as "upstream":

```bash
git remote add upstream https://github.com/percy-raskova/babylon.git
```

5. Verify your remotes:

```bash
git remote -v
```

You should see:

```
origin    https://github.com/YOUR-USERNAME/babylon.git (fetch)
origin    https://github.com/YOUR-USERNAME/babylon.git (push)
upstream  https://github.com/percy-raskova/babylon.git (fetch)
upstream  https://github.com/percy-raskova/babylon.git (push)
```

### Option B: Clone Directly (For Collaborators with Write Access)

```bash
git clone https://github.com/percy-raskova/babylon.git
cd babylon
```

______________________________________________________________________

## Step 2: Set Up Your Environment

1. Install dependencies:

```bash
poetry install
```

This creates a virtual environment and installs everything. Takes 1-2 minutes.

2. Install pre-commit hooks:

```bash
poetry run pre-commit install
```

This sets up automatic code checking before each commit.

3. Verify everything works:

```bash
poetry run pytest -m "not ai" -x -q
```

You should see tests passing. If not, ask for help (see Step 8).

______________________________________________________________________

## Step 3: Understand the Branches

Babylon uses a **two-tier** branching model:

```
main ────────────────────────────► Stable releases (don't touch!)
  │                        ▲
  │                        │ Only the project maintainer merges here
  ▼                        │
dev ─────────────────────────────► Development (your PRs go here)
  │         ▲
  │         │ Your PR
  ▼         │
feature/your-feature ────────────► Your work
```

**The Golden Rules:**

1. **NEVER** commit directly to `main` or `dev`
1. **ALWAYS** create a branch from `dev`
1. **ALWAYS** open PRs to `dev` (not `main`)

______________________________________________________________________

## Step 4: Create Your Branch

1. Make sure you're up to date:

```bash
git fetch upstream
git checkout dev
git pull upstream dev
```

2. Create your branch FROM `dev`:

```bash
git checkout -b feature/your-feature-name
```

### Branch Naming Convention

Use this format: `type/short-description`

| Type        | When to Use                         | Example                        |
| ----------- | ----------------------------------- | ------------------------------ |
| `feature/`  | Adding something new                | `feature/add-territory-system` |
| `fix/`      | Fixing a bug                        | `fix/rent-calculation-error`   |
| `docs/`     | Documentation only                  | `docs/update-readme`           |
| `refactor/` | Improving code (no behavior change) | `refactor/simplify-formulas`   |
| `test/`     | Adding/fixing tests                 | `test/add-survival-tests`      |

**Good names:**

- `feature/add-consciousness-drift`
- `fix/123-overflow-error` (references issue #123)
- `docs/improve-quickstart`

**Bad names:**

- `my-branch` (not descriptive)
- `fix` (too vague)
- `Feature/Add_Thing` (wrong format)

______________________________________________________________________

## Step 5: Make Your Changes

### Writing Code

1. Make your changes
1. Follow the coding standards in [CLAUDE.md](CLAUDE.md)
1. Add tests for new functionality

### Commit Messages

We use **Conventional Commits**. Format:

```
type(scope): description

[optional body]
```

**Types:**

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `refactor:` - Code change that doesn't add features or fix bugs
- `test:` - Adding or fixing tests
- `chore:` - Maintenance tasks

**Examples:**

```bash
git commit -m "feat(engine): add territory heat system"
git commit -m "fix(survival): correct probability calculation"
git commit -m "docs: update installation instructions"
```

### Running Tests

Before committing, always run:

```bash
# Run fast tests
poetry run pytest -m "not ai" -x

# Check code style
poetry run ruff check . --fix
poetry run ruff format .

# Check types
poetry run mypy src
```

Or use the shortcut:

```bash
mise run ci
```

______________________________________________________________________

## Step 6: Submit a Pull Request

1. Push your branch:

```bash
# If you forked:
git push origin feature/your-feature-name

# If you cloned directly:
git push -u origin feature/your-feature-name
```

2. Go to GitHub and you'll see a prompt to create a PR
1. **IMPORTANT:** Set the base branch to `dev` (not `main`!)

```
base: dev  <--  YOUR BRANCH MERGES INTO THIS
compare: feature/your-feature-name
```

4. Fill out the PR description:

   - What does this change?
   - Why is it needed?
   - How was it tested?
   - Reference any related issues: `Fixes #123`

1. Submit and wait for:

   - CI checks to pass (automatic)
   - Code review (from maintainer)

### What Happens Next

- **CI passes + Approved:** Your PR gets merged!
- **CI fails:** Check the logs, fix the issues, push again
- **Changes requested:** Make the requested changes, push again

______________________________________________________________________

## Step 7: After Your PR is Merged

1. Switch back to dev:

```bash
git checkout dev
```

2. Update your local dev:

```bash
git pull upstream dev
```

3. Delete your feature branch:

```bash
# Delete locally
git branch -d feature/your-feature-name

# Delete from your fork (if applicable)
git push origin --delete feature/your-feature-name
```

4. Celebrate! You're now a contributor!

______________________________________________________________________

## Step 8: Getting Help

**Stuck? Have questions?**

1. **GitHub Issues:** [Open an issue](https://github.com/percy-raskova/babylon/issues)
1. **GitHub Discussions:** For general questions
1. **Code questions:** Tag `@percy-raskova` in your PR

**Common Problems:**

| Problem                | Solution                            |
| ---------------------- | ----------------------------------- |
| Tests failing locally  | Run `poetry install` again          |
| Pre-commit hook fails  | Run `poetry run ruff check . --fix` |
| Can't push to dev/main | You need to create a branch first!  |
| Merge conflicts        | Ask for help in your PR             |

______________________________________________________________________

## Quick Reference Card

```bash
# Start new work
git fetch upstream
git checkout dev
git pull upstream dev
git checkout -b feature/my-feature

# Save your work
git add .
git commit -m "feat: description"

# Submit for review
git push origin feature/my-feature
# Then open PR on GitHub: your-branch → dev

# After merge, cleanup
git checkout dev
git pull upstream dev
git branch -d feature/my-feature
```

______________________________________________________________________

**Thank you for contributing to Babylon!**
