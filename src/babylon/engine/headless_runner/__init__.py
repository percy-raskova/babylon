"""Headless Postgres-backed simulation runner package.

The canonical CLI surface for end-to-end Babylon simulations. A single
``run()`` entry point bootstraps Postgres, hydrates hex state, executes the
tick loop, and emits an LLM-parseable artifact bundle (``trace.csv`` +
``summary.json`` + ``manifest.json``).

Spec: 064-headless-sim-runner
"""

from babylon.engine.headless_runner.runner import run

__all__ = ["run"]
