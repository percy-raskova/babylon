Run Parameter Sweeps and Optimization
======================================

This guide shows how to run parameter sweeps, Monte Carlo uncertainty
quantification, global sensitivity analysis, and Bayesian search over
``GameDefines`` coefficients using the
:mod:`tools.devtools.sim_analysis` package.

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

Every trial routes through :func:`tools.devtools.sim_analysis.runner_api.run`.
The in-memory backend passes the possibly swept ``GameDefines`` to
``simulation_engine.step`` on every tick. The parameter-injection and
reproducibility tests pin that path.

The four subcommands
--------------------

``sweep``, ``monte-carlo``, and ``sensitivity`` expose ``--backend
in-memory``, ``--scenario``, ``--objective {carceral,survival}``, and
``--max-ticks``. Bayesian search exposes ``--backend`` and ``--max-ticks``;
it deliberately fixes the imperial-circuit scenario and Carceral Equilibrium
objective. Run ``uv run python -m tools.devtools.sim_analysis <subcommand>
--help`` for the authoritative flag list.

sweep — 1D or 2D coefficient sweep
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sweep one coefficient across a range, or two for a grid:

.. code-block:: bash

   uv run python -m tools.devtools.sim_analysis sweep \
       --param "economy.extraction_efficiency=0.1:0.3:0.1" \
       --backend in-memory \
       --output-csv results/sweep.csv \
       --report

Add ``--param2 "economy.comprador_cut=0.5:1.0:0.1"`` for a 2D grid instead
of a 1D line. ``--report`` prints the Playable Boundary report after a 1D
sweep.

When ``--output-csv`` is present, the command also writes a sibling
``.manifest.json`` file unless ``--manifest-path`` chooses another location.
The versioned strict-JSON manifest stores the base defines and hash, exact
native-typed values or grid, run configuration, objective identity, every
result, and its verification receipt. Sweep campaigns reject more than 2,048
evaluations or five million aggregate simulated ticks before the first trial.

Via mise:

.. code-block:: bash

   mise run analysis:sweep                       # 1D default range, --report enabled
   mise run analysis:sweep-custom -- 0.1 0.9 0.1 # custom start/end/step
   mise run analysis:landscape                    # 2D grid, 100-year trials

monte-carlo — uncertainty quantification
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Run N stochastic replications of one fixed configuration to see outcome
variance under a shared seed-derivation scheme:

.. code-block:: bash

   uv run python -m tools.devtools.sim_analysis monte-carlo \
       --n-samples 100 \
       --seed 42 \
       --param "economy.extraction_efficiency=0.5" \
       --backend in-memory \
       --csv-path results/monte_carlo.csv

``--param`` is repeatable here (fixed overrides, not ranges — use
``PATH=VALUE``, not ``PATH=START:END:STEP``).
The command also writes ``results/monte_carlo.manifest.json`` by default.
That strict-JSON manifest stores the full validated ``GameDefines`` payload
once, every derived sample seed and outcome, the overrides, and the matching
verification receipts. Use ``--manifest-path`` to choose another location.

Via mise:

.. code-block:: bash

   mise run analysis:monte-carlo                # defaults: 100 samples
   mise run analysis:monte-carlo -- 500 42      # 500 samples, seed 42

sensitivity — Morris/Sobol global sensitivity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Rank coefficients by influence on the objective, via SALib:

.. code-block:: bash

   uv run python -m tools.devtools.sim_analysis sensitivity \
       --method morris \
       --trajectories 8 \
       --morris-output results/morris.json

   uv run python -m tools.devtools.sim_analysis sensitivity \
       --method sobol \
       --samples 64 \
       --sobol-output results/sobol.json

Omitting ``--param-names`` selects eight curated Carceral Equilibrium drivers,
not every numeric field in ``GameDefines``. ``--method both`` screens that
explicit set with Morris and promotes only the top four ``mu*`` parameters to
Sobol. With the defaults this means 72 Morris evaluations and 640 Sobol
evaluations, each capped at 2,600 ticks. A direct Sobol run over all eight uses
1,152 evaluations.

Use ``--param-names
"economy.extraction_efficiency,economy.comprador_cut"`` to select a different
explicit subset. The command rejects more than 16 parameters, more than 2,048
evaluations, more than five million evaluation-ticks, or an estimated artifact
larger than 8 MiB before sampling. Requires the dev dependency group (SALib) —
without it, the subcommand exits with a clear message rather than an import
traceback.

