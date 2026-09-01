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

.. mermaid::

   flowchart TB
       subgraph protected["Protected Branches"]
           MAIN["main<br/>(stable releases)"]
           DEV["dev<br/>(integration)"]
       end

       subgraph work["Working Branches"]
           FEAT["feature/*"]
           FIX["fix/*"]
           DOCS["docs/*"]
           REFACT["refactor/*"]
           TEST["test/*"]
       end

       FEAT & FIX & DOCS & REFACT & TEST -->|"PR"| DEV
       DEV -->|"BD merge"| MAIN
       MAIN -.->|"hotfix backport"| DEV

   %% Luxe Gothic styling
   classDef protected fill:#8B0A1A,stroke:#DC143C,color:#F7F5F3
   classDef work fill:#1A3A1A,stroke:#2A6B2A,color:#39FF14

   class MAIN,DEV protected
   class FEAT,FIX,DOCS,REFACT,TEST work

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
   * - ``fast-gate``
     - Yes
     - Hygiene, lint, formatting, import, type, and lock-file checks
   * - ``test-unit``
     - Yes
     - Parallel unit tests and the coverage floor
   * - ``qa-regression``
     - Yes
     - Deterministic regression and vault evidence
   * - ``rust-gate``
     - Yes
     - Rust formatting, lint, tests, BSL sentinels, and documentation checks
   * - ``ceremony-gate``
     - Yes
     - Baseline-change provenance
   * - ``pg-integration``
     - Yes
     - Aggregate result for the PostgreSQL contract shards
   * - ``security``
     - Yes
     - Python dependency audit with governed exceptions
   * - ``gitleaks``
     - Yes
     - Full-history secret scan
   * - ``trivy-config``
     - Yes
     - High- and critical-severity infrastructure configuration scan

**Concurrency**: Pull-request runs cancel when a newer head supersedes them.
Integrated ``dev`` runs do not cancel one another, so each protected-branch
commit retains a complete evidence record.

codeql.yml
~~~~~~~~~~

**File**: ``.github/workflows/codeql.yml``

**Triggers**:

- Push and pull request for ``main`` or ``dev``
- Weekly schedule on Sunday
- Manual dispatch

**Purpose**: Run semantic static application security testing over the live
Python and Rust paths, the GitHub Actions supply chain, and executable
JavaScript/TypeScript repository tooling. All four languages use CodeQL's
``security-extended`` query suite. This adds lower-precision security queries
to the default suite; it does not add the code-quality queries from
``security-and-quality``.

The path exclusions are deliberately narrow:

- ``.design-sync`` and ``design`` are non-executable design material.
- Two ``bsl-lint`` fixture roots are intentionally malformed nested Rust
  workspaces used to test source-file-scope policy. CodeQL cannot extract
  them as Cargo workspaces, while the surrounding production and fixture Rust
  sources remain scanned.

The workflow's ``upload: always`` setting controls whether analysis results are
uploaded after an earlier step failure. It does not select an alert severity or
make a warning advisory. The protected-branch rulesets require the ``CodeQL``
tool at ``all`` for both alert thresholds, so any open CodeQL alert blocks a
protected merge. The sanctioned merge command also queries the repository alert
database and requires the same zero-alert floor.

CodeQL complements, rather than replaces, the other security gates:
``gitleaks`` finds committed secrets, ``pip-audit`` checks Python dependency
advisories, and Trivy checks infrastructure configuration. Ruff, Clippy, tests,
and the Rust gate enforce correctness and quality outside CodeQL's security
scope.

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

Weekly Python and Rust persistence workflows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``weekly-py313.yml`` runs the Python 3.13 forward-compatibility suite each
Sunday and on manual dispatch. ``weekly-sim-artifacts.yml`` runs the embedded
Michigan persistence slice through ``mise run sim:report 520`` and uploads the
resulting JSONL and summaries from ``reports/sim-runs/``. This report covers
the runtime binary's two embedded smoke rules, not every Rust content pack.

