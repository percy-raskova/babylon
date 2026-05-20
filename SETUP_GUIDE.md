# Getting Started with Babylon

Welcome! This guide takes you from a **bare computer** to a **running simulation**,
then shows you around the codebase. No prior development experience assumed — if
you can copy-paste commands into a terminal, you can do this.

It has two parts:

- **Part 1 — Get Babylon running** (and take a tour). Start here.
- **Part 2 — Your first contribution** (fork, branch, pull request). For when
  you want to change something.

______________________________________________________________________

# Part 1 — Get Babylon running

## Step 1: Get a Linux-style terminal

Babylon is developed on Linux. Pick the section for your machine.

### Windows

You'll run Babylon inside **WSL** (Windows Subsystem for Linux) — a real Linux
environment inside Windows. Follow Microsoft's guide:
[Install WSL](https://learn.microsoft.com/en-us/windows/wsl/install). It's a
one-line command (`wsl --install`) plus a restart.

When asked to pick a Linux distribution, choose **Debian** — that's what Babylon
is built on, so the commands below match exactly. (Ubuntu also works and is very
similar. Other distros are fine too, but Debian and Ubuntu are the only ones we
can help you with.)

Once WSL is installed, open the **Debian** app from your Start menu. Everything
from Step 2 onward happens inside that terminal.

### macOS

Open the **Terminal** app (Applications → Utilities → Terminal). You'll use
[Homebrew](https://brew.sh), the macOS package manager. If you don't have it:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Linux

You already have a terminal. The commands below assume Debian/Ubuntu
(`apt`). On other distros, use your package manager's equivalent.

______________________________________________________________________

## Step 2: Install Git

Git is the version-control tool we use to track every change. It's
non-negotiable. (Read more at the [official Git site](https://git-scm.com).)

- **Debian / Ubuntu / WSL:** `sudo apt update && sudo apt install git`
- **macOS:** `brew install git`

Check it worked:

```bash
git --version
```

______________________________________________________________________

## Step 3: Install mise

[**mise**](https://mise.jdx.dev) (rhymes with "ease") is our one-stop tool for
the development environment. It installs the right version of Python, installs
Poetry for us, sets environment variables, and runs every common task (tests,
linting, the simulation) behind simple `mise run ...` commands. The name comes
from *mise en place* — the kitchen idea of having everything in its place before
you start cooking. That's exactly what it does here.

Install it:

- **Debian / Ubuntu / WSL:** `curl https://mise.run | sh`
- **macOS:** `brew install mise` (or the same `curl` line as above)

Now tell your shell to load mise automatically. Run the line that matches your
shell (if unsure, you're probably using `bash` on WSL/Linux and `zsh` on macOS):

```bash
# bash
echo 'eval "$(mise activate bash)"' >> ~/.bashrc

# zsh
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc
```

**Then close and reopen your terminal** (or run `exec $SHELL`). This step is easy
to forget — if `mise` later says "command not found," it's because the terminal
wasn't restarted. Verify:

```bash
mise --version
```

______________________________________________________________________

## Step 4: Get the code

Clone the repository and enter it. We develop on the `dev` branch, so check it
out:

```bash
git clone https://github.com/percy-raskova/babylon.git
cd babylon
git checkout dev
```

______________________________________________________________________

## Step 5: Trust the project, then install everything

The first time you enter the folder, mise will refuse to load the project's
configuration until you explicitly trust it (a safety feature). Run:

```bash
mise trust
```

Now install the toolchain. This single command reads `.mise.toml` and provisions
**both Python 3.12 and Poetry** for you:

```bash
mise install
```

Then install Babylon's Python dependencies:

```bash
mise run install
```

> **First-time note:** these two steps download a fair amount (Python itself,
> then ~hundreds of packages) and can take a few minutes. That's normal and only
> happens once.

______________________________________________________________________

## Step 6: Run your first simulation 🎉

This is the payoff. Run:

```bash
mise run sim:run
```

You should see output like this — a tiny two-node world (one *Periphery Worker*,
one *Core Owner*) advancing a single tick:

```text
[INFO] __main__: Babylon - The Fall of America
[INFO] __main__: Initial state: tick=0
[INFO] __main__: Initial tension: 0.0000
[INFO] __main__:   Periphery Worker (C001): wealth=0.50
[INFO] __main__:   Core Owner (C002): wealth=0.50
[INFO] __main__: Running simulation step...
[INFO] __main__: After step: tick=1
[INFO] __main__: Tension: 0.0015
[INFO] __main__:   Periphery Worker (C001): wealth=0.51
[INFO] __main__:   Core Owner (C002): wealth=0.49
[INFO] __main__: Simulation step complete.
```

Look closely: in one tick the Owner's wealth fell and the Worker's rose, and
tension appeared on the edge between them. That's the engine modelling a
material relationship — *Graph + Math = History*. **If you saw this, your setup
works.** 🎉

For a second confidence check, run the fast quality gate (lint + types + unit
tests):

```bash
mise run check
```

### You do **not** need any of this (yet)

A common beginner mistake is over-installing. For everything above — setup, the
simulation, the tests, and the tour below — you do **not** need:

- ❌ Docker
- ❌ PostgreSQL
- ❌ Node.js
- ❌ The large reference database

Those are only required for the advanced runs in the [appendix](#appendix--going-further).

______________________________________________________________________

## Step 7: Take a tour

Now poke around. Here's where the interesting things live and a one-liner for
each. (`less` shows a file; press `q` to quit.)

| What                                                                                      | Where                                                                   | Try                                            |
| ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------- |
| **The toy world you just ran**                                                            | `src/babylon/__main__.py`                                               | `less src/babylon/__main__.py`                 |
| **The engine spine** — the 25 systems that run every tick, in materialist-causality order | `src/babylon/engine/simulation_engine.py` (the `_DEFAULT_SYSTEMS` list) | `less src/babylon/engine/simulation_engine.py` |
| **The math** — 18 formula modules (imperial rent, survival calculus, solidarity, …)       | `src/babylon/formulas/`                                                 | `ls src/babylon/formulas/`                     |
| **Tunable coefficients**                                                                  | `src/babylon/config/defines.py`                                         | `less src/babylon/config/defines.py`           |
| **Every available command**                                                               | —                                                                       | `mise tasks`                                   |
| **The project map & theory**                                                              | `README.md`                                                             | `less README.md`                               |
| **Coding standards & architecture**                                                       | `CLAUDE.md`                                                             | `less CLAUDE.md`                               |

A good first read is `fundamental_theorem.py` and `survival_calculus.py` in the
formulas folder — they encode the core of the model the worker-vs-owner tick
just demonstrated. After a test run you can also print a summary of the last
results with `mise run test:summary`.

______________________________________________________________________

# Part 2 — Your first contribution

Ready to change something? Here's the full workflow. (Governance and branch
rules are summarized in [CONTRIBUTORS.md](CONTRIBUTORS.md).)

## Step 1: Fork and connect

For first-time contributors, **fork** the repo (your own copy on GitHub):

1. Go to [github.com/percy-raskova/babylon](https://github.com/percy-raskova/babylon)
   and click **Fork**.
1. Clone *your* fork and add the original as `upstream`:

```bash
git clone https://github.com/YOUR-USERNAME/babylon.git
cd babylon
git remote add upstream https://github.com/percy-raskova/babylon.git
git remote -v   # confirm: origin = your fork, upstream = percy-raskova
```

(Collaborators with write access can clone the main repo directly instead.)

## Step 2: Branch from `dev`

Always branch from an up-to-date `dev` — **never** commit directly to `main` or
`dev`:

```bash
git fetch upstream
git checkout dev
git pull upstream dev
git checkout -b feature/your-feature-name
```

Name branches `type/short-description`, e.g. `feature/add-territory-system`,
`fix/123-rent-overflow`, `docs/improve-quickstart`. Prefixes: `feature/`,
`fix/`, `docs/`, `refactor/`, `test/`.

## Step 3: Make your changes

Follow the standards in [CLAUDE.md](CLAUDE.md) and add tests for new behavior.
We use **Conventional Commits**:

```bash
git commit -m "feat(engine): add faction influence system"
git commit -m "fix(survival): correct revolution probability"
git commit -m "docs: clarify mise setup"
```

> **First commit is slow.** Babylon installs Git pre-commit hooks (run once via
> `poetry run pre-commit install`). On the first push the hooks build their
> environments and run type-checking plus a fast test slice, which can take a
> couple of minutes. Later commits are quick.

Before pushing, run the gate:

```bash
mise run check
```

## Step 4: Open a pull request

```bash
git push origin feature/your-feature-name
```

On GitHub, open a PR and **set the base branch to `dev`** (not `main`).
Describe what changed, why, and how you tested it; reference issues with
`Fixes #123`. Then CI runs and a maintainer reviews. After merge:

```bash
git checkout dev
git pull upstream dev
git branch -d feature/your-feature-name
```

That's it — you're a contributor. 🚩

______________________________________________________________________

# Appendix — Going further

These are the heavier, "real" runs. They need infrastructure you can add once
you're comfortable.

| What                                                                    | Command                     | Needs                                        |
| ----------------------------------------------------------------------- | --------------------------- | -------------------------------------------- |
| **Full county-scale simulation** (Michigan + Canada, hundreds of ticks) | `mise run sim:e2e-michigan` | PostgreSQL + Docker + the reference database |
| **The web app** (React + Django map UI)                                 | `mise run web:dev`          | Node.js (`mise run web:install` first)       |
| **The collapse trajectory viewer**                                      | `mise run viz:necropolis`   | reference data                               |
| **Postgres test container**                                             | `mise run db:up`            | Docker                                       |

See [README.md](README.md) for the full command reference and the architecture
overview, and `mise tasks` for everything available.

______________________________________________________________________

## Getting help

- **Issues / questions:** [open an issue](https://github.com/percy-raskova/babylon/issues)
- **Code questions in a PR:** tag `@percy-raskova`

| Problem                            | Try                                                         |
| ---------------------------------- | ----------------------------------------------------------- |
| `mise: command not found`          | You didn't restart your terminal after Step 3.              |
| mise won't load the config         | Run `mise trust` in the project folder.                     |
| `poetry` / tests fail unexpectedly | Re-run `mise run install`.                                  |
| Pre-commit hook fails on commit    | `poetry run ruff check . --fix && poetry run ruff format .` |
| "Can't push to dev/main"           | Create a branch first (Part 2, Step 2).                     |

**Thank you for contributing to Babylon!**
