Run Parameter Sweeps and Optimization
======================================

This guide shows how to run parameter sweeps, Monte Carlo uncertainty
quantification, global sensitivity analysis, and Bayesian search over
``GameDefines`` coefficients using the
:mod:`babylon.engine.optimization` package.

.. note::

   This guide covers the intentional in-memory Python periphery for systematic
   sweeps and search: ``sweep``, ``monte-carlo``, ``sensitivity``, and
   ``bayesian``. It does not exercise Rust persistence authority.

Prerequisites
-------------

- Familiarity with :doc:`modding-defines` (the ``GameDefines`` schema these
  tools override).
- The dev dependency group installed for ``sensitivity`` (SALib) and
  ``bayesian`` (Optuna): ``uv sync``.

The retained in-memory backend
------------------------------

The optimizer runs the frozen Python engine in-process with no database.
Select ``imperial_circuit`` or ``two_node`` with ``--scenario``. This is an
intentional analysis periphery and does not exercise Rust persistence or make
a claim about the playable runtime.

Defines now actually reach the simulation
------------------------------------------

Every trial routes through :func:`babylon.engine.optimization.runner_api.run`.
The in-memory backend passes the possibly swept ``GameDefines`` to
``simulation_engine.step`` on every tick. The parameter-injection and
reproducibility tests pin that path.

The four subcommands
---------------------

All four share ``--backend in-memory``, ``--scenario``,
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

   uv run python -m babylon.engine.optimization sweep \
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

   uv run python -m babylon.engine.optimization monte-carlo \
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

   uv run python -m babylon.engine.optimization sensitivity \
       --method morris \
       --trajectories 10 \
       --morris-output results/morris.json

   uv run python -m babylon.engine.optimization sensitivity \
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

   uv run python -m babylon.engine.optimization bayesian \
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
the trial's canonical ``GameDefines.model_dump()``; see
:doc:`/reference/determinism-contract` for the canonical serialization),
``rng_seed``, ``backend``, ``scenario``, ``max_ticks``, and the outcome
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
- :doc:`analyze-parameter-sensitivity` — current sensitivity commands and the
  authority boundary for their results.
- :doc:`/reference/determinism-contract` — the canonical ``defines_hash``
  serialization contract and Constitution III.7.
- :py:mod:`babylon.engine.optimization` — package API reference.