release.yml
~~~~~~~~~~~

**File**: ``.github/workflows/release.yml``

**Triggers**: Push tag matching ``v*``

**Purpose**: Create GitHub Release with changelog and artifacts.

dependabot-automerge.yml
~~~~~~~~~~~~~~~~~~~~~~~~

**File**: ``.github/workflows/dependabot-automerge.yml``

**Triggers**: Successful completion of the ``CI`` workflow for a pull request.

**Purpose**: Revalidate the exact Dependabot candidate from trusted ``dev``
tools, then merge only an eligible minor or patch update. The workflow has no
actor-triggered write phase and does not treat presentation labels as merge
authority.

``.github/dependabot.yml`` separates the weekly queues: Python updates run on
Monday, GitHub Actions updates on Tuesday, and Rust updates on Thursday at
09:00 ``America/New_York``. Dependabot rejects YAML aliases and has no schedule
variable, so all four schema fields remain explicit; a policy test enforces one
daylight-saving-aware timezone across them. Docker image updates remain monthly.
This cadence keeps three full validation batches from competing for the same
runner window and avoids Wednesday's scheduled deep-validation workflows.

Branch Protection Rules
-----------------------

Configured as repository rulesets and synchronized from
``.github/settings/pr-policy.json`` by ``tools/sync_github_pr_policy.py``.

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
   * - Require the complete ``dev`` blocking-check manifest
     - ON
     - Exact GitHub Actions producer IDs; strict head qualification
   * - Require resolved review threads
     - ON
     - A disposition is required for every review thread
   * - Require CodeQL zero-alert floor
     - ON
     - Both CodeQL thresholds are ``all``
   * - Require approving reviews
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
   * - Require the complete ``main`` blocking-check manifest
     - ON
     - Includes the release-qualification contexts
   * - Require resolved review threads
     - ON
     - A disposition is required for every review thread
   * - Require CodeQL zero-alert floor
     - ON
     - Both CodeQL thresholds are ``all``
   * - Require approving reviews
     - OFF
     - Director authority does not depend on self-approval
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

The exact blocking manifests live in ``tools/pr_policy.py`` and are synchronized
to the repository rulesets from ``.github/settings/pr-policy.json``. The
``dev`` manifest requires the nine aggregate checks produced by ``ci.yml``.
The ``main`` manifest requires those checks plus the release-qualification
contexts produced by ``main.yml``. CodeQL uses the native code-scanning ruleset
rule instead of a status-check context, and its zero-alert floor is also a hard
merge condition.

Copilot review state is advisory, but every review thread must be resolved.

Merge Strategies
----------------

Both feature-to-``dev`` and ``dev``-to-``main`` pull requests use merge commits.
The repository disables squash and rebase merges. Use only the sanctioned
``mise run pr:merge -- N`` command after exact-head qualification; the Director
controls merges to ``main``.

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

Secrets (not used in current config):

- ``GITHUB_TOKEN`` - Auto-provided for GitHub API calls
- ``CODECOV_TOKEN`` - If coverage reporting enabled (not currently used)

Local Testing
-------------

**Direct commands**:

.. code-block:: bash

   uv run ruff check .
   uv run mypy src
   uv run pytest -m "not ai"

**Mise tasks**:

.. code-block:: bash

   mise run ci        # lint + format + typecheck + test:unit
   mise run test:all  # all non-AI tests
   mise run docs:build # build documentation

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

      mise run docs:strict

**Duplicate object warnings (autodoc)**
   Expected with Pydantic model re-exports. Suppressed via ``suppress_warnings``
   in ``docs/conf.py``.

See Also
--------

- :doc:`/how-to/contribute` - Contribution workflow
- :doc:`/how-to/run-ci-locally` - Local CI testing
- ``ai/ci-workflow.yaml`` - Machine-readable CI documentation
