Run CI Locally
==============

This guide shows how to run CI checks locally before pushing, using both
direct commands and ``gh act`` for full workflow simulation.

Prerequisites
-------------

- Poetry installed with dependencies: ``poetry install``
- For ``gh act``: GitHub CLI with act extension (``gh extension install nektos/gh-act``)
- For ``gh act``: Docker running

Quick Checks (Direct Commands)
------------------------------

Run individual CI checks directly:

**Lint check:**

.. code-block:: bash

   poetry run ruff check .

   # Auto-fix issues
   poetry run ruff check . --fix

**Type check:**

.. code-block:: bash

   poetry run mypy src

**Run tests:**

.. code-block:: bash

   # All non-AI tests
   poetry run pytest -m "not ai" --tb=short

   # Fast math/engine tests only
   mise run test-fast

**Check documentation:**

.. code-block:: bash

   # Build docs
   cd docs && poetry run sphinx-build -b html . _build/html

   # Strict mode (warnings as errors)
   mise run docs-strict

**Check formatting:**

.. code-block:: bash

   # Check only (no changes)
   poetry run ruff format --check .

   # Auto-format
   poetry run ruff format .

Using Mise Tasks
----------------

Mise provides convenient task shortcuts:

.. code-block:: bash

   # List all available tasks
   mise tasks

   # Quick CI (lint + format + typecheck + fast tests)
   mise run ci

   # Full test suite
   mise run test

   # Type checking only
   mise run typecheck

   # Documentation build
   mise run docs

   # Live documentation server (auto-reload)
   mise run docs-live

Full CI Simulation with gh act
------------------------------

``gh act`` runs GitHub Actions workflows locally in Docker, simulating
exactly what CI will do.

**Dry run (see what would execute):**

.. code-block:: bash

   gh act --dryrun

**Run specific job:**

.. code-block:: bash

   # Run the main CI job
   gh act -j ci

   # Run documentation build
   gh act -j docs

   # Run style check
   gh act -j style

**Simulate specific events:**

.. code-block:: bash

   # Simulate push event
   gh act push

   # Simulate pull request event
   gh act pull_request

**Custom event payloads:**

Create ``.github/test-events/pr-to-dev.json``:

.. code-block:: json

   {
     "pull_request": {
       "base": { "ref": "dev" },
       "head": { "ref": "feature/test" }
     }
   }

Then run:

.. code-block:: bash

   gh act pull_request -e .github/test-events/pr-to-dev.json

gh act Limitations
------------------

Some GitHub-specific features don't work locally:

- **Secrets**: Not available (by design—this is a security feature)
- **GitHub API calls**: May fail without proper authentication
- **Caching**: Works differently than GitHub's infrastructure
- **Artifacts**: Upload/download behaves differently

For most development purposes, dry-run validation is sufficient:

.. code-block:: bash

   # Validates YAML syntax and shows execution plan
   gh act --dryrun

Pre-Commit Hooks
----------------

Pre-commit hooks run automatically on ``git commit``. To run manually:

.. code-block:: bash

   # Run all hooks on staged files
   poetry run pre-commit run

   # Run all hooks on all files
   poetry run pre-commit run --all-files

   # Run specific hook
   poetry run pre-commit run ruff

Hooks configured (from ``.pre-commit-config.yaml``):

1. **ruff (lint)** - Catches bugs, style issues
2. **ruff (format)** - Enforces formatting
3. **mypy (typecheck)** - Type errors
4. **pytest (fast tests)** - Quick sanity check
5. **yamllint** - YAML syntax validation
6. **commitizen** - Commit message format

CI Job Reference
----------------

The CI workflow (``.github/workflows/ci.yml``) runs three jobs:

.. list-table::
   :widths: 20 30 50
   :header-rows: 1

   * - Job
     - Blocks Merge
     - Purpose
   * - ``ci``
     - Yes
     - Lint (Ruff), types (MyPy), tests (Pytest)
   * - ``docs``
     - Yes
     - Doctest examples, Sphinx build
   * - ``style``
     - No (advisory)
     - Formatting check (informational only)

Troubleshooting
---------------

**"command not found: gh"**
   Install GitHub CLI: https://cli.github.com/

**"gh act: command not found"**
   Install the act extension:

   .. code-block:: bash

      gh extension install nektos/gh-act

**"Cannot connect to Docker daemon"**
   Ensure Docker is running. On Linux:

   .. code-block:: bash

      sudo systemctl start docker

**MyPy errors on third-party libraries**
   Install type stubs:

   .. code-block:: bash

      poetry add --group dev types-requests  # example

**Pre-commit hooks slow**
   Skip hooks for WIP commits:

   .. code-block:: bash

      git commit --no-verify -m "wip: work in progress"

   .. warning::

      Remember to run hooks before final commit!

See Also
--------

- :doc:`/how-to/contribute` - Full contribution workflow
- :doc:`/reference/ci-workflow` - CI technical reference
- :doc:`/reference/configuration` - Configuration options
