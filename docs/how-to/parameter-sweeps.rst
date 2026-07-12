Run Parameter Sweeps and Optimization
======================================

This guide shows how to run parameter sweeps, Monte Carlo uncertainty
quantification, global sensitivity analysis, and Bayesian search over
``GameDefines`` coefficients using the
:mod:`babylon.engine.optimization` package.

.. note::

   Looking for one-off manual parameter overrides, or the older single-trace
   ``tools/parameter_analysis.py`` workflow? See :doc:`parameter-tuning` and
   :doc:`analyze-parameter-sensitivity`. This guide covers the package that
   powers systematic sweeps and search: ``sweep``, ``monte-carlo``,
   ``sensitivity``, and ``bayesian``.

Prerequisites
-------------

- Familiarity with :doc:`modding-defines` (the ``GameDefines`` schema these
  tools override).
- The dev dependency group installed for ``sensitivity`` (SALib) and
  ``bayesian`` (Optuna): ``poetry install --with dev``.

Two backends, and when to use each
-----------------------------------

Every subcommand accepts ``--backend {headless,in-memory}``:

``in-memory``
   The fast legacy engine, run entirely in-process — no database. Use this
   for iterating quickly, for CI-adjacent checks, and for any sweep where
   you want dozens to hundreds of trials in seconds. Select a scenario with
   ``--scenario`` (``imperial_circuit`` or ``two_node``).

``headless``
   The Postgres-backed runner (spec-064/065/066) — the realistic path,
   scoped to a county set via ``--scope-name`` (default
   ``detroit-tri-county``: Wayne/Oakland/Macomb). Use this when a result
   needs to reflect the full persistence/hex/trade stack, not just the
   in-memory approximation. It is slower and requires a reachable Postgres
   instance.

Each algorithm defaults to ``headless`` unless documented otherwise; pass
``--backend in-memory`` explicitly to get the fast path. Both backends
return the same normalized
:class:`~babylon.engine.optimization.backends.types.Result`, so a sweep's
CSV columns are identical regardless of which backend produced them.

Defines now actually reach the simulation
------------------------------------------

