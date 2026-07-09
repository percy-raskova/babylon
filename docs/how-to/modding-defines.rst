Mod Game Parameters (defines.yaml)
==================================

Babylon exposes every tunable game coefficient in a single, documented,
player-editable file — the way Paradox grand-strategy games expose their rules,
but in YAML rather than INI. This guide shows how to change the game's balance
without touching any code.

The canonical file
------------------

All coefficients live in:

``src/babylon/data/defines.yaml``

Each value carries an inline comment giving its meaning and valid range, for
example::

   economy:
     extraction_efficiency: 0.8  # α: imperial extraction capacity (>= 0.0, <= 1.0)
     comprador_cut: 0.9          # fraction kept by the comprador class (>= 0.0, <= 1.0)

The file is grouped into categories (``economy``, ``survival``, ``territory``,
``consciousness``, ...) that mirror the :class:`~babylon.config.defines.GameDefines`
schema.

How the game loads it
---------------------

``GameDefines.load_default()`` reads ``defines.yaml`` when it is present and
applies your values; if the file is absent it falls back to the compiled schema
defaults. The shipped ``defines.yaml`` is generated *from* those defaults, so a
fresh checkout plays identically whether or not the file exists.

Change a parameter
------------------

1. Open ``src/babylon/data/defines.yaml``.
2. Edit any value. Keep the key names, structure, and value types intact — the
   inline comment tells you the valid range. A value outside its range is
   rejected by validation at load time.
3. Restart the simulation. Your values take effect on the next run.

Partial overrides are allowed: a category you omit falls back to its schema
defaults, and a field you omit within a present category falls back to that
field's default.

Revert to the shipped defaults
------------------------------

Either delete the file, or regenerate it from the schema::

   poetry run python tools/generate_defines_config.py

Regeneration is also required (and enforced in CI) whenever the schema itself
changes — a new coefficient, a changed default, or an updated description. To
check whether the committed file is in sync::

   poetry run python tools/generate_defines_config.py --check

Why not edit the schema directly?
---------------------------------

The Python schema in :mod:`babylon.config.defines` defines *what* parameters
exist, their types, and their valid ranges. ``defines.yaml`` holds the *values*.
Editing the YAML is the supported, code-free way to rebalance the game; editing
the schema is a development change that requires regenerating the YAML and
re-running the regression suite.

See Also
--------

- :doc:`/how-to/parameter-tuning` — sweeps and sensitivity analysis over these
  same parameters.
- :mod:`babylon.config.defines` — the schema the file is generated from.