Via mise:

.. code-block:: bash

   mise run analysis:morris       # Morris only, fast screening
   mise run analysis:sobol        # Sobol only, slower variance decomposition
   mise run analysis:sensitivity  # Morris, then Sobol on the top four

Each ``morris.json`` or ``sobol.json`` artifact is versioned strict JSON. It
stores the base defines once, declared and effective bounds, the exact SALib
sample vector, the native typed overrides actually executed, objective output,
seed, and verification receipt for every trial. Integer parameters are sampled
on SALib's continuous design and deterministically rounded to their nearest
valid native integer; both values are retained in the artifact.

bayesian — Optuna TPE + Hyperband search
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Search for coefficients maximizing the Carceral Equilibrium objective:

.. code-block:: bash

   uv run python -m tools.devtools.sim_analysis bayesian \
       --n-trials 100 \
       --study-name babylon_carceral \
       --storage sqlite:///optuna.db

Resume a study by reusing ``--study-name``/``--storage`` only with the same
persisted experiment fingerprint. Inspect the best trial so far without
running new ones via ``--show-best``; inspection enforces that fingerprint as
well. Restrict the search space with ``--categories
"economy,consciousness"`` (default: ``TUNING_CATEGORIES``). Parameter
identities are full ``category.field`` paths so same-named fields cannot
collide. Start a new study name or storage for any fingerprint mismatch,
including a database created by the pre-consolidation leaf-name
implementation.
Optuna persists completed trials but not sampler RNG state, so a resumed study
is durable without claiming the exact proposal order of one uninterrupted
process. Requires the dev dependency group (Optuna).

Via mise:

.. code-block:: bash

   mise run analysis:optuna -- 200 my_study   # trials, study name
   mise run analysis:dashboard                # uv-managed Optuna Dashboard

The ``--param``/``--param2`` grammar
--------------------------------------

Both ``sweep`` and ``monte-carlo`` parse parameter flags through the same
grammar (:mod:`tools.devtools.sim_analysis.ranges`), which unifies what
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

Integer fields retain native integer values. Their override and range
components must be mathematically integral; fractional values, non-finite
numbers, reversed ranges, non-advancing steps, and ranges above one million
points fail before a trial runs. Pydantic then revalidates the complete rebuilt
``GameDefines`` value, including cross-field invariants and strict open bounds.

Reproducibility records
------------------------

Every trial run through ``runner_api.run`` produces a normalized
:class:`~tools.devtools.sim_analysis.backends.types.Result`. From that,
:func:`~tools.devtools.sim_analysis.reproducibility.build_repro_record`
builds a frozen
:class:`~tools.devtools.sim_analysis.reproducibility.ReproRecord` — a
verification receipt containing ``defines_hash`` (a SHA-256 over the
trial's canonical ``GameDefines.model_dump()``; see
:doc:`/reference/determinism-contract` for the canonical serialization),
``rng_seed``, ``backend``, ``scenario``, ``max_ticks``, and the outcome
summary (``ticks_survived``, ``outcome``, ``terminal_outcome``). A replay
identity requires the same defines hash, RNG seed, backend, scenario, maximum
tick, and source revision; with all of those fixed, the trial should reproduce
byte-identically per Constitution III.7.
The hash cannot reconstruct those coefficients. A durable replay therefore
also needs the exact base-defines payload or overrides and the source
revision. Keep the parent CSV/JSON artifact with its verification records;
the Monte Carlo JSON manifest stores the full validated defines payload once
alongside every derived sample seed. Sensitivity phase artifacts store the
base defines plus each sampled vector and native override. These artifacts
still depend on the same source revision; a coefficient payload cannot replay
different simulation code.

Determinism: a sweep is *expected* to move ``defines_hash``
--------------------------------------------------------------

This is the one gotcha every new user of this package hits: **do not**
validate a sweep or optimization trial against ``tests/baselines/*``.

Those baselines exist to catch *unintentional* drift in the default
configuration — ``mise run qa:regression`` re-runs 12 fixed scenarios and
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
- :py:mod:`tools.devtools.sim_analysis` — development-tool API reference.