Every trial in this package routes through
:func:`babylon.engine.optimization.runner_api.run`, which threads the
(possibly swept) ``GameDefines`` into the backend. Before commit
``bd3772a9`` (*"fix(engine): headless runner honors caller-supplied
GameDefines (inert-sweep bug)"*), the headless runner called
``GameDefines.load_default()`` unconditionally — so every headless
sweep/Monte Carlo/Optuna/Morris-Sobol trial silently ran bit-identical math
regardless of the parameter override, a Constitution III.11 Loud-Failure
violation. That is fixed: the headless runner now resolves
``config.defines`` (in-process override) ahead of ``load_default()``, and a
contract test (``tests/unit/engine/headless_runner/test_defines_resolution.py``)
pins the precedence. If you swept parameters with this package before that
fix, re-run — the earlier results did not reflect the parameter you thought
you were varying.

The four subcommands
---------------------

All four share ``--backend``, ``--scope-name``/``--scenario``,
``--objective {carceral,survival}`` (default ``carceral``, the Carceral
Equilibrium phase-timing scorer — see
:func:`~babylon.engine.optimization.objectives.carceral_objective`), and
``--max-ticks``. Run ``python -m babylon.engine.optimization <subcommand>
--help`` for the authoritative, current flag list — the invocations below
are verified against that output but the ``--help`` text is the source of
truth.

sweep — 1D or 2D coefficient sweep
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sweep one coefficient across a range, or two for a grid:

.. code-block:: bash

   poetry run python -m babylon.engine.optimization sweep \
       --param "economy.extraction_efficiency=0.1:0.3:0.1" \
       --backend in-memory \
       --output-csv results/sweep.csv \
       --report

Add ``--param2 "economy.comprador_cut=0.5:1.0:0.1"`` for a 2D grid instead
of a 1D line. ``--report`` prints the Playable Boundary report after a 1D
sweep.

Via mise:

.. code-block:: bash

   mise run sim:sweep            # 1D: economy.extraction_efficiency 0.05:0.50:0.05
   mise run tune:params           # same sweep, --report enabled
   mise run tune:params-custom -- 0.1 0.9 0.1   # start end step
   mise run tune:landscape        # 2D grid, 100-year (5200-tick) trials

monte-carlo — uncertainty quantification
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Run N stochastic replications of one fixed configuration to see outcome
variance under a shared seed-derivation scheme:

.. code-block:: bash

   poetry run python -m babylon.engine.optimization monte-carlo \
       --n-samples 100 \
       --seed 42 \
       --param "economy.extraction_efficiency=0.5" \
       --backend in-memory \
       --csv-path results/monte_carlo.csv

``--param`` is repeatable here (fixed overrides, not ranges — use
``PATH=VALUE``, not ``PATH=START:END:STEP``).

Via mise:

.. code-block:: bash

   mise run sim:monte-carlo                # defaults: 100 samples
   mise run sim:monte-carlo -- 500 42      # 500 samples, seed 42

sensitivity — Morris/Sobol global sensitivity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Rank coefficients by influence on the objective, via SALib:

.. code-block:: bash

   poetry run python -m babylon.engine.optimization sensitivity \
       --method morris \
       --trajectories 10 \
       --morris-output results/morris.json

   poetry run python -m babylon.engine.optimization sensitivity \
       --method sobol \
       --samples 256 \
       --sobol-output results/sobol.json

``--method both`` runs Morris then Sobol in one invocation. Restrict the
parameter set with ``--param-names "economy.extraction_efficiency,economy.comprador_cut"``;
omitted, every known tunable parameter
(:func:`~babylon.engine.optimization.params.get_tunable_parameters`) is
analyzed. Requires the dev dependency group (SALib) — without it, the
subcommand exits with a clear message rather than an import traceback.

Via mise:

.. code-block:: bash

   mise run tune:morris     # Morris only, fast screening
   mise run tune:sobol      # Sobol only, slower variance decomposition
   mise run tune:sensitivity  # both, sequentially

bayesian — Optuna TPE + Hyperband search
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Search for coefficients maximizing the Carceral Equilibrium objective:

.. code-block:: bash

   poetry run python -m babylon.engine.optimization bayesian \
       --n-trials 100 \
       --study-name babylon_carceral \
       --storage sqlite:///optuna.db

Resume a study by reusing ``--study-name``/``--storage``. Inspect the best
trial so far without running new ones via ``--show-best``. Restrict the
search space with ``--categories "economy,consciousness"`` (default:
``TUNING_CATEGORIES``). Requires the dev dependency group (Optuna).

Via mise:

.. code-block:: bash

   mise run tune:optuna -- 200 my_study   # trials, study name
   mise run tune:dashboard                # optuna-dashboard sqlite:///optuna.db

The ``--param``/``--param2`` grammar
--------------------------------------

Both ``sweep`` and ``monte-carlo`` parse parameter flags through the same
grammar (:mod:`babylon.engine.optimization.ranges`), which unifies what
used to be three inconsistent formats across older tools:

Override (one fixed value) — used by ``monte-carlo --param``:

.. code-block:: text

   category.field=VALUE
   economy.extraction_efficiency=0.5

Range (a swept sequence) — used by ``sweep --param``/``--param2``:

.. code-block:: text

   category.field=START:END:STEP
   economy.extraction_efficiency=0.1:0.3:0.1   # -> [0.1, 0.2, 0.3]

Ranges are inclusive of both endpoints (subject to a small float-tolerance
window, not Python's exclusive-end ``range()``), and each expanded value is
rounded to 6 decimal places to avoid float-accumulation drift across many
additions of ``step``. ``category.field`` is any dot-separated path into
``GameDefines`` (see :doc:`modding-defines` for the schema); the CLI
validates the spec eagerly, so a malformed grammar fails immediately with a
usage error rather than deep inside a trial.

Reproducibility records
------------------------

Every trial run through ``runner_api.run`` produces a normalized
:class:`~babylon.engine.optimization.backends.types.Result`. From that,
:func:`~babylon.engine.optimization.reproducibility.build_repro_record`
builds a frozen
:class:`~babylon.engine.optimization.reproducibility.ReproRecord` — the
minimal receipt needed to replay a trial: ``defines_hash`` (a SHA-256 over
the trial's canonical ``GameDefines.model_dump()`` — the same hash the
headless runner's ``_defines_hash`` computes; see
:doc:`/reference/determinism-contract` for the canonical serialization),
``rng_seed``, ``backend``, ``scope_name``, ``max_ticks``, and the outcome
summary (``ticks_survived``, ``outcome``, ``terminal_outcome``). Two trials
with the same ``defines_hash`` and ``rng_seed`` ran against byte-identical
coefficients and should reproduce byte-identically per Constitution III.7.
Keep the CSV/JSON artifacts a sweep produces alongside their ``ReproRecord``
if you need to defend a result later.

Determinism: a sweep is *expected* to move ``defines_hash``
--------------------------------------------------------------

This is the one gotcha every new user of this package hits: **do not**
validate a sweep or optimization trial against ``tests/baselines/*``.

Those baselines exist to catch *unintentional* drift in the default
configuration — ``mise run qa:regression`` re-runs 5 fixed scenarios and
demands byte-identical output against them. A parameter sweep does the
opposite on purpose: it deliberately varies ``GameDefines``, so its
``defines_hash`` is *supposed* to differ from the baseline's, trial by
trial, across every point on the swept range. A sweep trial diverging from
``tests/baselines/*`` is not a regression — it is the sweep working. If you
want to confirm the *no-override* path is still byte-identical (i.e. that
this package hasn't perturbed default behavior), that is exactly what
``mise run qa:regression`` is for; run it directly rather than comparing
sweep output to those files.

See Also
--------

- :doc:`modding-defines` — the ``GameDefines``/``defines.yaml`` schema these
  tools override.
- :doc:`parameter-tuning` — manual, single-run parameter adjustment.
- :doc:`analyze-parameter-sensitivity` — the earlier single-parameter
  ``tools/parameter_analysis.py`` trace/sweep workflow and result
  interpretation.
- :doc:`/reference/determinism-contract` — the canonical ``defines_hash``
  serialization contract and Constitution III.7.
- :py:mod:`babylon.engine.optimization` — package API reference.
