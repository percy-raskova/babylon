CI/CD Workflow Reference
========================

Technical reference for GitHub Actions workflows, branch protection, and
the Benevolent Dictator governance model.

Governance Model
----------------

Babylon uses the **Benevolent Dictator (BD)** governance model:

- **Benevolent Dictator**: Persephone Raskova (@percy-raskova)
- **Authority**: Final decision on all merges to ``main``
- **Contributors**: Branch from ``dev``, PR to ``dev``

Branch Structure
----------------

.. code-block:: text

   main ────► stable releases (BD merges only)
     │              ▲
     ▼              │
   dev ─────► integration (PRs welcome here)
     │    ▲
     ▼    │
   feature/*, fix/*, docs/*, refactor/*, test/*

.. list-table::
   :widths: 15 20 65
   :header-rows: 1

   * - Branch
     - Who Merges
     - Purpose
   * - ``main``
     - BD only
     - Stable releases, protected history
   * - ``dev``
     - BD
     - Integration branch, accepts contributor PRs
   * - ``feature/*``
     - Author
     - New functionality (branch from dev)
   * - ``fix/*``
     - Author
     - Bug fixes (branch from dev, or main for hotfixes)
   * - ``docs/*``
     - Author
     - Documentation changes
   * - ``refactor/*``
     - Author
     - Code improvements
   * - ``test/*``
     - Author
     - Test additions/changes

Workflow Files
--------------

All workflow files are in ``.github/workflows/``:

ci.yml
~~~~~~

**File**: ``.github/workflows/ci.yml``

**Triggers**:

- Push to ``main`` or ``dev``
- Pull request to ``main`` or ``dev``

**Jobs**:

.. list-table::
   :widths: 20 15 65
   :header-rows: 1

   * - Job
     - Blocks
     - Steps
   * - ``ci``
     - Yes
     - ``ruff check .``, ``mypy src``, ``pytest -m "not ai"``
   * - ``docs``
     - Yes
     - ``pytest --doctest-modules``, ``sphinx-build -b html``
   * - ``style``
     - No
     - ``ruff format --check .`` (``continue-on-error: true``)

**Concurrency**: Cancels in-progress runs on same branch.

docs.yml
~~~~~~~~

**File**: ``.github/workflows/docs.yml``

**Triggers**:

- Push to ``main`` (paths: ``docs/**``, ``src/**``)
- Manual dispatch

**Purpose**: Build and deploy documentation to GitHub Pages.

**Jobs**:

1. ``build`` - Build HTML documentation
2. ``deploy`` - Deploy to GitHub Pages

**Note**: Only runs on ``main``—development docs are not deployed.

extended-analysis.yml
~~~~~~~~~~~~~~~~~~~~~

**File**: ``.github/workflows/extended-analysis.yml``

**Triggers**:

- Release published
- Weekly schedule (Sunday midnight)
- Manual dispatch

**Jobs**:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Job
     - Purpose
   * - ``extended_tests``
     - Python 3.12/3.13 matrix testing
   * - ``parameter_analysis``
     - Run ``mise run analyze-trace`` and ``mise run analyze-sweep``
   * - ``ai_evaluation``
     - Run AI tests (release only): ``pytest -m "ai"``

release.yml
~~~~~~~~~~~

**File**: ``.github/workflows/release.yml``

**Triggers**: Push tag matching ``v*``

**Purpose**: Create GitHub Release with changelog and artifacts.

dependabot-automerge.yml
~~~~~~~~~~~~~~~~~~~~~~~~

**File**: ``.github/workflows/dependabot-automerge.yml``

**Triggers**: Pull request from Dependabot

**Purpose**: Auto-merge minor/patch dependency updates after CI passes.

Branch Protection Rules
-----------------------

Configured in GitHub Settings → Branches → Branch protection rules.

dev Branch
~~~~~~~~~~

.. list-table::
   :widths: 50 15 35
   :header-rows: 1

   * - Setting
     - Value
     - Rationale
   * - Require PR before merging
     - ON
     - No direct pushes
   * - Require status checks: ``ci``
     - ON
     - Quality gate
   * - Require branches up to date
     - OFF
     - Avoid rebase churn
   * - Require review
     - OFF
     - BD can self-merge
   * - Allow force push
     - OFF
     - Protect history
   * - Allow deletions
     - OFF
     - Prevent accidents

main Branch
~~~~~~~~~~~

.. list-table::
   :widths: 50 15 35
   :header-rows: 1

   * - Setting
     - Value
     - Rationale
   * - Require PR before merging
     - ON
     - Even BD uses PRs
   * - Require status checks: ``ci``, ``docs``
     - ON
     - Release quality
   * - Require branches up to date
     - ON
     - No stale releases
   * - Require review (Code Owners)
     - ON
     - BD self-review as pause
   * - Allow force push
     - OFF
     - Immutable releases
   * - Allow deletions
     - OFF
     - Protect history

CODEOWNERS
----------

**File**: ``.github/CODEOWNERS``

.. code-block:: text

   # Default owner for everything
   * @percy-raskova

Makes the BD required reviewer for all PRs to ``main``.

PR Template
-----------

**File**: ``.github/PULL_REQUEST_TEMPLATE.md``

Sections:

1. **What does this PR do?** - Brief description
2. **Related Issue** - Link or "N/A"
3. **Checklist** - Guide (not strict requirements)
4. **Questions for Reviewers** - Encourages asking

Philosophy: Welcoming to beginners. Checklist is guidance, not gatekeeping.

Required vs Advisory Checks
---------------------------

**PRs to dev**:

- Required: ``ci`` (lint, types, tests)
- Advisory: ``docs``, ``style``

**PRs to main**:

- Required: ``ci``, ``docs``
- Advisory: ``style``

The ``style`` job always has ``continue-on-error: true``—it shows warnings
but never blocks merge.

Merge Strategies
----------------

**Feature → Dev**: Squash merge

- Each PR becomes one atomic commit
- Easy to revert
- Clean history

**Dev → Main**: Merge commit (no squash)

- Preserves individual commits
- Creates release boundary
- Easy to diff between releases

Hotfix Workflow
---------------

Hotfixes bypass ``dev`` for critical issues:

1. Branch from ``main``: ``git checkout -b fix/critical-bug main``
2. Fix the issue
3. PR to ``main`` (BD only)
4. After merge, backport to ``dev`` (create separate PR)

.. warning::

   Always backport hotfixes to ``dev``. Otherwise the next dev→main merge
   may re-introduce the bug or create conflicts.

Environment Variables
---------------------

CI workflows may use these variables:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Variable
     - Purpose
   * - ``PYTHON_VERSION``
     - Python version for setup-python (default: 3.12)
   * - ``POETRY_VERSION``
     - Poetry version for install-poetry (default: 1.8.4)

Secrets (not used in current config):

- ``GITHUB_TOKEN`` - Auto-provided for GitHub API calls
- ``CODECOV_TOKEN`` - If coverage reporting enabled (not currently used)

Local Testing
-------------

**Direct commands**:

.. code-block:: bash

   poetry run ruff check .
   poetry run mypy src
   poetry run pytest -m "not ai"

**Mise tasks**:

.. code-block:: bash

   mise run ci        # lint + format + typecheck + test-fast
   mise run test      # all non-AI tests
   mise run docs      # build documentation

**gh act** (full simulation):

.. code-block:: bash

   gh act --dryrun    # validate workflow
   gh act -j ci       # run ci job
   gh act push        # simulate push event

See :doc:`/how-to/run-ci-locally` for detailed instructions.

Troubleshooting
---------------

**CI not running on PR to dev**
   Verify ``.github/workflows/ci.yml`` has ``dev`` in the triggers:

   .. code-block:: yaml

      on:
        pull_request:
          branches: [main, dev]

**Style check blocking merge**
   Style should have ``continue-on-error: true``. Check the workflow.

**Sphinx warnings causing failures**
   Warnings are allowed in CI (no ``-W`` flag). For strict local builds:

   .. code-block:: bash

      mise run docs-strict

**Duplicate object warnings (autodoc)**
   Expected with Pydantic model re-exports. Suppressed via ``suppress_warnings``
   in ``docs/conf.py``.

See Also
--------

- :doc:`/how-to/contribute` - Contribution workflow
- :doc:`/how-to/run-ci-locally` - Local CI testing
- ``ai-docs/ci-workflow.yaml`` - Machine-readable CI documentation
